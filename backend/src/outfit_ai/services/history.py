import json
from datetime import date
from uuid import uuid4

from sqlalchemy import literal_column, select
from sqlalchemy.orm import Session

from ..models import OutfitHistory, WardrobeItem
from ..schemas import OutfitHistoryAction, ProposedLook
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


def get_prepared_outfits(
    db: Session, user_id: str, local_date: date
) -> list[OutfitHistory]:
    tiers = ("safe", "fresh", "stretch")
    rows = db.scalars(
        select(OutfitHistory)
        .where(
            OutfitHistory.user_id == user_id,
            OutfitHistory.date == local_date,
            OutfitHistory.pick_mode.in_(tiers),
        )
        .order_by(literal_column("outfit_history.rowid").desc())
    )
    latest_by_tier = {}
    for row in rows:
        try:
            context = json.loads(row.context_json) if row.context_json else {}
        except (TypeError, ValueError):
            continue
        if not isinstance(context, dict):
            continue
        if row.action != "prepared" and context.get("prepared") is not True:
            continue
        latest_by_tier.setdefault(row.pick_mode, row)
    if any(tier not in latest_by_tier for tier in tiers):
        return []
    return [latest_by_tier[tier] for tier in tiers]


def record_outfit(
    db: Session,
    user_id: str,
    look: ProposedLook,
    *,
    occasion: str,
    mood: str | None,
    weather_summary: str,
    temp: float,
    action: OutfitHistoryAction = "shown",
    context: dict[str, object] | None = None,
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
        action=action,
        context_json=json.dumps(context, ensure_ascii=False) if context is not None else None,
    )
    db.add(history)
    return history
