_ALIASES = {
    "accessories": "accessory",
    "accessory": "accessory",
    "blouse": "top",
    "blazer": "outerwear",
    "coat": "outerwear",
    "dress": "dress",
    "hoodie": "top",
    "jacket": "outerwear",
    "outerwear": "outerwear",
    "shirt": "top",
    "sweater": "top",
    "t-shirt": "top",
    "tee": "top",
    "top": "top",
    "bottom": "bottom",
    "jeans": "bottom",
    "pants": "bottom",
    "shorts": "bottom",
    "skirt": "bottom",
    "trouser": "bottom",
    "trousers": "bottom",
    "boot": "shoes",
    "boots": "shoes",
    "loafer": "shoes",
    "loafers": "shoes",
    "shoe": "shoes",
    "shoes": "shoes",
    "sneaker": "shoes",
    "sneakers": "shoes",
}
CANONICAL_CATEGORIES = {"accessory", "bottom", "dress", "outerwear", "shoes", "top"}


def canonical_category(category: str | None) -> str:
    value = (category or "").strip().lower()
    return _ALIASES.get(value, value)


def confirmed_category(category: str | None) -> str:
    value = canonical_category(category)
    if value not in CANONICAL_CATEGORIES:
        raise ValueError("确认前请选择有效类别")
    return value
