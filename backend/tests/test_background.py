from io import BytesIO
from types import SimpleNamespace

from PIL import Image

from outfit_ai.services import background, storage


def _png_bytes() -> bytes:
    output = BytesIO()
    Image.new("RGBA", (2, 2), (255, 255, 255, 0)).save(output, "PNG")
    return output.getvalue()


def test_background_path_is_deterministic(tmp_path) -> None:
    source = tmp_path / "item.jpg"

    assert background.background_path(source) == tmp_path / "item.nobg.png"


def test_background_removal_is_idempotent(monkeypatch, tmp_path) -> None:
    source = tmp_path / "item.jpg"
    source.write_bytes(b"source")
    calls = []
    monkeypatch.setattr(
        background,
        "_remove",
        lambda data: calls.append(data) or _png_bytes(),
    )

    first = background.ensure_background_removed(source)
    second = background.ensure_background_removed(source)

    assert first == second == tmp_path / "item.nobg.png"
    assert calls == [b"source"]
    with Image.open(first) as image:
        assert image.mode == "RGBA"


def test_display_path_uses_transparent_image_only_when_ready(tmp_path) -> None:
    source = tmp_path / "item.jpg"
    transparent = tmp_path / "item.nobg.png"
    source.write_bytes(b"source")
    transparent.write_bytes(_png_bytes())

    assert (
        background.display_image_path(
            SimpleNamespace(image_path=str(source), status="ready")
        )
        == transparent
    )
    assert (
        background.display_image_path(
            SimpleNamespace(image_path=str(source), status="failed")
        )
        == source
    )


def test_display_path_resolves_legacy_absolute_path_after_migration(
    monkeypatch, tmp_path
) -> None:
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    source = uploads / "item.jpg"
    transparent = uploads / "item.nobg.png"
    source.write_bytes(b"source")
    transparent.write_bytes(_png_bytes())
    monkeypatch.setattr(storage.settings, "upload_dir", str(uploads))

    resolved = background.display_image_path(
        SimpleNamespace(
            image_path="/Users/novel/.outfit-ai/uploads/item.jpg",
            status="ready",
        )
    )

    assert resolved == transparent
