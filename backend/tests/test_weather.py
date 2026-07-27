import httpx
import pytest
from fastapi import HTTPException

from outfit_ai.routers import recommend as recommend_router
from outfit_ai.services import weather


def test_weather_wraps_network_failure(monkeypatch) -> None:
    class BrokenClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def get(self, *args, **kwargs):
            request = httpx.Request("GET", "https://api.open-meteo.com")
            raise httpx.ConnectError("provider internals", request=request)

    monkeypatch.setattr(weather.httpx, "Client", BrokenClient)

    with pytest.raises(weather.WeatherServiceError, match="天气服务暂时不可用"):
        weather.get_weather("上海")


def test_weather_route_maps_provider_failure_to_502(monkeypatch) -> None:
    monkeypatch.setattr(
        recommend_router,
        "get_weather",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            weather.WeatherServiceError("天气服务暂时不可用")
        ),
    )

    with pytest.raises(HTTPException) as error:
        recommend_router.weather(city="上海")

    assert error.value.status_code == 502
