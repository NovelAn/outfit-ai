from pydantic import BaseModel, Field

from ..schemas import ProposedLook
from .llm import LLMResponseError, chat_multimodal
from .prompt_builder import stylist_context, stylist_system


class ProposedLooks(BaseModel):
    looks: list[ProposedLook] = Field(min_length=3, max_length=3)


class ProposedSingleLook(BaseModel):
    look: ProposedLook


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
    )
    if correction:
        content += f"\n上次结果错误，请修正：{correction}"
    response = chat_multimodal(
        [
            {"role": "system", "content": stylist_system(locked_ids)},
            {"role": "user", "content": content},
        ],
        tools=[_LOOKS_SCHEMA],
        tool_choice={"type": "function", "function": {"name": "propose_looks"}},
    )
    try:
        arguments = response.choices[0].message.tool_calls[0].function.arguments
        return ProposedLooks.model_validate_json(arguments).looks
    except (AttributeError, IndexError, KeyError, TypeError, ValueError) as exc:
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
    )
    content += f"\n这次只替换 {tier} 档，返回一个 tier 为 {tier} 的 look。"
    if correction:
        content += f"\n上次结果错误，请修正：{correction}"
    response = chat_multimodal(
        [
            {"role": "system", "content": stylist_system(locked_ids, tier)},
            {"role": "user", "content": content},
        ],
        tools=[_SINGLE_LOOK_SCHEMA],
        tool_choice={"type": "function", "function": {"name": "propose_one_look"}},
    )
    try:
        arguments = response.choices[0].message.tool_calls[0].function.arguments
        look = ProposedSingleLook.model_validate_json(arguments).look
        if look.tier != tier:
            raise ValueError(f"tier 必须为 {tier}")
        return look
    except (AttributeError, IndexError, KeyError, TypeError, ValueError) as exc:
        raise LLMResponseError("造型师未返回有效的 propose_one_look 工具调用") from exc
