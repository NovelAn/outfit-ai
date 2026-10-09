from outfit_ai.schemas import ProposedLook
from outfit_ai.services.validator import validate_look, validate_looks


def _look(tier: str, item_ids: list[str]) -> ProposedLook:
    return ProposedLook(
        tier=tier,
        item_ids=item_ids,
        reason="协调",
        weather_fit="适合",
        occasion_fit="合适",
    )


def test_rejects_unknown_item_and_missing_required_category() -> None:
    categories = {"top-1": "top", "bottom-1": "bottom", "shoes-1": "shoes"}
    looks = [
        _look("safe", ["top-1", "bottom-1", "missing"]),
        _look("fresh", ["top-1", "bottom-1", "shoes-1"]),
        _look("stretch", ["top-1", "bottom-1", "shoes-1"]),
    ]

    ok, error = validate_looks(looks, categories)

    assert not ok
    assert "missing" in error


def test_compacts_overlong_look_reason() -> None:
    look = ProposedLook(
        tier="safe",
        item_ids=["top", "bottom", "shoes"],
        reason="先用浅色上装提亮整体，再以深色长裤稳住比例，最后用白色板鞋呼应色彩并强化日常休闲感。",
        weather_fit="适合",
        occasion_fit="日常",
    )

    assert len(look.reason) <= 50
    assert look.reason.endswith("。") or look.reason.endswith("…")


def test_accepts_three_distinct_complete_tiers() -> None:
    categories = {
        "top-1": "top",
        "top-2": "top",
        "top-3": "top",
        "bottom-1": "bottom",
        "bottom-2": "bottom",
        "bottom-3": "bottom",
        "shoes-1": "shoes",
        "shoes-2": "shoes",
        "shoes-3": "shoes",
    }
    looks = [
        _look("safe", ["top-1", "bottom-1", "shoes-1"]),
        _look("fresh", ["top-2", "bottom-2", "shoes-2"]),
        _look("stretch", ["top-3", "bottom-3", "shoes-3"]),
    ]

    assert validate_looks(looks, categories) == (True, "")


def test_accepts_singular_category_aliases() -> None:
    categories = {
        "top-1": "shirt",
        "bottom-1": "trouser",
        "shoes-1": "boot",
        "top-2": "tee",
        "bottom-2": "pants",
        "shoes-2": "sneaker",
        "top-3": "sweater",
        "bottom-3": "jeans",
        "shoes-3": "loafer",
    }
    looks = [
        _look("safe", ["top-1", "bottom-1", "shoes-1"]),
        _look("fresh", ["top-2", "bottom-2", "shoes-2"]),
        _look("stretch", ["top-3", "bottom-3", "shoes-3"]),
    ]

    assert validate_looks(looks, categories) == (True, "")


def test_rejects_look_that_omits_locked_item() -> None:
    categories = {
        "top-1": "sweater",
        "bottom-1": "skirt",
        "shoes-1": "boots",
        "locked-jacket": "outerwear",
    }
    looks = [
        _look("safe", ["top-1", "bottom-1", "shoes-1"]),
        _look("fresh", ["top-1", "bottom-1", "shoes-1", "locked-jacket"]),
        _look("stretch", ["top-1", "bottom-1", "shoes-1", "locked-jacket"]),
    ]

    ok, error = validate_looks(looks, categories, locked_ids={"locked-jacket"})

    assert not ok
    assert "safe" in error
    assert "locked-jacket" in error


def test_requires_fresh_and_stretch_coverage_targets() -> None:
    categories = {
        "top-1": "top",
        "top-2": "top",
        "top-3": "top",
        "bottom-1": "bottom",
        "bottom-2": "bottom",
        "bottom-3": "bottom",
        "shoes-1": "shoes",
        "shoes-2": "shoes",
        "shoes-3": "shoes",
    }
    looks = [
        _look("safe", ["top-1", "bottom-1", "shoes-1"]),
        _look("fresh", ["top-2", "bottom-2", "shoes-2"]),
        _look("stretch", ["top-3", "bottom-3", "shoes-3"]),
    ]

    ok, error = validate_looks(
        looks,
        categories,
        coverage_targets={"fresh": "unused-top", "stretch": "unused-bottom"},
    )

    assert not ok
    assert "unused-top" in error


def test_rejects_recent_exact_look() -> None:
    categories = {
        "top-1": "top",
        "top-2": "top",
        "top-3": "top",
        "bottom-1": "bottom",
        "bottom-2": "bottom",
        "bottom-3": "bottom",
        "shoes-1": "shoes",
        "shoes-2": "shoes",
        "shoes-3": "shoes",
    }
    looks = [
        _look("safe", ["top-1", "bottom-1", "shoes-1"]),
        _look("fresh", ["top-2", "bottom-2", "shoes-2"]),
        _look("stretch", ["top-3", "bottom-3", "shoes-3"]),
    ]

    ok, error = validate_looks(
        looks,
        categories,
        recent_look_keys={("bottom-1", "shoes-1", "top-1")},
    )

    assert not ok
    assert "30" in error


def test_rejects_avoidable_core_overlap_when_three_candidates_exist() -> None:
    categories = {
        "top-1": "top",
        "top-2": "top",
        "top-3": "top",
        "bottom-1": "bottom",
        "bottom-2": "bottom",
        "bottom-3": "bottom",
        "shoes-1": "shoes",
        "shoes-2": "shoes",
        "shoes-3": "shoes",
    }
    looks = [
        _look("safe", ["top-1", "bottom-1", "shoes-1"]),
        _look("fresh", ["top-1", "bottom-2", "shoes-2"]),
        _look("stretch", ["top-3", "bottom-3", "shoes-3"]),
    ]

    ok, error = validate_looks(looks, categories)

    assert not ok
    assert "上装" in error


def test_rejects_any_cross_tier_overlap_when_wardrobe_is_large() -> None:
    categories = {
        "top-1": "top",
        "top-2": "top",
        "top-3": "top",
        "bottom-1": "bottom",
        "bottom-2": "bottom",
        "bottom-3": "bottom",
        "shoes-1": "shoes",
        "shoes-2": "shoes",
        "shoes-3": "shoes",
        "hat-1": "accessory",
    }
    looks = [
        _look("safe", ["top-1", "bottom-1", "shoes-1", "hat-1"]),
        _look("fresh", ["top-2", "bottom-2", "shoes-2", "hat-1"]),
        _look("stretch", ["top-3", "bottom-3", "shoes-3"]),
    ]

    ok, error = validate_looks(looks, categories)

    assert not ok
    assert "hat-1" in error


def test_rejects_three_tiers_with_identical_style_signature() -> None:
    categories = {
        "top-1": "top",
        "top-2": "top",
        "top-3": "top",
        "bottom-1": "bottom",
        "bottom-2": "bottom",
        "bottom-3": "bottom",
        "shoes-1": "shoes",
        "shoes-2": "shoes",
        "shoes-3": "shoes",
        "top-4": "top",
        "bottom-4": "bottom",
        "shoes-4": "shoes",
    }
    attributes = {
        item_id: {
            "primary_color": "黑色",
            "fit": "宽松",
            "formality": "休闲",
            "styles": ["极简"],
            "tags": [],
            "category": categories[item_id],
        }
        for item_id in categories
    }
    attributes["top-4"].update(primary_color="白色", fit="修身")
    looks = [
        _look("safe", ["top-1", "bottom-1", "shoes-1"]),
        _look("fresh", ["top-2", "bottom-2", "shoes-2"]),
        _look("stretch", ["top-3", "bottom-3", "shoes-3"]),
    ]

    ok, error = validate_looks(looks, categories, candidate_attributes=attributes)

    assert not ok
    assert "颜色、版型或风格标签" in error


def test_rejects_look_with_duplicate_bottom() -> None:
    categories = {
        "top-1": "top",
        "top-2": "top",
        "top-3": "top",
        "bottom-1": "bottom",
        "bottom-2": "pants",
        "bottom-3": "bottom",
        "shoes-1": "shoes",
        "shoes-2": "shoes",
        "shoes-3": "shoes",
    }
    looks = [
        _look("safe", ["top-1", "bottom-1", "bottom-2", "shoes-1"]),
        _look("fresh", ["top-2", "bottom-3", "shoes-2"]),
        _look("stretch", ["top-3", "bottom-3", "shoes-3"]),
    ]

    ok, error = validate_looks(looks, categories)

    assert not ok
    assert "下装" in error


def test_rejects_outerwear_without_inner_top() -> None:
    categories = {
        "top-1": "top",
        "top-2": "top",
        "top-3": "top",
        "jacket-1": "outerwear",
        "jacket-2": "outerwear",
        "jacket-3": "outerwear",
        "bottom-1": "bottom",
        "bottom-2": "bottom",
        "bottom-3": "bottom",
        "shoes-1": "shoes",
        "shoes-2": "shoes",
        "shoes-3": "shoes",
    }
    looks = [
        _look("safe", ["jacket-1", "bottom-1", "shoes-1"]),
        _look("fresh", ["jacket-2", "top-2", "bottom-2", "shoes-2"]),
        _look("stretch", ["jacket-3", "top-3", "bottom-3", "shoes-3"]),
    ]

    ok, error = validate_looks(looks, categories)

    assert not ok
    assert "外套" in error and "内搭" in error


def test_allows_outerwear_with_inner_top() -> None:
    categories = {
        "top-1": "top",
        "top-2": "top",
        "top-3": "top",
        "jacket-1": "outerwear",
        "jacket-2": "outerwear",
        "jacket-3": "outerwear",
        "bottom-1": "bottom",
        "bottom-2": "bottom",
        "bottom-3": "bottom",
        "shoes-1": "shoes",
        "shoes-2": "shoes",
        "shoes-3": "shoes",
    }
    looks = [
        _look("safe", ["jacket-1", "top-1", "bottom-1", "shoes-1"]),
        _look("fresh", ["jacket-2", "top-2", "bottom-2", "shoes-2"]),
        _look("stretch", ["jacket-3", "top-3", "bottom-3", "shoes-3"]),
    ]

    ok, error = validate_looks(looks, categories)

    assert ok, error




def test_allows_two_tops_when_one_is_a_base_layer() -> None:
    categories = {
        "tee-1": "t-shirt",
        "tee-2": "tee",
        "tee-3": "t-shirt",
        "shirt-1": "shirt",
        "shirt-2": "shirt",
        "shirt-3": "shirt",
        "bottom-1": "bottom",
        "bottom-2": "bottom",
        "bottom-3": "bottom",
        "shoes-1": "shoes",
        "shoes-2": "shoes",
        "shoes-3": "shoes",
    }
    looks = [
        _look("safe", ["tee-1", "shirt-1", "bottom-1", "shoes-1"]),
        _look("fresh", ["tee-2", "shirt-2", "bottom-2", "shoes-2"]),
        _look("stretch", ["tee-3", "shirt-3", "bottom-3", "shoes-3"]),
    ]

    ok, error = validate_looks(looks, categories)

    assert ok, error


def test_allows_two_tops_as_generic_layered_items() -> None:
    categories = {
        "shirt-1": "shirt",
        "shirt-2": "shirt",
        "shirt-3": "shirt",
        "hoodie-1": "hoodie",
        "hoodie-2": "hoodie",
        "hoodie-3": "hoodie",
        "bottom-1": "bottom",
        "bottom-2": "bottom",
        "bottom-3": "bottom",
        "shoes-1": "shoes",
        "shoes-2": "shoes",
        "shoes-3": "shoes",
    }
    looks = [
        _look("safe", ["shirt-1", "hoodie-1", "bottom-1", "shoes-1"]),
        _look("fresh", ["shirt-2", "hoodie-2", "bottom-2", "shoes-2"]),
        _look("stretch", ["shirt-3", "hoodie-3", "bottom-3", "shoes-3"]),
    ]

    ok, error = validate_looks(looks, categories)

    assert ok, error


def test_rejects_three_tops_even_when_one_is_a_base_layer() -> None:
    categories = {
        "tee-1": "t-shirt",
        "shirt-1": "shirt",
        "knit-1": "sweater",
        "bottom-1": "bottom",
        "shoes-1": "shoes",
    }
    looks = [_look("safe", ["tee-1", "shirt-1", "knit-1", "bottom-1", "shoes-1"])]

    ok, error = validate_look(looks[0], categories)

    assert not ok
    assert "上装最多两件" in error


def test_allows_two_tops_with_non_english_base_layer_alias() -> None:
    from outfit_ai.services.categories import canonical_category

    canonical_category("背心")
    categories = {
        "shell-1": "背心",
        "shell-2": "背心",
        "shell-3": "背心",
        "shirt-1": "shirt",
        "shirt-2": "shirt",
        "shirt-3": "shirt",
        "bottom-1": "bottom",
        "bottom-2": "bottom",
        "bottom-3": "bottom",
        "shoes-1": "shoes",
        "shoes-2": "shoes",
        "shoes-3": "shoes",
    }
    looks = [
        _look("safe", ["shell-1", "shirt-1", "bottom-1", "shoes-1"]),
        _look("fresh", ["shell-2", "shirt-2", "bottom-2", "shoes-2"]),
        _look("stretch", ["shell-3", "shirt-3", "bottom-3", "shoes-3"]),
    ]

    ok, error = validate_looks(looks, categories)

    assert ok, error
