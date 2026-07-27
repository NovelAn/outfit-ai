from collections import Counter

from ..schemas import ProposedLook

_CATEGORY_GROUP = {
    "shirt": "top",
    "t-shirt": "top",
    "sweater": "top",
    "top": "top",
    "pants": "bottom",
    "jeans": "bottom",
    "skirt": "bottom",
    "bottom": "bottom",
    "shoe": "shoes",
    "shoes": "shoes",
    "sneakers": "shoes",
    "boots": "shoes",
}


def normalize_category(category: str) -> str:
    return _CATEGORY_GROUP.get(category.lower(), category.lower())


def validate_looks(
    looks: list[ProposedLook],
    candidate_categories: dict[str, str],
    *,
    locked_ids: set[str] | None = None,
) -> tuple[bool, str]:
    locked_ids = locked_ids or set()
    tiers = Counter(look.tier for look in looks)
    if tiers != {"safe": 1, "fresh": 1, "stretch": 1}:
        return False, "必须恰好包含 safe、fresh、stretch 各一套"
    combinations: set[tuple[str, ...]] = set()
    for look in looks:
        unknown = set(look.item_ids) - candidate_categories.keys()
        if unknown:
            return False, f"{look.tier} 使用了未知 item_id: {', '.join(sorted(unknown))}"
        if len(look.item_ids) != len(set(look.item_ids)):
            return False, f"{look.tier} 内有重复单品"
        missing_locked = locked_ids - set(look.item_ids)
        if missing_locked:
            return False, f"{look.tier} 缺少锁定单品: {', '.join(sorted(missing_locked))}"
        categories = {
            normalize_category(candidate_categories[item_id])
            for item_id in look.item_ids
        }
        missing = {"top", "bottom", "shoes"} - categories
        if missing:
            return False, f"{look.tier} 缺少类别: {', '.join(sorted(missing))}"
        combination = tuple(sorted(look.item_ids))
        if combination in combinations:
            return False, "三档推荐必须互不相同"
        combinations.add(combination)
    return True, ""
