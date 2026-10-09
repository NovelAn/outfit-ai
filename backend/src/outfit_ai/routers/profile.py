import json
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..models import Profile
from ..schemas import ProfileIn, ProfileOut, StyleDnaDraftRequest, TasteMemoCorrectionIn
from ..services.llm import LLMResponseError, LLMUnavailableError, require_api_key
from ..services.profile_state import decode_profile_state, encode_profile_state
from ..services.taste_memo import FEEDBACK_BATCH_SIZE, refresh, seed

router = APIRouter(prefix="/profile", tags=["profile"])
DbSession = Annotated[Session, Depends(get_db)]


def _out(profile: Profile) -> dict:
    state = decode_profile_state(profile.learned_from_feedback_json or "[]")
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
        "budget_top_cents": profile.budget_top_cents,
        "budget_bottom_cents": profile.budget_bottom_cents,
        "budget_outerwear_cents": profile.budget_outerwear_cents,
        "learned_from_feedback": state["learnings"],
        "recent_style_signals": state["recent_style_signals"],
        "style_tag_preferences": state["style_tag_preferences"],
        "last_location": state["last_location"],
        "formulas": json.loads(profile.formulas_json or "[]"),
        "taste_memo": profile.taste_memo,
        "taste_memo_updated_at": profile.taste_memo_updated_at,
        "feedback_since_refresh": profile.feedback_since_refresh or 0,
        "feedback_batch_size": FEEDBACK_BATCH_SIZE,
        "feedback_remaining": max(0, FEEDBACK_BATCH_SIZE - (profile.feedback_since_refresh or 0)),
        "taste_memo_last_change": profile.taste_memo_last_change or "",
        "taste_memo_source_feedback_ids": json.loads(
            profile.taste_memo_source_feedback_ids_json or "[]"
        ),
        "taste_memo_source_event_ids": json.loads(
            profile.taste_memo_source_event_ids_json or "[]"
        ),
        "taste_memo_refresh_status": profile.taste_memo_refresh_status or "idle",
        "taste_memo_refresh_error": profile.taste_memo_refresh_error,
        "taste_memo_revision": profile.taste_memo_revision or 0,
    }


def _save(db: Session, payload: ProfileIn) -> Profile:
    profile = db.get(Profile, settings.user_id) or Profile(user_id=settings.user_id)
    data = payload.model_dump()
    state = decode_profile_state(profile.learned_from_feedback_json or "[]")
    for source, target in (
        ("body", "body_json"),
        ("palette", "palette_json"),
        ("style_keywords", "style_keywords_json"),
        ("avoids", "avoids_json"),
        ("preferred_colors", "preferred_colors_json"),
        ("preferred_styles", "preferred_styles_json"),
        ("brand_sizes", "brand_sizes_json"),
        ("occasions", "occasions_json"),
        ("formulas", "formulas_json"),
    ):
        setattr(profile, target, json.dumps(data.pop(source), ensure_ascii=False))
    recent_style_signals = data.pop("recent_style_signals")
    style_tag_preferences = data.pop("style_tag_preferences")
    last_location = data.pop("last_location")
    # taste_memo is service-owned. It remains accepted for Style DNA drafts and
    # older clients, but a normal Profile PUT can never overwrite it.
    data.pop("taste_memo", None)
    profile.learned_from_feedback_json = encode_profile_state(
        learnings=data.pop("learned_from_feedback"),
        recent_style_signals=(
            recent_style_signals
            if "recent_style_signals" in payload.model_fields_set
            else state["recent_style_signals"]
        ),
        style_tag_preferences=(
            style_tag_preferences
            if "style_tag_preferences" in payload.model_fields_set
            else state["style_tag_preferences"]
        ),
        last_location=(
            last_location
            if "last_location" in payload.model_fields_set
            else state["last_location"]
        ),
    )
    for field, value in data.items():
        setattr(profile, field, value)
    db.add(profile)
    db.commit()
    return profile


@router.get("")
def get_profile(db: DbSession):
    profile = db.get(Profile, settings.user_id)
    if profile:
        return _out(profile)
    return ProfileOut(user_id=settings.user_id).model_dump()


@router.put("")
def put_profile(payload: ProfileIn, db: DbSession):
    return _out(_save(db, payload))


@router.post("/style-dna/draft")
def draft(payload: StyleDnaDraftRequest):
    try:
        generated = seed(payload.samples, payload.text)
    except LLMUnavailableError as exc:
        raise HTTPException(503, str(exc)) from exc
    except LLMResponseError as exc:
        raise HTTPException(502, str(exc)) from exc
    return {
        "draft": ProfileOut(
            user_id=settings.user_id,
            **generated.model_dump(),
        ).model_dump()
    }


@router.post("/taste-memo/refresh", status_code=202)
def refresh_memo(background_tasks: BackgroundTasks):
    try:
        require_api_key()
    except LLMUnavailableError as exc:
        raise HTTPException(503, str(exc)) from exc
    background_tasks.add_task(refresh, settings.user_id, True)
    return {"ok": True}


@router.post("/taste-memo/retry", status_code=202)
def retry_memo(background_tasks: BackgroundTasks):
    try:
        require_api_key()
    except LLMUnavailableError as exc:
        raise HTTPException(503, str(exc)) from exc
    background_tasks.add_task(refresh, settings.user_id, True)
    return {"ok": True}


@router.post("/taste-memo/correct")
def correct_memo(payload: TasteMemoCorrectionIn, db: DbSession):
    profile = db.get(Profile, settings.user_id) or Profile(user_id=settings.user_id)
    profile.taste_memo = payload.taste_memo.strip()
    profile.taste_memo_updated_at = datetime.now()
    profile.taste_memo_last_change = "用户手动修正品味备忘录"
    profile.taste_memo_refresh_status = "idle"
    profile.taste_memo_refresh_error = None
    profile.taste_memo_revision = (profile.taste_memo_revision or 0) + 1
    db.add(profile)
    db.commit()
    return _out(profile)
