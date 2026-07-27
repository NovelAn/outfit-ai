import json
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import OutfitHistory, WardrobeItem
from ..schemas import ProposedLook


def get_recent_outfits(db: Session, user_id: str, limit: int = 7) -> list[OutfitHistory]:
    return list(
        db.scalars(
            select(OutfitHistory)
            .where(OutfitHistory.user_id == user_id)
            .order_by(OutfitHistory.date.desc())
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
    shoes = set(
        db.scalars(
            select(WardrobeItem.id).where(
                WardrobeItem.id.in_(ids), WardrobeItem.category.in_(["shoe", "shoes"])
            )
        )
    )
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
