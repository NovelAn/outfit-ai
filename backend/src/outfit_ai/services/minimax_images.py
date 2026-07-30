import base64
import json
import mimetypes
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from ..config import settings

_REGIONS = {
    "cn": "https://api.minimaxi.com",
    "global": "https://api.minimax.io",
}


class MiniMaxUnavailableError(RuntimeError):
    pass


class MiniMaxQuotaError(RuntimeError):
    pass


class MiniMaxResponseError(ValueError):
    pass


@dataclass(frozen=True)
class MiniMaxAccess:
    api_key: str
    base_url: str


def _config_path() -> Path:
    root = os.environ.get("MMX_CONFIG_DIR")
    return Path(root).expanduser() / "config.json" if root else Path.home() / ".mmx/config.json"


def _read_config() -> dict[str, Any]:
    path = _config_path()
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MiniMaxUnavailableError("MiniMax 配置文件无效") from exc
    if not isinstance(value, dict):
        raise MiniMaxUnavailableError("MiniMax 配置文件无效")
    return value


def _root_url(value: str) -> str:
    url = value.rstrip("/")
    return url[:-3] if url.endswith("/v1") else url


def resolve_minimax_access() -> MiniMaxAccess:
    config = _read_config()
    api_key = os.environ.get("MINIMAX_API_KEY") or settings.minimax_api_key
    if not api_key:
        file_key = config.get("api_key")
        api_key = file_key if isinstance(file_key, str) else ""
    if not api_key:
        raise MiniMaxUnavailableError("未配置 MiniMax API Key")

    configured_url = os.environ.get("MINIMAX_BASE_URL")
    if not configured_url and isinstance(config.get("base_url"), str):
        configured_url = config["base_url"]
    if not configured_url and settings.minimax_base_url != "https://api.minimaxi.com/v1":
        configured_url = settings.minimax_base_url
    region = config.get("region") if config.get("region") in _REGIONS else "cn"
    return MiniMaxAccess(api_key=api_key, base_url=_root_url(configured_url or _REGIONS[region]))


def _provider_error(status: int, body: dict[str, Any]) -> Exception:
    base_resp = body.get("base_resp")
    code = base_resp.get("status_code") if isinstance(base_resp, dict) else None
    if status in {401, 403}:
        return MiniMaxUnavailableError("MiniMax API Key 无效或无权限")
    if status == 429 or code in {1028, 1030, 2061}:
        return MiniMaxQuotaError("MiniMax 图片额度不足，请稍后重试")
    return MiniMaxUnavailableError("MiniMax 图片服务调用失败")


def _post_json(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    access = resolve_minimax_access()
    try:
        with httpx.Client(timeout=120) as client:
            response = client.post(
                f"{access.base_url}{path}",
                headers={"Authorization": f"Bearer {access.api_key}"},
                json=payload,
            )
    except httpx.TimeoutException as exc:
        raise MiniMaxUnavailableError("MiniMax 图片服务响应超时") from exc
    except httpx.HTTPError as exc:
        raise MiniMaxUnavailableError("无法连接 MiniMax 图片服务") from exc

    try:
        body = response.json()
    except ValueError as exc:
        raise MiniMaxResponseError("MiniMax 图片服务返回格式错误") from exc
    if not isinstance(body, dict):
        raise MiniMaxResponseError("MiniMax 图片服务返回格式错误")
    base_resp = body.get("base_resp")
    failed = isinstance(base_resp, dict) and base_resp.get("status_code") not in {None, 0}
    if response.status_code >= 400 or failed:
        raise _provider_error(response.status_code, body)
    return body


def image_data_url(path: str | Path) -> str:
    source = Path(path)
    mime = mimetypes.guess_type(source.name)[0] or "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(source.read_bytes()).decode()}"


def describe_image(path: str | Path, prompt: str) -> str:
    body = _post_json(
        "/v1/coding_plan/vlm",
        {"prompt": prompt, "image_url": image_data_url(path)},
    )
    content = body.get("content")
    if not isinstance(content, str) or not content.strip():
        raise MiniMaxResponseError("MiniMax VLM 未返回有效内容")
    return content


def generate_image(prompt: str) -> bytes:
    body = _post_json(
        "/v1/image_generation",
        {
            "model": "image-01",
            "prompt": prompt,
            "aspect_ratio": "3:4",
            "n": 1,
            "response_format": "base64",
        },
    )
    try:
        encoded = body["data"]["image_base64"][0]
        return base64.b64decode(encoded, validate=True)
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise MiniMaxResponseError("MiniMax 未返回有效图片") from exc
