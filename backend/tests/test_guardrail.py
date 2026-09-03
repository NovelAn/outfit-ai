from types import SimpleNamespace

import pytest

from outfit_ai.schemas import ProposedLook
from outfit_ai.services.guardrail import filter_candidates
from outfit_ai.services.prompt_builder import stylist_system
from outfit_ai.services.validator import validate_looks


def _item(item_id: str, category: str, seasons: str, *, locked: bool = False):
    return SimpleNamespace(
        id=item_id,
        category=category,
        seasons_json=seasons,
        confirmed_by_user=True,
        status="ready",
        added_at=None,
        locked=locked,
    )


def test_filters_wrong_season_but_keeps_recent_items_as_low_priority() -> None:
    items = [
        _item("summer-top", "top", '["summer"]'),
        _item("winter-top", "top", '["winter"]'),
        _item("recent-bottom", "bottom", '["summer"]'),
        _item("recent-shoes", "shoes", '["summer"]'),
    ]

    result = filter_candidates(
        items,
        season="summer",
        locked_ids=set(),
        recent_item_ids={"recent-bottom", "recent-shoes"},
    )

    assert {item.id for item in result} == {"summer-top", "recent-bottom", "recent-shoes"}


def test_locked_items_are_not_dropped_by_candidate_limit() -> None:
    items = [_item(f"top-{index}", "top", '["summer"]') for index in range(3)]

    result = filter_candidates(
        items,
        season="summer",
        locked_ids={item.id for item in items},
        recent_item_ids=set(),
        limit=2,
    )

    assert {item.id for item in result} == {"top-0", "top-1", "top-2"}


def test_transition_season_accepts_spring_and_autumn_items() -> None:
    items = [
        _item("spring-top", "top", '["spring"]'),
        _item("autumn-bottom", "bottom", '["autumn"]'),
        _item("winter-shoes", "shoes", '["winter"]'),
    ]

    result = filter_candidates(
        items,
        season="spring_autumn",
        locked_ids=set(),
        recent_item_ids=set(),
    )

    assert {item.id for item in result} == {"spring-top", "autumn-bottom"}


def test_normalizes_chinese_season_labels_from_vision() -> None:
    items = [
        _item("summer-top", "top", '["夏季"]'),
        _item("autumn-bottom", "bottom", '["初秋"]'),
        _item("all-shoes", "shoes", '["四季"]'),
    ]

    result = filter_candidates(
        items,
        season="summer",
        locked_ids=set(),
        recent_item_ids=set(),
    )

    assert {item.id for item in result} == {"summer-top", "all-shoes"}


def test_candidate_selection_returns_all_eligible_items_without_random_cap() -> None:
    items = [
        *[_item(f"top-{index}", "top", '["summer"]') for index in range(4)],
        _item("bottom-1", "skirt", '["summer"]'),
        _item("shoes-1", "boots", '["summer"]'),
    ]

    result = filter_candidates(
        items,
        season="summer",
        locked_ids=set(),
        recent_item_ids=set(),
        limit=3,
    )

    assert len(result) == 6


def test_candidate_selection_handles_empty_or_bad_seasons() -> None:
    items = [_item("empty", "top", "[]"), _item("bad", "top", "not-json")]

    result = filter_candidates(items, season="summer", locked_ids=set(), recent_item_ids=set())

    assert {item.id for item in result} == {"empty", "bad"}


def test_candidate_selection_prioritizes_targets_then_lower_exposure() -> None:
    items = [
        _item("often", "top", '["summer"]'),
        _item("seldom", "top", '["summer"]'),
        _item("unseen", "top", '["summer"]'),
    ]

    result = filter_candidates(
        items,
        season="summer",
        locked_ids=set(),
        recent_item_ids=set(),
        usage_stats={
            "often": {"count": 8, "last_seen": "2026-08-01"},
            "seldom": {"count": 1, "last_seen": "2026-08-02"},
        },
        coverage_target_ids={"unseen"},
    )

    assert [item.id for item in result] == ["unseen", "seldom", "often"]


def test_validator_allows_three_to_six_items_and_prompt_describes_optional_pieces() -> None:
    categories = {
        "top": "top",
        "bottom": "bottom",
        "shoes": "shoes",
        "outerwear": "outerwear",
        "scarf": "accessory",
        "bag": "accessory",
    }
    looks = [
        ProposedLook(
            tier="safe",
            item_ids=["top", "bottom", "shoes"],
            reason="基础完整",
            weather_fit="适合",
            occasion_fit="日常",
        ),
        ProposedLook(
            tier="fresh",
            item_ids=["top", "bottom", "shoes", "outerwear"],
            reason="可选叠穿",
            weather_fit="适合",
            occasion_fit="日常",
        ),
        ProposedLook(
            tier="stretch",
            item_ids=["top", "bottom", "shoes", "outerwear", "scarf", "bag"],
            reason="可选配饰",
            weather_fit="适合",
            occasion_fit="日常",
        ),
    ]

    assert validate_looks(looks, categories) == (True, "")
    prompt = stylist_system(set())
    assert "3–6" in prompt
    assert "叠穿" in prompt
    assert "配饰" in prompt


def test_stylist_prompt_defines_three_tier_boundaries_and_targets() -> None:
    prompt = stylist_system(
        set(), coverage_targets={"fresh": "unused-top", "stretch": "unused-bottom"}
    )

    assert "Safe" in prompt and "Fresh" in prompt and "Stretch" in prompt
    assert "低曝光" in prompt
    assert "unused-top" in prompt and "unused-bottom" in prompt


def test_validator_rejects_looks_outside_three_to_six_items_or_with_duplicates() -> None:
    categories = {
        "top": "top",
        "bottom": "bottom",
        "shoes": "shoes",
        "outerwear": "outerwear",
        "scarf": "accessory",
        "bag": "accessory",
        "watch": "accessory",
    }

    def look(tier: str, item_ids: list[str], *, unchecked: bool = False) -> ProposedLook:
        values = dict(
            tier=tier,
            item_ids=item_ids,
            reason="测试",
            weather_fit="适合",
            occasion_fit="日常",
        )
        return ProposedLook.model_construct(**values) if unchecked else ProposedLook(**values)

    valid_fresh = look("fresh", ["top", "bottom", "shoes", "outerwear"])
    valid_stretch = look("stretch", ["top", "bottom", "shoes", "outerwear", "scarf", "bag"])
    invalid_safe_looks = [
        look("safe", ["top", "bottom"], unchecked=True),
        look(
            "safe",
            ["top", "bottom", "shoes", "outerwear", "scarf", "bag", "watch"],
            unchecked=True,
        ),
        look("safe", ["top", "bottom", "shoes", "shoes"], unchecked=True),
    ]

    for invalid_safe in invalid_safe_looks:
        assert validate_looks([invalid_safe, valid_fresh, valid_stretch], categories)[0] is False


@pytest.mark.parametrize(
    "item_ids",
    [
        ["top", "bottom"],
        ["top", "bottom", "shoes", "outerwear", "scarf", "bag", "watch"],
        ["top", "bottom", "shoes", "shoes"],
    ],
)
def test_proposed_look_requires_three_to_six_unique_items(item_ids: list[str]) -> None:
    with pytest.raises(ValueError):
        ProposedLook(
            tier="safe",
            item_ids=item_ids,
            reason="测试",
            weather_fit="适合",
            occasion_fit="日常",
        )
