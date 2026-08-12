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
from outfit_ai.schemas import StyleReferenceAnalysis
from outfit_ai.services.profile_state import CANONICAL_PALETTE_NAMES
from outfit_ai.services.storage import LocalStorage
from outfit_ai.services.style_references import get_reference_analyses, merge_style_dna
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


def test_reference_worker_reanalyzes_an_empty_cached_result(monkeypatch, tmp_path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'references.db'}")
    Base.metadata.create_all(engine)

    def session_factory():
        return Session(engine)

    monkeypatch.setattr(worker, "SessionLocal", session_factory)
    monkeypatch.setattr(
        worker,
        "analyze_reference",
        lambda _: (
            StyleReferenceAnalysis(style_keywords=["复古"], palette=["棕色"]),
            '{"style_keywords":["复古"],"palette":["棕色"]}',
        ),
    )
    monkeypatch.setattr(
        worker,
        "merge_style_dna",
        lambda profile, analysis: {
            "style_keywords": analysis.style_keywords,
            "palette": analysis.palette,
            "preferred_colors": analysis.palette,
            "preferred_styles": analysis.style_keywords,
            "avoids": [],
            "taste_memo": "偏爱复古配色。",
        },
    )
    with session_factory() as db:
        db.add(
            StyleReference(
                id="ref-empty",
                user_id="local",
                image_path=str(tmp_path / "look.jpg"),
                analysis_json=json.dumps(
                    {
                        "style_keywords": [],
                        "palette": [],
                        "silhouettes": [],
                        "layering": [],
                        "materials": [],
                        "seasons": [],
                        "scenes": [],
                        "notable_elements": [],
                    }
                ),
                status="pending",
            )
        )
        db.commit()

    worker.process_reference("ref-empty")

    with session_factory() as db:
        reference = db.get(StyleReference, "ref-empty")
        assert reference.status == "ready"
        assert json.loads(reference.analysis_json)["style_keywords"] == ["复古"]


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


def test_merge_style_dna_curates_keywords_signals_and_palette(monkeypatch) -> None:
    from outfit_ai.services import style_references

    monkeypatch.setattr(
        style_references,
        "generate_json",
        lambda *args: {
            "style_keywords": ["日杂休闲", "轻量叠穿", "商务会议"],
            "recent_style_signals": ["近期尝试低饱和"] * 4,
            "palette": ["深蓝色", "海军蓝", "棕色", "灰色", "白色", "黑色"],
            "preferred_colors": [],
            "preferred_styles": [],
            "avoids": [],
            "taste_memo": "偏爱松弛层次。",
        },
    )
    profile = Profile(
        user_id="local",
        style_keywords_json='["复古"]',
        learned_from_feedback_json=json.dumps(
            {
                "version": 1,
                "learnings": [],
                "recent_style_signals": [],
                "style_tag_preferences": {
                    "pinned": ["复古"],
                    "hidden": ["商务会议", "复古"],
                    "aliases": {"日杂休闲": "日系松弛"},
                },
                "last_location": None,
            },
            ensure_ascii=False,
        ),
    )

    merged = merge_style_dna(profile, StyleReferenceAnalysis(style_keywords=["日杂休闲"]))

    assert merged.style_keywords == ["日系松弛", "轻量叠穿", "复古"]
    assert merged.recent_style_signals == ["近期尝试低饱和"]
    assert set(merged.palette) <= CANONICAL_PALETTE_NAMES


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
