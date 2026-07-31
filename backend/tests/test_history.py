import json
from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from outfit_ai.db import Base
from outfit_ai.models import OutfitHistory, WardrobeItem
from outfit_ai.routers.feedback import history
from outfit_ai.schemas import ProposedLook
from outfit_ai.services.history import (
    get_prepared_outfits,
    get_recent_item_ids,
    get_recent_outfits,
    record_outfit,
)


def test_recent_item_ids_skip_all_shoe_aliases() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all(
            [
                WardrobeItem(
                    id=item_id,
                    user_id="local",
                    category=category,
                    image_path=f"/tmp/{item_id}.jpg",
                )
                for item_id, category in (
                    ("top-1", "shirt"),
                    ("boot-1", "boot"),
                    ("sneaker-1", "sneaker"),
                )
            ]
        )
        db.add(
            OutfitHistory(
                id="history-1",
                user_id="local",
                item_ids_json=json.dumps(["top-1", "boot-1", "sneaker-1"]),
                pick_mode="safe",
            )
        )
        db.commit()

        assert get_recent_item_ids(db, "local") == {"top-1"}


def test_same_day_history_uses_latest_sqlite_row_first() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all(
            [
                OutfitHistory(
                    id=history_id,
                    user_id="local",
                    item_ids_json="[]",
                    pick_mode="safe",
                )
                for history_id in ("first", "second")
            ]
        )
        db.commit()

        assert [row.id for row in get_recent_outfits(db, "local")] == [
            "second",
            "first",
        ]
        assert [row["id"] for row in history(db)] == ["second", "first"]


def test_prepared_outfits_require_all_three_latest_tiers() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all(
            [
                OutfitHistory(
                    id=history_id,
                    user_id="local",
                    date=date(2026, 7, 31),
                    item_ids_json="[]",
                    pick_mode=tier,
                    action="prepared",
                )
                for history_id, tier in (
                    ("safe-first", "safe"),
                    ("safe-latest", "safe"),
                    ("fresh", "fresh"),
                    ("stretch", "stretch"),
                )
            ]
        )
        db.commit()

        prepared = get_prepared_outfits(db, "local", date(2026, 7, 31))

        assert [row.id for row in prepared] == ["safe-latest", "fresh", "stretch"]
        assert [row.pick_mode for row in prepared] == ["safe", "fresh", "stretch"]
        assert all(row.action == "prepared" for row in prepared)


def test_prepared_outfits_require_each_tier() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(
            OutfitHistory(
                id="safe",
                user_id="local",
                date=date(2026, 7, 31),
                item_ids_json="[]",
                pick_mode="safe",
                action="prepared",
            )
        )
        db.commit()

        assert get_prepared_outfits(db, "local", date(2026, 7, 31)) == []


def test_prepared_marker_survives_a_user_action_and_skips_ordinary_shown_rows() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all(
            [
                OutfitHistory(
                    id=f"prepared-{tier}",
                    user_id="local",
                    date=date(2026, 7, 31),
                    item_ids_json="[]",
                    pick_mode=tier,
                    action="shown",
                    context_json='{"prepared": true}',
                )
                for tier in ("safe", "fresh", "stretch")
            ]
            + [
                OutfitHistory(
                    id=f"shown-{tier}",
                    user_id="local",
                    date=date(2026, 7, 31),
                    item_ids_json="[]",
                    pick_mode=tier,
                    action="shown",
                    context_json="{}",
                )
                for tier in ("safe", "fresh", "stretch")
            ]
        )
        db.commit()

        prepared = get_prepared_outfits(db, "local", date(2026, 7, 31))

        assert [row.id for row in prepared] == [
            "prepared-safe",
            "prepared-fresh",
            "prepared-stretch",
        ]


def test_prepared_outfits_ignore_non_object_context() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all(
            [
                OutfitHistory(
                    id=f"invalid-{tier}",
                    user_id="local",
                    date=date(2026, 7, 31),
                    item_ids_json="[]",
                    pick_mode=tier,
                    action="shown",
                    context_json=context_json,
                )
                for tier, context_json in zip(
                    ("safe", "fresh", "stretch"), ("null", "[]", '"prepared"'), strict=True
                )
            ]
        )
        db.commit()

        assert get_prepared_outfits(db, "local", date(2026, 7, 31)) == []


def test_record_outfit_stores_optional_context_without_ascii_escaping() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        history = record_outfit(
            db,
            "local",
            ProposedLook(
                tier="safe",
                item_ids=["shirt"],
                reason="舒适",
                weather_fit="适合",
                occasion_fit="日常",
            ),
            occasion="日常",
            mood=None,
            weather_summary="晴",
            temp=25,
            action="prepared",
            context={"city": "上海"},
        )

        assert history.action == "prepared"
        assert history.context_json == '{"city": "上海"}'
