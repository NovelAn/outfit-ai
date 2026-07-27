from io import BytesIO

from PIL import Image

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
