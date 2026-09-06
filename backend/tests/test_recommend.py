import json
from datetime import date, datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from outfit_ai.config import settings
from outfit_ai.db import Base, get_db
from outfit_ai.main import app
from outfit_ai.models import OutfitHistory, StyleReference, WardrobeItem
from outfit_ai.schemas import ProposedLook, RecommendRequest
from outfit_ai.services import recommend as recommend_service
from outfit_ai.services.llm import LLMResponseError
from outfit_ai.services.profile_state import decode_profile_state, encode_profile_state


def _item(item_id: str, category: str) -> WardrobeItem:
    return WardrobeItem(
        id=item_id,
        user_id="local",
        name=item_id,
        category=category,
        primary_color="黑色",
        image_path=f"/tmp/{item_id}.jpg",
        status="ready",
        confirmed_by_user=True,
        added_at=datetime.now(),
    )


def _weather(*, temp: float = 20, rain_chance: int = 20) -> SimpleNamespace:
    payload = {
        "temp": temp,
        "condition": "晴",
        "city": "上海",
        "local_date": date(2026, 7, 31),
        "timezone": "Asia/Shanghai",
        "precipitation_probability_max": rain_chance,
    }
    return SimpleNamespace(**payload, model_dump=lambda: payload)


def _prepared_rows(*, latitude: float = 31.230, longitude: float = 121.474) -> list[OutfitHistory]:
    return [
        OutfitHistory(
            id=f"prepared-{tier}",
            user_id="local",
            date=date(2026, 7, 31),
            occasion="日常",
            weather_summary="晴",
            temp=20,
            item_ids_json=json.dumps([f"top-{index}", f"bottom-{index}", f"shoes-{index}"]),
            pick_mode=tier,
            reason=f"{tier} reason",
            action="prepared",
            context_json=json.dumps(
                {
                    "latitude": latitude,
                    "longitude": longitude,
                    "weather": {"temp": 20, "precipitation_probability_max": 20},
                    "local_date": "2026-07-31",
                    "prepared_at": "2026-07-31T06:30:00+08:00",
                    "prepared": True,
                    "weather_fit": "适合",
                    "occasion_fit": "日常",
                },
                ensure_ascii=False,
            ),
        )
        for index, tier in enumerate(("safe", "fresh", "stretch"), 1)
    ]


def _looks(coverage_targets: dict[str, str] | None = None) -> list[ProposedLook]:
    if coverage_targets:
        targets = {
            "fresh": coverage_targets.get("fresh", "top-2"),
            "stretch": coverage_targets.get("stretch", "bottom-2"),
        }
        pools = {
            category: [f"{category}-{index}" for index in (1, 2, 3)]
            for category in ("top", "bottom", "shoes")
        }
        used: set[str] = set()

        def build(tier: str, target: str | None = None) -> ProposedLook:
            item_ids: list[str] = []
            for category, pool in pools.items():
                if target and target.startswith(f"{category}-"):
                    item_id = target
                else:
                    item_id = next(
                        item_id
                        for item_id in pool
                        if item_id not in used and item_id not in targets.values()
                    )
                item_ids.append(item_id)
            used.update(item_ids)
            return ProposedLook(
                tier=tier,
                item_ids=item_ids,
                reason=f"{tier} reason",
                weather_fit="适合",
                occasion_fit="日常",
            )

        return [
            build("safe"),
            build("fresh", targets["fresh"]),
            build("stretch", targets["stretch"]),
        ]
    return [
        ProposedLook(
            tier=tier,
            item_ids=[f"top-{index}", f"bottom-{index}", f"shoes-{index}"],
            reason=f"{tier} reason",
            weather_fit="适合",
            occasion_fit="日常",
        )
        for index, tier in enumerate(("safe", "fresh", "stretch"), 1)
    ]


def _recommendation_items() -> list[WardrobeItem]:
    return [
        _item(f"{category}-{index}", category)
        for category in ("top", "bottom", "shoes")
        for index in range(1, 4)
    ]


def _same_day_set_rows(
    set_id: str, *, created_at: str, local_date: date | None = None
) -> list[OutfitHistory]:
    return [
        OutfitHistory(
            id=f"{set_id}-{tier}",
            user_id="local",
            date=local_date or date.today(),
            item_ids_json=json.dumps([f"top-{index}", f"bottom-{index}", f"shoes-{index}"]),
            pick_mode=tier,
            action="shown",
            context_json=json.dumps(
                {
                    "recommendation_set_id": set_id,
                    "recommendation_set_created_at": created_at,
                    "weather": _weather().model_dump(),
                    "weather_fit": "适合",
                    "occasion_fit": "日常",
                },
                default=str,
            ),
        )
        for index, tier in enumerate(("safe", "fresh", "stretch"), 1)
    ]


def test_haversine_shanghai_to_suzhou_exceeds_prepared_reuse_radius() -> None:
    assert recommend_service._haversine_km(31.230, 121.474, 31.299, 120.585) > 20


def test_recommend_request_limits_refresh_tier() -> None:
    assert RecommendRequest(refresh_tier="stretch", force_refresh=True).refresh_tier == "stretch"
    with pytest.raises(ValueError):
        RecommendRequest(refresh_tier="unknown")
    with pytest.raises(ValueError, match="force_refresh"):
        RecommendRequest(refresh_tier="safe")


def test_normal_request_reuses_latest_complete_same_day_set_for_manual_city(monkeypatch) -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    monkeypatch.setattr(
        recommend_service,
        "get_weather",
        lambda *args, **kwargs: pytest.fail("same-day reuse must precede weather matching"),
    )
    monkeypatch.setattr(
        recommend_service,
        "require_api_key",
        lambda: pytest.fail("same-day reuse must precede API-key validation"),
    )
    monkeypatch.setattr(
        recommend_service,
        "propose",
        lambda *args, **kwargs: pytest.fail("same-day set should be reused"),
    )
    with Session(engine) as db:
        db.add_all(
            _recommendation_items()
            + _same_day_set_rows("older-set", created_at="2026-07-31T06:30:00+08:00")
            + _same_day_set_rows("latest-set", created_at="2026-07-31T08:30:00+08:00")
        )
        db.commit()

        result = recommend_service.recommend(db, RecommendRequest(city="上海"))

        assert [result[tier]["history_id"] for tier in ("safe", "fresh", "stretch")] == [
            "latest-set-safe",
            "latest-set-fresh",
            "latest-set-stretch",
        ]


def test_force_refresh_creates_a_new_recommendation_set(monkeypatch) -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    monkeypatch.setattr(recommend_service, "get_weather", lambda *args, **kwargs: _weather())
    monkeypatch.setattr(recommend_service, "require_api_key", lambda: None)
    monkeypatch.setattr(recommend_service, "get_recent_item_ids", lambda *args, **kwargs: set())
    monkeypatch.setattr(
        recommend_service,
        "propose",
        lambda *args, **kwargs: _looks(kwargs.get("coverage_targets")),
    )
    with Session(engine) as db:
        db.add_all(
            _recommendation_items()
            + _same_day_set_rows("old-set", created_at="2026-07-31T06:30:00+08:00")
        )
        db.commit()

        result = recommend_service.recommend(db, RecommendRequest(city="上海", force_refresh=True))
        refreshed_set_ids = {
            json.loads(db.get(OutfitHistory, result[tier]["history_id"]).context_json)[
                "recommendation_set_id"
            ]
            for tier in ("safe", "fresh", "stretch")
        }

        assert refreshed_set_ids.isdisjoint({"old-set"})
        assert len(refreshed_set_ids) == 1


def test_refresh_tier_generates_only_target_and_keeps_other_history(monkeypatch) -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    weather = SimpleNamespace(
        temp=20,
        condition="晴",
        city="上海",
        local_date=date.today(),
        timezone="Asia/Shanghai",
        model_dump=lambda: {
            "temp": 20,
            "condition": "晴",
            "city": "上海",
            "local_date": date.today(),
            "timezone": "Asia/Shanghai",
        },
    )
    target = ProposedLook(
        tier="safe",
        item_ids=["top-1", "bottom-1", "shoes-1"],
        reason="换一套更利落的安全牌",
        weather_fit="适合",
        occasion_fit="日常",
    )
    monkeypatch.setattr(recommend_service, "get_weather", lambda *args, **kwargs: weather)
    monkeypatch.setattr(recommend_service, "require_api_key", lambda: None)
    monkeypatch.setattr(recommend_service, "get_recent_item_ids", lambda *args, **kwargs: set())
    monkeypatch.setattr(
        recommend_service,
        "propose",
        lambda *args, **kwargs: pytest.fail("single-tier refresh must not generate all looks"),
    )
    monkeypatch.setattr(recommend_service, "propose_tier", lambda *args, **kwargs: target)

    with Session(engine) as db:
        db.add_all(
            _recommendation_items()
            + _same_day_set_rows("current-set", created_at="2026-08-09T06:30:00+08:00")
        )
        db.commit()
        before = {
            row.pick_mode: row.id
            for row in db.scalars(select(OutfitHistory)).all()
            if row.pick_mode in {"safe", "fresh", "stretch"}
        }

        result = recommend_service.recommend(
            db,
            RecommendRequest(
                city="上海", local_date=date.today(), force_refresh=True, refresh_tier="safe"
            ),
        )

        assert result["fresh"]["history_id"] == before["fresh"]
        assert result["stretch"]["history_id"] == before["stretch"]
        assert result["safe"]["history_id"] != before["safe"]
        assert result["safe"]["items"][0]["id"] == "top-1"
        assert len(list(db.scalars(select(OutfitHistory)))) == 4


def test_refresh_tier_failure_does_not_write_history(monkeypatch) -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    monkeypatch.setattr(recommend_service, "get_weather", lambda *args, **kwargs: _weather())
    monkeypatch.setattr(recommend_service, "require_api_key", lambda: None)
    monkeypatch.setattr(recommend_service, "get_recent_item_ids", lambda *args, **kwargs: set())
    monkeypatch.setattr(
        recommend_service,
        "propose_tier",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("MiniMax unavailable")),
    )

    with Session(engine) as db:
        db.add_all(
            _recommendation_items()
            + _same_day_set_rows("current-set", created_at="2026-08-09T06:30:00+08:00")
        )
        db.commit()
        count_before = len(list(db.scalars(select(OutfitHistory))))

        with pytest.raises(RuntimeError, match="MiniMax unavailable"):
            recommend_service.recommend(
                db,
                RecommendRequest(city="上海", force_refresh=True, refresh_tier="fresh"),
            )

        assert len(list(db.scalars(select(OutfitHistory)))) == count_before


def test_refresh_tier_retries_when_model_omits_tool_call(monkeypatch) -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    weather = SimpleNamespace(
        temp=20,
        condition="晴",
        city="上海",
        local_date=date.today(),
        timezone="Asia/Shanghai",
        model_dump=lambda: {},
    )
    target = ProposedLook(
        tier="safe",
        item_ids=["top-1", "bottom-1", "shoes-1"],
        reason="换一套安全牌",
        weather_fit="适合",
        occasion_fit="日常",
    )
    calls = []

    def flaky_propose_tier(*args, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            raise LLMResponseError("造型师未返回有效的 propose_one_look 工具调用")
        return target

    monkeypatch.setattr(recommend_service, "get_weather", lambda *args, **kwargs: weather)
    monkeypatch.setattr(recommend_service, "require_api_key", lambda: None)
    monkeypatch.setattr(recommend_service, "get_recent_item_ids", lambda *args, **kwargs: set())
    monkeypatch.setattr(
        recommend_service, "propose", lambda *args, **kwargs: pytest.fail("must not generate")
    )
    monkeypatch.setattr(recommend_service, "propose_tier", flaky_propose_tier)

    with Session(engine) as db:
        db.add_all(
            _recommendation_items()
            + _same_day_set_rows("current-set", created_at="2026-08-09T06:30:00+08:00")
        )
        db.commit()

        result = recommend_service.recommend(
            db,
            RecommendRequest(
                city="上海", local_date=date.today(), force_refresh=True, refresh_tier="safe"
            ),
        )

        assert len(calls) == 2
        assert result["safe"]["items"][0]["id"] == "top-1"


def test_same_day_reuse_skips_latest_prepared_group_before_weather(monkeypatch) -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    monkeypatch.setattr(
        recommend_service,
        "get_weather",
        lambda *args, **kwargs: pytest.fail("ordinary same-day reuse must precede weather"),
    )
    monkeypatch.setattr(
        recommend_service,
        "require_api_key",
        lambda: pytest.fail("ordinary same-day reuse must precede API-key validation"),
    )
    with Session(engine) as db:
        ordinary = _same_day_set_rows("ordinary", created_at="2026-07-31T06:30:00+08:00")
        prepared = _same_day_set_rows("prepared", created_at="2026-07-31T08:30:00+08:00")
        for row in prepared:
            row.action = "prepared"
            row.context_json = json.dumps({**json.loads(row.context_json), "prepared": True})
        db.add_all(_recommendation_items() + ordinary + prepared)
        db.commit()

        result = recommend_service.recommend(db, RecommendRequest(city="上海"))

        assert [result[tier]["history_id"] for tier in ("safe", "fresh", "stretch")] == [
            "ordinary-safe",
            "ordinary-fresh",
            "ordinary-stretch",
        ]


def test_same_day_reuse_prefers_request_local_date_before_weather(monkeypatch) -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    local_date = date.today() - timedelta(days=1)
    monkeypatch.setattr(
        recommend_service,
        "get_weather",
        lambda *args, **kwargs: pytest.fail("request local date must be used before weather"),
    )
    monkeypatch.setattr(
        recommend_service,
        "require_api_key",
        lambda: pytest.fail("request local date must be used before API-key validation"),
    )
    with Session(engine) as db:
        db.add_all(
            _recommendation_items()
            + _same_day_set_rows(
                "request-local", created_at="2026-07-31T06:30:00+08:00", local_date=local_date
            )
        )
        db.commit()

        result = recommend_service.recommend(
            db, RecommendRequest(city="上海", local_date=local_date)
        )

        assert result["safe"]["history_id"] == "request-local-safe"


def test_recommend_reuses_matching_prepared_looks_without_stylist(monkeypatch) -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    monkeypatch.setattr(recommend_service, "get_weather", lambda *args, **kwargs: _weather())
    monkeypatch.setattr(
        recommend_service,
        "propose",
        lambda *args, **kwargs: pytest.fail("stylist should not be called"),
    )

    with Session(engine) as db:
        db.add_all(_recommendation_items() + _prepared_rows())
        db.commit()

        result = recommend_service.recommend(
            db,
            RecommendRequest(latitude=31.230, longitude=121.474, force_refresh=False),
        )

        assert [result[tier]["history_id"] for tier in ("safe", "fresh", "stretch")] == [
            "prepared-safe",
            "prepared-fresh",
            "prepared-stretch",
        ]
        repeated = recommend_service.recommend(
            db,
            RecommendRequest(latitude=31.230, longitude=121.474, force_refresh=False),
        )
        assert [repeated[tier]["history_id"] for tier in ("safe", "fresh", "stretch")] == [
            "prepared-safe",
            "prepared-fresh",
            "prepared-stretch",
        ]
        assert all(
            row.action == "shown"
            for row in db.scalars(select(OutfitHistory).where(OutfitHistory.id.like("prepared-%")))
        )
        location = decode_profile_state(
            db.get(recommend_service.Profile, "local").learned_from_feedback_json
        )["last_location"]
        assert (location["latitude"], location["longitude"]) == (31.23, 121.474)
        assert (location["city"], location["timezone"]) == ("上海", "Asia/Shanghai")
        assert isinstance(location["updated_at"], str)


def test_recommend_reuses_prepared_looks_with_saved_coordinates(monkeypatch) -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    weather_calls = []

    def fake_weather(city, **kwargs):
        weather_calls.append((city, kwargs))
        return _weather()

    monkeypatch.setattr(recommend_service, "get_weather", fake_weather)
    monkeypatch.setattr(
        recommend_service,
        "propose",
        lambda *args, **kwargs: pytest.fail("stylist should not be called"),
    )

    with Session(engine) as db:
        db.add_all(_recommendation_items() + _prepared_rows())
        db.add(
            recommend_service.Profile(
                user_id="local",
                city="上海",
                learned_from_feedback_json=encode_profile_state(
                    learnings=[],
                    recent_style_signals=[],
                    style_tag_preferences={},
                    last_location={"latitude": 31.23, "longitude": 121.474},
                ),
            )
        )
        db.commit()

        result = recommend_service.recommend(db, RecommendRequest(city="上海"))

        assert result["safe"]["history_id"] == "prepared-safe"
        assert weather_calls == [("上海", {"latitude": None, "longitude": None})]


def test_recommend_regenerates_for_malformed_prepared_weather_context(monkeypatch) -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    calls = []
    monkeypatch.setattr(recommend_service, "get_weather", lambda *args, **kwargs: _weather())
    monkeypatch.setattr(recommend_service, "get_recent_item_ids", lambda *args, **kwargs: set())
    monkeypatch.setattr(
        recommend_service,
        "propose",
        lambda *args, **kwargs: calls.append(1) or _looks(kwargs.get("coverage_targets")),
    )

    with Session(engine) as db:
        prepared = _prepared_rows()
        prepared[0].context_json = json.dumps(
            {"latitude": 31.23, "longitude": 121.474, "weather": None}
        )
        db.add_all(_recommendation_items() + prepared)
        db.commit()

        recommend_service.recommend(db, RecommendRequest(latitude=31.230, longitude=121.474))

        assert calls == [1]


def test_recommend_preserves_saved_coordinates_for_city_only_request(monkeypatch) -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    monkeypatch.setattr(recommend_service, "get_weather", lambda *args, **kwargs: _weather())
    monkeypatch.setattr(recommend_service, "get_recent_item_ids", lambda *args, **kwargs: set())
    monkeypatch.setattr(
        recommend_service,
        "propose",
        lambda *args, **kwargs: _looks(kwargs.get("coverage_targets")),
    )

    with Session(engine) as db:
        db.add_all(_recommendation_items())
        db.add(
            recommend_service.Profile(
                user_id="local",
                learned_from_feedback_json=encode_profile_state(
                    learnings=[],
                    recent_style_signals=[],
                    style_tag_preferences={},
                    last_location={"latitude": 31.23, "longitude": 121.474},
                ),
            )
        )
        db.commit()

        recommend_service.recommend(db, RecommendRequest(city="上海", force_refresh=True))

        location = decode_profile_state(
            db.get(recommend_service.Profile, "local").learned_from_feedback_json
        )["last_location"]
        assert (location["latitude"], location["longitude"]) == (31.23, 121.474)


@pytest.mark.parametrize(
    ("payload", "weather"),
    [
        (RecommendRequest(latitude=31.299, longitude=120.585), _weather()),
        (RecommendRequest(latitude=31.230, longitude=121.474), _weather(temp=12)),
        (RecommendRequest(latitude=31.230, longitude=121.474), _weather(temp=25)),
        (RecommendRequest(latitude=31.230, longitude=121.474), _weather(rain_chance=50)),
        (RecommendRequest(latitude=31.230, longitude=121.474, force_refresh=True), _weather()),
    ],
    ids=(
        "distance",
        "winter-temperature-band",
        "summer-temperature-band",
        "rain-threshold",
        "force-refresh",
    ),
)
def test_recommend_regenerates_when_prepared_context_is_invalid(
    monkeypatch, payload: RecommendRequest, weather: SimpleNamespace
) -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    calls = []
    monkeypatch.setattr(recommend_service, "get_weather", lambda *args, **kwargs: weather)
    monkeypatch.setattr(recommend_service, "get_recent_item_ids", lambda *args, **kwargs: set())
    monkeypatch.setattr(
        recommend_service,
        "propose",
        lambda *args, **kwargs: calls.append(1) or _looks(kwargs.get("coverage_targets")),
    )

    with Session(engine) as db:
        db.add_all(_recommendation_items() + _prepared_rows())
        db.commit()

        recommend_service.recommend(db, payload)

        assert calls == [1]


def test_recommend_accepts_category_aliases_and_records_three_looks(monkeypatch) -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    items = [
        _item("top-1", "sweater"),
        _item("top-2", "shirt"),
        _item("top-3", "t-shirt"),
        _item("bottom-1", "skirt"),
        _item("bottom-2", "pants"),
        _item("bottom-3", "jeans"),
        _item("shoes-1", "boots"),
        _item("shoes-2", "shoe"),
        _item("shoes-3", "sneakers"),
    ]
    monkeypatch.setattr(
        recommend_service,
        "get_weather",
        lambda *args, **kwargs: SimpleNamespace(
            temp=20,
            condition="晴",
            model_dump=lambda: {"temp": 20, "condition": "晴"},
        ),
    )
    captured = {}

    def fake_propose(*args, **kwargs):
        captured.update(kwargs)
        return _looks(kwargs.get("coverage_targets"))

    monkeypatch.setattr(recommend_service, "propose", fake_propose)

    with Session(engine) as db:
        db.add_all(items)
        db.add(
            StyleReference(
                id="ref-1",
                user_id="local",
                image_path="/tmp/look.jpg",
                status="ready",
                analysis_json='{"style_keywords":["极简"]}',
            )
        )
        db.commit()

        result = recommend_service.recommend(
            db,
            RecommendRequest(
                city="上海",
                scene="通勤",
                season="autumn",
                style_note="今天想轻松一点",
                reference_ids=["ref-1"],
            ),
        )

        assert set(result) == {"weather", "safe", "fresh", "stretch"}
        assert "base_score" not in result["safe"]
        assert len(list(db.scalars(select(OutfitHistory)))) == 3
        assert captured["references"] == [{"style_keywords": ["极简"]}]
        assert captured["scene"] == "通勤"
        assert captured["season"] == "autumn"
        assert captured["style_note"] == "今天想轻松一点"


def test_recommend_rejects_unavailable_locked_item_before_calling_stylist(
    monkeypatch,
) -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    monkeypatch.setattr(
        recommend_service,
        "get_weather",
        lambda *args, **kwargs: SimpleNamespace(
            temp=20,
            condition="晴",
            model_dump=lambda: {"temp": 20, "condition": "晴"},
        ),
    )
    monkeypatch.setattr(
        recommend_service,
        "propose",
        lambda *args, **kwargs: pytest.fail("stylist should not be called"),
    )

    with Session(engine) as db:
        db.add_all(
            [
                _item("top-1", "top"),
                _item("bottom-1", "bottom"),
                _item("shoes-1", "shoes"),
            ]
        )
        db.commit()

        with pytest.raises(ValueError, match="missing-locked"):
            recommend_service.recommend(
                db,
                RecommendRequest(city="上海", locked_item_ids=["missing-locked"]),
            )


def test_recommend_passes_usage_targets_and_recent_looks_to_stylist(monkeypatch) -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    captured = {}

    def fake_propose(*args, **kwargs):
        captured.update(kwargs)
        captured["recent_looks"] = args[5]
        return _looks(kwargs["coverage_targets"])

    monkeypatch.setattr(recommend_service, "get_weather", lambda *args, **kwargs: _weather())
    monkeypatch.setattr(recommend_service, "require_api_key", lambda: None)
    monkeypatch.setattr(recommend_service, "propose", fake_propose)

    with Session(engine) as db:
        db.add_all(_recommendation_items())
        db.commit()
        recommend_service.recommend(db, RecommendRequest(city="上海"))

    assert isinstance(captured["usage_stats"], dict)
    assert set(captured["coverage_targets"]) == {"fresh", "stretch"}
    assert isinstance(captured["recent_looks"], list)


def test_recommend_does_not_prune_old_ordinary_history(monkeypatch) -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    monkeypatch.setattr(recommend_service, "get_weather", lambda *args, **kwargs: _weather())
    monkeypatch.setattr(recommend_service, "require_api_key", lambda: None)
    monkeypatch.setattr(
        recommend_service,
        "propose",
        lambda *args, **kwargs: _looks(kwargs.get("coverage_targets")),
    )

    with Session(engine) as db:
        db.add_all(_recommendation_items())
        db.add(
            OutfitHistory(
                id="old-history",
                user_id="local",
                date=date(2026, 1, 1),
                item_ids_json='["top-1"]',
                pick_mode="safe",
                action="shown",
            )
        )
        db.commit()

        recommend_service.recommend(db, RecommendRequest(city="上海"))

        assert db.get(OutfitHistory, "old-history") is not None


def test_recommend_http_reuses_prepared_without_minimax_key(monkeypatch, tmp_path) -> None:
    from outfit_ai.services import llm
    from outfit_ai.services.minimax_images import MiniMaxUnavailableError

    engine = create_engine(f"sqlite:///{tmp_path / 'prepared-no-key.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all(_recommendation_items() + _prepared_rows())
        db.commit()

    def override_db():
        with Session(engine) as db:
            yield db

    monkeypatch.setattr(
        llm,
        "resolve_minimax_access",
        lambda: (_ for _ in ()).throw(MiniMaxUnavailableError("未配置 MiniMax API Key")),
    )
    monkeypatch.setattr(
        recommend_service,
        "get_weather",
        lambda *args, **kwargs: _weather(),
    )
    monkeypatch.setattr(
        recommend_service,
        "propose",
        lambda *args, **kwargs: pytest.fail("MiniMax should not be called"),
    )
    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/recommend",
                json={"latitude": 31.23, "longitude": 121.474},
            )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    assert response.json()["safe"]["history_id"] == "prepared-safe"


def test_recommend_http_requires_minimax_key_without_prepared(monkeypatch, tmp_path) -> None:
    from outfit_ai.services import llm
    from outfit_ai.services.minimax_images import MiniMaxUnavailableError

    engine = create_engine(f"sqlite:///{tmp_path / 'no-prepared-no-key.db'}")
    Base.metadata.create_all(engine)

    def override_db():
        with Session(engine) as db:
            yield db

    monkeypatch.setattr(
        llm,
        "resolve_minimax_access",
        lambda: (_ for _ in ()).throw(MiniMaxUnavailableError("未配置 MiniMax API Key")),
    )
    monkeypatch.setattr(recommend_service, "get_weather", lambda *args, **kwargs: _weather())
    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/recommend",
                json={"latitude": 31.23, "longitude": 121.474},
            )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 503
    assert response.json()["detail"] == "未配置 MiniMax API Key"


def test_recommend_feedback_history_http_loop(monkeypatch, tmp_path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'loop.db'}")
    Base.metadata.create_all(engine)
    items = [
        _item("top-1", "top"),
        _item("top-2", "top"),
        _item("top-3", "top"),
        _item("bottom-1", "bottom"),
        _item("bottom-2", "bottom"),
        _item("bottom-3", "bottom"),
        _item("shoes-1", "shoes"),
        _item("shoes-2", "shoes"),
        _item("shoes-3", "shoes"),
    ]
    with Session(engine) as db:
        db.add_all(items)
        db.commit()

    def override_db():
        with Session(engine) as db:
            yield db

    monkeypatch.setattr(settings, "minimax_api_key", "test-key")
    monkeypatch.setattr(
        recommend_service,
        "get_weather",
        lambda *args, **kwargs: SimpleNamespace(
            temp=20,
            condition="晴",
            model_dump=lambda: {"temp": 20, "condition": "晴"},
        ),
    )
    monkeypatch.setattr(
        recommend_service,
        "propose",
        lambda *args, **kwargs: _looks(kwargs.get("coverage_targets")),
    )
    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            recommended = client.post("/api/recommend", json={"city": "上海"})
            safe = recommended.json()["safe"]
            feedback = client.post(
                "/api/feedback",
                json={
                    "history_id": safe["history_id"],
                    "items_worn": [item["id"] for item in safe["items"]],
                    "action": "worn",
                },
            )
            history = client.get("/api/history")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert recommended.status_code == 200
    assert feedback.json() == {"ok": True}
    safe_history = next(row for row in history.json() if row["id"] == safe["history_id"])
    assert safe_history["action"] == "worn"
    assert safe_history["wore_it"] is True
