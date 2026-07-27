import base64

from PIL import Image

from outfit_ai.services.vision import image_data_url


def test_image_data_url_can_bound_stylist_payload(tmp_path) -> None:
    path = tmp_path / "large.png"
    Image.effect_noise((1400, 1400), 100).convert("RGB").save(path)

    data_url = image_data_url(path, max_bytes=100_000)
    header, encoded = data_url.split(",", 1)

    assert header == "data:image/jpeg;base64"
    assert len(base64.b64decode(encoded)) <= 100_000
