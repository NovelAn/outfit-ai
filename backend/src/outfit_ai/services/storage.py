from io import BytesIO
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from fastapi import UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError

from ..config import settings

MAX_IMAGE_PIXELS = 25_000_000
_FORMATS = {
    "JPEG": (".jpg", "JPEG"),
    "PNG": (".png", "PNG"),
    "WEBP": (".webp", "WEBP"),
}


class ImageTooLargeError(ValueError):
    pass


class Storage(Protocol):
    def save(self, upload: UploadFile) -> Path: ...

    def delete(self, path: str) -> None: ...


class LocalStorage:
    def __init__(self, root: str | Path = settings.upload_dir):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, upload: UploadFile) -> Path:
        size = 0
        chunks = []
        while chunk := upload.file.read(1024 * 1024):
            size += len(chunk)
            if size > settings.max_image_bytes:
                raise ImageTooLargeError("图片不能超过 10MB")
            chunks.append(chunk)
        try:
            with Image.open(BytesIO(b"".join(chunks))) as source:
                if source.format not in _FORMATS:
                    raise ValueError("仅支持 JPEG、PNG、WebP 图片")
                if source.width * source.height > MAX_IMAGE_PIXELS:
                    raise ValueError(f"图片像素不能超过 {MAX_IMAGE_PIXELS}")
                image = ImageOps.exif_transpose(source)
                image.load()
                suffix, image_format = _FORMATS[source.format]
                if image_format == "JPEG":
                    image = image.convert("RGB")
                elif image.mode not in {"RGB", "RGBA"}:
                    image = image.convert("RGBA")
                output = BytesIO()
                image.save(output, image_format, optimize=True)
                if output.tell() > settings.max_image_bytes:
                    raise ImageTooLargeError("重编码后的图片不能超过 10MB")
        except (OSError, UnidentifiedImageError, Image.DecompressionBombError) as exc:
            raise ValueError("无效图片文件") from exc
        path = self.root / f"{uuid4().hex}{suffix}"
        path.write_bytes(output.getvalue())
        return path

    def delete(self, path: str) -> None:
        Path(path).unlink(missing_ok=True)
