from io import BytesIO

import pytest
from fastapi import BackgroundTasks, UploadFile
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from starlette.datastructures import Headers

from outfit_ai.db import Base
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


def test_storage_rejects_invalid_image_and_removes_partial_file(tmp_path) -> None:
    storage = LocalStorage(tmp_path)
    upload_file = UploadFile(BytesIO(b"not-an-image"), filename="fake.jpg")

    with pytest.raises(ValueError, match="无效图片"):
        storage.save(upload_file)

    assert list(tmp_path.iterdir()) == []
