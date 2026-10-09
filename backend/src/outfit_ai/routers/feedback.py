import json
import re
from datetime import date, datetime
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import literal_column, select, update
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..models import Feedback, FeedbackEvent, OutfitHistory, Profile
from ..schemas import FeedbackIn
from ..services.history import get_history_outfits, get_recent_outfits
from ..services.taste_memo import FEEDBACK_BATCH_SIZE, refresh

router = APIRouter(tags=["feedback"])
DbSession = Annotated[Session, Depends(get_db)]


def _json_list(value: str | None) -> list:
    try:
        decoded = json.loads(value or "[]")
    except (TypeError, ValueError):
        return []
    return decoded if isinstance(decoded, list) else []


def _feedback_state(row: Feedback | None) -> dict:
    if not row:
        return {
            "items_worn": [],
            "action": None,
            "rating": None,
            "sentiment": None,
            "positive_signals": [],
            "negative_signals": [],
            "adjustment_signals": [],
            "didnt_work": None,
            "learnings": None,
            "wore_it": False,
        }
    positive = _json_list(row.positive_signals_json)
    if not positive:
        positive = _json_list(row.compliments_json)
    return {
        "items_worn": _json_list(row.items_worn_json),
        "action": row.action,
        "rating": row.rating,
        "sentiment": row.sentiment,
        "positive_signals": positive,
        "negative_signals": _json_list(row.negative_signals_json),
        "adjustment_signals": _json_list(row.adjustment_signals_json),
        "didnt_work": row.didnt_work,
        "learnings": row.learnings,
        "wore_it": row.wore_it,
    }


def _has_learning_signal(payload: FeedbackIn) -> bool:
    fields = payload.model_fields_set
    return bool(
        payload.action
        or payload.rating is not None
        or payload.sentiment
        or payload.compliments
        or payload.negative_signals
        or payload.adjustment_signals
        or payload.didnt_work
        or payload.learnings
        or "items_worn" in fields and payload.items_worn
    )


@router.post("/feedback")
def feedback(
    payload: FeedbackIn,
    background_tasks: BackgroundTasks,
    db: DbSession,
):
    history = None
    existing = None
    if payload.history_id:
        history = db.get(OutfitHistory, payload.history_id)
        if not history or history.user_id != settings.user_id:
            raise HTTPException(404, "推荐历史不存在")
        existing = db.scalar(
            select(Feedback)
            .where(
                Feedback.user_id == settings.user_id,
                Feedback.history_id == payload.history_id,
            )
            .order_by(
                Feedback.created_at.desc(),
                literal_column("feedback.rowid").desc(),
            )
        )
    before = _feedback_state(existing)

    rating = payload.rating
    if rating is None and payload.sentiment:
        match = re.search(r"([1-5])\s*星", payload.sentiment)
        rating = int(match.group(1)) if match else None

    if history:
        if rating is not None:
            history.user_rating = rating
        if payload.action == "worn":
            history.wore_it = True
            if history.action != "saved":
                history.action = "worn"
        elif payload.action is not None:
            history.action = payload.action

    after = {
        "items_worn": (
            payload.items_worn
            if "items_worn" in payload.model_fields_set
            else before["items_worn"]
        ),
        "action": (
            payload.action
            if "action" in payload.model_fields_set
            else (before["action"] if existing else history.action if history else None)
        ),
        "rating": rating if rating is not None else before["rating"],
        "sentiment": (
            payload.sentiment
            if "sentiment" in payload.model_fields_set
            else before["sentiment"]
        ),
        "positive_signals": (
            payload.compliments
            if "compliments" in payload.model_fields_set
            else before["positive_signals"]
        ),
        "negative_signals": (
            payload.negative_signals
            if "negative_signals" in payload.model_fields_set
            else before["negative_signals"]
        ),
        "adjustment_signals": (
            payload.adjustment_signals
            if "adjustment_signals" in payload.model_fields_set
            else before["adjustment_signals"]
        ),
        "didnt_work": (
            payload.didnt_work
            if "didnt_work" in payload.model_fields_set
            else before["didnt_work"]
        ),
        "learnings": (
            payload.learnings
            if "learnings" in payload.model_fields_set
            else before["learnings"]
        ),
        "wore_it": history.wore_it if history else payload.action == "worn",
    }
    changed = after != before

    if existing:
        row = existing
    else:
        row = Feedback(id=uuid4().hex, user_id=settings.user_id)
        db.add(row)
    row.history_id = payload.history_id
    row.date = history.date if history else date.today()
    row.items_worn_json = json.dumps(after["items_worn"], ensure_ascii=False)
    row.action = after["action"]
    row.rating = after["rating"]
    row.occasion = payload.occasion if "occasion" in payload.model_fields_set else None
    row.occasion_type = (
        payload.occasion_type
        if "occasion_type" in payload.model_fields_set
        else None
    )
    row.sentiment = after["sentiment"]
    row.positive_signals_json = json.dumps(after["positive_signals"], ensure_ascii=False)
    row.negative_signals_json = json.dumps(after["negative_signals"], ensure_ascii=False)
    row.adjustment_signals_json = json.dumps(after["adjustment_signals"], ensure_ascii=False)
    row.compliments_json = row.positive_signals_json
    row.didnt_work = after["didnt_work"]
    row.learnings = after["learnings"]
    row.wore_it = after["wore_it"]
    learning_changed = changed and _has_learning_signal(payload)
    if changed or existing is None:
        row.updated_at = datetime.now()
    if learning_changed:
        db.add(
            FeedbackEvent(
                id=uuid4().hex,
                feedback_id=row.id,
                user_id=settings.user_id,
                history_id=row.history_id,
                date=row.date,
                event_at=row.updated_at,
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
        )
    db.execute(
        insert(Profile)
        .values(user_id=settings.user_id)
        .on_conflict_do_nothing(index_elements=[Profile.user_id])
    )
    count = (
        db.scalar(
            select(Profile.feedback_since_refresh).where(
                Profile.user_id == settings.user_id
            )
        )
        or 0
    )
    if learning_changed:
        count = db.scalar(
            update(Profile)
            .where(Profile.user_id == settings.user_id)
            .values(feedback_since_refresh=Profile.feedback_since_refresh + 1)
            .returning(Profile.feedback_since_refresh)
        )
    db.commit()
    if count is not None and count >= FEEDBACK_BATCH_SIZE:
        background_tasks.add_task(refresh, settings.user_id)
    return {"ok": True}


@router.get("/history")
def history(
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    scope: Literal["recent", "archive"] | None = None,
):
    rows = (
        get_history_outfits(db, settings.user_id, scope=scope, limit=limit)
        if scope
        else get_recent_outfits(db, settings.user_id, limit)
    )
    history_ids = [row.id for row in rows]
    feedback_rows = list(
        db.scalars(
            select(Feedback)
            .where(
                Feedback.user_id == settings.user_id,
                Feedback.history_id.in_(history_ids),
            )
            .order_by(literal_column("feedback.rowid").desc())
        )
    ) if history_ids else []
    feedback_by_history = {row.history_id: row for row in feedback_rows}

    result = []
    for row in rows:
        matched = feedback_by_history.get(row.id)
        matched_state = _feedback_state(matched)
        result.append({
            "id": row.id,
            "date": row.date,
            "item_ids": json.loads(row.item_ids_json),
            "pick_mode": row.pick_mode,
            "occasion": row.occasion,
            "mood": row.mood,
            "reason": row.reason,
            "collage_path": row.collage_path,
            "action": row.action,
            "wore_it": row.wore_it,
            "rating": row.user_rating,
            "feedback": (
                {
                    "history_id": matched.history_id,
                    "action": matched.action,
                    "rating": matched.rating,
                    "created_at": matched.created_at,
                    "sentiment": matched.sentiment,
                    "compliments": matched_state["positive_signals"],
                    "positive_signals": matched_state["positive_signals"],
                    "negative_signals": matched_state["negative_signals"],
                    "adjustment_signals": matched_state["adjustment_signals"],
                    "didnt_work": matched.didnt_work,
                    "learnings": matched.learnings,
                }
                if matched
                else None
            ),
            "scope": (
                "archive"
                if row.action == "saved" or row.wore_it or (row.user_rating or 0) >= 4
                else "recent"
            ),
        })
    return result
