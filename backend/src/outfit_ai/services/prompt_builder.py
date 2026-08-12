import json
from typing import Any

from .profile_state import active_style_keywords, decode_profile_state


def style_dna_messages(samples: list[str], text: str) -> list[dict[str, Any]]:
    content: list[dict[str, Any]] = [
        {
            "type": "text",
            "text": (
                "根据用户文字和风格参考图生成可编辑 Style DNA 与初版 taste_memo。"
                "只总结明确证据，不杜撰身体、预算或品牌信息。"
                f"\n用户描述：{text or '未提供'}"
            ),
        }
    ]
    content.extend(
        {"type": "image_url", "image_url": {"url": sample}} for sample in samples
    )
    return [
        {
            "role": "system",
            "content": "你是克制的个人风格档案编辑，输出中文，偏好要具体可执行。",
        },
        {"role": "user", "content": content},
    ]


def stylist_system(locked_ids: set[str], tier: str | None = None) -> str:
    locked = ", ".join(sorted(locked_ids)) or "无"
    target = f"只生成 {tier} 这一档，不要生成其它档位；" if tier else ""
    output = (
        "必须给出 safe、fresh、stretch 各一套；"
        if not tier
        else f"必须给出 tier 为 {tier} 的一套；"
    )
    return (
        "你是一位克制、懂个人风格的造型师。只能使用候选 item_id；"
        f"{target}{output}每套 3–6 件，必须包含 top、bottom、shoes。"
        "天气需要时可加叠穿，配饰可选；不要为了凑数量加入无作用的单品。"
        f"锁定单品必须出现：{locked}。"
    )


def stylist_context(
    candidates: list[Any],
    profile: Any,
    weather: dict,
    occasion: str,
    mood: str | None,
    recent_looks: list[list[str]],
    *,
    references: list[dict] | None = None,
    style_note: str | None = None,
    season: str | None = None,
    scene: str | None = None,
) -> str:
    items = [
        {
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
        }
        for item in candidates
    ]
    state = (
        decode_profile_state(profile.learned_from_feedback_json or "[]")
        if profile
        else decode_profile_state("[]")
    )
    return json.dumps(
        {
            "items": items,
            "style_dna": {
                "keywords": active_style_keywords(
                    json.loads(profile.style_keywords_json or "[]") if profile else [],
                    state["style_tag_preferences"],
                ),
                "recent_style_signals": state["recent_style_signals"],
            },
            "taste_memo": profile.taste_memo if profile else "",
            "weather": weather,
            "occasion": occasion,
            "scene": scene or occasion,
            "season": season,
            "mood": mood,
            "optional_style_request": style_note,
            "selected_reference_analyses": references or [],
            "recent_looks": recent_looks,
        },
        ensure_ascii=False,
        default=str,
    )
