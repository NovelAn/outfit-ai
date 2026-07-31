import json
from types import SimpleNamespace

from outfit_ai.services.profile_state import (
    active_style_keywords,
    decode_profile_state,
)
from outfit_ai.services.prompt_builder import stylist_context


def test_legacy_feedback_array_decodes_without_data_loss() -> None:
    state = decode_profile_state('["偏爱天然材质"]')

    assert state["learnings"] == ["偏爱天然材质"]
    assert state["recent_style_signals"] == []


def test_active_keywords_respect_pin_hide_and_alias() -> None:
    result = active_style_keywords(
        ["日杂休闲", "商务会议", "轻量叠穿", "复古"],
        {
            "pinned": ["复古"],
            "hidden": ["商务会议"],
            "aliases": {"日杂休闲": "日系松弛"},
        },
    )

    assert result == ["复古", "日系松弛", "轻量叠穿"]


def test_pinned_keyword_wins_over_hidden_after_alias_normalization() -> None:
    preferences = {
        "pinned": ["日杂休闲"],
        "hidden": ["日系松弛"],
        "aliases": {"日杂休闲": "日系松弛"},
    }

    result = active_style_keywords(["日杂休闲", "商务会议"], preferences)
    profile = SimpleNamespace(
        style_keywords_json='["日杂休闲", "商务会议"]',
        learned_from_feedback_json=json.dumps(
            {
                "version": 1,
                "learnings": [],
                "recent_style_signals": [],
                "style_tag_preferences": preferences,
                "last_location": None,
            },
            ensure_ascii=False,
        ),
        taste_memo="偏爱松弛感。",
    )
    context = json.loads(
        stylist_context([], profile, {}, "日常", None, [])
    )

    assert result == ["日系松弛", "商务会议"]
    assert context["style_dna"]["keywords"] == ["日系松弛", "商务会议"]
