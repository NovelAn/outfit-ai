import json

from sqlalchemy import update

from ..db import SessionLocal
from ..models import WardrobeItem
from ..services.background import ensure_background_removed
from ..services.categories import canonical_category
from ..services.vision import extract

THICKNESS_TAGS = {"轻薄", "适中", "厚实"}


def analyze_item(item_id: str) -> None:
    with SessionLocal() as db:
        claimed = db.scalar(
            update(WardrobeItem)
            .where(
                WardrobeItem.id == item_id,
                WardrobeItem.status == "pending",
            )
            .values(
                status="analyzing",
                attempt_count=WardrobeItem.attempt_count + 1,
            )
            .returning(WardrobeItem.id)
        )
        db.commit()
        if not claimed:
            return
        item = db.get(WardrobeItem, item_id)
        if not item:
            return
        try:
            analysis_path = ensure_background_removed(item.image_path)
            attributes, raw = extract(analysis_path)
            for field in (
                "name",
                "category",
                "primary_color",
                "secondary_color",
                "material",
                "fit",
                "formality",
                "versatility",
            ):
                setattr(item, field, getattr(attributes, field))
            item.category = canonical_category(attributes.category)
            tags = [tag for tag in attributes.tags if tag not in THICKNESS_TAGS]
            thickness = attributes.thickness or next(
                (tag for tag in attributes.tags if tag in THICKNESS_TAGS), None
            )
            if thickness:
                tags.append(thickness)
            for source, target in (
                ("styles", "style_json"),
                ("seasons", "seasons_json"),
                ("occasions", "occasions_json"),
            ):
                setattr(item, target, json.dumps(getattr(attributes, source), ensure_ascii=False))
            item.tags_json = json.dumps(tags, ensure_ascii=False)
            item.ai_raw_response = raw
            item.status = "ready"
        except Exception as exc:
            item.ai_raw_response = str(exc)[:2000]
            item.status = "failed"
        db.commit()
