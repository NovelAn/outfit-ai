from io import BytesIO
from pathlib import Path

from PIL import Image

MAX_CANVAS_PIXELS = 20_000_000


class UnsafeImageError(ValueError):
    pass


def render(images: list[str | Path], output: BytesIO, item_width: int = 420, padding: int = 6):
    if not 1 <= len(images) <= 15:
        raise ValueError("拼图需要 1–15 张图片")
    try:
        sizes = []
        for path in images:
            with Image.open(path) as image:
                sizes.append(image.size)
    except Image.DecompressionBombError as exc:
        raise UnsafeImageError("图片像素异常") from exc
    heights = [round(height * item_width / width) for width, height in sizes]
    canvas_height = sum(heights) + padding * (len(images) - 1)
    if item_width * canvas_height > MAX_CANVAS_PIXELS:
        raise ValueError("拼图画布过大")
    opened = []
    try:
        for path, height in zip(images, heights, strict=True):
            with Image.open(path) as source:
                image = source.convert("RGB")
            opened.append(image.resize((item_width, height)))
    except Image.DecompressionBombError as exc:
        raise UnsafeImageError("图片像素异常") from exc
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
