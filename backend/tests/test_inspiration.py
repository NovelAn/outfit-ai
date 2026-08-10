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


def test_inspiration_generates_three_saved_images(monkeypatch, tmp_path) -> None:
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
                "prompt": (
                    "3:4 都市通勤穿搭编辑画报，克制的海军蓝与羊毛层次，"
                    "完整呈现帽子、上装、下装和鞋履的从上到下关系"
                ),
                "negative_prompt": "文字、水印、品牌 logo、无关物体",
                "visual_focus": ["海军蓝", "层次穿搭"],
            },
        )
        calls = []
        monkeypatch.setattr(
            inspiration,
            "generate_images",
            lambda prompt, count: calls.append((prompt, count))
            or [_jpeg_bytes(), _jpeg_bytes(), _jpeg_bytes()],
        )

        result = inspiration.generate(
            db,
            InspirationRequest(
                reference_ids=["ref-1"],
                season="autumn",
                scene="通勤",
            ),
        )

    assert calls[0][0].startswith("3:4 都市通勤穿搭编辑画报，克制的海军蓝与羊毛层次")
    assert "必须避免：文字、水印、品牌 logo、无关物体" in calls[0][0]
    assert calls[0][1] == 3
    assert len(result["looks"]) == 3
    assert all(
        look["image_url"].startswith("/media/inspiration_")
        for look in result["looks"]
    )
    assert result["disclaimer"] == "AI 灵感图 · 不代表衣橱已有单品"
    assert len(list(tmp_path.glob("inspiration_*.jpg"))) == 3


def test_inspiration_returns_partial_generation_without_stale_failure(
    monkeypatch, tmp_path
) -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        monkeypatch.setattr(inspiration.settings, "upload_dir", str(tmp_path))
        monkeypatch.setattr(
            inspiration,
            "generate_json",
            lambda *args, **kwargs: {
                "prompt": (
                    "3:4 都市通勤穿搭编辑画报，基于灵感库的低饱和蓝灰配色和清晰的"
                    "帽子、上装、下装、鞋履层次，完整全身构图"
                ),
                "negative_prompt": "文字、水印、品牌 logo、无关物体",
                "visual_focus": ["蓝灰配色", "层次"]
            },
        )
        monkeypatch.setattr(
            inspiration,
            "generate_images",
            lambda prompt, count: [_jpeg_bytes(), _jpeg_bytes()],
        )

        result = inspiration.generate(
            db,
            InspirationRequest(season="autumn", scene="通勤"),
        )

    assert len(result["looks"]) == 2
    assert result["requested_count"] == 3
    assert result["generated_count"] == 2
    assert result["status"] == "partial"
