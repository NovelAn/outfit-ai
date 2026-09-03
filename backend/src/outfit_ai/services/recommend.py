import json
from datetime import date, datetime
from math import asin, cos, radians, sin, sqrt
from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Profile, WardrobeItem
from ..schemas import RecommendRequest
from .background import display_image_path
from .categories import canonical_category
from .guardrail import filter_candidates, select_coverage_targets
from .history import (
    get_item_usage_stats,
    get_latest_recommendation_set,
    get_prepared_outfits,
    get_recent_item_ids,
    get_recent_look_keys,
    get_recent_outfits,
    record_outfit,
)
from .llm import require_api_key
from .profile_state import decode_profile_state, save_last_location
from .style_references import get_reference_analyses
from .stylist import propose, propose_tier
from .validator import validate_look, validate_looks
from .weather import get_weather


def _season(temp: float) -> str:
    if temp >= 25:
        return "summer"
    if temp <= 12:
        return "winter"
    return "spring_autumn"


def _haversine_km(
    latitude_a: float, longitude_a: float, latitude_b: float, longitude_b: float
) -> float:
    latitude_delta = radians(latitude_b - latitude_a)
    longitude_delta = radians(longitude_b - longitude_a)
    distance = sin(latitude_delta / 2) ** 2 + cos(radians(latitude_a)) * cos(
        radians(latitude_b)
    ) * sin(longitude_delta / 2) ** 2
    return 6371 * 2 * asin(sqrt(distance))


def _weather_context(weather: object) -> dict:
    return json.loads(json.dumps(weather.model_dump(), default=str))


def _effective_coordinates(
    profile: Profile | None, request: RecommendRequest
) -> tuple[float | None, float | None]:
    if request.latitude is not None or request.longitude is not None:
        return request.latitude, request.longitude
    state = decode_profile_state(profile.learned_from_feedback_json) if profile else {}
    location = state.get("last_location") or {}
    latitude, longitude = location.get("latitude"), location.get("longitude")
    if (
        not isinstance(latitude, int | float)
        or isinstance(latitude, bool)
        or not isinstance(longitude, int | float)
        or isinstance(longitude, bool)
        or not -90 <= latitude <= 90
        or not -180 <= longitude <= 180
    ):
        return None, None
    return latitude, longitude


def _prepared_matches(
    prepared: list, latitude: float | None, longitude: float | None, weather: object
) -> bool:
    if latitude is None or longitude is None:
        return False
    weather_context = _weather_context(weather)
    for history in prepared:
        try:
            context = json.loads(history.context_json or "{}")
            prepared_weather = context["weather"]
            if not isinstance(prepared_weather, dict):
                return False
            prepared_temp = prepared_weather.get("temp")
            prepared_rain = prepared_weather.get("precipitation_probability_max", 0)
            distance = _haversine_km(
                context["latitude"],
                context["longitude"],
                latitude,
                longitude,
            )
        except (KeyError, TypeError, ValueError):
            return False
        if (
            not isinstance(prepared_temp, int | float)
            or isinstance(prepared_temp, bool)
            or not isinstance(prepared_rain, int | float)
            or isinstance(prepared_rain, bool)
        ):
            return False
        if (
            distance > 20
            or _season(prepared_temp) != _season(weather.temp)
            or (prepared_rain >= 50)
            != (weather_context.get("precipitation_probability_max", 0) >= 50)
        ):
            return False
    return True


def _card(history: object, items: dict[str, WardrobeItem]) -> dict | None:
    try:
        item_ids = json.loads(history.item_ids_json)
        context = json.loads(history.context_json or "{}")
        cards = [
            {
                "id": item_id,
                "name": items[item_id].name,
                "category": items[item_id].category,
                "image_url": f"/media/{display_image_path(items[item_id]).name}",
                "primary_color": items[item_id].primary_color,
            }
            for item_id in item_ids
        ]
    except (KeyError, TypeError, ValueError):
        return None
    return {
        "history_id": history.id,
        "items": cards,
        "reason": history.reason,
        "weather_fit": context.get("weather_fit", ""),
        "occasion_fit": context.get("occasion_fit", ""),
        "pick_mode": history.pick_mode,
    }


def _reuse_same_day(
    db: Session, items: dict[str, WardrobeItem], local_date: date
) -> dict | None:
    looks = get_latest_recommendation_set(
        db, settings.user_id, local_date, prepared=False
    )
    if not looks:
        return None
    cards = {history.pick_mode: _card(history, items) for history in looks}
    weather = _history_weather(looks[0])
    if weather is None or any(card is None for card in cards.values()):
        return None
    return {"weather": weather, **cards}


def _history_weather(history: object) -> dict | None:
    try:
        context = json.loads(history.context_json or "{}")
        weather = context.get("weather")
    except (AttributeError, TypeError, ValueError):
        return None
    return weather if isinstance(weather, dict) else None


def _request_local_date(profile: Profile | None, request: RecommendRequest) -> date:
    if request.local_date is not None:
        return request.local_date
    state = decode_profile_state(profile.learned_from_feedback_json) if profile else {}
    timezone = (state.get("last_location") or {}).get("timezone")
    if isinstance(timezone, str):
        try:
            return datetime.now(ZoneInfo(timezone)).date()
        except ZoneInfoNotFoundError:
            pass
    return date.today()


def _reuse_prepared(
    db: Session,
    latitude: float | None,
    longitude: float | None,
    weather: object,
    items: dict[str, WardrobeItem],
) -> dict | None:
    prepared = get_prepared_outfits(
        db, settings.user_id, getattr(weather, "local_date", date.today())
    )
    if not prepared or not _prepared_matches(prepared, latitude, longitude, weather):
        return None
    cards = {history.pick_mode: _card(history, items) for history in prepared}
    if any(card is None for card in cards.values()):
        return None
    for history in prepared:
        if history.action == "prepared":
            history.action = "shown"
    return {"weather": weather.model_dump(), **cards}


def recommend(
    db: Session, request: RecommendRequest, *, history_action: str = "shown"
) -> dict:
    profile = db.get(Profile, settings.user_id)
    items = list(
        db.scalars(select(WardrobeItem).where(WardrobeItem.user_id == settings.user_id))
    )
    if not request.force_refresh and history_action != "prepared":
        reused = _reuse_same_day(
            db, {item.id: item for item in items}, _request_local_date(profile, request)
        )
        if reused is not None:
            return reused
    local_date = _request_local_date(profile, request)
    current_set = None
    if request.force_refresh and request.refresh_tier:
        current_set = get_latest_recommendation_set(
            db, settings.user_id, local_date, prepared=False
        ) or get_latest_recommendation_set(db, settings.user_id, local_date, prepared=True)
        if current_set is None:
            raise ValueError("当前推荐组不可用，请先重新加载今日推荐")
    latitude, longitude = _effective_coordinates(profile, request)
    city = request.city or (profile.city if profile else None)
    weather = get_weather(
        city, latitude=request.latitude, longitude=request.longitude
    )
    if profile is None:
        profile = Profile(user_id=settings.user_id)
        db.add(profile)
    save_last_location(
        profile,
        latitude=latitude,
        longitude=longitude,
        city=getattr(weather, "city", None) or city,
        timezone=getattr(weather, "timezone", ""),
        updated_at=datetime.now().astimezone().isoformat(),
    )
    if not request.force_refresh and history_action != "prepared":
        reused = _reuse_prepared(
            db, latitude, longitude, weather, {item.id: item for item in items}
        )
        if reused is not None:
            db.commit()
            return reused
    require_api_key()
    recommendation_date = getattr(weather, "local_date", local_date)
    usage_stats = get_item_usage_stats(
        db,
        settings.user_id,
        local_date=recommendation_date,
    )
    candidates = filter_candidates(
        items,
        season=request.season or _season(weather.temp),
        locked_ids=set(request.locked_item_ids),
        recent_item_ids=get_recent_item_ids(db, settings.user_id, skip_shoes=False),
        usage_stats=usage_stats,
    )
    unavailable_locked = set(request.locked_item_ids) - {item.id for item in candidates}
    if unavailable_locked:
        raise ValueError(
            f"锁定单品不可用: {', '.join(sorted(unavailable_locked))}"
        )
    categories = {item.id: item.category or "" for item in candidates}
    if not {"top", "bottom", "shoes"} <= {
        canonical_category(value) for value in categories.values()
    }:
        raise ValueError("已确认衣橱不足：至少需要上装、下装和鞋履")
    recent = get_recent_outfits(db, settings.user_id)
    recent_looks = []
    for outfit in recent:
        if outfit.action == "prepared":
            continue
        try:
            item_ids = json.loads(outfit.item_ids_json or "[]")
        except (TypeError, ValueError):
            continue
        if isinstance(item_ids, list):
            recent_looks.append([item_id for item_id in item_ids if isinstance(item_id, str)])
    recent_look_keys = get_recent_look_keys(
        db,
        settings.user_id,
        local_date=recommendation_date,
    )
    coverage_target_ids = select_coverage_targets(
        candidates,
        usage_stats,
        locked_ids=set(request.locked_item_ids),
        count=2,
    )
    coverage_targets = {
        tier: item_id
        for tier, item_id in zip(("fresh", "stretch"), coverage_target_ids, strict=False)
    }
    references = get_reference_analyses(db, request.reference_ids)
    scene = request.scene or request.occasion

    if request.force_refresh and request.refresh_tier and current_set:
        base_items = {item.id: item for item in items}
        base_cards = {history.pick_mode: _card(history, base_items) for history in current_set}
        if all(base_cards.get(tier) is not None for tier in ("safe", "fresh", "stretch")):
            occupied_ids = {
                item["id"]
                for tier, card in base_cards.items()
                if tier != request.refresh_tier
                for item in card["items"]
            }
            refresh_targets = select_coverage_targets(
                candidates,
                usage_stats,
                locked_ids=set(request.locked_item_ids),
                occupied_ids=occupied_ids,
                count=1,
            )
            refresh_coverage_targets = (
                {request.refresh_tier: refresh_targets[0]} if refresh_targets else {}
            )
            error = ""
            for _ in range(2):
                target = propose_tier(
                    candidates,
                    profile,
                    weather.model_dump(),
                    request.occasion,
                    request.mood,
                    recent_looks,
                    set(request.locked_item_ids),
                    request.refresh_tier,
                    error,
                    references=references,
                    style_note=request.style_note,
                    season=request.season or _season(weather.temp),
                    scene=scene,
                    usage_stats=usage_stats,
                    coverage_targets=refresh_coverage_targets,
                )
                if target.tier != request.refresh_tier:
                    ok, error = False, f"返回 tier 必须为 {request.refresh_tier}"
                else:
                    ok, error = validate_look(
                        target,
                        categories,
                        locked_ids=set(request.locked_item_ids),
                        coverage_target=refresh_coverage_targets.get(request.refresh_tier),
                    )
                if ok:
                    break
            else:
                raise ValueError(f"造型师结果校验失败：{error}")
            existing_set_id = json.loads(current_set[0].context_json or "{}").get(
                "recommendation_set_id"
            )
            if not isinstance(existing_set_id, str) or not existing_set_id:
                raise ValueError("当前推荐缺少 recommendation_set_id，无法单卡刷新")
            context_base = {
                "latitude": round(latitude, 3) if latitude is not None else None,
                "longitude": round(longitude, 3) if longitude is not None else None,
                "weather": _weather_context(weather),
                "local_date": getattr(weather, "local_date", date.today()).isoformat(),
                "prepared_at": datetime.now().astimezone().isoformat(),
                "prepared": False,
                "recommendation_set_created_at": datetime.now().astimezone().isoformat(),
            }
            history = record_outfit(
                db,
                settings.user_id,
                target,
                occasion=scene,
                mood=request.mood,
                weather_summary=weather.condition,
                temp=weather.temp,
                action=history_action,
                context={
                    **context_base,
                    "weather_fit": target.weather_fit,
                    "occasion_fit": target.occasion_fit,
                },
                recommendation_set_id=existing_set_id,
            )
            history.date = getattr(weather, "local_date", local_date)
            result = {"weather": weather.model_dump(), **base_cards}
            result[target.tier] = _card(history, base_items)
            db.commit()
            return result

    error = ""
    for _ in range(2):
        looks = propose(
            candidates,
            profile,
            weather.model_dump(),
            request.occasion,
            request.mood,
            recent_looks,
            set(request.locked_item_ids),
            error,
            references=references,
            style_note=request.style_note,
            season=request.season or _season(weather.temp),
            scene=scene,
            usage_stats=usage_stats,
            coverage_targets=coverage_targets,
        )
        ok, error = validate_looks(
            looks,
            categories,
            locked_ids=set(request.locked_item_ids),
            coverage_targets=coverage_targets,
            recent_look_keys=recent_look_keys,
        )
        if ok:
            break
    else:
        raise ValueError(f"造型师结果校验失败：{error}")
    by_id = {item.id: item for item in candidates}
    context_base = {
        "latitude": round(latitude, 3) if latitude is not None else None,
        "longitude": round(longitude, 3) if longitude is not None else None,
        "weather": _weather_context(weather),
        "local_date": getattr(weather, "local_date", date.today()).isoformat(),
        "prepared_at": datetime.now().astimezone().isoformat(),
        "prepared": history_action == "prepared",
        "recommendation_set_created_at": datetime.now().astimezone().isoformat(),
    }
    recommendation_set_id = uuid4().hex
    result = {"weather": weather.model_dump()}
    for look in looks:
        history = record_outfit(
            db,
            settings.user_id,
            look,
            occasion=scene,
            mood=request.mood,
            weather_summary=weather.condition,
            temp=weather.temp,
            action=history_action,
            context={
                **context_base,
                "weather_fit": look.weather_fit,
                "occasion_fit": look.occasion_fit,
            },
            recommendation_set_id=recommendation_set_id,
        )
        history.date = getattr(weather, "local_date", date.today())
        result[look.tier] = {
            "history_id": history.id,
            "items": [
                {
                    "id": item_id,
                    "name": by_id[item_id].name,
                    "category": by_id[item_id].category,
                    "image_url": f"/media/{display_image_path(by_id[item_id]).name}",
                    "primary_color": by_id[item_id].primary_color,
                }
                for item_id in look.item_ids
            ],
            "reason": look.reason,
            "weather_fit": look.weather_fit,
            "occasion_fit": look.occasion_fit,
            "pick_mode": look.tier,
        }
    db.commit()
    return result


def _self_check() -> None:
    assert _season(30) == "summer"
    assert _season(5) == "winter"
    assert _season(18) == "spring_autumn"


if __name__ == "__main__":
    _self_check()
    print("recommend self-check passed")
