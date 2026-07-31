import json
from typing import Any

CANONICAL_PALETTE_NAMES = {
    "黑色",
    "白色",
    "深蓝色",
    "浅蓝色",
    "灰色",
    "米白色",
    "米黄色",
    "卡其色",
    "棕色",
    "绿色",
    "红色",
    "紫色",
}


def _strings(value: Any, limit: int | None = None) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        if isinstance(item, str) and item and item not in result:
            result.append(item)
            if limit is not None and len(result) == limit:
                break
    return result


def _preferences(value: Any) -> dict:
    if not isinstance(value, dict):
        return {"pinned": [], "hidden": [], "aliases": {}}
    aliases = {
        source: target
        for source, target in value.get("aliases", {}).items()
        if isinstance(source, str) and source and isinstance(target, str) and target
    } if isinstance(value.get("aliases"), dict) else {}
    return {
        "pinned": _strings(value.get("pinned"), 3),
        "hidden": _strings(value.get("hidden")),
        "aliases": aliases,
    }


def _empty_state() -> dict:
    return {
        "version": 1,
        "learnings": [],
        "recent_style_signals": [],
        "style_tag_preferences": {"pinned": [], "hidden": [], "aliases": {}},
        "last_location": None,
    }


def decode_profile_state(raw: str) -> dict:
    try:
        value = json.loads(raw)
    except (TypeError, ValueError):
        return _empty_state()
    if isinstance(value, list):
        state = _empty_state()
        state["learnings"] = _strings(value)
        return state
    if not isinstance(value, dict) or value.get("version") != 1:
        return _empty_state()
    return {
        "version": 1,
        "learnings": _strings(value.get("learnings")),
        "recent_style_signals": _strings(value.get("recent_style_signals"), 3),
        "style_tag_preferences": _preferences(value.get("style_tag_preferences")),
        "last_location": value.get("last_location")
        if isinstance(value.get("last_location"), dict)
        else None,
    }


def encode_profile_state(
    *,
    learnings: list[str],
    recent_style_signals: list[str],
    style_tag_preferences: dict,
    last_location: dict | None,
) -> str:
    return json.dumps(
        {
            "version": 1,
            "learnings": _strings(learnings),
            "recent_style_signals": _strings(recent_style_signals, 3),
            "style_tag_preferences": _preferences(style_tag_preferences),
            "last_location": last_location if isinstance(last_location, dict) else None,
        },
        ensure_ascii=False,
    )


def active_style_keywords(keywords: list[str], preferences: dict) -> list[str]:
    preferences = _preferences(preferences)
    aliases = preferences["aliases"]

    def normalize(tag: str) -> str:
        return aliases.get(tag, tag)

    hidden = {normalize(tag) for tag in preferences["hidden"]}
    candidates = [normalize(tag) for tag in preferences["pinned"]]
    candidates.extend(normalize(tag) for tag in _strings(keywords))
    return _strings([tag for tag in candidates if tag not in hidden], 7)
