from outfit_ai.services.profile_state import (
    active_style_keywords,
    decode_profile_state,
)


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
