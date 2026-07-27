import json
from typing import Any


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
