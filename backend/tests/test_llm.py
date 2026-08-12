from types import SimpleNamespace

import pytest
from openai import OpenAIError

from outfit_ai.services import llm, stylist
from outfit_ai.services.minimax_images import MiniMaxAccess


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


def test_generate_json_rejects_non_object_json(monkeypatch) -> None:
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="[]"))]
    )
    monkeypatch.setattr(llm, "_create_completion", lambda **kwargs: response)

    with pytest.raises(llm.LLMResponseError, match="有效 JSON"):
        llm.generate_json("system", "user", "{}", max_attempts=1)


def test_generate_json_extracts_object_after_reasoning(monkeypatch) -> None:
    response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content='<think>先整理字段</think>\n{"prompt":"valid"}'
                )
            )
        ]
    )
    monkeypatch.setattr(llm, "_create_completion", lambda **kwargs: response)

    assert llm.generate_json("system", "user", "{}") == {"prompt": "valid"}


def test_text_client_reuses_resolved_mmx_credentials(monkeypatch) -> None:
    captured = {}
    http_options = {}

    class FakeHttpClient:
        pass

    http_client = FakeHttpClient()
    monkeypatch.setattr(
        llm.httpx,
        "Client",
        lambda **kwargs: http_options.update(kwargs) or http_client,
    )
    monkeypatch.setattr(
        llm,
        "resolve_minimax_access",
        lambda: MiniMaxAccess("file-key", "https://api.minimaxi.com"),
        raising=False,
    )
    monkeypatch.setattr(
        llm,
        "OpenAI",
        lambda **kwargs: captured.update(kwargs) or SimpleNamespace(),
    )

    llm.get_client()

    assert captured == {
        "api_key": "file-key",
        "base_url": "https://api.minimaxi.com/v1",
        "http_client": http_client,
    }
    assert http_options == {"timeout": 120, "trust_env": False}


def test_stylist_sends_text_attributes_and_reference_analysis(monkeypatch) -> None:
    captured = {}
    response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    tool_calls=[
                        SimpleNamespace(
                            function=SimpleNamespace(
                                arguments=(
                                    '{"looks":['
                                    '{"tier":"safe","item_ids":["top","bottom","shoes"],'
                                    '"reason":"稳妥","weather_fit":"适合","occasion_fit":"合适"},'
                                    '{"tier":"fresh","item_ids":["top","bottom","shoes"],'
                                    '"reason":"新鲜","weather_fit":"适合","occasion_fit":"合适"},'
                                    '{"tier":"stretch","item_ids":["top","bottom","shoes"],'
                                    '"reason":"突破","weather_fit":"适合","occasion_fit":"合适"}]}'
                                )
                            )
                        )
                    ]
                )
            )
        ]
    )

    def fake_chat(messages, **kwargs):
        captured["messages"] = messages
        return response

    monkeypatch.setattr(stylist, "chat_multimodal", fake_chat)
    candidates = [
        SimpleNamespace(
            id="top",
            name="白衬衫",
            category="top",
            primary_color="白色",
            secondary_color=None,
            material="棉",
            fit="regular",
            formality="smart casual",
            style_json='["极简"]',
            tags_json="[]",
            seasons_json='["autumn"]',
            occasions_json='["通勤"]',
        ),
        SimpleNamespace(
            id="bottom",
            name="西裤",
            category="bottom",
            primary_color="海军蓝",
            secondary_color=None,
            material="羊毛",
            fit="straight",
            formality="smart casual",
            style_json="[]",
            tags_json="[]",
            seasons_json="[]",
            occasions_json="[]",
        ),
        SimpleNamespace(
            id="shoes",
            name="乐福鞋",
            category="shoes",
            primary_color="棕色",
            secondary_color=None,
            material="皮革",
            fit=None,
            formality=None,
            style_json="[]",
            tags_json="[]",
            seasons_json="[]",
            occasions_json="[]",
        ),
    ]

    stylist.propose(
        candidates,
        None,
        {"temp": 18},
        "通勤",
        None,
        [],
        set(),
        references=[{"style_keywords": ["克制"]}],
        style_note="轻松一点",
        season="autumn",
        scene="通勤",
    )

    content = captured["messages"][1]["content"]
    assert isinstance(content, str)
    assert "白衬衫" in content
    assert "克制" in content
    assert "image_url" not in content
