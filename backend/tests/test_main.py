from datetime import date

from fastapi.testclient import TestClient

from outfit_ai.main import app
from outfit_ai.routers import recommend as recommend_router
from outfit_ai.services.weather import WeatherData


def test_media_responses_disable_content_sniffing() -> None:
    with TestClient(app) as client:
        response = client.get("/media/missing.jpg")

    assert response.headers["x-content-type-options"] == "nosniff"


def test_weather_route_returns_daily_context(monkeypatch) -> None:
    monkeypatch.setattr(
        recommend_router,
        "get_weather",
        lambda *args, **kwargs: WeatherData(
            temp=27.1,
            feels_like=30.2,
            condition="小雨",
            humidity=81,
            wind_speed=8.0,
            is_daytime=True,
            temp_max=31.0,
            temp_min=25.0,
            city="上海市",
            local_date=date(2026, 7, 31),
            timezone="Asia/Shanghai",
            precipitation=0.2,
            rain=0.2,
            precipitation_probability_max=70,
            precipitation_sum=5.4,
            rain_window="09:00–10:00",
        ),
    )

    with TestClient(app) as client:
        response = client.get("/api/weather?latitude=31.230&longitude=121.474")

    assert response.status_code == 200
    assert {
        "temp", "feels_like", "condition", "humidity", "wind_speed",
        "is_daytime", "temp_max", "temp_min", "city", "local_date",
        "timezone", "precipitation", "rain",
        "precipitation_probability_max", "precipitation_sum", "rain_window",
    } <= response.json().keys()
