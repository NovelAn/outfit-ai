import json
from collections.abc import Iterable
from typing import Any

from .categories import canonical_category


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
    accepted_seasons = (
        {"spring", "autumn", "spring_autumn"}
        if season == "spring_autumn"
        else {season}
    )
    for item in items:
        if not item.confirmed_by_user or item.status != "ready":
            continue
        locked = item.id in locked_ids
        seasons = set(json.loads(item.seasons_json or "[]"))
        wrong_season = seasons and not (accepted_seasons & seasons) and "all" not in seasons
        recently_worn = item.id in recent_item_ids and item.category != "shoes"
        if locked or (not wrong_season and not recently_worn):
            candidates.append(item)
    candidates.sort(key=lambda item: (item.id not in locked_ids, item.added_at is None))
    selected = [item for item in candidates if item.id in locked_ids]
    selected_ids = {item.id for item in selected}
    selected_categories = {canonical_category(item.category) for item in selected}
    for category in {"top", "bottom", "shoes"} - selected_categories:
        item = next(
            (
                item
                for item in candidates
                if item.id not in selected_ids
                and canonical_category(item.category) == category
            ),
            None,
        )
        if item:
            selected.append(item)
            selected_ids.add(item.id)
    target = max(limit, len(selected))
    selected.extend(
        item
        for item in candidates
        if item.id not in selected_ids
    )
    return selected[:target]
