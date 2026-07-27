import json
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..models import Profile
from ..schemas import ProfileIn
from ..services.taste_memo import refresh, seed

router = APIRouter(prefix="/profile", tags=["profile"])


def _out(profile: Profile) -> dict:
    return {
        "user_id": profile.user_id,
        "body": json.loads(profile.body_json or "{}"),
        "color_season": profile.color_season,
        "color_undertone": profile.color_undertone,
        "palette": json.loads(profile.palette_json or "[]"),
        "style_keywords": json.loads(profile.style_keywords_json or "[]"),
        "avoids": json.loads(profile.avoids_json or "[]"),
        "preferred_colors": json.loads(profile.preferred_colors_json or "[]"),
        "preferred_styles": json.loads(profile.preferred_styles_json or "[]"),
        "brand_sizes": json.loads(profile.brand_sizes_json or "{}"),
        "city": profile.city,
        "climate": profile.climate,
        "occasions": json.loads(profile.occasions_json or "[]"),
        "taste_memo": profile.taste_memo,
        "taste_memo_updated_at": profile.taste_memo_updated_at,
        "feedback_since_refresh": profile.feedback_since_refresh,
    }


def _save(db: Session, payload: ProfileIn) -> Profile:
    profile = db.get(Profile, settings.user_id) or Profile(user_id=settings.user_id)
    data = payload.model_dump()
    for source, target in (
        ("body", "body_json"),
        ("palette", "palette_json"),
        ("style_keywords", "style_keywords_json"),
        ("avoids", "avoids_json"),
        ("preferred_colors", "preferred_colors_json"),
        ("preferred_styles", "preferred_styles_json"),
        ("brand_sizes", "brand_sizes_json"),
        ("occasions", "occasions_json"),
    ):
        setattr(profile, target, json.dumps(data.pop(source), ensure_ascii=False))
    for field, value in data.items():
        setattr(profile, field, value)
    db.add(profile)
    db.commit()
    return profile


@router.get("")
def get_profile(db: Session = Depends(get_db)):
    profile = db.get(Profile, settings.user_id)
    return _out(profile) if profile else _out(_save(db, ProfileIn()))


@router.put("")
def put_profile(payload: ProfileIn, db: Session = Depends(get_db)):
    return _out(_save(db, payload))


@router.post("/style-dna/draft")
def draft(payload: ProfileIn, db: Session = Depends(get_db)):
    data = payload.model_dump()
    data["taste_memo"] = seed(data)
    profile = _save(db, ProfileIn.model_validate(data))
    profile.taste_memo_updated_at = datetime.now()
    db.commit()
    return {"draft": _out(profile)}


@router.post("/taste-memo/refresh", status_code=202)
def refresh_memo(background_tasks: BackgroundTasks):
    background_tasks.add_task(refresh, settings.user_id)
    return {"ok": True}
