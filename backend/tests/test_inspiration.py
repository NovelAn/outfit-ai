import json
from io import BytesIO

from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from outfit_ai.db import Base
from outfit_ai.models import Profile, StyleReference
from outfit_ai.schemas import InspirationRequest
from outfit_ai.services import inspiration


def _jpeg_bytes() -> bytes:
    output = BytesIO()
    Image.new("RGB", (8, 12), "navy").save(output, "JPEG")
    return output.getvalue()


def test_inspiration_generates_one_saved_image(monkeypatch, tmp_path) -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Profile(user_id="local", taste_memo="偏爱克制的都市造型。"))
        db.add(
            StyleReference(
                id="ref-1",
                user_id="local",
                image_path="/tmp/look.jpg",
                status="ready",
                analysis_json=json.dumps(
                    {
                        "style_keywords": ["极简"],
                        "palette": ["海军蓝"],
                        "silhouettes": [],
                        "layering": [],
                        "materials": [],
                        "seasons": [],
                        "scenes": [],
                        "notable_elements": [],
                    },
                    ensure_ascii=False,
                ),
            )
        )
        db.commit()
        monkeypatch.setattr(inspiration.settings, "upload_dir", str(tmp_path))
        monkeypatch.setattr(
            inspiration,
            "generate_json",
            lambda *args, **kwargs: {
                "prompt": "3:4 都市通勤穿搭编辑画报，克制的海军蓝与羊毛层次"
            },
        )
        calls = []
        monkeypatch.setattr(
            inspiration,
            "generate_image",
            lambda prompt: calls.append(prompt) or _jpeg_bytes(),
        )

        result = inspiration.generate(
            db,
            InspirationRequest(
                reference_ids=["ref-1"],
                season="autumn",
                scene="通勤",
            ),
        )

    assert calls == ["3:4 都市通勤穿搭编辑画报，克制的海军蓝与羊毛层次"]
    assert result["image_url"].startswith("/media/inspiration_")
    assert result["disclaimer"] == "AI 灵感图 · 不代表衣橱已有单品"
    assert len(list(tmp_path.glob("inspiration_*.jpg"))) == 1
