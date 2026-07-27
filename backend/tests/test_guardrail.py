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
