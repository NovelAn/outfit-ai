from fastapi import BackgroundTasks
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from outfit_ai.db import Base
from outfit_ai.models import Profile
from outfit_ai.routers.feedback import feedback
from outfit_ai.schemas import FeedbackIn
from outfit_ai.services import taste_memo


def test_first_feedback_initializes_profile_counter() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        result = feedback(
            FeedbackIn(action="worn", items_worn=["top-1"]),
            BackgroundTasks(),
            db,
        )

        assert result == {"ok": True}
        assert db.get(Profile, "local").feedback_since_refresh == 1


def test_eighth_feedback_queues_single_memo_refresh() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    background_tasks = BackgroundTasks()

    with Session(engine) as db:
        for _ in range(8):
            feedback(FeedbackIn(action="shown"), background_tasks, db)

        assert db.get(Profile, "local").feedback_since_refresh == 8
        assert len(background_tasks.tasks) == 1


def test_successful_memo_refresh_updates_profile_and_resets_counter(monkeypatch) -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)

    def session_factory():
        return Session(engine)

    monkeypatch.setattr(taste_memo, "SessionLocal", session_factory)
    monkeypatch.setattr(
        taste_memo,
        "generate_json",
        lambda *args, **kwargs: {"taste_memo": "偏爱低饱和与利落剪裁。"},
    )

    with session_factory() as db:
        db.add(Profile(user_id="local", taste_memo="旧 memo", feedback_since_refresh=8))
        db.commit()

    taste_memo.refresh("local")

    with session_factory() as db:
        profile = db.get(Profile, "local")
        assert profile.taste_memo == "偏爱低饱和与利落剪裁。"
        assert profile.feedback_since_refresh == 0
        assert profile.taste_memo_updated_at is not None
