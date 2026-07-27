import json
from typing import Any


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


def stylist_system(locked_ids: set[str]) -> str:
    locked = ", ".join(sorted(locked_ids)) or "无"
    return (
        "你是一位克制、懂个人风格的造型师。只能使用候选 item_id，必须给出 safe、fresh、"
        f"stretch 各一套，且每套包含 top、bottom、shoes。锁定单品必须出现：{locked}。"
    )


def stylist_context(
    candidates: list[Any],
    profile: Any,
    weather: dict,
    occasion: str,
    mood: str | None,
    recent_looks: list[list[str]],
) -> str:
    items = [
        {
            "id": item.id,
            "name": item.name,
            "category": item.category,
            "color": item.primary_color,
            "style": json.loads(item.style_json or "[]"),
        }
        for item in candidates
    ]
    return json.dumps(
        {
            "items": items,
            "style_dna": {
                "keywords": json.loads(profile.style_keywords_json or "[]") if profile else [],
                "avoids": json.loads(profile.avoids_json or "[]") if profile else [],
            },
            "taste_memo": profile.taste_memo if profile else "",
            "weather": weather,
            "occasion": occasion,
            "mood": mood,
            "recent_looks": recent_looks,
        },
        ensure_ascii=False,
    )
