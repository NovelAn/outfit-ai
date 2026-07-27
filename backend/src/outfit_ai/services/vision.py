import base64
import json
import mimetypes
from pathlib import Path

from ..schemas import ClothingAttributes
from .llm import chat_multimodal

_TOOL = {
    "type": "function",
    "function": {
        "name": "save_clothing_attributes",
        "description": "保存图片中主要衣物的结构化属性",
        "parameters": ClothingAttributes.model_json_schema(),
    },
}


def image_data_url(path: str | Path) -> str:
    path = Path(path)
    mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"


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
    arguments = response.choices[0].message.tool_calls[0].function.arguments
    return ClothingAttributes.model_validate_json(arguments), json.dumps(
        response.model_dump(), ensure_ascii=False
    )
