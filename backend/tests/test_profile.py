import json
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from outfit_ai.config import settings
from outfit_ai.db import Base
from outfit_ai.main import app
from outfit_ai.models import Profile
from outfit_ai.routers import profile as profile_router
from outfit_ai.routers.profile import _out, _save
from outfit_ai.schemas import ProfileIn, StyleDnaDraftRequest
from outfit_ai.services import taste_memo


def test_style_dna_draft_reports_missing_minimax_key(monkeypatch) -> None:
    monkeypatch.setattr(settings, "minimax_api_key", "")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/api/profile/style-dna/draft",
            json={"samples": ["https://example.com/look.jpg"], "text": "简洁、低调"},
        )

    assert response.status_code == 503
    assert response.json()["detail"] == "未配置 MINIMAX_API_KEY"


def test_style_dna_draft_requires_text_or_sample() -> None:
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/api/profile/style-dna/draft", json={})

    assert response.status_code == 422


def test_style_dna_seed_returns_editable_profile_and_memo(monkeypatch) -> None:
    captured = {}

    def fake_chat(messages, **kwargs):
        captured["messages"] = messages
        arguments = json.dumps(
            {
                "style_keywords": ["极简", "经典"],
                "avoids": ["夸张 logo"],
                "taste_memo": "偏爱低饱和、利落剪裁。",
            },
            ensure_ascii=False,
        )
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        tool_calls=[
                            SimpleNamespace(function=SimpleNamespace(arguments=arguments))
                        ]
                    )
                )
            ]
        )

    monkeypatch.setattr(taste_memo, "chat_multimodal", fake_chat, raising=False)

    draft = taste_memo.seed(["https://example.com/look.jpg"], "简洁、低调")

    assert draft.style_keywords == ["极简", "经典"]
    assert draft.taste_memo == "偏爱低饱和、利落剪裁。"
    assert captured["messages"][1]["content"][1]["image_url"]["url"].endswith("look.jpg")


def test_profile_round_trip_preserves_full_spec_fields() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    payload = ProfileIn(
        formulas=["针织衫 + 长裤"],
        learned_from_feedback=["避免高对比"],
        budget_top_cents=200000,
    )

    with Session(engine) as db:
        output = _out(_save(db, payload))

    assert output["formulas"] == ["针织衫 + 长裤"]
    assert output["learned_from_feedback"] == ["避免高对比"]
    assert output["budget_top_cents"] == 200000


def test_style_dna_draft_does_not_save_before_user_confirms(monkeypatch) -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    monkeypatch.setattr(
        profile_router,
        "seed",
        lambda samples, text: ProfileIn(
            style_keywords=["极简"],
            taste_memo="偏爱利落剪裁。",
        ),
    )

    with Session(engine) as db:
        result = profile_router.draft(
            StyleDnaDraftRequest(samples=[], text="极简"),
            db,
        )

        assert result["draft"]["style_keywords"] == ["极简"]
        assert db.get(Profile, "local") is None
