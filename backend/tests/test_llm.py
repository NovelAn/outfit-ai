from types import SimpleNamespace

import pytest
from openai import OpenAIError

from outfit_ai.services import llm, stylist


def test_chat_multimodal_wraps_provider_failure_without_exposing_details(
    monkeypatch,
) -> None:
    class BrokenCompletions:
        def create(self, **kwargs):
            raise OpenAIError("provider internals")

    client = SimpleNamespace(
        chat=SimpleNamespace(completions=BrokenCompletions())
    )
    monkeypatch.setattr(llm, "get_client", lambda: client)

    with pytest.raises(llm.LLMUnavailableError, match="MiniMax 服务调用失败") as error:
        llm.chat_multimodal([], tools=[], tool_choice={})

    assert "provider internals" not in str(error.value)


def test_stylist_rejects_response_without_required_tool_call(monkeypatch) -> None:
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(tool_calls=[]))]
    )
    monkeypatch.setattr(stylist, "chat_multimodal", lambda *args, **kwargs: response)

    with pytest.raises(llm.LLMResponseError, match="造型师"):
        stylist.propose([], None, {}, "日常", None, [], set())
