from io import BytesIO

import pytest
from fastapi import BackgroundTasks, HTTPException, UploadFile
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from starlette.datastructures import Headers

from outfit_ai.db import Base, get_db, recover_interrupted_analyses
from outfit_ai.main import app
from outfit_ai.models import WardrobeItem
from outfit_ai.routers import wardrobe
from outfit_ai.schemas import ClothingAttributes, WardrobePatch
from outfit_ai.services.storage import LocalStorage
from outfit_ai.workers import analysis


def test_upload_analyze_confirm_and_list_flow(monkeypatch, tmp_path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)

    def session_factory():
        return Session(engine)

    monkeypatch.setattr(analysis, "SessionLocal", session_factory)
    monkeypatch.setattr(analysis, "ensure_background_removed", lambda path: path)
    monkeypatch.setattr(wardrobe, "storage", LocalStorage(tmp_path / "uploads"))
    monkeypatch.setattr(
        analysis,
        "extract",
        lambda path: (
            ClothingAttributes(
                name="黑色针织衫",
                category="sweater",
                primary_color="黑色",
                styles=["极简"],
                seasons=["winter"],
            ),
            '{"source":"test"}',
        ),
    )
    image = BytesIO()
    Image.new("RGB", (10, 10), "black").save(image, "JPEG")
    image.seek(0)
    upload_file = UploadFile(
        image,
        filename="sweater.jpg",
        headers=Headers({"content-type": "image/jpeg"}),
    )

    with session_factory() as db:
        created = wardrobe.upload(BackgroundTasks(), upload_file, db)
        assert created["status"] == "pending"

    analysis.analyze_item(created["id"])

    with session_factory() as db:
        status = wardrobe.status(created["id"], db)
        assert status["status"] == "ready"
        assert status["attempt_count"] == 1
        assert status["name"] == "黑色针织衫"

        wardrobe.patch(
            created["id"],
            WardrobePatch(confirmed_by_user=True),
            db,
        )
        listed = wardrobe.items(db, category="sweater")

    assert [item["id"] for item in listed] == [created["id"]]
    assert listed[0]["category"] == "top"


def test_storage_rejects_invalid_image_and_removes_partial_file(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    upload_file = UploadFile(BytesIO(b"not-an-image"), filename="fake.jpg")

    with pytest.raises(ValueError, match="无效图片"):
        storage.save(upload_file)

    assert list(tmp_path.iterdir()) == []


def test_storage_maps_decompression_bomb_to_invalid_image(monkeypatch, tmp_path) -> None:
    from outfit_ai.services import storage as storage_service

    def reject(_):
        raise Image.DecompressionBombError("too many pixels")

    monkeypatch.setattr(storage_service.Image, "open", reject)

    with pytest.raises(ValueError, match="无效图片"):
        LocalStorage(tmp_path).save(UploadFile(BytesIO(b"image"), filename="large.jpg"))


def test_storage_uses_detected_format_and_safe_extension(tmp_path) -> None:
    image = BytesIO()
    Image.new("RGBA", (10, 10), (0, 0, 0, 0)).save(image, "PNG")
    image.seek(0)

    path = LocalStorage(tmp_path).save(
        UploadFile(image, filename="misleading.jpg")
    )

    assert path.suffix == ".png"
    with Image.open(path) as saved:
        assert saved.format == "PNG"


def test_storage_converts_mpo_jpg_to_standard_jpeg(tmp_path) -> None:
    image = BytesIO()
    Image.new("RGB", (10, 10), "blue").save(
        image,
        "MPO",
        save_all=True,
        append_images=[Image.new("RGB", (10, 10), "red")],
    )
    image.seek(0)

    path = LocalStorage(tmp_path).save(
        UploadFile(image, filename="iphone.jpg")
    )

    assert path.suffix == ".jpg"
    with Image.open(path) as saved:
        assert saved.format == "JPEG"
        assert getattr(saved, "n_frames", 1) == 1


def test_upload_accepts_valid_jpeg_with_generic_browser_mime(
    monkeypatch, tmp_path
) -> None:
    class RecordingDb:
        def add(self, item):
            self.item = item

        def commit(self):
            pass

        def rollback(self):
            pass

    image = BytesIO()
    Image.new("RGB", (10, 10), "blue").save(image, "JPEG")
    image.seek(0)
    monkeypatch.setattr(wardrobe, "storage", LocalStorage(tmp_path))

    created = wardrobe.upload(
        BackgroundTasks(),
        UploadFile(
            image,
            filename="iphone.jpg",
            headers=Headers({"content-type": "application/octet-stream"}),
        ),
        RecordingDb(),
    )

    assert created["status"] == "pending"


def test_storage_rejects_excessive_pixel_count(monkeypatch, tmp_path) -> None:
    from outfit_ai.services import storage as storage_service

    monkeypatch.setattr(storage_service, "MAX_IMAGE_PIXELS", 50)
    image = BytesIO()
    Image.new("RGB", (10, 10), "black").save(image, "JPEG")
    image.seek(0)

    with pytest.raises(ValueError, match="像素"):
        LocalStorage(tmp_path).save(UploadFile(image, filename="large.jpg"))

    assert list(tmp_path.iterdir()) == []


def test_upload_removes_saved_image_when_database_commit_fails(monkeypatch, tmp_path) -> None:
    local_storage = LocalStorage(tmp_path)
    monkeypatch.setattr(wardrobe, "storage", local_storage)
    image = BytesIO()
    Image.new("RGB", (10, 10), "black").save(image, "JPEG")
    image.seek(0)

    class FailingDb:
        def add(self, item):
            pass

        def commit(self):
            raise RuntimeError("commit failed")

        def rollback(self):
            pass

    with pytest.raises(RuntimeError, match="commit failed"):
        wardrobe.upload(
            BackgroundTasks(),
            UploadFile(
                image,
                filename="shirt.jpg",
                headers=Headers({"content-type": "image/jpeg"}),
            ),
            FailingDb(),
        )

    assert list(tmp_path.iterdir()) == []


def test_delete_keeps_image_when_database_commit_fails(monkeypatch, tmp_path) -> None:
    path = tmp_path / "item.jpg"
    path.write_bytes(b"image")
    item = WardrobeItem(id="item-1", user_id="local", image_path=str(path))
    monkeypatch.setattr(wardrobe, "storage", LocalStorage(tmp_path))

    class FailingDb:
        def get(self, model, item_id):
            return item

        def delete(self, found):
            pass

        def commit(self):
            raise RuntimeError("commit failed")

        def rollback(self):
            pass

    with pytest.raises(RuntimeError, match="commit failed"):
        wardrobe.delete("item-1", FailingDb())

    assert path.exists()


def test_wardrobe_http_upload_status_confirm_and_list(monkeypatch, tmp_path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'api.db'}")
    Base.metadata.create_all(engine)

    def session_factory():
        return Session(engine)

    def override_db():
        with session_factory() as db:
            yield db

    monkeypatch.setattr(analysis, "SessionLocal", session_factory)
    monkeypatch.setattr(analysis, "ensure_background_removed", lambda path: path)
    monkeypatch.setattr(wardrobe, "storage", LocalStorage(tmp_path / "uploads"))
    monkeypatch.setattr(
        analysis,
        "extract",
        lambda path: (
            ClothingAttributes(
                name="黑色针织衫",
                category="sweater",
                primary_color="黑色",
                styles=["极简"],
                seasons=["winter"],
            ),
            '{"source":"test"}',
        ),
    )
    image = BytesIO()
    Image.new("RGB", (10, 10), "black").save(image, "JPEG")
    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            uploaded = client.post(
                "/api/wardrobe/upload",
                files={"file": ("sweater.jpg", image.getvalue(), "image/jpeg")},
            )
            item_id = uploaded.json()["id"]
            status = client.get(f"/api/wardrobe/{item_id}/status")
            confirmed = client.post(
                f"/api/wardrobe/{item_id}/confirm",
                json={"category": "sweater"},
            )
            listed = client.get("/api/wardrobe/items?category=sweater")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert uploaded.status_code == 201
    assert status.json()["status"] == "ready"
    assert status.json()["attributes"]["category"] == "top"
    assert confirmed.json()["confirmed_by_user"] is True
    assert [item["id"] for item in listed.json()] == [item_id]


def test_confirm_rejects_unknown_category() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(
            WardrobeItem(
                id="item-1",
                user_id="local",
                category="mystery",
                image_path="/tmp/item.jpg",
                status="ready",
            )
        )
        db.commit()

        with pytest.raises(HTTPException) as error:
            wardrobe.confirm("item-1", WardrobePatch(), db)

    assert error.value.status_code == 422


def test_retry_rejects_analyzing_item_even_when_old() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(
            WardrobeItem(
                id="item-1",
                user_id="local",
                image_path="/tmp/item.jpg",
                status="analyzing",
            )
        )
        db.commit()

        with pytest.raises(HTTPException) as error:
            wardrobe.retry("item-1", BackgroundTasks(), db)

    assert error.value.status_code == 409


def test_worker_claims_only_pending_item(monkeypatch) -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)

    def session_factory():
        return Session(engine)

    monkeypatch.setattr(analysis, "SessionLocal", session_factory)
    monkeypatch.setattr(
        analysis,
        "extract",
        lambda path: pytest.fail("already claimed item must not be analyzed"),
    )
    with session_factory() as db:
        db.add(
            WardrobeItem(
                id="item-1",
                user_id="local",
                image_path="/tmp/item.jpg",
                status="analyzing",
                attempt_count=1,
            )
        )
        db.commit()

    analysis.analyze_item("item-1")

    with session_factory() as db:
        item = db.get(WardrobeItem, "item-1")
        assert item.status == "analyzing"
        assert item.attempt_count == 1


def test_startup_recovery_marks_interrupted_analysis_failed() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(
            WardrobeItem(
                id="item-1",
                user_id="local",
                image_path="/tmp/item.jpg",
                status="analyzing",
            )
        )
        db.commit()

        assert recover_interrupted_analyses(db) == 1
        db.commit()
        item = db.get(WardrobeItem, "item-1")
        assert item.status == "failed"
        assert "服务重启" in item.ai_raw_response
