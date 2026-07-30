import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Profile, StyleReference
from ..schemas import StyleDnaMerge, StyleReferenceAnalysis
from .llm import generate_json


def get_reference_analyses(db: Session, reference_ids: list[str]) -> list[dict]:
    if not reference_ids:
        return []
    if len(reference_ids) != len(set(reference_ids)):
        raise ValueError("参考 Look 不能重复选择")
    found = list(
        db.scalars(
            select(StyleReference).where(
                StyleReference.user_id == settings.user_id,
                StyleReference.id.in_(reference_ids),
                StyleReference.status == "ready",
            )
        )
    )
    by_id = {reference.id: reference for reference in found}
    if set(by_id) != set(reference_ids):
        raise ValueError("部分参考 Look 不存在或仍在分析")
    return [json.loads(by_id[reference_id].analysis_json) for reference_id in reference_ids]


def merge_style_dna(
    profile: Profile | None, analysis: StyleReferenceAnalysis
) -> StyleDnaMerge:
    current = {
        "style_keywords": json.loads(profile.style_keywords_json or "[]") if profile else [],
        "palette": json.loads(profile.palette_json or "[]") if profile else [],
        "preferred_colors": (
            json.loads(profile.preferred_colors_json or "[]") if profile else []
        ),
        "preferred_styles": (
            json.loads(profile.preferred_styles_json or "[]") if profile else []
        ),
        "avoids": json.loads(profile.avoids_json or "[]") if profile else [],
        "taste_memo": profile.taste_memo if profile else "",
    }
    return StyleDnaMerge.model_validate(
        generate_json(
            (
                "将新参考 Look 合并进长期 Style DNA。保留旧档案中仍有效的信息，允许多个"
                "风格方向并存，不根据单张图片推断身体、预算、品牌或人物身份。"
            ),
            json.dumps(
                {"current_style_dna": current, "new_reference": analysis.model_dump()},
                ensure_ascii=False,
            ),
            (
                '{"style_keywords":[],"palette":[],"preferred_colors":[],'
                '"preferred_styles":[],"avoids":[],"taste_memo":""}'
            ),
        )
    )
