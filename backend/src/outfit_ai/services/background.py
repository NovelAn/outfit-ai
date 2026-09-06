from functools import lru_cache
from io import BytesIO
from pathlib import Path
from threading import Lock
from typing import Any

from PIL import Image

from .storage import resolve_storage_path

_REMBG_LOCK = Lock()
# ponytail: one-process lock prevents rembg's first-use model download from racing;
# use a shared file/lease if the API ever runs with multiple worker processes.


def background_path(path: str | Path) -> Path:
    source = Path(path)
    return source.with_name(f"{source.stem}.nobg.png")


@lru_cache(maxsize=1)
def _rembg_session() -> Any:
    from rembg import new_session

    return new_session("u2net")


def _remove(data: bytes) -> Any:
    from rembg import remove

    return remove(data, session=_rembg_session())


def ensure_background_removed(path: str | Path) -> Path:
    with _REMBG_LOCK:
        source = resolve_storage_path(path)
        target = background_path(source)
        if target.exists():
            return target

        result = _remove(source.read_bytes())
        output = BytesIO()
        with Image.open(BytesIO(bytes(result))) as image:
            image.convert("RGBA").save(output, "PNG", optimize=True)
        temporary = target.with_suffix(".tmp")
        temporary.write_bytes(output.getvalue())
        temporary.replace(target)
        return target


def display_image_path(item) -> Path:
    source = resolve_storage_path(item.image_path)
    derived = background_path(source)
    return derived if getattr(item, "status", None) == "ready" and derived.exists() else source
