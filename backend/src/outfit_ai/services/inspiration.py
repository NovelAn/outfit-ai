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
from .minimax_images import MiniMaxResponseError, generate_images
from .style_references import get_reference_analyses


class ImagePrompt(BaseModel):
    prompt: str = Field(min_length=20, max_length=1200)
    negative_prompt: str = Field(default="", max_length=1000)
    visual_focus: list[str] = Field(default_factory=list, max_length=8)


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
    image_prompt = ImagePrompt.model_validate(
        generate_json(
            (
                "你是个人穿搭视觉总监。只根据给定的 Style DNA 和长期灵感参考 Look 的结构化"
                "分析提炼共性，不复制某一张图片，不使用用户真实衣橱 item_id，也不要声称图中商品"
                "已被用户拥有。输出 JSON，不要 Markdown。prompt 必须是一条 3:4 全身穿搭编辑画报"
                "提示，明确季节、场景、主色、廓形、叠穿顺序和必要配饰；negative_prompt 写明必须"
                "排除的无关元素；visual_focus 只列 1–8 个最关键的视觉锚点。画面不生成文字、水印"
                "或品牌 logo。"
            ),
            json.dumps(context, ensure_ascii=False),
            (
                '{"prompt":"至少五十字的完整 3:4 全身穿搭画报提示", '
                '"negative_prompt":"文字、水印、品牌 logo、无关物体", '
                '"visual_focus":["配色","廓形"]}'
            ),
        )
    )
    prompt = image_prompt.prompt.strip()
    if image_prompt.visual_focus:
        prompt += f"\n视觉锚点：{'、'.join(image_prompt.visual_focus)}。"
    if image_prompt.negative_prompt.strip():
        prompt += f"\n必须避免：{image_prompt.negative_prompt.strip()}。"
    targets = []
    for image in generate_images(prompt, count=3):
        try:
            targets.append(_save_image(image))
        except (OSError, ValueError):
            continue
    if not targets:
        raise MiniMaxResponseError("生成结果无法保存为有效图片")
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
        "requested_count": 3,
        "generated_count": len(targets),
        "status": "complete" if len(targets) == 3 else "partial",
        "disclaimer": "AI 灵感图 · 不代表衣橱已有单品",
    }
