from io import BytesIO
from pathlib import Path

from PIL import Image


def render(images: list[str | Path], output: BytesIO, item_width: int = 420, padding: int = 6):
    opened = []
    for path in images:
        image = Image.open(path).convert("RGB")
        height = round(image.height * item_width / image.width)
        opened.append(image.resize((item_width, height)))
    canvas = Image.new(
        "RGB",
        (item_width, sum(image.height for image in opened) + padding * (len(opened) - 1)),
        "#FAF8F4",
    )
    y = 0
    for image in opened:
        canvas.paste(image, (0, y))
        y += image.height + padding
    canvas.save(output, "PNG")
    output.seek(0)
