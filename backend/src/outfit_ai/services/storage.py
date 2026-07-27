from pathlib import Path
from typing import Protocol
from uuid import uuid4

from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError

from ..config import settings


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
        suffix = Path(upload.filename or "").suffix.lower() or ".jpg"
        path = self.root / f"{uuid4().hex}{suffix}"
        size = 0
        with path.open("wb") as target:
            while chunk := upload.file.read(1024 * 1024):
                size += len(chunk)
                if size > settings.max_image_bytes:
                    target.close()
                    path.unlink(missing_ok=True)
                    raise ImageTooLargeError("图片不能超过 10MB")
                target.write(chunk)
        try:
            with Image.open(path) as image:
                image.verify()
        except (OSError, UnidentifiedImageError) as exc:
            path.unlink(missing_ok=True)
            raise ValueError("无效图片文件") from exc
        return path

    def delete(self, path: str) -> None:
        Path(path).unlink(missing_ok=True)
