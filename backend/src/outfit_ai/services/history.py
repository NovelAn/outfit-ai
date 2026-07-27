import json
from uuid import uuid4

from sqlalchemy import literal_column, select
from sqlalchemy.orm import Session

from ..models import OutfitHistory, WardrobeItem
from ..schemas import ProposedLook
from .categories import canonical_category


def get_recent_outfits(db: Session, user_id: str, limit: int = 7) -> list[OutfitHistory]:
    # ponytail: SQLite rowid orders same-day rows; replace with created_at when approved.
    return list(
        db.scalars(
            select(OutfitHistory)
            .where(OutfitHistory.user_id == user_id)
            .order_by(
                OutfitHistory.date.desc(),
                literal_column("outfit_history.rowid").desc(),
            )
            .limit(limit)
        )
    )


def get_recent_item_ids(
    db: Session, user_id: str, *, limit: int = 3, skip_shoes: bool = True
) -> set[str]:
    outfits = get_recent_outfits(db, user_id, limit)
    ids = {item_id for outfit in outfits for item_id in json.loads(outfit.item_ids_json)}
    if not skip_shoes or not ids:
        return ids
    shoes = {
        item.id
        for item in db.scalars(select(WardrobeItem).where(WardrobeItem.id.in_(ids)))
        if canonical_category(item.category) == "shoes"
    }
    return ids - shoes


def record_outfit(
    db: Session,
    user_id: str,
    look: ProposedLook,
    *,
    occasion: str,
    mood: str | None,
    weather_summary: str,
    temp: float,
) -> OutfitHistory:
    history = OutfitHistory(
        id=uuid4().hex,
        user_id=user_id,
        occasion=occasion,
        mood=mood,
        weather_summary=weather_summary,
        temp=temp,
        item_ids_json=json.dumps(look.item_ids),
        pick_mode=look.tier,
        reason=look.reason,
        action="shown",
    )
    db.add(history)
    return history
