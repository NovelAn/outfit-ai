import json
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import update
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..models import Feedback, OutfitHistory, Profile
from ..schemas import FeedbackIn
from ..services.history import get_history_outfits, get_recent_outfits
from ..services.taste_memo import FEEDBACK_BATCH_SIZE, refresh

router = APIRouter(tags=["feedback"])
DbSession = Annotated[Session, Depends(get_db)]


@router.post("/feedback")
def feedback(
    payload: FeedbackIn,
    background_tasks: BackgroundTasks,
    db: DbSession,
):
    if payload.history_id:
        history = db.get(OutfitHistory, payload.history_id)
        if not history or history.user_id != settings.user_id:
            raise HTTPException(404, "推荐历史不存在")
        if payload.rating is not None:
            history.user_rating = payload.rating
        if payload.action == "worn":
            history.wore_it = True
            if history.action != "saved":
                history.action = "worn"
        elif payload.action is not None:
            history.action = payload.action
    row = Feedback(
        id=uuid4().hex,
        user_id=settings.user_id,
        items_worn_json=json.dumps(payload.items_worn),
        occasion=payload.occasion,
        occasion_type=payload.occasion_type,
        sentiment=payload.sentiment,
        compliments_json=json.dumps(payload.compliments, ensure_ascii=False),
        didnt_work=payload.didnt_work,
        learnings=payload.learnings,
    )
    db.add(row)
    db.execute(
        insert(Profile)
        .values(user_id=settings.user_id)
        .on_conflict_do_nothing(index_elements=[Profile.user_id])
    )
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
    return [
        {
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
            "scope": (
                "archive"
                if row.action == "saved" or row.wore_it or (row.user_rating or 0) >= 4
                else "recent"
            ),
        }
        for row in rows
    ]
