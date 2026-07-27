import json

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from outfit_ai.db import Base
from outfit_ai.models import OutfitHistory, WardrobeItem
from outfit_ai.routers.feedback import history
from outfit_ai.services.history import get_recent_item_ids, get_recent_outfits


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
