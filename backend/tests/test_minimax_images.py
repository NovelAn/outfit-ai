import base64
import json

import pytest

from outfit_ai.services import minimax_images


def test_access_prefers_environment_key(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("MINIMAX_API_KEY", "env-key")
    monkeypatch.setenv("MMX_CONFIG_DIR", str(tmp_path))
    (tmp_path / "config.json").write_text(
        json.dumps({"api_key": "file-key", "region": "cn"}),
        encoding="utf-8",
    )

    access = minimax_images.resolve_minimax_access()

    assert access.api_key == "env-key"
    assert access.base_url == "https://api.minimaxi.com"


def test_access_falls_back_to_mmx_config(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
    monkeypatch.setenv("MMX_CONFIG_DIR", str(tmp_path))
    (tmp_path / "config.json").write_text(
        json.dumps(
            {
                "api_key": "file-key",
                "region": "cn",
                "base_url": "https://example.minimax.test/",
            }
        ),
        encoding="utf-8",
    )

    access = minimax_images.resolve_minimax_access()

    assert access.api_key == "file-key"
    assert access.base_url == "https://example.minimax.test"


def test_access_rejects_invalid_config_without_leaking_contents(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
    monkeypatch.setenv("MMX_CONFIG_DIR", str(tmp_path))
    (tmp_path / "config.json").write_text('{"api_key":"secret"', encoding="utf-8")

    with pytest.raises(minimax_images.MiniMaxUnavailableError) as exc_info:
        minimax_images.resolve_minimax_access()

    assert str(exc_info.value) == "MiniMax 配置文件无效"
    assert "secret" not in str(exc_info.value)


def test_generate_image_decodes_one_base64_image(monkeypatch) -> None:
    expected = b"image-bytes"
    captured = {}

    def fake_post(path, payload):
        captured.update(path=path, payload=payload)
        return {
            "data": {
                "image_base64": [base64.b64encode(expected).decode()],
                "success_count": 1,
                "failed_count": 0,
                "task_id": "task-1",
            }
        }

    monkeypatch.setattr(minimax_images, "_post_json", fake_post)

    assert minimax_images.generate_image("一个克制的通勤造型") == expected
    assert captured["path"] == "/v1/image_generation"
    assert captured["payload"]["model"] == "image-01"
    assert captured["payload"]["n"] == 1
    assert captured["payload"]["response_format"] == "base64"
    assert captured["payload"]["prompt_optimizer"] is True


def test_generate_images_requests_and_decodes_three_images(monkeypatch) -> None:
    expected = [b"image-1", b"image-2", b"image-3"]
    captured = {}

    def fake_post(path, payload):
        captured.update(path=path, payload=payload)
        return {"data": {"image_base64": [base64.b64encode(image).decode() for image in expected]}}

    monkeypatch.setattr(minimax_images, "_post_json", fake_post)

    assert minimax_images.generate_images("三套编辑画报", count=3) == expected
    assert captured["payload"]["n"] == 3


def test_generate_images_keeps_valid_partial_results(monkeypatch) -> None:
    expected = [b"image-1", b"image-2"]

    monkeypatch.setattr(
        minimax_images,
        "_post_json",
        lambda *_args, **_kwargs: {
            "data": {
                "image_base64": [
                    base64.b64encode(expected[0]).decode(),
                    "not-base64",
                    base64.b64encode(expected[1]).decode(),
                ],
                "success_count": 2,
                "failed_count": 1,
            }
        },
    )

    assert minimax_images.generate_images("三套编辑画报", count=3) == expected


def test_generate_images_accepts_image_urls(monkeypatch) -> None:
    expected = b"downloaded-image"
    captured = {}
    monkeypatch.setattr(
        minimax_images,
        "_post_json",
        lambda *_args, **_kwargs: {"data": {"image_urls": ["https://cdn.test/look.jpg"]}},
    )

    class Response:
        content = expected

        def raise_for_status(self):
            return None

    def fake_get(*args, **kwargs):
        captured.update(kwargs)
        return Response()

    monkeypatch.setattr(minimax_images.httpx, "get", fake_get)

    assert minimax_images.generate_images("一套编辑画报", count=1) == [expected]
    assert captured == {"timeout": 120, "trust_env": False}


def test_post_json_retries_one_transient_server_failure(monkeypatch) -> None:
    attempts = []

    class Response:
        status_code = 503

        def json(self):
            return {"message": "temporary"}

    class Client:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def post(self, *args, **kwargs):
            attempts.append(1)
            if len(attempts) == 1:
                return Response()
            return type(
                "Success",
                (),
                {
                    "status_code": 200,
                    "json": lambda self: {
                        "data": {"image_base64": [base64.b64encode(b"ok").decode()]}
                    },
                },
            )()

    monkeypatch.setattr(
        minimax_images,
        "resolve_minimax_access",
        lambda: minimax_images.MiniMaxAccess("key", "https://example.test"),
    )
    monkeypatch.setattr(minimax_images.httpx, "Client", Client)

    assert minimax_images.generate_images("稳定重试", count=1) == [b"ok"]
    assert attempts == [1, 1]


def test_post_json_does_not_retry_quota_failure(monkeypatch) -> None:
    attempts = []

    class Response:
        status_code = 429

        def json(self):
            return {"base_resp": {"status_code": 1028}}

    class Client:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def post(self, *args, **kwargs):
            attempts.append(1)
            return Response()

    monkeypatch.setattr(
        minimax_images,
        "resolve_minimax_access",
        lambda: minimax_images.MiniMaxAccess("key", "https://example.test"),
    )
    monkeypatch.setattr(minimax_images.httpx, "Client", Client)

    with pytest.raises(minimax_images.MiniMaxQuotaError):
        minimax_images.generate_images("额度错误", count=1)
    assert attempts == [1]


def test_image_logs_have_phase_only_and_never_prompt_text(monkeypatch, caplog) -> None:
    monkeypatch.setattr(
        minimax_images,
        "_post_json",
        lambda *_args, **_kwargs: {"data": {"image_base64": [base64.b64encode(b"ok").decode()]}},
    )

    with caplog.at_level("INFO", logger="outfit_ai.services.minimax_images"):
        minimax_images.generate_images("不要写入日志的 prompt", count=1)

    assert "phase=prompt" in caplog.text
    assert "不要写入日志的 prompt" not in caplog.text


def test_download_image_retries_a_transient_timeout(monkeypatch) -> None:
    attempts = []

    class Response:
        content = b"downloaded-after-timeout"

        def raise_for_status(self):
            return None

    def fake_get(*args, **kwargs):
        attempts.append(1)
        if len(attempts) == 1:
            raise minimax_images.httpx.ReadTimeout("temporary download timeout")
        return Response()

    monkeypatch.setattr(minimax_images.httpx, "get", fake_get)

    response = minimax_images._download_image("https://cdn.test/look.jpg")

    assert response.content == b"downloaded-after-timeout"
    assert attempts == [1, 1]
