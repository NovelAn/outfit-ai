import json
from collections.abc import Iterable
from typing import Any


def filter_candidates(
    items: Iterable[Any],
    *,
    season: str,
    locked_ids: set[str],
    recent_item_ids: set[str],
    limit: int = 15,
) -> list[Any]:
    """Apply hard constraints only; taste ranking belongs to the stylist."""
    candidates = []
    for item in items:
        if not item.confirmed_by_user or item.status != "ready":
            continue
        locked = item.id in locked_ids
        seasons = set(json.loads(item.seasons_json or "[]"))
        wrong_season = seasons and season not in seasons and "all" not in seasons
        recently_worn = item.id in recent_item_ids and item.category != "shoes"
        if locked or (not wrong_season and not recently_worn):
            candidates.append(item)
    candidates.sort(key=lambda item: (item.id not in locked_ids, item.added_at is None))
    return candidates[:limit]
