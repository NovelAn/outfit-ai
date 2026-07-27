import json

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from outfit_ai.db import Base
from outfit_ai.models import OutfitHistory, WardrobeItem
from outfit_ai.services.history import get_recent_item_ids


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
