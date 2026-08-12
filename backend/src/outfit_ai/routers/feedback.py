import json
import re
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import literal_column, select, update
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..models import Feedback, OutfitHistory, Profile
from ..schemas import FeedbackIn
from ..services.history import get_recent_outfits
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
        history.action = payload.action
        history.wore_it = payload.action == "worn"
        rating = re.search(r"([1-5])\s*星", payload.sentiment or "")
        if rating:
            history.user_rating = int(rating.group(1))
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
def history(db: DbSession, limit: Annotated[int, Query(ge=1, le=100)] = 20):
    rows = get_recent_outfits(db, settings.user_id, limit)
    dates = {row.date for row in rows}
    feedback_rows = list(
        db.scalars(
            select(Feedback)
            .where(Feedback.user_id == settings.user_id, Feedback.date.in_(dates))
            .order_by(literal_column("feedback.rowid").desc())
        )
    ) if dates else []

    def feedback_for(row: OutfitHistory) -> Feedback | None:
        target = tuple(sorted(json.loads(row.item_ids_json or "[]")))
        for candidate in feedback_rows:
            if candidate.date != row.date:
                continue
            if tuple(sorted(json.loads(candidate.items_worn_json or "[]"))) == target:
                return candidate
        return None

    result = []
    for row in rows:
        matched = feedback_for(row)
        rating = row.user_rating
        if rating is None and matched:
            match = re.search(r"([1-5])\s*星", matched.sentiment or "")
            rating = int(match.group(1)) if match else None
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
            "rating": rating,
            "feedback": (
                {
                    "sentiment": matched.sentiment,
                    "compliments": json.loads(matched.compliments_json or "[]"),
                    "didnt_work": matched.didnt_work,
                    "learnings": matched.learnings,
                }
                if matched
                else None
            ),
        })
    return result
