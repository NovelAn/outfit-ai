import json
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageOps
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Profile
from ..schemas import InspirationRequest
from .llm import generate_json
from .minimax_images import generate_images
from .style_references import get_reference_analyses


class ImagePrompt(BaseModel):
    prompt: str = Field(min_length=20, max_length=4000)


def _save_image(data: bytes) -> Path:
    root = Path(settings.upload_dir)
    root.mkdir(parents=True, exist_ok=True)
    target = root / f"inspiration_{uuid4().hex}.jpg"
    output = BytesIO()
    with Image.open(BytesIO(data)) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
        if image.width * image.height > 25_000_000:
            raise ValueError("生成图片像素过大")
        image.save(output, "JPEG", quality=92, optimize=True)
    temporary = target.with_suffix(".tmp")
    temporary.write_bytes(output.getvalue())
    temporary.replace(target)
    return target


def generate(db: Session, request: InspirationRequest) -> dict:
    profile = db.get(Profile, settings.user_id)
    references = get_reference_analyses(db, request.reference_ids)
    context = {
        "style_dna": {
            "style_keywords": (
                json.loads(profile.style_keywords_json or "[]") if profile else []
            ),
            "palette": json.loads(profile.palette_json or "[]") if profile else [],
            "taste_memo": profile.taste_memo if profile else "",
        },
        "selected_references": references,
        "season": request.season,
        "scene": request.scene,
        "optional_request": request.style_note,
    }
    prompt = ImagePrompt.model_validate(
        generate_json(
            (
                "为 image-01 写一条 3:4 全身穿搭编辑画报 prompt。不要使用用户真实衣橱"
                "item_id，不要声称图中商品已被用户拥有。画面只展示穿搭，不生成文字、水印"
                "或品牌 logo。"
            ),
            json.dumps(context, ensure_ascii=False),
            '{"prompt":"至少二十字的图像生成提示"}',
        )
    ).prompt
    targets = [_save_image(image) for image in generate_images(prompt, count=3)]
    titles = (
        "Look 01 / Texture Focus",
        "Look 02 / Silhouette Study",
        "Look 03 / Color Palette",
    )
    return {
        "image_url": f"/media/{targets[0].name}",
        "looks": [
            {
                "id": f"look-{index + 1}",
                "title": titles[index],
                "subtitle": f"{request.scene} · {request.season or '当季'}",
                "image_url": f"/media/{target.name}",
            }
            for index, target in enumerate(targets)
        ],
        "disclaimer": "AI 灵感图 · 不代表衣橱已有单品",
    }
