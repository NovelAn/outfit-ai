import json
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..models import Feedback, OutfitHistory, Profile
from ..schemas import FeedbackIn
from ..services.taste_memo import refresh

router = APIRouter(tags=["feedback"])


@router.post("/feedback")
def feedback(
    payload: FeedbackIn,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    if payload.history_id:
        history = db.get(OutfitHistory, payload.history_id)
        if not history or history.user_id != settings.user_id:
            raise HTTPException(404, "推荐历史不存在")
        history.action = payload.action
        history.wore_it = payload.action == "worn"
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
    profile = db.get(Profile, settings.user_id) or Profile(user_id=settings.user_id)
    profile.feedback_since_refresh += 1
    db.add(profile)
    should_refresh = profile.feedback_since_refresh >= 8
    db.commit()
    if should_refresh:
        background_tasks.add_task(refresh, settings.user_id)
    return {"ok": True}


@router.get("/history")
def history(limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(OutfitHistory)
        .where(OutfitHistory.user_id == settings.user_id)
        .order_by(OutfitHistory.date.desc())
        .limit(limit)
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
        }
        for row in rows
    ]
