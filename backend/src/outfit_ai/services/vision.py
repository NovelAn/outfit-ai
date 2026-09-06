import base64
import json
import mimetypes
import re
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps

from ..schemas import ClothingAttributes, StyleReferenceAnalysis
from . import minimax_images
from .minimax_images import MiniMaxResponseError
from .storage import resolve_storage_path


def image_data_url(path: str | Path, *, max_bytes: int | None = None) -> str:
    path = resolve_storage_path(path)
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
            "识别图片中的主要衣物，只返回一个 JSON 对象，不要输出 JSON Schema 或 Markdown。"
            "category 只能是 top/bottom/outerwear/dress/shoes/accessory。"
            "除 category 外，所有面向用户的字段必须使用简体中文；品牌名可保留原文。"
            "字段：name、category、primary_color、secondary_color、material、thickness、fit、"
            "formality、styles、tags、seasons、occasions、versatility。"
            "thickness 只能是轻薄、适中、厚实之一；仅凭图片无法可靠判断时使用 null。"
            "厚薄度单独填写 thickness，不要把厚薄度重复放进 tags。"
            "versatility 必须是 0 到 1 的数字；styles、tags、seasons、occasions "
            "必须是字符串数组；可空字段使用 null。"
        ),
    )
    try:
        return ClothingAttributes.model_validate_json(_json_content(raw)), raw
    except ValueError as exc:
        raise MiniMaxResponseError("MiniMax VLM 未返回有效衣物属性") from exc


def _json_content(raw: str) -> str:
    content = raw.strip()
    blocks = re.findall(r"```(?:json)?\s*(.*?)```", content, re.IGNORECASE | re.DOTALL)
    for block in reversed(blocks):
        candidate = block.strip()
        try:
            json.loads(candidate)
        except ValueError:
            continue
        return candidate
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
