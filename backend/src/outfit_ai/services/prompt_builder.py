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


def stylist_system(
    locked_ids: set[str],
    tier: str | None = None,
    coverage_targets: dict[str, str] | None = None,
) -> str:
    locked = ", ".join(sorted(locked_ids)) or "无"
    coverage_targets = coverage_targets or {}
    target = f"只生成 {tier} 这一档，不要生成其它档位；" if tier else ""
    output = (
        "必须给出 safe、fresh、stretch 各一套；"
        if not tier
        else f"必须给出 tier 为 {tier} 的一套；"
    )
    coverage = "；".join(
        f"{name} 档必须包含 {item_id}（低曝光覆盖目标）"
        for name, item_id in coverage_targets.items()
        if item_id
    )
    return (
        "你是一位克制、懂个人风格的造型师。只能使用候选 item_id；"
        f"{target}{output}每套 3–6 件，必须包含 top、bottom、shoes。"
        "天气需要时可加叠穿，配饰可选；不要为了凑数量加入无作用的单品。"
        "Safe：天气合适、符合长期 Style DNA，优先熟悉耐穿的组合，不强制冷门单品。"
        "Fresh：必须包含指定低曝光单品，并在颜色、廓形、层次或鞋型中改变"
        "一个主要维度，仍在 Style DNA 内；不能只替换帽子或其它配饰。"
        "Stretch：必须包含另一指定低曝光单品，并比 Fresh 在颜色、廓形或"
        "搭配公式上至少形成两个更明显的突破，不能只替换一个配饰，同时保持天气安全。"
        "厚薄度用于结合温度、体感温度和湿度判断适穿度：高温高湿优先轻薄，"
        "低温优先适中或厚实，轻薄单品只有在叠穿成立时才使用；没有厚薄标签时不要臆造。"
        "季节资格是硬边界，不能用锁定或风格突破绕过；reason 必须用一句话说明核心搭配思路，"
        "最多 50 个字符，避免复述单品名称、天气和完整分析。"
        f"锁定单品必须出现：{locked}。{coverage}"
    )


def _json_list(value: str | None) -> list:
    try:
        parsed = json.loads(value or "[]")
    except (TypeError, ValueError):
        return []
    return parsed if isinstance(parsed, list) else []


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
    usage_stats: dict[str, dict[str, object]] | None = None,
    coverage_targets: dict[str, str] | None = None,
) -> str:
    usage_stats = usage_stats or {}
    coverage_targets = coverage_targets or {}
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
            "styles": _json_list(item.style_json),
            "tags": _json_list(item.tags_json),
            "thickness": next(
                (
                    tag
                    for tag in _json_list(item.tags_json)
                    if tag in {"轻薄", "适中", "厚实"}
                ),
                "",
            ),
            "seasons": _json_list(item.seasons_json),
            "occasions": _json_list(item.occasions_json),
            "usage_count": usage_stats.get(item.id, {}).get("count", 0),
            "last_seen": usage_stats.get(item.id, {}).get("last_seen"),
            "unseen": item.id not in usage_stats,
            "coverage_targets": [
                tier for tier, target in coverage_targets.items() if target == item.id
            ],
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
                    _json_list(profile.style_keywords_json) if profile else [],
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
