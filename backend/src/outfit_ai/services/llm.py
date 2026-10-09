import json
import logging
from time import monotonic
from typing import Any

import httpx
from openai import APIConnectionError, APITimeoutError, OpenAI, OpenAIError, RateLimitError
from pydantic import TypeAdapter, ValidationError

from ..config import settings
from .minimax_images import (
    MiniMaxAccess,
    MiniMaxUnavailableError,
    resolve_minimax_access,
)

_JSON_OBJECT = TypeAdapter(dict[str, Any])
_LLM_TIMEOUT_SECONDS = 120
_DISABLE_THINKING = {"thinking": {"type": "disabled"}}
_MAX_TRANSIENT_ATTEMPTS = 2
logger = logging.getLogger(__name__)


class LLMUnavailableError(RuntimeError):
    pass


class LLMResponseError(ValueError):
    pass


def _is_quota_error(error: OpenAIError) -> bool:
    body = getattr(error, "body", None)
    if isinstance(body, dict):
        code = body.get("code") or body.get("status_code")
        if code in {1028, 1030, 2061, "1028", "1030", "2061"}:
            return True
    message = str(error).lower()
    return "quota" in message or "额度" in message


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
        http_client=httpx.Client(timeout=_LLM_TIMEOUT_SECONDS, trust_env=False),
        max_retries=0,
    )


def _create_completion(**kwargs):
    started = monotonic()
    for attempt in range(_MAX_TRANSIENT_ATTEMPTS):
        try:
            response = get_client().chat.completions.create(extra_body=_DISABLE_THINKING, **kwargs)
            logger.info(
                "MiniMax M3 request completed elapsed=%.1fs attempt=%d",
                monotonic() - started,
                attempt + 1,
            )
            return response
        except (APITimeoutError, APIConnectionError) as exc:
            if attempt == 0:
                logger.warning("MiniMax M3 transient=network attempt=1")
                continue
            raise LLMUnavailableError("MiniMax 响应超时或网络不可达，请稍后重试") from exc
        except RateLimitError as exc:
            if _is_quota_error(exc):
                raise LLMUnavailableError("MiniMax 额度不足，请稍后重试") from exc
            if attempt == 0:
                logger.warning("MiniMax M3 transient=rate_limit attempt=1")
                continue
            raise LLMUnavailableError("MiniMax 请求受限，请稍后重试") from exc
        except LLMUnavailableError:
            raise
        except OpenAIError as exc:
            status = getattr(exc, "status_code", None)
            if attempt == 0 and (status == 429 or (isinstance(status, int) and status >= 500)):
                logger.warning("MiniMax M3 transient_status=%s attempt=1", status)
                continue
            logger.warning(
                "MiniMax M3 request failed elapsed=%.1fs status=%s error=%s",
                monotonic() - started,
                status,
                type(exc).__name__,
            )
            raise LLMUnavailableError("MiniMax 服务调用失败") from exc
    raise LLMUnavailableError("MiniMax 服务调用失败")


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
        response = _create_completion(model=settings.minimax_model, messages=messages)
        content = ""
        try:
            content = response.choices[0].message.content or ""
            return _parse_json_object(content)
        except (AttributeError, IndexError, ValidationError) as exc:
            last_error = str(exc)
            messages.append({"role": "assistant", "content": content})
            messages.append({"role": "user", "content": f"JSON 解析失败：{exc}。请修正。"})
    raise LLMResponseError(f"模型未返回有效 JSON：{last_error}")
