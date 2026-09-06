from collections import Counter
from typing import Any

from ..schemas import ProposedLook
from .categories import canonical_category


def _style_signature(
    item_ids: list[str], candidate_attributes: dict[str, dict[str, Any]]
) -> frozenset[str]:
    signature: set[str] = set()
    for item_id in item_ids:
        attributes = candidate_attributes.get(item_id)
        if not isinstance(attributes, dict):
            return frozenset()
        for field in ("primary_color", "fit", "formality"):
            value = attributes.get(field)
            if isinstance(value, str) and value:
                signature.add(f"{field}:{value}")
        for field in ("styles", "tags"):
            values = attributes.get(field)
            if isinstance(values, list):
                signature.update(
                    f"{field}:{value}" for value in values if isinstance(value, str) and value
                )
    return frozenset(signature)


def validate_look(
    look: ProposedLook,
    candidate_categories: dict[str, str],
    *,
    locked_ids: set[str] | None = None,
    coverage_target: str | None = None,
) -> tuple[bool, str]:
    locked_ids = locked_ids or set()
    if not 3 <= len(look.item_ids) <= 6:
        return False, f"{look.tier} 必须包含 3–6 件单品"
    unknown = set(look.item_ids) - candidate_categories.keys()
    if unknown:
        return False, f"{look.tier} 使用了未知 item_id: {', '.join(sorted(unknown))}"
    if coverage_target and coverage_target not in look.item_ids:
        return False, f"{look.tier} 必须包含低曝光覆盖目标: {coverage_target}"
    if len(look.item_ids) != len(set(look.item_ids)):
        return False, f"{look.tier} 内有重复单品"
    missing_locked = locked_ids - set(look.item_ids)
    if missing_locked:
        return False, f"{look.tier} 缺少锁定单品: {', '.join(sorted(missing_locked))}"
    categories = {canonical_category(candidate_categories[item_id]) for item_id in look.item_ids}
    missing = {"top", "bottom", "shoes"} - categories
    if missing:
        return False, f"{look.tier} 缺少类别: {', '.join(sorted(missing))}"
    return True, ""


def validate_looks(
    looks: list[ProposedLook],
    candidate_categories: dict[str, str],
    *,
    locked_ids: set[str] | None = None,
    coverage_targets: dict[str, str] | None = None,
    recent_look_keys: set[tuple[str, ...]] | None = None,
    candidate_attributes: dict[str, dict[str, Any]] | None = None,
) -> tuple[bool, str]:
    locked_ids = locked_ids or set()
    coverage_targets = coverage_targets or {}
    recent_look_keys = recent_look_keys or set()
    tiers = Counter(look.tier for look in looks)
    if tiers != {"safe": 1, "fresh": 1, "stretch": 1}:
        return False, "必须恰好包含 safe、fresh、stretch 各一套"
    combinations: set[tuple[str, ...]] = set()
    for look in looks:
        valid, error = validate_look(
            look,
            candidate_categories,
            locked_ids=locked_ids,
            coverage_target=coverage_targets.get(look.tier),
        )
        if not valid:
            return False, error
        combination = tuple(sorted(look.item_ids))
        if combination in recent_look_keys:
            return False, f"{look.tier} 与最近 30 天的完整 Look 重复"
        if combination in combinations:
            return False, "三档推荐必须互不相同"
        combinations.add(combination)
    core_counts = Counter(
        canonical_category(category) for category in candidate_categories.values()
    )
    if all(core_counts[category] >= 3 for category in ("top", "bottom", "shoes")):
        by_tier = {look.tier: set(look.item_ids) for look in looks}
        if len(candidate_categories) >= 9:
            for left, right in (("safe", "fresh"), ("safe", "stretch"), ("fresh", "stretch")):
                overlap = by_tier[left] & by_tier[right] - locked_ids
                non_core_overlap = {
                    item_id
                    for item_id in overlap
                    if canonical_category(candidate_categories[item_id])
                    not in {"top", "bottom", "shoes"}
                }
                if non_core_overlap:
                    return False, (
                        f"{left} 与 {right} 不应共用单品: "
                        f"{', '.join(sorted(non_core_overlap))}"
                    )
        for left, right in (("safe", "fresh"), ("safe", "stretch"), ("fresh", "stretch")):
            overlap = by_tier[left] & by_tier[right] - locked_ids
            core_overlap = {
                item_id
                for item_id in overlap
                if canonical_category(candidate_categories[item_id]) in {"top", "bottom", "shoes"}
            }
            if core_overlap:
                categories = sorted(
                    {canonical_category(candidate_categories[item_id]) for item_id in core_overlap}
                )
                category_names = {"top": "上装", "bottom": "下装", "shoes": "鞋履"}
                names = ", ".join(category_names[name] for name in categories)
                return False, f"{left} 与 {right} 不应共用核心类别: {names}"
    if candidate_attributes:
        signatures = {
            look.tier: _style_signature(look.item_ids, candidate_attributes)
            for look in looks
        }
        available_signatures = {
            _style_signature([item_id], candidate_attributes)
            for item_id in candidate_attributes
        }
        if (
            len(available_signatures) > 1
            and all(signatures.values())
            and len(set(signatures.values())) < 3
        ):
            return False, "Safe、Fresh、Stretch 必须在颜色、版型或风格标签上形成差异"
    return True, ""
