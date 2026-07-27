import json
import threading
import time
from datetime import date, datetime

from fastapi import BackgroundTasks
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from outfit_ai.db import Base
from outfit_ai.models import Feedback, Profile, WardrobeItem
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


def test_feedback_batch_is_claimed_once_and_keeps_remainder() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    background_tasks = BackgroundTasks()

    with Session(engine) as db:
        for _ in range(9):
            feedback(FeedbackIn(action="shown"), background_tasks, db)

        assert db.get(Profile, "local").feedback_since_refresh == 1
        assert len(background_tasks.tasks) == 1


def test_successful_memo_refresh_preserves_feedback_after_claim(monkeypatch) -> None:
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
        db.add(Profile(user_id="local", taste_memo="旧 memo", feedback_since_refresh=3))
        db.commit()

    taste_memo.refresh("local")

    with session_factory() as db:
        profile = db.get(Profile, "local")
        assert profile.taste_memo == "偏爱低饱和与利落剪裁。"
        assert profile.feedback_since_refresh == 3
        assert profile.taste_memo_updated_at is not None


def test_failed_memo_refresh_restores_claimed_batch(monkeypatch) -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)

    def session_factory():
        return Session(engine)

    monkeypatch.setattr(taste_memo, "SessionLocal", session_factory)
    monkeypatch.setattr(
        taste_memo,
        "generate_json",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("provider failed")),
    )
    with session_factory() as db:
        db.add(Profile(user_id="local", feedback_since_refresh=0))
        db.commit()

    try:
        taste_memo.refresh("local", claimed_batch=8)
    except RuntimeError:
        pass

    with session_factory() as db:
        assert db.get(Profile, "local").feedback_since_refresh == 8


def test_memo_refresh_uses_complete_feedback_and_worn_item_attributes(
    monkeypatch,
) -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    captured = {}

    def session_factory():
        return Session(engine)

    def generate_json(system, user, schema_hint):
        captured.update(json.loads(user))
        return {"taste_memo": "新 memo"}

    monkeypatch.setattr(taste_memo, "SessionLocal", session_factory)
    monkeypatch.setattr(taste_memo, "generate_json", generate_json)
    with session_factory() as db:
        db.add(Profile(user_id="local", taste_memo="旧 memo", feedback_since_refresh=0))
        db.add(
            WardrobeItem(
                id="boot-1",
                user_id="local",
                name="棕色短靴",
                category="shoes",
                primary_color="棕色",
                material="皮革",
                fit="合身",
                formality="smart casual",
                style_json='["经典"]',
                tags_json='["通勤"]',
                seasons_json='["autumn"]',
                occasions_json='["work"]',
                image_path="/tmp/boot.jpg",
                status="ready",
                confirmed_by_user=True,
                added_at=datetime.now(),
            )
        )
        db.add(
            Feedback(
                id="feedback-1",
                user_id="local",
                date=date.today(),
                items_worn_json='["boot-1"]',
                occasion="通勤",
                occasion_type="work",
                sentiment="confident",
                compliments_json='["配色好"]',
                didnt_work="鞋底偏硬",
                learnings="适合搭配直筒裤",
            )
        )
        db.commit()

    taste_memo.refresh("local")

    assert captured["feedback"][0]["items_worn"] == ["boot-1"]
    assert captured["feedback"][0]["compliments"] == ["配色好"]
    assert captured["wardrobe_items"][0]["material"] == "皮革"
    assert captured["wardrobe_items"][0]["styles"] == ["经典"]


def test_memo_refresh_calls_are_serialized_within_process(monkeypatch, tmp_path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'refresh.db'}")
    Base.metadata.create_all(engine)
    active = 0
    max_active = 0
    state_lock = threading.Lock()

    def session_factory():
        return Session(engine)

    def generate_json(*args, **kwargs):
        nonlocal active, max_active
        with state_lock:
            active += 1
            max_active = max(max_active, active)
        time.sleep(0.05)
        with state_lock:
            active -= 1
        return {"taste_memo": "新 memo"}

    monkeypatch.setattr(taste_memo, "SessionLocal", session_factory)
    monkeypatch.setattr(taste_memo, "generate_json", generate_json)
    with session_factory() as db:
        db.add(Profile(user_id="local", taste_memo="旧 memo", feedback_since_refresh=0))
        db.commit()

    threads = [threading.Thread(target=taste_memo.refresh, args=("local",)) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert max_active == 1
