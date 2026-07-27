import json
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..models import WardrobeItem
from ..schemas import WardrobePatch
from ..services.collage import render
from ..services.storage import LocalStorage
from ..workers.analysis import analyze_item

router = APIRouter(prefix="/wardrobe", tags=["wardrobe"])
storage = LocalStorage()


def _item(item: WardrobeItem) -> dict:
    return {
        "id": item.id,
        "name": item.name,
        "category": item.category,
        "primary_color": item.primary_color,
        "secondary_color": item.secondary_color,
        "material": item.material,
        "fit": item.fit,
        "formality": item.formality,
        "styles": json.loads(item.style_json or "[]"),
        "tags": json.loads(item.tags_json or "[]"),
        "seasons": json.loads(item.seasons_json or "[]"),
        "occasions": json.loads(item.occasions_json or "[]"),
        "versatility": item.versatility,
        "brand": item.brand,
        "size": item.size,
        "image_url": f"/media/{Path(item.image_path).name}",
        "status": item.status,
        "attempt_count": item.attempt_count,
        "confirmed_by_user": item.confirmed_by_user,
    }


def _get(db: Session, item_id: str) -> WardrobeItem:
    item = db.get(WardrobeItem, item_id)
    if not item or item.user_id != settings.user_id:
        raise HTTPException(404, "单品不存在")
    return item


@router.post("/upload", status_code=201)
def upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if file.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(415, "仅支持 JPEG、PNG、WebP")
    try:
        path = storage.save(file)
    except ValueError as exc:
        raise HTTPException(413, str(exc)) from exc
    item = WardrobeItem(
        id=uuid4().hex,
        user_id=settings.user_id,
        image_path=str(path),
        status="pending",
    )
    db.add(item)
    db.commit()
    background_tasks.add_task(analyze_item, item.id)
    return {"id": item.id, "status": item.status}


@router.get("/items")
def items(category: str | None = None, db: Session = Depends(get_db)):
    query = select(WardrobeItem).where(
        WardrobeItem.user_id == settings.user_id,
        WardrobeItem.confirmed_by_user.is_(True),
    )
    if category:
        query = query.where(WardrobeItem.category == category)
    return [_item(item) for item in db.scalars(query.order_by(WardrobeItem.added_at.desc()))]


@router.get("/collage")
def collage(item_ids: str, db: Session = Depends(get_db)):
    ids = [value for value in item_ids.split(",") if value]
    found = list(
        db.scalars(
            select(WardrobeItem).where(
                WardrobeItem.user_id == settings.user_id, WardrobeItem.id.in_(ids)
            )
        )
    )
    if len(found) != len(set(ids)):
        raise HTTPException(404, "部分单品不存在")
    by_id = {item.id: item for item in found}
    output = BytesIO()
    render([by_id[item_id].image_path for item_id in ids], output)
    return Response(output.getvalue(), media_type="image/png")


@router.get("/{item_id}/status")
def status(item_id: str, db: Session = Depends(get_db)):
    return _item(_get(db, item_id))


@router.get("/{item_id}")
def detail(item_id: str, db: Session = Depends(get_db)):
    return _item(_get(db, item_id))


@router.patch("/{item_id}")
def patch(item_id: str, payload: WardrobePatch, db: Session = Depends(get_db)):
    item = _get(db, item_id)
    data = payload.model_dump(exclude_unset=True)
    for source, target in (
        ("styles", "style_json"),
        ("tags", "tags_json"),
        ("seasons", "seasons_json"),
        ("occasions", "occasions_json"),
    ):
        if source in data:
            data[target] = json.dumps(data.pop(source), ensure_ascii=False)
    for field, value in data.items():
        setattr(item, field, value)
    db.commit()
    return _item(item)


@router.post("/{item_id}/retry", status_code=202)
def retry(
    item_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    item = _get(db, item_id)
    stuck = item.status == "analyzing" and item.added_at < datetime.now() - timedelta(minutes=10)
    if item.status != "failed" and not stuck:
        raise HTTPException(409, "仅失败或卡住的任务可重试")
    item.status = "pending"
    db.commit()
    background_tasks.add_task(analyze_item, item.id)
    return {"id": item.id, "status": item.status}


@router.delete("/{item_id}", status_code=204)
def delete(item_id: str, db: Session = Depends(get_db)):
    item = _get(db, item_id)
    storage.delete(item.image_path)
    db.delete(item)
    db.commit()
