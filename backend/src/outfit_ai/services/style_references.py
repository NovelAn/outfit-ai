import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Profile, StyleReference
from ..schemas import StyleDnaMerge, StyleReferenceAnalysis
from .llm import generate_json
from .profile_state import (
    CANONICAL_PALETTE_NAMES,
    active_style_keywords,
    decode_profile_state,
)


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
    state = decode_profile_state(
        profile.learned_from_feedback_json if profile else "[]"
    )
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
        "recent_style_signals": state["recent_style_signals"],
        "style_tag_preferences": state["style_tag_preferences"],
    }
    merged = StyleDnaMerge.model_validate(
        generate_json(
            (
                "将新参考 Look 合并进长期 Style DNA。保留旧档案中仍有效的信息，允许多个"
                "风格方向并存，不根据单张图片推断身体、预算、品牌或人物身份。style_keywords"
                "只保留可复用、有图片证据的风格概念，最多 7 个；不要把单件衣物、场景或季节"
                "写成核心关键词。recent_style_signals 只记录最多 3 个较新的信号；palette"
                "只能使用黑色、白色、深蓝色、浅蓝色、灰色、米白色、米黄色、卡其色、棕色、"
                "绿色、红色、紫色，最多 5 个。"
            ),
            json.dumps(
                {"current_style_dna": current, "new_reference": analysis.model_dump()},
                ensure_ascii=False,
            ),
            (
                '{"style_keywords":[],"recent_style_signals":[],"palette":[],"preferred_colors":[],'
                '"preferred_styles":[],"avoids":[],"taste_memo":""}'
            ),
        )
    )
    preferences = state["style_tag_preferences"]
    model_keywords = active_style_keywords(
        merged.style_keywords,
        {**preferences, "pinned": []},
    )
    pinned = active_style_keywords([], {**preferences, "hidden": []})
    style_keywords = model_keywords[: 7 - len(pinned)]
    style_keywords.extend(tag for tag in pinned if tag not in style_keywords)
    return merged.model_copy(
        update={
            "style_keywords": style_keywords,
            "recent_style_signals": list(
                dict.fromkeys(merged.recent_style_signals)
            )[:3],
            "palette": [
                color
                for color in dict.fromkeys(merged.palette)
                if color in CANONICAL_PALETTE_NAMES
            ][:5],
        }
    )
