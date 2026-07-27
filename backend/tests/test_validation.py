from outfit_ai.schemas import ProposedLook
from outfit_ai.services.validator import validate_looks


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
