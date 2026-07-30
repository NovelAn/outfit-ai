import json
from io import BytesIO
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..models import WardrobeItem
from ..schemas import WardrobePatch
from ..services.background import background_path, display_image_path
from ..services.categories import canonical_category, confirmed_category
from ..services.collage import UnsafeImageError, render
from ..services.storage import ImageTooLargeError, LocalStorage
from ..workers.analysis import analyze_item

router = APIRouter(prefix="/wardrobe", tags=["wardrobe"])
storage = LocalStorage()
DbSession = Annotated[Session, Depends(get_db)]
ImageUpload = Annotated[UploadFile, File()]


def _item(item: WardrobeItem) -> dict:
    attributes = {
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
    }
    return {
        "id": item.id,
        **attributes,
        "image_url": f"/media/{display_image_path(item).name}",
        "status": item.status,
        "attempt_count": item.attempt_count,
        "confirmed_by_user": item.confirmed_by_user,
        "attributes": attributes if item.status == "ready" else None,
    }


def _get(db: Session, item_id: str) -> WardrobeItem:
    item = db.get(WardrobeItem, item_id)
    if not item or item.user_id != settings.user_id:
        raise HTTPException(404, "单品不存在")
    return item


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
    item = WardrobeItem(
        id=uuid4().hex,
        user_id=settings.user_id,
        image_path=str(path),
        status="pending",
    )
    db.add(item)
    try:
        db.commit()
    except Exception:
        db.rollback()
        storage.delete(str(path))
        raise
    background_tasks.add_task(analyze_item, item.id)
    return {"id": item.id, "status": item.status}


@router.get("/items")
def items(db: DbSession, category: str | None = None):
    query = select(WardrobeItem).where(
        WardrobeItem.user_id == settings.user_id,
        WardrobeItem.confirmed_by_user.is_(True),
    )
    found = list(db.scalars(query.order_by(WardrobeItem.added_at.desc())))
    if category:
        wanted = canonical_category(category)
        found = [item for item in found if canonical_category(item.category) == wanted]
    return [_item(item) for item in found]


@router.get("/collage")
def collage(item_ids: str, db: DbSession):
    ids = [value.strip() for value in item_ids.split(",") if value.strip()]
    if not 1 <= len(ids) <= 15 or len(ids) != len(set(ids)):
        raise HTTPException(422, "item_ids 需要 1–15 个唯一值")
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
    try:
        render([display_image_path(by_id[item_id]) for item_id in ids], output)
    except UnsafeImageError as exc:
        raise HTTPException(400, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return Response(output.getvalue(), media_type="image/png")


@router.get("/{item_id}/status")
def status(item_id: str, db: DbSession):
    return _item(_get(db, item_id))


@router.get("/{item_id}")
def detail(item_id: str, db: DbSession):
    return _item(_get(db, item_id))


@router.patch("/{item_id}")
def patch(item_id: str, payload: WardrobePatch, db: DbSession):
    return _update(item_id, payload, db)


def _update(
    item_id: str,
    payload: WardrobePatch,
    db: Session,
    *,
    confirm: bool = False,
):
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
    if data.get("category") is not None:
        data["category"] = canonical_category(data["category"])
    if confirm or data.get("confirmed_by_user") is True:
        try:
            data["category"] = confirmed_category(data.get("category", item.category))
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        data["confirmed_by_user"] = True
    for field, value in data.items():
        setattr(item, field, value)
    db.commit()
    return _item(item)


@router.post("/{item_id}/confirm")
def confirm(item_id: str, payload: WardrobePatch, db: DbSession):
    return _update(item_id, payload, db, confirm=True)


@router.post("/{item_id}/retry", status_code=202)
def retry(
    item_id: str, background_tasks: BackgroundTasks, db: DbSession
):
    item = _get(db, item_id)
    if item.status != "failed":
        raise HTTPException(409, "仅失败任务可重试")
    item.status = "pending"
    db.commit()
    background_tasks.add_task(analyze_item, item.id)
    return {"id": item.id, "status": item.status}


@router.delete("/{item_id}", status_code=204)
def delete(item_id: str, db: DbSession):
    item = _get(db, item_id)
    image_path = item.image_path
    db.delete(item)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    storage.delete(image_path)
    storage.delete(str(background_path(image_path)))
