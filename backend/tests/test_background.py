import sys
from io import BytesIO
from threading import Event, Thread
from time import sleep
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


def test_remove_reuses_a_named_lightweight_u2net_session(monkeypatch) -> None:
    calls = []
    session = object()
    fake_rembg = SimpleNamespace(
        new_session=lambda model: calls.append(("new_session", model)) or session,
        remove=lambda data, session: calls.append(("remove", data, session)) or _png_bytes(),
    )
    monkeypatch.setitem(sys.modules, "rembg", fake_rembg)
    background._rembg_session.cache_clear()

    assert background._remove(b"source") == _png_bytes()
    assert background._remove(b"again") == _png_bytes()
    assert calls == [
        ("new_session", "u2net"),
        ("remove", b"source", session),
        ("remove", b"again", session),
    ]


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


def test_background_removal_serializes_model_initialization(monkeypatch, tmp_path) -> None:
    first_source = tmp_path / "first.jpg"
    second_source = tmp_path / "second.jpg"
    first_source.write_bytes(b"first")
    second_source.write_bytes(b"second")
    first_entered = Event()
    second_started = Event()
    release_first = Event()
    entered = []

    def remove(data):
        entered.append(data)
        if data == b"first":
            first_entered.set()
            assert release_first.wait(1)
        return _png_bytes()

    monkeypatch.setattr(background, "_remove", remove)
    first = Thread(target=background.ensure_background_removed, args=(first_source,))
    second = Thread(
        target=lambda: (second_started.set(), background.ensure_background_removed(second_source))
    )

    first.start()
    assert first_entered.wait(1)
    second.start()
    assert second_started.wait(1)
    sleep(0.1)
    assert entered == [b"first"]

    release_first.set()
    first.join(1)
    second.join(1)
    assert entered == [b"first", b"second"]


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
