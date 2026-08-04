from types import SimpleNamespace

from outfit_ai.services.guardrail import filter_candidates


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


def test_filters_wrong_season_and_recent_items_but_keeps_locked() -> None:
    items = [
        _item("summer-top", "top", '["summer"]'),
        _item("winter-top", "top", '["winter"]'),
        _item("recent-bottom", "bottom", '["summer"]'),
        _item("recent-shoes", "shoes", '["summer"]'),
    ]

    result = filter_candidates(
        items,
        season="summer",
        locked_ids={"winter-top"},
        recent_item_ids={"recent-bottom", "recent-shoes"},
    )

    assert {item.id for item in result} == {"summer-top", "winter-top", "recent-shoes"}


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


def test_candidate_cap_keeps_required_categories_when_available() -> None:
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

    assert {item.category for item in result} == {"top", "skirt", "boots"}
