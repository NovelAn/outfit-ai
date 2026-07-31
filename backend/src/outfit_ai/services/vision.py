import base64
import mimetypes
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps

from ..schemas import ClothingAttributes, StyleReferenceAnalysis
from . import minimax_images
from .minimax_images import MiniMaxResponseError


def image_data_url(path: str | Path, *, max_bytes: int | None = None) -> str:
    path = Path(path)
    mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    data = path.read_bytes()
    if max_bytes is not None and len(data) > max_bytes:
        with Image.open(path) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
            while True:
                output = BytesIO()
                image.save(output, "JPEG", quality=80, optimize=True)
                data = output.getvalue()
                if len(data) <= max_bytes:
                    break
                width, height = image.size
                image = image.resize(
                    (max(1, width * 4 // 5), max(1, height * 4 // 5)),
                    Image.Resampling.LANCZOS,
                )
        mime = "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(data).decode()}"


def extract(image_path: str | Path) -> tuple[ClothingAttributes, str]:
    raw = minimax_images.describe_image(
        image_path,
        (
            "识别图片中的主要衣物，只返回 JSON。category 使用英文单数类别。"
            "除 category 外，所有面向用户的字段必须使用简体中文；品牌名可保留原文。"
            f"结构必须符合：{ClothingAttributes.model_json_schema()}"
        ),
    )
    try:
        return ClothingAttributes.model_validate_json(_json_content(raw)), raw
    except ValueError as exc:
        raise MiniMaxResponseError("MiniMax VLM 未返回有效衣物属性") from exc


def _json_content(raw: str) -> str:
    content = raw.strip()
    if content.startswith("```"):
        content = content.removeprefix("```json").removeprefix("```")
        content = content.removesuffix("```").strip()
    return content


def analyze_reference(image_path: str | Path) -> tuple[StyleReferenceAnalysis, str]:
    raw = minimax_images.describe_image(
        image_path,
        (
            "分析这张完整穿搭参考图，不识别人物身份。只返回一个 JSON 对象，不要"
            " Markdown 或解释。所有文本使用简体中文。结构："
            '{"style_keywords":[],"palette":[],"silhouettes":[],"layering":[],'
            '"materials":[],"seasons":[],"scenes":[],"notable_elements":[]}。'
            "必须基于图片填写可见特征，不要照抄空数组模板；style_keywords、palette、"
            "silhouettes 和 notable_elements 各至少填写 1 项，其余无法判断时可为空。"
        ),
    )
    try:
        return StyleReferenceAnalysis.model_validate_json(_json_content(raw)), raw
    except ValueError as exc:
        raise MiniMaxResponseError("MiniMax VLM 未返回有效参考 Look 分析") from exc
