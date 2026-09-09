from pydantic import BaseModel, Field, ValidationError

from ..schemas import ProposedLook
from .llm import LLMResponseError, _parse_json_object, chat_multimodal
from .prompt_builder import stylist_context, stylist_system


class ProposedLooks(BaseModel):
    looks: list[ProposedLook] = Field(min_length=3, max_length=3)


class ProposedSingleLook(BaseModel):
    look: ProposedLook


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
    response = chat_multimodal(
        [
            {
                "role": "system",
                "content": stylist_system(locked_ids, coverage_targets=coverage_targets),
            },
            {"role": "user", "content": content},
        ],
        tools=[_LOOKS_SCHEMA],
        tool_choice={"type": "function", "function": {"name": "propose_looks"}},
    )
    message = _message(response)
    try:
        arguments = _tool_call_arguments(message)
        if arguments is not None:
            return ProposedLooks.model_validate_json(arguments).looks
    except (ValueError, ValidationError):
        pass
    try:
        content = getattr(message, "content", "") or ""
        return ProposedLooks.model_validate(_parse_json_object(content)).looks
    except (ValueError, ValidationError) as exc:
        raise LLMResponseError("造型师未返回有效的 propose_looks 工具调用") from exc


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
    response = chat_multimodal(
        [
            {"role": "system", "content": stylist_system(locked_ids, tier, coverage_targets)},
            {"role": "user", "content": content},
        ],
        tools=[_SINGLE_LOOK_SCHEMA],
        tool_choice={"type": "function", "function": {"name": "propose_one_look"}},
    )
    message = _message(response)
    try:
        arguments = _tool_call_arguments(message)
        if arguments is not None:
            look = ProposedSingleLook.model_validate_json(arguments).look
            if look.tier != tier:
                raise ValueError(f"tier 必须为 {tier}")
            return look
    except (ValueError, ValidationError):
        pass
    try:
        content = getattr(message, "content", "") or ""
        look = ProposedSingleLook.model_validate(_parse_json_object(content)).look
        if look.tier != tier:
            raise ValueError(f"tier 必须为 {tier}")
        return look
    except (ValueError, ValidationError) as exc:
        raise LLMResponseError("造型师未返回有效的 propose_one_look 工具调用") from exc
