import json
from collections.abc import Iterable
from typing import Any

from .categories import canonical_category

_SEASON_ALIASES = {
    "春": "spring",
    "春季": "spring",
    "夏": "summer",
    "夏季": "summer",
    "秋": "autumn",
    "秋季": "autumn",
    "初秋": "autumn",
    "冬": "winter",
    "冬季": "winter",
    "四季": "all",
    "全年": "all",
}


def canonical_season(season: str) -> str:
    value = (season or "").strip().lower()
    return _SEASON_ALIASES.get(value, value)


def _json_list(value: str | None) -> list[str]:
    try:
        parsed = json.loads(value or "[]")
    except (TypeError, ValueError):
        return []
    return [item for item in parsed if isinstance(item, str)] if isinstance(parsed, list) else []


def _season_values(seasons: set[str]) -> set[str]:
    values = set(seasons)
    if "spring_autumn" in values:
        values.update({"spring", "autumn"})
    return values


def _usage_sort_key(item: Any, usage_stats: dict[str, dict[str, object]]) -> tuple:
    stats = usage_stats.get(item.id, {})
    count = stats.get("count", 0)
    last_seen = stats.get("last_seen")
    last_key = last_seen.isoformat() if hasattr(last_seen, "isoformat") else str(last_seen or "")
    return (int(item.id in usage_stats), int(count), last_key, item.id)


def filter_candidates(
    items: Iterable[Any],
    *,
    season: str,
    locked_ids: set[str],
    recent_item_ids: set[str],
    usage_stats: dict[str, dict[str, object]] | None = None,
    coverage_target_ids: set[str] | None = None,
    limit: int = 15,
) -> list[Any]:
    """Apply hard constraints only; taste ranking belongs to the stylist."""
    usage_stats = usage_stats or {}
    coverage_target_ids = coverage_target_ids or set()
    candidates: list[Any] = []
    accepted_seasons = (
        {"spring", "autumn", "spring_autumn"}
        if season == "spring_autumn"
        else {season}
    )
    for item in items:
        if not item.confirmed_by_user or item.status != "ready":
            continue
        seasons = _season_values(
            {canonical_season(value) for value in _json_list(item.seasons_json)}
        )
        wrong_season = bool(seasons) and not (accepted_seasons & seasons) and "all" not in seasons
        if not wrong_season:
            candidates.append(item)
    candidates.sort(
        key=lambda item: (
            item.id not in locked_ids,
            item.id not in coverage_target_ids,
            *_usage_sort_key(item, usage_stats),
            item.added_at is None,
        )
    )
    return candidates


def select_coverage_targets(
    candidates: Iterable[Any],
    usage_stats: dict[str, dict[str, object]],
    *,
    locked_ids: set[str] | None = None,
    occupied_ids: set[str] | None = None,
    count: int = 2,
) -> list[str]:
    locked_ids = locked_ids or set()
    occupied_ids = occupied_ids or set()
    available = [
        item
        for item in candidates
        if item.id not in locked_ids and item.id not in occupied_ids
    ]
    available.sort(key=lambda item: _usage_sort_key(item, usage_stats))
    selected: list[Any] = []
    for item in available:
        if len(selected) >= count:
            break
        if selected and canonical_category(item.category) == canonical_category(
            selected[0].category
        ):
            different_category = next(
                (
                    candidate
                    for candidate in available
                    if candidate not in selected
                    and canonical_category(candidate.category)
                    != canonical_category(selected[0].category)
                ),
                None,
            )
            if different_category is not None:
                item = different_category
        if item not in selected:
            selected.append(item)
    return [item.id for item in selected]
