import json
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from outfit_ai.db import Base, get_db
from outfit_ai.main import app
from outfit_ai.models import Profile, StyleReference
from outfit_ai.routers import style_references as router
from outfit_ai.services.storage import LocalStorage
from outfit_ai.services.style_references import get_reference_analyses
from outfit_ai.workers import style_references as worker


def test_reference_worker_reuses_valid_analysis(monkeypatch, tmp_path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'references.db'}")
    Base.metadata.create_all(engine)

    def session_factory():
        return Session(engine)

    monkeypatch.setattr(worker, "SessionLocal", session_factory)
    monkeypatch.setattr(
        worker,
        "analyze_reference",
        lambda _: pytest.fail("validated VLM analysis must be reused"),
    )
    monkeypatch.setattr(
        worker,
        "merge_style_dna",
        lambda profile, analysis: {
            "style_keywords": ["克制"],
            "palette": ["海军蓝"],
            "preferred_colors": ["海军蓝"],
            "preferred_styles": ["极简"],
            "avoids": [],
            "taste_memo": "偏爱克制且利落的造型。",
        },
    )
    with session_factory() as db:
        db.add(
            StyleReference(
                id="ref-1",
                user_id="local",
                image_path=str(tmp_path / "look.jpg"),
                analysis_json=json.dumps(
                    {
                        "style_keywords": ["克制"],
                        "palette": ["海军蓝"],
                        "silhouettes": ["直线"],
                        "layering": [],
                        "materials": ["羊毛"],
                        "seasons": ["autumn"],
                        "scenes": ["通勤"],
                        "notable_elements": [],
                    },
                    ensure_ascii=False,
                ),
                status="pending",
            )
        )
        db.commit()

    worker.process_reference("ref-1")

    with session_factory() as db:
        reference = db.get(StyleReference, "ref-1")
        profile = db.get(Profile, "local")
        assert reference.status == "ready"
        assert profile.taste_memo == "偏爱克制且利落的造型。"


def test_selected_references_must_be_ready_and_owned() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(
            StyleReference(
                id="ref-1",
                user_id="local",
                image_path="/tmp/look.jpg",
                status="failed",
            )
        )
        db.commit()

        with pytest.raises(ValueError, match="参考 Look"):
            get_reference_analyses(db, ["ref-1"])


def test_reference_upload_and_list_http_flow(monkeypatch, tmp_path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'api.db'}")
    Base.metadata.create_all(engine)

    def override_db():
        with Session(engine) as db:
            yield db

    image = BytesIO()
    Image.new("RGB", (8, 12), "navy").save(image, "JPEG")
    monkeypatch.setattr(router, "storage", LocalStorage(tmp_path / "uploads"))
    monkeypatch.setattr(router, "process_reference", lambda _: None)
    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            uploaded = client.post(
                "/api/style-references/upload",
                files={
                    "file": (
                        "look.jpg",
                        image.getvalue(),
                        "application/octet-stream",
                    )
                },
            )
            references = client.get("/api/style-references")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert uploaded.status_code == 201
    assert references.status_code == 200
    assert references.json()[0]["id"] == uploaded.json()["id"]
    assert references.json()[0]["status"] == "pending"


def test_reference_delete_removes_record_and_uploaded_image(monkeypatch, tmp_path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'delete.db'}")
    Base.metadata.create_all(engine)

    def override_db():
        with Session(engine) as db:
            yield db

    image = BytesIO()
    Image.new("RGB", (8, 12), "navy").save(image, "JPEG")
    uploads = tmp_path / "uploads"
    monkeypatch.setattr(router, "storage", LocalStorage(uploads))
    monkeypatch.setattr(router, "process_reference", lambda _: None)
    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            uploaded = client.post(
                "/api/style-references/upload",
                files={"file": ("look.jpg", image.getvalue(), "image/jpeg")},
            )
            reference_id = uploaded.json()["id"]
            deleted = client.delete(f"/api/style-references/{reference_id}")
            remaining = client.get("/api/style-references")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert deleted.status_code == 204
    assert remaining.json() == []
    assert list(uploads.iterdir()) == []
