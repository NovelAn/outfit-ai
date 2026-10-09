from collections.abc import Callable
from typing import TypeVar

from pydantic import BaseModel, Field, ValidationError

from ..schemas import ProposedLook
from .llm import LLMResponseError, _parse_json_object, chat_multimodal
from .prompt_builder import stylist_context, stylist_system


class ProposedLooks(BaseModel):
    looks: list[ProposedLook] = Field(min_length=3, max_length=3)


class ProposedSingleLook(BaseModel):
    look: ProposedLook


_Validated = TypeVar("_Validated")


def _message(response) -> object:
    try:
        return response.choices[0].message
    except (AttributeError, IndexError) as exc:
        raise LLMResponseError("造型师未返回有效响应") from exc


def _tool_call_arguments(message) -> str | None:
    calls = getattr(message, "tool_calls", None)
    if not calls:
        return None
    try:
        return calls[0].function.arguments
    except (AttributeError, IndexError, KeyError, TypeError):
        return None


def _normalize_look_item_ids(value: dict) -> dict:
    """Repair the known MiniMax tool-shape variant without weakening validation."""
    looks = value.get("looks")
    if isinstance(looks, list):
        for look in looks:
            if not isinstance(look, dict):
                continue
            item_ids = look.get("item_ids")
            if isinstance(item_ids, dict) and isinstance(item_ids.get("item"), list):
                look["item_ids"] = item_ids["item"]
    look = value.get("look")
    if isinstance(look, dict):
        item_ids = look.get("item_ids")
        if isinstance(item_ids, dict) and isinstance(item_ids.get("item"), list):
            look["item_ids"] = item_ids["item"]
    return value


def _request_validated(
    messages: list[dict],
    schema: dict,
    function_name: str,
    validate: Callable[[dict], _Validated],
) -> _Validated:
    response = chat_multimodal(
        messages,
        tools=[schema],
        tool_choice={"type": "function", "function": {"name": function_name}},
    )
    message = _message(response)
    payloads = (_tool_call_arguments(message), getattr(message, "content", None))
    last_error: Exception | None = None
    for payload in payloads:
        if not payload:
            continue
        try:
            return validate(_normalize_look_item_ids(_parse_json_object(payload)))
        except (ValueError, ValidationError, TypeError, KeyError) as exc:
            last_error = exc
    raise LLMResponseError(
        f"造型师未返回有效的 {function_name} 工具调用；参数结构校验失败"
    ) from last_error


_LOOKS_SCHEMA = {
    "type": "function",
    "function": {
        "name": "propose_looks",
        "description": "提交三档穿搭",
        "parameters": ProposedLooks.model_json_schema(),
    },
}

_SINGLE_LOOK_SCHEMA = {
    "type": "function",
    "function": {
        "name": "propose_one_look",
        "description": "提交一档穿搭",
        "parameters": ProposedSingleLook.model_json_schema(),
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
    *,
    references: list[dict] | None = None,
    style_note: str | None = None,
    season: str | None = None,
    scene: str | None = None,
    usage_stats: dict[str, dict[str, object]] | None = None,
    coverage_targets: dict[str, str] | None = None,
) -> list[ProposedLook]:
    content = stylist_context(
        candidates,
        profile,
        weather,
        occasion,
        mood,
        recent_looks,
        references=references,
        style_note=style_note,
        season=season,
        scene=scene,
        usage_stats=usage_stats,
        coverage_targets=coverage_targets,
    )
    if correction:
        content += f"\n上次结果错误，请修正：{correction}"
    messages = [
        {
            "role": "system",
            "content": stylist_system(locked_ids, coverage_targets=coverage_targets)
            + " 输出字段必须严格符合工具参数：looks 是三项数组。"
            "每项含 tier、item_ids 字符串数组、reason、weather_fit、occasion_fit。",
        },
        {"role": "user", "content": content},
    ]
    result = _request_validated(
        messages,
        _LOOKS_SCHEMA,
        "propose_looks",
        lambda arguments: ProposedLooks.model_validate(arguments).looks,
    )
    return result


def propose_tier(
    candidates,
    profile,
    weather: dict,
    occasion: str,
    mood: str | None,
    recent_looks: list[list[str]],
    locked_ids: set[str],
    tier: str,
    correction: str = "",
    *,
    references: list[dict] | None = None,
    style_note: str | None = None,
    season: str | None = None,
    scene: str | None = None,
    usage_stats: dict[str, dict[str, object]] | None = None,
    coverage_targets: dict[str, str] | None = None,
) -> ProposedLook:
    content = stylist_context(
        candidates,
        profile,
        weather,
        occasion,
        mood,
        recent_looks,
        references=references,
        style_note=style_note,
        season=season,
        scene=scene,
        usage_stats=usage_stats,
        coverage_targets=coverage_targets,
    )
    content += f"\n这次只替换 {tier} 档，返回一个 tier 为 {tier} 的 look。"
    if correction:
        content += f"\n上次结果错误，请修正：{correction}"
    messages = [
        {
            "role": "system",
            "content": stylist_system(locked_ids, tier, coverage_targets)
            + " 输出字段必须严格符合工具参数，item_ids 必须是字符串数组。",
        },
        {"role": "user", "content": content},
    ]

    def validate_single(arguments: dict) -> ProposedLook:
        look = ProposedSingleLook.model_validate(arguments).look
        if look.tier != tier:
            raise ValueError(f"tier 必须为 {tier}")
        return look

    return _request_validated(messages, _SINGLE_LOOK_SCHEMA, "propose_one_look", validate_single)
