import json
from datetime import date, datetime, timedelta

import pytest
from fastapi import BackgroundTasks
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from outfit_ai.db import _ADDITIVE_COLUMNS, Base, _run_additive_migrations
from outfit_ai.models import Feedback, FeedbackEvent, OutfitHistory, Profile
from outfit_ai.routers import profile as profile_router
from outfit_ai.routers.feedback import feedback, history
from outfit_ai.routers.profile import _save
from outfit_ai.schemas import FeedbackIn, ProfileIn, TasteMemoCorrectionIn
from outfit_ai.services import taste_memo


def _history(history_id: str, item_ids: str = '["top-1", "bottom-1", "shoes-1"]'):
    return OutfitHistory(
        id=history_id,
        user_id="local",
        date=date(2026, 10, 8),
        item_ids_json=item_ids,
        pick_mode="safe",
        action="shown",
    )


def _add_events(db: Session, rows: list[Feedback], prefix: str) -> None:
    db.flush()
    db.add_all(
        FeedbackEvent(
            id=f"{prefix}-{index}",
            feedback_id=row.id,
            user_id=row.user_id,
            history_id=row.history_id,
            date=row.date,
            event_at=row.updated_at or row.created_at or datetime.now(),
            items_worn_json=row.items_worn_json,
            action=row.action,
            rating=row.rating,
            occasion=row.occasion,
            occasion_type=row.occasion_type,
            sentiment=row.sentiment,
            positive_signals_json=row.positive_signals_json,
            negative_signals_json=row.negative_signals_json,
            adjustment_signals_json=row.adjustment_signals_json,
            didnt_work=row.didnt_work,
            learnings=row.learnings,
            wore_it=row.wore_it,
        )
        for index, row in enumerate(rows)
    )


def test_feedback_persists_recommendation_identity_final_fact_and_intents() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(_history("history-1"))
        db.commit()

        feedback(
            FeedbackIn(
                history_id="history-1",
                items_worn=["top-1", "bottom-1", "shoes-1"],
                action="saved",
                rating=4,
                compliments=["色彩搭配好"],
                negative_signals=["过于正式"],
                adjustment_signals=["想看叠穿"],
            ),
            BackgroundTasks(),
            db,
        )

        row = db.query(Feedback).one()
        assert row.history_id == "history-1"
        assert row.action == "saved"
        assert row.rating == 4
        assert row.created_at is not None
        assert json.loads(row.positive_signals_json) == ["色彩搭配好"]
        assert json.loads(row.negative_signals_json) == ["过于正式"]
        assert json.loads(row.adjustment_signals_json) == ["想看叠穿"]


def test_repeated_final_facts_do_not_increment_learning_counter_but_real_changes_do() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(_history("history-1"))
        db.commit()

        payload = FeedbackIn(history_id="history-1", action="saved", rating=5)
        feedback(payload, BackgroundTasks(), db)
        feedback(payload, BackgroundTasks(), db)
        assert db.get(Profile, "local").feedback_since_refresh == 1

        feedback(FeedbackIn(history_id="history-1", rating=3), BackgroundTasks(), db)
        feedback(FeedbackIn(history_id="history-1", action="shown"), BackgroundTasks(), db)
        feedback(FeedbackIn(history_id="history-1", action="shown"), BackgroundTasks(), db)
        assert db.get(Profile, "local").feedback_since_refresh == 3

        row = db.query(Feedback).one()
        assert row.action == "shown"
        assert row.rating == 3


def test_same_day_same_items_keep_feedback_attached_to_their_history_id() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([_history("history-1"), _history("history-2")])
        db.commit()
        feedback(
            FeedbackIn(history_id="history-1", action="saved", rating=5),
            BackgroundTasks(),
            db,
        )
        rows = {row["id"]: row for row in history(db, 20)}

    assert rows["history-1"]["feedback"]["history_id"] == "history-1"
    assert rows["history-2"]["feedback"] is None


def test_profile_put_cannot_overwrite_service_owned_taste_memo() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Profile(user_id="local", taste_memo="服务端最新 memo"))
        db.commit()
        saved = _save(db, ProfileIn(city="杭州", taste_memo="客户端旧 memo"))
        assert saved.taste_memo == "服务端最新 memo"


def test_refresh_failure_is_visible_and_retryable_without_losing_pending_feedback(
    monkeypatch,
) -> None:
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
        db.add(Profile(user_id="local", feedback_since_refresh=4))
        rows = [Feedback(id=f"feedback-{i}", user_id="local") for i in range(4)]
        db.add_all(rows)
        _add_events(db, rows, "event")
        db.commit()

    with pytest.raises(RuntimeError, match="provider failed"):
        taste_memo.refresh("local")

    with session_factory() as db:
        profile = db.get(Profile, "local")
        assert profile.taste_memo_refresh_status == "failed"
        assert profile.taste_memo_refresh_error == "provider failed"
        assert profile.feedback_since_refresh == 4

    monkeypatch.setattr(
        taste_memo,
        "generate_json",
        lambda *args, **kwargs: {
            "taste_memo": "重试后的 memo",
            "learned_this_round": "更偏好轻松层次",
        },
    )
    taste_memo.refresh("local", force=True)

    with session_factory() as db:
        profile = db.get(Profile, "local")
        assert profile.taste_memo_refresh_status == "idle"
        assert profile.taste_memo_refresh_error is None
        assert profile.feedback_since_refresh == 0
        assert profile.taste_memo_last_change == "更偏好轻松层次"


def test_refresh_context_contains_history_action_rating_time_and_polarity(monkeypatch) -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    captured = {}

    def session_factory():
        return Session(engine)

    def generate_json(system, user, schema_hint):
        captured.update(json.loads(user))
        return {"taste_memo": "新 memo", "learned_this_round": "保留轻松感"}

    monkeypatch.setattr(taste_memo, "SessionLocal", session_factory)
    monkeypatch.setattr(taste_memo, "generate_json", generate_json)
    with session_factory() as db:
        db.add(Profile(user_id="local", taste_memo="旧 memo", feedback_since_refresh=1))
        row = Feedback(
                id="feedback-1",
                user_id="local",
                history_id="history-1",
                action="saved",
                rating=4,
                positive_signals_json='["色彩搭配好"]',
                negative_signals_json='["过于正式"]',
                adjustment_signals_json='["想看叠穿"]',
        )
        db.add(row)
        _add_events(db, [row], "event")
        db.commit()

    taste_memo.refresh("local", force=True)
    fact = captured["feedback"][0]
    assert fact["history_id"] == "history-1"
    assert fact["action"] == "saved"
    assert fact["rating"] == 4
    assert fact["created_at"]
    assert fact["positive_signals"] == ["色彩搭配好"]
    assert fact["negative_signals"] == ["过于正式"]
    assert fact["adjustment_signals"] == ["想看叠穿"]


def test_additive_migration_is_idempotent_and_preserves_legacy_feedback() -> None:
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE profile (user_id TEXT PRIMARY KEY, taste_memo TEXT)"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE feedback (id TEXT PRIMARY KEY, user_id TEXT, date DATE, "
                "items_worn_json TEXT, compliments_json TEXT)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO feedback (id, user_id, items_worn_json, compliments_json) "
                "VALUES ('legacy', 'local', '[]', '[]')"
            )
        )

    _run_additive_migrations(engine)
    _run_additive_migrations(engine)
    feedback_columns = {column["name"] for column in inspect(engine).get_columns("feedback")}

    assert {
        "history_id",
        "action",
        "rating",
        "created_at",
        "updated_at",
        "positive_signals_json",
        "negative_signals_json",
        "adjustment_signals_json",
    } <= feedback_columns
    assert "taste_memo_revision" in {
        column["name"] for column in inspect(engine).get_columns("profile")
    }
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT id FROM feedback WHERE id = 'legacy'")) == "legacy"


def test_additive_migration_keeps_backup_when_ddl_fails_and_rolls_back(
    monkeypatch,
    tmp_path,
) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.sqlite'}")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE feedback (id TEXT PRIMARY KEY)"))
        connection.execute(text("INSERT INTO feedback (id) VALUES ('legacy')"))

    monkeypatch.setitem(
        _ADDITIVE_COLUMNS["feedback"],
        "broken_column",
        "TEXT NOT NULL DEFAULT (random())",
    )
    backup_path = tmp_path / "feedback-before-migration.sqlite"

    with pytest.raises(OperationalError):
        _run_additive_migrations(engine, backup_path=backup_path)

    assert backup_path.exists()
    assert "broken_column" not in {
        column["name"] for column in inspect(engine).get_columns("feedback")
    }
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT id FROM feedback")) == "legacy"


def test_manual_memo_correction_fences_an_inflight_refresh(monkeypatch) -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)

    def session_factory():
        return Session(engine)

    monkeypatch.setattr(taste_memo, "SessionLocal", session_factory)

    with session_factory() as db:
        db.add(Profile(user_id="local", feedback_since_refresh=4))
        rows = [Feedback(id=f"feedback-{i}", user_id="local") for i in range(4)]
        db.add_all(rows)
        _add_events(db, rows, "event")
        db.commit()

    def generate_json(*args, **kwargs):
        with Session(engine) as correction_db:
            profile_router.correct_memo(
                TasteMemoCorrectionIn(taste_memo="用户刚刚修正的 memo"),
                correction_db,
            )
        return {"taste_memo": "已经过期的 AI memo", "learned_this_round": "旧结论"}

    monkeypatch.setattr(taste_memo, "generate_json", generate_json)
    taste_memo.refresh("local")

    with session_factory() as db:
        profile = db.get(Profile, "local")
        assert profile.taste_memo == "用户刚刚修正的 memo"
        assert profile.feedback_since_refresh == 4
        assert profile.taste_memo_refresh_status == "idle"


def test_changed_legacy_feedback_reenters_next_refresh_batch(monkeypatch) -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    captured_batches = []

    def session_factory():
        return Session(engine)

    def generate_json(system, user, schema_hint):
        captured_batches.append(json.loads(user)["feedback"])
        return {"taste_memo": "memo", "learned_this_round": "变化"}

    monkeypatch.setattr(taste_memo, "SessionLocal", session_factory)
    monkeypatch.setattr(taste_memo, "generate_json", generate_json)
    base_time = datetime(2026, 10, 8, 9, 0, 0)
    with session_factory() as db:
        db.add(Profile(user_id="local", feedback_since_refresh=4))
        rows = [
            Feedback(
                id=f"feedback-{i}",
                user_id="local",
                created_at=base_time + timedelta(minutes=i),
                updated_at=base_time + timedelta(minutes=i),
            )
            for i in range(4)
        ]
        db.add_all(rows)
        _add_events(db, rows, "initial-event")
        db.commit()

    taste_memo.refresh("local")

    with session_factory() as db:
        old = db.get(Feedback, "feedback-0")
        old.rating = 5
        old.updated_at = base_time + timedelta(hours=1)
        new_rows = [
            Feedback(
                id=f"new-feedback-{i}",
                user_id="local",
                created_at=base_time + timedelta(hours=2, minutes=i),
                updated_at=base_time + timedelta(hours=2, minutes=i),
            )
            for i in range(3)
        ]
        db.add_all(new_rows)
        _add_events(db, [old, *new_rows], "next-event")
        db.get(Profile, "local").feedback_since_refresh = 4
        db.commit()

    taste_memo.refresh("local")
    assert len(captured_batches) == 2
    assert "feedback-0" in {row["feedback_id"] for row in captured_batches[1]}


def test_malformed_feedback_json_is_safely_ignored_and_does_not_stick_running(
    monkeypatch,
) -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)

    def session_factory():
        return Session(engine)

    monkeypatch.setattr(taste_memo, "SessionLocal", session_factory)
    monkeypatch.setattr(
        taste_memo,
        "generate_json",
        lambda *args, **kwargs: {
            "taste_memo": "安全 memo",
            "learned_this_round": "忽略损坏字段",
        },
    )
    with session_factory() as db:
        db.add(Profile(user_id="local", feedback_since_refresh=4))
        bad_row = Feedback(
                id="bad-json",
                user_id="local",
                items_worn_json="{not-json",
                positive_signals_json="{also-not-json",
        )
        rows = [bad_row, *[Feedback(id=f"feedback-{i}", user_id="local") for i in range(3)]]
        db.add_all(rows)
        _add_events(db, rows, "event")
        db.commit()

    taste_memo.refresh("local")

    with session_factory() as db:
        profile = db.get(Profile, "local")
        assert profile.taste_memo_refresh_status == "idle"
        assert profile.feedback_since_refresh == 0


def test_multiple_real_changes_to_one_history_refresh_as_events(monkeypatch) -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    captured = {}

    def session_factory():
        return Session(engine)

    monkeypatch.setattr(taste_memo, "SessionLocal", session_factory)

    def generate_json(system, user, schema_hint):
        captured.update(json.loads(user))
        return {"taste_memo": "按事件更新的 memo", "learned_this_round": "变化"}

    monkeypatch.setattr(taste_memo, "generate_json", generate_json)
    with session_factory() as db:
        db.add(_history("history-1"))
        db.commit()

        for payload in (
            FeedbackIn(history_id="history-1", action="saved", rating=1),
            FeedbackIn(history_id="history-1", rating=2),
            FeedbackIn(history_id="history-1", action="shown"),
            FeedbackIn(history_id="history-1", action="worn"),
            FeedbackIn(history_id="history-1", action="worn"),
        ):
            feedback(payload, BackgroundTasks(), db)

        profile = db.get(Profile, "local")
        assert profile.feedback_since_refresh == 4
        assert db.query(Feedback).count() == 1
        assert db.query(FeedbackEvent).count() == 4

    taste_memo.refresh("local")

    with session_factory() as db:
        profile = db.get(Profile, "local")
        assert profile.feedback_since_refresh == 0
        assert profile.taste_memo_refresh_status == "idle"
    assert len(captured["feedback"]) == 4
    assert {row["feedback_id"] for row in captured["feedback"]} == {
        captured["feedback"][0]["feedback_id"]
    }
