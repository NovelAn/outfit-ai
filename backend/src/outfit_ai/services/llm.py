import json
from typing import Any

from openai import OpenAI

from ..config import settings


def get_client() -> OpenAI:
    if not settings.minimax_api_key:
        raise RuntimeError("未配置 MINIMAX_API_KEY")
    return OpenAI(api_key=settings.minimax_api_key, base_url=settings.minimax_base_url)


def chat_multimodal(
    messages: list[dict[str, Any]],
    *,
    tools: list[dict[str, Any]],
    tool_choice: dict[str, Any],
) -> Any:
    return get_client().chat.completions.create(
        model=settings.minimax_model,
        messages=messages,
        tools=tools,
        tool_choice=tool_choice,
    )


def generate_json(system: str, user: str, schema_hint: str, max_attempts: int = 2) -> dict:
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"{user}\n只返回 JSON，结构：{schema_hint}"},
    ]
    last_error = ""
    for _ in range(max_attempts):
        response = get_client().chat.completions.create(
            model=settings.minimax_model, messages=messages
        )
        content = response.choices[0].message.content or ""
        try:
            return json.loads(content.removeprefix("```json").removesuffix("```").strip())
        except json.JSONDecodeError as exc:
            last_error = str(exc)
            messages.append({"role": "assistant", "content": content})
            messages.append({"role": "user", "content": f"JSON 解析失败：{exc}。请修正。"})
    raise ValueError(f"模型未返回有效 JSON：{last_error}")
