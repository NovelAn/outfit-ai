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


def test_access_rejects_invalid_config_without_leaking_contents(
    monkeypatch, tmp_path
) -> None:
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
