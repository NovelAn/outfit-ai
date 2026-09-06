import json

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from outfit_ai.db import Base
from outfit_ai.models import Profile
from outfit_ai.services.profile_state import encode_profile_state


class _FakeSession:
    def __init__(self) -> None:
        self.rollbacks = 0

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def get(self, _model, _user_id):
        return Profile(
            user_id="local",
            city="上海",
            learned_from_feedback_json=encode_profile_state(
                learnings=[],
                recent_style_signals=[],
                style_tag_preferences={},
                last_location={"latitude": 31.23, "longitude": 121.474, "city": "上海"},
            ),
        )

    def rollback(self) -> None:
        self.rollbacks += 1


def test_precompute_retries_transient_llm_failure(monkeypatch, capsys) -> None:
    from outfit_ai import precompute_daily

    db = _FakeSession()
    attempts = 0

    def flaky_recommend(*_args, **_kwargs):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise precompute_daily.LLMUnavailableError("超时")
        return {"weather": {"local_date": "2026-07-31", "city": "上海"}}

    monkeypatch.setattr(precompute_daily, "SessionLocal", lambda: db)
    monkeypatch.setattr(precompute_daily, "require_api_key", lambda: True)
    monkeypatch.setattr(precompute_daily, "recommend", flaky_recommend)
    monkeypatch.setattr(precompute_daily, "sleep", lambda _seconds: None, raising=False)

    assert precompute_daily.main() == 0
    assert attempts == 2
    assert db.rollbacks == 1
    assert "重试" in capsys.readouterr().err


def test_precompute_stops_after_retry_limit(monkeypatch, capsys) -> None:
    from outfit_ai import precompute_daily

    db = _FakeSession()
    attempts = 0

    def broken_recommend(*_args, **_kwargs):
        nonlocal attempts
        attempts += 1
        raise precompute_daily.LLMResponseError("工具调用格式错误")

    monkeypatch.setattr(precompute_daily, "SessionLocal", lambda: db)
    monkeypatch.setattr(precompute_daily, "require_api_key", lambda: True)
    monkeypatch.setattr(precompute_daily, "recommend", broken_recommend)
    monkeypatch.setattr(precompute_daily, "sleep", lambda _seconds: None, raising=False)

    assert precompute_daily.main() == 1
    assert attempts == 2
    assert db.rollbacks == 2
    assert "工具调用格式错误" in capsys.readouterr().err


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
        "refresh_tier": None,
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
