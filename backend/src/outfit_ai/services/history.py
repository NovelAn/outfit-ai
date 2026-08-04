import json
from datetime import date, timedelta
from uuid import uuid4

from sqlalchemy import delete, literal_column, or_, select
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


def _context(row: OutfitHistory) -> dict[str, object]:
    try:
        context = json.loads(row.context_json) if row.context_json else {}
    except (TypeError, ValueError):
        return {}
    return context if isinstance(context, dict) else {}


def _latest_complete_set(rows: list[OutfitHistory]) -> list[OutfitHistory]:
    tiers = ("safe", "fresh", "stretch")
    grouped: dict[str, dict[str, OutfitHistory]] = {}
    group_order: dict[str, tuple[str, int]] = {}
    legacy: dict[str, OutfitHistory] = {}
    for index, row in enumerate(rows):
        context = _context(row)
        set_id = context.get("recommendation_set_id")
        if isinstance(set_id, str) and set_id:
            grouped.setdefault(set_id, {}).setdefault(row.pick_mode, row)
            created_at = context.get("recommendation_set_created_at")
            created = created_at if isinstance(created_at, str) else ""
            group_order.setdefault(set_id, (created, -index))
        else:
            legacy.setdefault(row.pick_mode, row)
    complete = [
        set_id
        for set_id, looks in grouped.items()
        if all(tier in looks for tier in tiers)
    ]
    if complete:
        latest = max(complete, key=lambda set_id: group_order[set_id])
        return [grouped[latest][tier] for tier in tiers]
    if all(tier in legacy for tier in tiers):
        return [legacy[tier] for tier in tiers]
    return []


def get_latest_recommendation_set(
    db: Session, user_id: str, local_date: date
) -> list[OutfitHistory]:
    return _latest_complete_set(
        list(
            db.scalars(
                select(OutfitHistory)
                .where(
                    OutfitHistory.user_id == user_id,
                    OutfitHistory.date == local_date,
                    OutfitHistory.pick_mode.in_(("safe", "fresh", "stretch")),
                )
                .order_by(literal_column("outfit_history.rowid").desc())
            )
        )
    )


def get_history_outfits(
    db: Session, user_id: str, *, scope: str = "recent", limit: int = 20
) -> list[OutfitHistory]:
    statement = select(OutfitHistory).where(OutfitHistory.user_id == user_id)
    if scope == "archive":
        statement = statement.where(
            or_(
                OutfitHistory.action == "saved",
                OutfitHistory.wore_it.is_(True),
                OutfitHistory.user_rating >= 4,
            )
        )
    elif scope == "recent":
        statement = statement.where(
            OutfitHistory.action != "saved",
            OutfitHistory.wore_it.is_(False),
            or_(OutfitHistory.user_rating.is_(None), OutfitHistory.user_rating < 4),
        )
    else:
        raise ValueError("history scope 必须是 recent 或 archive")
    return list(
        db.scalars(
            statement.order_by(
                OutfitHistory.date.desc(), literal_column("outfit_history.rowid").desc()
            ).limit(limit)
        )
    )


def prune_temporary_history(
    db: Session, user_id: str, *, local_today: date | None = None
) -> int:
    cutoff = (local_today or date.today()) - timedelta(days=14)
    return db.execute(
        delete(OutfitHistory).where(
            OutfitHistory.user_id == user_id,
            OutfitHistory.date < cutoff,
            OutfitHistory.action != "saved",
            OutfitHistory.wore_it.is_(False),
            or_(OutfitHistory.user_rating.is_(None), OutfitHistory.user_rating < 4),
        )
    ).rowcount or 0


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
    prepared = []
    for row in rows:
        try:
            context = json.loads(row.context_json) if row.context_json else {}
        except (TypeError, ValueError):
            continue
        if not isinstance(context, dict):
            continue
        if row.action != "prepared" and context.get("prepared") is not True:
            continue
        prepared.append(row)
    return _latest_complete_set(prepared)


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
    recommendation_set_id: str | None = None,
) -> OutfitHistory:
    if recommendation_set_id:
        context = {
            **(context or {}),
            "recommendation_set_id": recommendation_set_id,
        }
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
