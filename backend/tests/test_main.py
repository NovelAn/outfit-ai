from fastapi.testclient import TestClient

from outfit_ai.main import app


def test_media_responses_disable_content_sniffing() -> None:
    with TestClient(app) as client:
        response = client.get("/media/missing.jpg")

    assert response.headers["x-content-type-options"] == "nosniff"
