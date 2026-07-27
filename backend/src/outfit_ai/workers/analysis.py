import json

from ..db import SessionLocal
from ..models import WardrobeItem
from ..services.categories import canonical_category
from ..services.vision import extract


def analyze_item(item_id: str) -> None:
    with SessionLocal() as db:
        item = db.get(WardrobeItem, item_id)
        if not item:
            return
        item.status = "analyzing"
        item.attempt_count += 1
        db.commit()
        try:
            attributes, raw = extract(item.image_path)
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
            for source, target in (
                ("styles", "style_json"),
                ("tags", "tags_json"),
                ("seasons", "seasons_json"),
                ("occasions", "occasions_json"),
            ):
                setattr(item, target, json.dumps(getattr(attributes, source), ensure_ascii=False))
            item.ai_raw_response = raw
            item.status = "ready"
        except Exception as exc:
            item.ai_raw_response = str(exc)[:2000]
            item.status = "failed"
        db.commit()
