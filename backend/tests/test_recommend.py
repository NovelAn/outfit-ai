from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from outfit_ai.config import settings
from outfit_ai.db import Base, get_db
from outfit_ai.main import app
from outfit_ai.models import OutfitHistory, StyleReference, WardrobeItem
from outfit_ai.routers.recommend import recommendation
from outfit_ai.schemas import ProposedLook, RecommendRequest
from outfit_ai.services import recommend as recommend_service


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


def test_recommend_api_reports_missing_minimax_key_before_network(monkeypatch) -> None:
    from outfit_ai.services import llm
    from outfit_ai.services.minimax_images import MiniMaxUnavailableError

    monkeypatch.setattr(
        llm,
        "resolve_minimax_access",
        lambda: (_ for _ in ()).throw(
            MiniMaxUnavailableError("未配置 MiniMax API Key")
        ),
    )
    monkeypatch.setattr(
        recommend_service,
        "get_weather",
        lambda *args, **kwargs: pytest.fail("weather should not be called"),
    )

    with pytest.raises(HTTPException) as error:
        recommendation(RecommendRequest(city="上海"), None)

    assert error.value.status_code == 503
    assert error.value.detail == "未配置 MiniMax API Key"


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
    safe_history = next(
        row for row in history.json() if row["id"] == safe["history_id"]
    )
    assert safe_history["action"] == "worn"
    assert safe_history["wore_it"] is True
