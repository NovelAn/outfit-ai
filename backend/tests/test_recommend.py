import json
from datetime import date, datetime
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


def _looks() -> list[ProposedLook]:
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


def _same_day_set_rows(set_id: str) -> list[OutfitHistory]:
    return [
        OutfitHistory(
            id=f"{set_id}-{tier}",
            user_id="local",
            date=date(2026, 7, 31),
            item_ids_json=json.dumps([f"top-{index}", f"bottom-{index}", f"shoes-{index}"]),
            pick_mode=tier,
            action="shown",
            context_json=json.dumps({"recommendation_set_id": set_id}),
        )
        for index, tier in enumerate(("safe", "fresh", "stretch"), 1)
    ]


def test_haversine_shanghai_to_suzhou_exceeds_prepared_reuse_radius() -> None:
    assert recommend_service._haversine_km(31.230, 121.474, 31.299, 120.585) > 20


def test_normal_request_reuses_latest_complete_same_day_set_for_manual_city(monkeypatch) -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    monkeypatch.setattr(recommend_service, "get_weather", lambda *args, **kwargs: _weather())
    monkeypatch.setattr(recommend_service, "require_api_key", lambda: None)
    monkeypatch.setattr(recommend_service, "get_recent_item_ids", lambda *args, **kwargs: set())
    monkeypatch.setattr(
        recommend_service,
        "propose",
        lambda *args, **kwargs: pytest.fail("same-day set should be reused"),
    )
    with Session(engine) as db:
        db.add_all(_recommendation_items() + _same_day_set_rows("latest-set"))
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
    monkeypatch.setattr(recommend_service, "propose", lambda *args, **kwargs: _looks())
    with Session(engine) as db:
        db.add_all(_recommendation_items() + _same_day_set_rows("old-set"))
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
        lambda *args, **kwargs: calls.append(1) or _looks(),
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
    monkeypatch.setattr(recommend_service, "propose", lambda *args, **kwargs: _looks())

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
        lambda *args, **kwargs: calls.append(1) or _looks(),
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
    looks = [
        ProposedLook(
            tier=tier,
            item_ids=[f"top-{index}", f"bottom-{index}", f"shoes-{index}"],
            reason=f"{tier} reason",
            weather_fit="适合",
            occasion_fit="合适",
        )
        for index, tier in enumerate(("safe", "fresh", "stretch"), 1)
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
        return looks

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
    looks = [
        ProposedLook(
            tier=tier,
            item_ids=[f"top-{index}", f"bottom-{index}", f"shoes-{index}"],
            reason=f"{tier} reason",
            weather_fit="适合",
            occasion_fit="合适",
        )
        for index, tier in enumerate(("safe", "fresh", "stretch"), 1)
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
    monkeypatch.setattr(recommend_service, "propose", lambda *args, **kwargs: looks)
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
