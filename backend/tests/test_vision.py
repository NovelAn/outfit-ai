import base64

import pytest
from PIL import Image
from pydantic import ValidationError

from outfit_ai.schemas import ClothingAttributes
from outfit_ai.services import minimax_images
from outfit_ai.services.minimax_images import MiniMaxResponseError
from outfit_ai.services.vision import analyze_reference, extract, image_data_url


def test_image_data_url_can_bound_stylist_payload(tmp_path) -> None:
    path = tmp_path / "large.png"
    Image.effect_noise((1400, 1400), 100).convert("RGB").save(path)

    data_url = image_data_url(path, max_bytes=100_000)
    header, encoded = data_url.split(",", 1)

    assert header == "data:image/jpeg;base64"
    assert len(base64.b64decode(encoded)) <= 100_000


def test_extract_accepts_markdown_wrapped_vlm_json(monkeypatch, tmp_path) -> None:
    image_path = tmp_path / "item.png"
    Image.new("RGB", (2, 2), "white").save(image_path)
    monkeypatch.setattr(
        minimax_images,
        "describe_image",
        lambda *_: (
            "```json\n"
            '{"name":"白衬衫","category":"top","primary_color":"白色",'
            '"styles":[],"tags":[],"seasons":[],"occasions":[]}'
            "\n```"
        ),
    )

    attributes, raw = extract(image_path)

    assert attributes.category == "top"
    assert attributes.name == "白衬衫"
    assert raw.startswith("```json")


def test_extract_uses_last_json_block_when_vlm_echoes_schema(
    monkeypatch, tmp_path
) -> None:
    image_path = tmp_path / "item.png"
    Image.new("RGB", (2, 2), "white").save(image_path)
    raw = (
        "```json\n"
        '{"properties":{"name":{"type":"string"}},"required":["name"]}'
        "\n```\n"
        "```json\n"
        '{"name":"蓝色棒球帽","category":"hat","primary_color":"蓝色",'
        '"styles":["休闲"],"tags":["棒球帽"],"seasons":["四季"],'
        '"occasions":["日常"]}'
        "\n```"
    )
    monkeypatch.setattr(minimax_images, "describe_image", lambda *_: raw)

    attributes, returned_raw = extract(image_path)

    assert attributes.name == "蓝色棒球帽"
    assert attributes.category == "hat"
    assert returned_raw == raw


def test_extract_normalizes_common_semantic_versatility(monkeypatch, tmp_path) -> None:
    image_path = tmp_path / "item.png"
    Image.new("RGB", (2, 2), "white").save(image_path)
    raw = (
        '{"name":"条纹长袖衬衫","category":"top",'
        '"primary_color":"浅蓝色","secondary_color":"白色",'
        '"material":"棉质","fit":"宽松","formality":"休闲",'
        '"styles":["休闲","简约"],"tags":["条纹","长袖"],'
        '"seasons":["春季","秋季"],"occasions":["日常","通勤"],'
        '"versatility":"高"}'
    )
    monkeypatch.setattr(minimax_images, "describe_image", lambda *_: raw)

    attributes, _ = extract(image_path)

    assert attributes.versatility == 0.85


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("高", 0.85),
        ("high", 0.85),
        ("中", 0.5),
        ("medium", 0.5),
        ("低", 0.25),
        ("low", 0.25),
        (0, 0.0),
        (1, 1.0),
        ("0.7", 0.7),
    ],
)
def test_clothing_attributes_accepts_supported_versatility(value, expected) -> None:
    attributes = ClothingAttributes(
        name="衬衫",
        category="top",
        primary_color="蓝色",
        versatility=value,
    )

    assert attributes.versatility == expected


@pytest.mark.parametrize("value", ["未知", -0.1, 1.1, True, False])
def test_clothing_attributes_rejects_unsupported_versatility(value) -> None:
    with pytest.raises(ValidationError):
        ClothingAttributes(
            name="衬衫",
            category="top",
            primary_color="蓝色",
            versatility=value,
        )


def test_extract_requests_simplified_chinese_display_fields(monkeypatch, tmp_path) -> None:
    image_path = tmp_path / "item.png"
    Image.new("RGB", (2, 2), "white").save(image_path)
    prompts = []

    def describe_image(_, prompt):
        prompts.append(prompt)
        return (
            '{"name":"白衬衫","category":"top","primary_color":"白色",'
            '"styles":[],"tags":[],"seasons":[],"occasions":[]}'
        )

    monkeypatch.setattr(minimax_images, "describe_image", describe_image)

    extract(image_path)

    assert "除 category 外，所有面向用户的字段必须使用简体中文" in prompts[0]
    assert "model_json_schema" not in prompts[0]
    assert "properties" not in prompts[0]
    assert "top/bottom/outerwear/dress/shoes/accessory" in prompts[0]
    assert "不要输出 JSON Schema 或 Markdown" in prompts[0]
    assert "versatility 必须是 0 到 1 的数字" in prompts[0]
    assert "styles、tags、seasons、occasions 必须是字符串数组" in prompts[0]
    assert "可空字段使用 null" in prompts[0]


def test_reference_analysis_is_structured(monkeypatch, tmp_path) -> None:
    image_path = tmp_path / "look.png"
    Image.new("RGB", (2, 2), "white").save(image_path)
    prompts = []

    def describe_image(_, prompt):
        prompts.append(prompt)
        return (
            '{"style_keywords":["克制"],"palette":["海军蓝"],'
            '"silhouettes":["直线"],"layering":[],"materials":["羊毛"],'
            '"seasons":["秋季"],"scenes":["通勤"],"notable_elements":["低饱和"]}'
        )

    monkeypatch.setattr(minimax_images, "describe_image", describe_image)

    analysis, _ = analyze_reference(image_path)

    assert analysis.style_keywords == ["克制"]
    assert analysis.scenes == ["通勤"]
    assert "style_keywords、palette、silhouettes 和 notable_elements 各至少填写 1 项" in prompts[0]


def test_reference_analysis_rejects_an_all_empty_result(monkeypatch, tmp_path) -> None:
    image_path = tmp_path / "look.png"
    Image.new("RGB", (2, 2), "white").save(image_path)
    monkeypatch.setattr(
        minimax_images,
        "describe_image",
        lambda *_: (
            '{"style_keywords":[],"palette":[],"silhouettes":[],"layering":[],'
            '"materials":[],"seasons":[],"scenes":[],"notable_elements":[]}'
        ),
    )

    with pytest.raises(MiniMaxResponseError, match="有效参考 Look 分析"):
        analyze_reference(image_path)
