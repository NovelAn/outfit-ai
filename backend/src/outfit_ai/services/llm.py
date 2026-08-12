import json
from typing import Any

import httpx
from openai import OpenAI, OpenAIError
from pydantic import TypeAdapter, ValidationError

from ..config import settings
from .minimax_images import (
    MiniMaxAccess,
    MiniMaxUnavailableError,
    resolve_minimax_access,
)

_JSON_OBJECT = TypeAdapter(dict[str, Any])


class LLMUnavailableError(RuntimeError):
    pass


class LLMResponseError(ValueError):
    pass


def require_api_key() -> MiniMaxAccess:
    try:
        return resolve_minimax_access()
    except MiniMaxUnavailableError as exc:
        raise LLMUnavailableError(str(exc)) from exc


def get_client() -> OpenAI:
    access = require_api_key()
    return OpenAI(
        api_key=access.api_key,
        base_url=f"{access.base_url}/v1",
        http_client=httpx.Client(timeout=120, trust_env=False),
    )


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


def _parse_json_object(content: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    for start, character in enumerate(content):
        if character != "{":
            continue
        try:
            value, _ = decoder.raw_decode(content[start:])
        except json.JSONDecodeError:
            continue
        return _JSON_OBJECT.validate_python(value)
    return _JSON_OBJECT.validate_json(content.strip())


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
        content = ""
        try:
            content = response.choices[0].message.content or ""
            return _parse_json_object(content)
        except (AttributeError, IndexError, ValidationError) as exc:
            last_error = str(exc)
            messages.append({"role": "assistant", "content": content})
            messages.append({"role": "user", "content": f"JSON 解析失败：{exc}。请修正。"})
    raise LLMResponseError(f"模型未返回有效 JSON：{last_error}")
