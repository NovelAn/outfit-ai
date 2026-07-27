import json
from typing import Any

from openai import OpenAI, OpenAIError

from ..config import settings


class LLMUnavailableError(RuntimeError):
    pass


class LLMResponseError(ValueError):
    pass


def require_api_key() -> None:
    if not settings.minimax_api_key:
        raise LLMUnavailableError("未配置 MINIMAX_API_KEY")


def get_client() -> OpenAI:
    require_api_key()
    return OpenAI(api_key=settings.minimax_api_key, base_url=settings.minimax_base_url)


def _create_completion(**kwargs):
    try:
        return get_client().chat.completions.create(**kwargs)
    except LLMUnavailableError:
        raise
    except OpenAIError as exc:
        raise LLMUnavailableError("MiniMax 服务调用失败") from exc


def chat_multimodal(
    messages: list[dict[str, Any]],
    *,
    tools: list[dict[str, Any]],
    tool_choice: dict[str, Any],
) -> Any:
    return _create_completion(
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
        response = _create_completion(
            model=settings.minimax_model, messages=messages
        )
        content = response.choices[0].message.content or ""
        try:
            return json.loads(content.removeprefix("```json").removesuffix("```").strip())
        except json.JSONDecodeError as exc:
            last_error = str(exc)
            messages.append({"role": "assistant", "content": content})
            messages.append({"role": "user", "content": f"JSON 解析失败：{exc}。请修正。"})
    raise LLMResponseError(f"模型未返回有效 JSON：{last_error}")
