from io import BytesIO

import pytest
from fastapi import HTTPException
from PIL import Image

from outfit_ai.routers import wardrobe
from outfit_ai.services import collage
from outfit_ai.services.collage import render


def test_collage_renders_png(tmp_path) -> None:
    paths = []
    for index, color in enumerate(("black", "white")):
        path = tmp_path / f"{index}.png"
        Image.new("RGB", (100, 200), color).save(path)
        paths.append(path)
    output = BytesIO()

    render(paths, output, item_width=50, padding=5)

    assert output.getvalue().startswith(b"\x89PNG\r\n\x1a\n")
    with Image.open(output) as collage:
        assert collage.size == (50, 205)


def test_collage_rejects_oversized_canvas(monkeypatch, tmp_path) -> None:
    path = tmp_path / "tall.png"
    Image.new("RGB", (10, 100), "black").save(path)
    monkeypatch.setattr(collage, "MAX_CANVAS_PIXELS", 1_000)
    monkeypatch.setattr(
        Image.Image,
        "resize",
        lambda *args, **kwargs: pytest.fail("must reject before resize"),
    )

    with pytest.raises(ValueError, match="画布"):
        render([path], BytesIO(), item_width=100)


@pytest.mark.parametrize(
    "item_ids",
    ["", "a,a", ",".join(f"item-{index}" for index in range(16))],
)
def test_collage_endpoint_requires_one_to_fifteen_unique_ids(item_ids) -> None:
    with pytest.raises(HTTPException) as error:
        wardrobe.collage(item_ids, None)

    assert error.value.status_code == 422


def test_collage_maps_decompression_bomb_to_400(monkeypatch) -> None:
    item = type("Item", (), {"id": "item-1", "image_path": "/tmp/item.jpg"})()

    class FakeDb:
        def scalars(self, query):
            return [item]

    monkeypatch.setattr(
        wardrobe,
        "render",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            collage.UnsafeImageError("图片像素异常")
        ),
    )

    with pytest.raises(HTTPException) as error:
        wardrobe.collage("item-1", FakeDb())

    assert error.value.status_code == 400
