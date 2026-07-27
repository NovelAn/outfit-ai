import json

from ..schemas import ProposedLook
from .llm import chat_multimodal
from .prompt_builder import stylist_context, stylist_system
from .vision import image_data_url

_LOOKS_SCHEMA = {
    "type": "function",
    "function": {
        "name": "propose_looks",
        "description": "提交三档穿搭",
        "parameters": {
            "type": "object",
            "properties": {
                "looks": {
                    "type": "array",
                    "items": ProposedLook.model_json_schema(),
                    "minItems": 3,
                    "maxItems": 3,
                }
            },
            "required": ["looks"],
        },
    },
}


def propose(
    candidates,
    profile,
    weather: dict,
    occasion: str,
    mood: str | None,
    recent_looks: list[list[str]],
    locked_ids: set[str],
    correction: str = "",
) -> list[ProposedLook]:
    content = [
        {
            "type": "text",
            "text": stylist_context(candidates, profile, weather, occasion, mood, recent_looks)
            + (f"\n上次结果错误，请修正：{correction}" if correction else ""),
        }
    ]
    for item in candidates:
        content.extend(
            [
                {"type": "text", "text": f"item_id={item.id}"},
                {"type": "image_url", "image_url": {"url": image_data_url(item.image_path)}},
            ]
        )
    response = chat_multimodal(
        [
            {"role": "system", "content": stylist_system(locked_ids)},
            {"role": "user", "content": content},
        ],
        tools=[_LOOKS_SCHEMA],
        tool_choice={"type": "function", "function": {"name": "propose_looks"}},
    )
    arguments = response.choices[0].message.tool_calls[0].function.arguments
    return [ProposedLook.model_validate(look) for look in json.loads(arguments)["looks"]]
