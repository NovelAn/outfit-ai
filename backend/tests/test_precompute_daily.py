import json

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from outfit_ai.db import Base
from outfit_ai.models import Profile
from outfit_ai.services.profile_state import encode_profile_state


def test_precompute_uses_stored_location_and_prepares_looks(monkeypatch, capsys) -> None:
    from outfit_ai import precompute_daily

    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(
            Profile(
                user_id="local",
                city="上海",
                learned_from_feedback_json=encode_profile_state(
                    learnings=[],
                    recent_style_signals=[],
                    style_tag_preferences={},
                    last_location={"latitude": 31.23, "longitude": 121.474, "city": "上海"},
                ),
            )
        )
        db.commit()

    captured = {}
    monkeypatch.setattr(precompute_daily, "SessionLocal", lambda: Session(engine))
    monkeypatch.setattr(
        precompute_daily, "require_api_key", lambda: captured.setdefault("key", True)
    )
    monkeypatch.setattr(
        precompute_daily,
        "recommend",
        lambda db, request, **kwargs: captured.update(
            request=request, history_action=kwargs["history_action"]
        )
        or {"weather": {"local_date": "2026-07-31", "city": "上海"}},
    )

    assert precompute_daily.main() == 0
    assert captured["key"] is True
    assert captured["history_action"] == "prepared"
    assert captured["request"].model_dump() == {
        "occasion": "日常",
        "scene": None,
        "mood": None,
        "season": None,
        "style_note": None,
        "reference_ids": [],
            "city": "上海",
            "latitude": 31.23,
            "longitude": 121.474,
            "local_date": None,
            "locked_item_ids": [],
        "force_refresh": True,
    }
    assert "2026-07-31 上海" in capsys.readouterr().out


def test_precompute_returns_error_without_saved_location_or_city(monkeypatch, capsys) -> None:
    from outfit_ai import precompute_daily

    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Profile(user_id="local", learned_from_feedback_json=json.dumps([])))
        db.commit()

    monkeypatch.setattr(precompute_daily, "SessionLocal", lambda: Session(engine))

    assert precompute_daily.main() == 1
    assert "未设置城市或定位" in capsys.readouterr().err
