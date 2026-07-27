from io import BytesIO
from pathlib import Path

from PIL import Image

MAX_CANVAS_PIXELS = 20_000_000


def render(images: list[str | Path], output: BytesIO, item_width: int = 420, padding: int = 6):
    if not 1 <= len(images) <= 15:
        raise ValueError("拼图需要 1–15 张图片")
    opened = []
    for path in images:
        image = Image.open(path).convert("RGB")
        height = round(image.height * item_width / image.width)
        opened.append(image.resize((item_width, height)))
    canvas_height = sum(image.height for image in opened) + padding * (len(opened) - 1)
    if item_width * canvas_height > MAX_CANVAS_PIXELS:
        raise ValueError("拼图画布过大")
    canvas = Image.new(
        "RGB",
        (item_width, canvas_height),
        "#FAF8F4",
    )
    y = 0
    for image in opened:
        canvas.paste(image, (0, y))
        y += image.height + padding
    canvas.save(output, "PNG")
    output.seek(0)
