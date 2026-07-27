import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Profile, WardrobeItem
from ..schemas import RecommendRequest
from .guardrail import filter_candidates
from .history import get_recent_item_ids, get_recent_outfits, record_outfit
from .stylist import propose
from .validator import validate_looks
from .weather import get_weather


def _season(temp: float) -> str:
    if temp >= 25:
        return "summer"
    if temp <= 12:
        return "winter"
    return "spring_autumn"


def recommend(db: Session, request: RecommendRequest) -> dict:
    profile = db.get(Profile, settings.user_id)
    city = request.city or (profile.city if profile else None)
    weather = get_weather(
        city, latitude=request.latitude, longitude=request.longitude
    )
    items = list(
        db.scalars(select(WardrobeItem).where(WardrobeItem.user_id == settings.user_id))
    )
    candidates = filter_candidates(
        items,
        season=_season(weather.temp),
        locked_ids=set(request.locked_item_ids),
        recent_item_ids=get_recent_item_ids(db, settings.user_id),
    )
    categories = {item.id: item.category or "" for item in candidates}
    if not {"top", "bottom", "shoes"} <= {
        {"shirt": "top", "t-shirt": "top", "pants": "bottom", "jeans": "bottom",
         "shoe": "shoes", "sneakers": "shoes"}.get(value, value)
        for value in categories.values()
    }:
        raise ValueError("已确认衣橱不足：至少需要上装、下装和鞋履")
    recent = get_recent_outfits(db, settings.user_id)
    recent_looks = [json.loads(outfit.item_ids_json) for outfit in recent]
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
        )
        ok, error = validate_looks(looks, categories)
        if ok:
            break
    else:
        raise ValueError(f"造型师结果校验失败：{error}")
    by_id = {item.id: item for item in candidates}
    result = {"weather": weather.model_dump()}
    for look in looks:
        history = record_outfit(
            db,
            settings.user_id,
            look,
            occasion=request.occasion,
            mood=request.mood,
            weather_summary=weather.condition,
            temp=weather.temp,
        )
        result[look.tier] = {
            "history_id": history.id,
            "items": [
                {
                    "id": item_id,
                    "name": by_id[item_id].name,
                    "category": by_id[item_id].category,
                    "image_url": f"/media/{by_id[item_id].image_path.split('/')[-1]}",
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
