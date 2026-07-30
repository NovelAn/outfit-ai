import json
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..models import StyleReference
from ..services.storage import ImageTooLargeError, LocalStorage
from ..workers.style_references import process_reference

router = APIRouter(prefix="/style-references", tags=["style-references"])
storage = LocalStorage()
DbSession = Annotated[Session, Depends(get_db)]
ImageUpload = Annotated[UploadFile, File()]


def _out(reference: StyleReference) -> dict:
    return {
        "id": reference.id,
        "image_url": f"/media/{Path(reference.image_path).name}",
        "status": reference.status,
        "attempt_count": reference.attempt_count,
        "analysis": (
            json.loads(reference.analysis_json)
            if reference.analysis_json and reference.status == "ready"
            else None
        ),
        "added_at": reference.added_at,
    }


def _get(db: Session, reference_id: str) -> StyleReference:
    reference = db.get(StyleReference, reference_id)
    if not reference or reference.user_id != settings.user_id:
        raise HTTPException(404, "参考 Look 不存在")
    return reference


@router.post("/upload", status_code=201)
def upload(
    background_tasks: BackgroundTasks,
    file: ImageUpload,
    db: DbSession,
):
    if file.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(415, "仅支持 JPEG、PNG、WebP")
    try:
        path = storage.save(file)
    except ImageTooLargeError as exc:
        raise HTTPException(413, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    reference = StyleReference(
        id=uuid4().hex,
        user_id=settings.user_id,
        image_path=str(path),
        status="pending",
    )
    db.add(reference)
    try:
        db.commit()
    except Exception:
        db.rollback()
        storage.delete(str(path))
        raise
    background_tasks.add_task(process_reference, reference.id)
    return {"id": reference.id, "status": reference.status}


@router.get("")
def references(db: DbSession):
    found = list(
        db.scalars(
            select(StyleReference)
            .where(StyleReference.user_id == settings.user_id)
            .order_by(StyleReference.added_at.desc())
        )
    )
    return [_out(reference) for reference in found]


@router.get("/{reference_id}/status")
def status(reference_id: str, db: DbSession):
    return _out(_get(db, reference_id))


@router.post("/{reference_id}/retry", status_code=202)
def retry(
    reference_id: str,
    background_tasks: BackgroundTasks,
    db: DbSession,
):
    reference = _get(db, reference_id)
    if reference.status != "failed":
        raise HTTPException(409, "仅失败任务可重试")
    reference.status = "pending"
    db.commit()
    background_tasks.add_task(process_reference, reference.id)
    return {"id": reference.id, "status": reference.status}


@router.delete("/{reference_id}", status_code=204)
def delete(reference_id: str, db: DbSession):
    reference = _get(db, reference_id)
    image_path = reference.image_path
    db.delete(reference)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    storage.delete(image_path)
