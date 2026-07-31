import base64

from PIL import Image

from outfit_ai.services import minimax_images
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


def test_reference_analysis_is_structured(monkeypatch, tmp_path) -> None:
    image_path = tmp_path / "look.png"
    Image.new("RGB", (2, 2), "white").save(image_path)
    monkeypatch.setattr(
        minimax_images,
        "describe_image",
        lambda *_: (
            '{"style_keywords":["克制"],"palette":["海军蓝"],'
            '"silhouettes":["直线"],"layering":[],"materials":["羊毛"],'
            '"seasons":["autumn"],"scenes":["通勤"],"notable_elements":[]}'
        ),
    )

    analysis, _ = analyze_reference(image_path)

    assert analysis.style_keywords == ["克制"]
    assert analysis.scenes == ["通勤"]
