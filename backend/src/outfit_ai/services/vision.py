import base64
import json
import mimetypes
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps

from ..schemas import ClothingAttributes
from .llm import LLMResponseError, chat_multimodal

_TOOL = {
    "type": "function",
    "function": {
        "name": "save_clothing_attributes",
        "description": "保存图片中主要衣物的结构化属性",
        "parameters": ClothingAttributes.model_json_schema(),
    },
}


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
    response = chat_multimodal(
        [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "识别这件衣物。category 使用英文单数类别。"},
                    {"type": "image_url", "image_url": {"url": image_data_url(image_path)}},
                ],
            }
        ],
        tools=[_TOOL],
        tool_choice={"type": "function", "function": {"name": "save_clothing_attributes"}},
    )
    try:
        arguments = response.choices[0].message.tool_calls[0].function.arguments
        attributes = ClothingAttributes.model_validate_json(arguments)
    except (AttributeError, IndexError, TypeError, ValueError) as exc:
        raise LLMResponseError("MiniMax 未返回有效的衣物属性工具调用") from exc
    return attributes, json.dumps(response.model_dump(), ensure_ascii=False)
