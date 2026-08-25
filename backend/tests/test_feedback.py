import json
import threading
import time
from datetime import date, datetime

import pytest
from fastapi import BackgroundTasks
from sqlalchemy import create_engine, update
from sqlalchemy.orm import Session

from outfit_ai.db import Base
from outfit_ai.models import Feedback, OutfitHistory, Profile, WardrobeItem
from outfit_ai.routers.feedback import feedback
from outfit_ai.routers.feedback import history as history_route
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


def test_feedback_rating_and_history_expose_persisted_tags() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        outfit = OutfitHistory(
            id="history-1",
            user_id="local",
            item_ids_json='["top-1", "bottom-1", "shoes-1"]',
            pick_mode="safe",
            action="shown",
        )
        db.add(outfit)
        db.commit()
        feedback(
            FeedbackIn(
                history_id=outfit.id,
                items_worn=["top-1", "bottom-1", "shoes-1"],
                action="saved",
                sentiment="4 星",
                compliments=["🎨 色彩搭配好"],
            ),
            BackgroundTasks(),
            db,
        )

        result = history_route(db, 20)

    assert result[0]["rating"] == 4
    assert result[0]["feedback"]["compliments"] == ["🎨 色彩搭配好"]


def test_feedback_is_not_deducted_before_background_task_starts() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    background_tasks = BackgroundTasks()

    with Session(engine) as db:
        for _ in range(4):
            feedback(FeedbackIn(action="shown"), background_tasks, db)

        assert db.get(Profile, "local").feedback_since_refresh == 4
        assert len(background_tasks.tasks) == 1


def test_feedback_accepts_an_actionless_rating_from_one_to_five() -> None:
    assert FeedbackIn(history_id="history-1", rating=1).rating == 1
    rating = FeedbackIn(history_id="history-1", rating=5)

    assert rating.action is None
    assert rating.rating == 5
    with pytest.raises(ValueError):
        FeedbackIn(history_id="history-1", action="saved", rating=0)
    with pytest.raises(ValueError):
        FeedbackIn(history_id="history-1", action="saved", rating=6)


def test_favorite_and_wear_preserve_saved_history_action() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(
            OutfitHistory(
                id="history-1",
                user_id="local",
                item_ids_json="[]",
                pick_mode="safe",
                action="shown",
            )
        )
        db.commit()

        feedback(FeedbackIn(history_id="history-1", action="saved"), BackgroundTasks(), db)
        feedback(FeedbackIn(history_id="history-1", action="worn"), BackgroundTasks(), db)

        saved = db.get(OutfitHistory, "history-1")
        assert saved.action == "saved"
        assert saved.wore_it is True


def test_rating_only_feedback_updates_history_without_changing_favorite() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(
            OutfitHistory(
                id="history-1",
                user_id="local",
                item_ids_json="[]",
                pick_mode="safe",
                action="saved",
            )
        )
        db.commit()

        feedback(FeedbackIn(history_id="history-1", rating=4), BackgroundTasks(), db)

        saved = db.get(OutfitHistory, "history-1")
        assert saved.action == "saved"
        assert saved.user_rating == 4


def test_manual_memo_refresh_deducts_only_after_success(monkeypatch) -> None:
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
        db.add_all(Feedback(id=f"feedback-{index}", user_id="local") for index in range(3))
        db.commit()

    taste_memo.refresh("local", force=True)

    with session_factory() as db:
        profile = db.get(Profile, "local")
        assert profile.taste_memo == "偏爱低饱和与利落剪裁。"
        assert profile.feedback_since_refresh == 0
        assert profile.taste_memo_updated_at is not None


def test_failed_memo_refresh_leaves_counter_unchanged(monkeypatch) -> None:
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
        db.add(Profile(user_id="local", feedback_since_refresh=8))
        db.add_all(Feedback(id=f"feedback-{index}", user_id="local") for index in range(8))
        db.commit()

    with pytest.raises(RuntimeError, match="provider failed"):
        taste_memo.refresh("local")

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
        db.add(Profile(user_id="local", taste_memo="旧 memo", feedback_since_refresh=1))
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

    taste_memo.refresh("local", force=True)

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
        db.add(Profile(user_id="local", taste_memo="旧 memo", feedback_since_refresh=8))
        db.add_all(Feedback(id=f"feedback-{index}", user_id="local") for index in range(8))
        db.commit()

    threads = [threading.Thread(target=taste_memo.refresh, args=("local",)) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert max_active == 1


def test_new_feedback_during_refresh_is_learned_in_second_distinct_batch(
    monkeypatch,
    tmp_path,
) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'batches.db'}")
    Base.metadata.create_all(engine)
    batches = []

    def session_factory():
        return Session(engine)

    def add_feedback(start: int, stop: int) -> None:
        with session_factory() as db:
            db.add_all(
                Feedback(id=f"feedback-{index}", user_id="local") for index in range(start, stop)
            )
            db.execute(
                update(Profile)
                .where(Profile.user_id == "local")
                .values(feedback_since_refresh=(Profile.feedback_since_refresh + stop - start))
            )
            db.commit()

    def generate_json(system, user, schema_hint):
        batches.append([row["id"] for row in json.loads(user)["feedback"]])
        if len(batches) == 1:
            add_feedback(8, 16)
        return {"taste_memo": f"memo-{len(batches)}"}

    monkeypatch.setattr(taste_memo, "SessionLocal", session_factory)
    monkeypatch.setattr(taste_memo, "generate_json", generate_json)
    with session_factory() as db:
        db.add(Profile(user_id="local", taste_memo="旧 memo", feedback_since_refresh=0))
        db.commit()
    add_feedback(0, 8)

    taste_memo.refresh("local")

    assert len(batches) == 2
    assert set(batches[0]).isdisjoint(batches[1])
    assert set(batches[0] + batches[1]) == {f"feedback-{index}" for index in range(16)}
    with session_factory() as db:
        profile = db.get(Profile, "local")
        assert profile.feedback_since_refresh == 0
        assert profile.taste_memo == "memo-2"
