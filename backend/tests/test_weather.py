import httpx
import pytest
from fastapi import HTTPException

from outfit_ai.routers import recommend as recommend_router
from outfit_ai.services import weather


class FakeResponse:
    def __init__(self, payload) -> None:
        self.payload = payload

    def raise_for_status(self):
        return self

    def json(self):
        return self.payload


class FakeClient:
    def __init__(self, forecast, reverse) -> None:
        self.forecast = forecast
        self.reverse = reverse

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def get(self, url, **kwargs):
        return FakeResponse(self.reverse if "nominatim" in url else self.forecast)


def test_weather_returns_local_date_city_and_rain(monkeypatch) -> None:
    forecast = {
        "timezone": "Asia/Shanghai",
        "current": {
            "time": "2026-07-31T08:00",
            "temperature_2m": 27.1,
            "apparent_temperature": 30.2,
            "relative_humidity_2m": 81,
            "weather_code": 61,
            "wind_speed_10m": 8.0,
            "is_day": 1,
            "precipitation": 0.2,
            "rain": 0.2,
        },
        "hourly": {
            "time": ["2026-07-31T08:00", "2026-07-31T09:00", "2026-07-31T10:00"],
            "precipitation_probability": [20, 60, 70],
        },
        "daily": {
            "time": ["2026-07-31"],
            "temperature_2m_max": [31.0],
            "temperature_2m_min": [25.0],
            "precipitation_probability_max": [70],
            "precipitation_sum": [5.4],
        },
    }
    reverse = {"features": [{"properties": {"geocoding": {"city": "上海市"}}}]}
    monkeypatch.setattr(
        weather.httpx,
        "Client",
        lambda **kwargs: FakeClient(forecast, reverse),
    )

    result = weather.get_weather(latitude=31.230, longitude=121.474)

    assert result.city == "上海市"
    assert result.local_date.isoformat() == "2026-07-31"
    assert result.timezone == "Asia/Shanghai"
    assert result.precipitation_probability_max == 70
    assert result.precipitation_sum == 5.4
    assert result.rain_window == "09:00–10:00"


def test_reverse_city_failure_does_not_fail_weather(monkeypatch) -> None:
    forecast = {
        "timezone": "Asia/Shanghai",
        "current": {
            "time": "2026-07-31T08:00",
            "temperature_2m": 27.1,
            "apparent_temperature": 30.2,
            "relative_humidity_2m": 81,
            "weather_code": 61,
            "wind_speed_10m": 8.0,
            "is_day": 1,
            "precipitation": 0.2,
            "rain": 0.2,
        },
        "hourly": {
            "time": ["2026-07-31T08:00"],
            "precipitation_probability": [20],
        },
        "daily": {
            "time": ["2026-07-31"],
            "temperature_2m_max": [31.0],
            "temperature_2m_min": [25.0],
            "precipitation_probability_max": [20],
            "precipitation_sum": [0.0],
        },
    }

    class ReverseFailureClient(FakeClient):
        def get(self, url, **kwargs):
            if "nominatim" in url:
                request = httpx.Request("GET", url)
                raise httpx.ConnectError("reverse unavailable", request=request)
            return super().get(url, **kwargs)

    monkeypatch.setattr(
        weather.httpx,
        "Client",
        lambda **kwargs: ReverseFailureClient(forecast, {}),
    )

    result = weather.get_weather(latitude=22.543, longitude=114.057)

    assert result.city is None
    assert result.temp == 27.1
    assert result.rain == 0.2


def test_reverse_city_uses_municipality_name_for_district(monkeypatch) -> None:
    reverse = {
        "features": [{"properties": {"geocoding": {"city": "黄浦区", "state": "上海市"}}}]
    }

    assert weather._reverse_city(FakeClient({}, reverse), 31.231, 121.475) == "上海市"


def test_manual_city_keeps_the_user_city_label(monkeypatch) -> None:
    forecast = {
        "timezone": "Asia/Shanghai",
        "current": {
            "time": "2026-07-31T08:00",
            "temperature_2m": 27.1,
            "apparent_temperature": 30.2,
            "relative_humidity_2m": 81,
            "weather_code": 61,
            "wind_speed_10m": 8.0,
            "is_day": 1,
            "precipitation": 0.2,
            "rain": 0.2,
        },
        "hourly": {"time": ["2026-07-31T08:00"], "precipitation_probability": [20]},
        "daily": {
            "time": ["2026-07-31"],
            "temperature_2m_max": [31.0],
            "temperature_2m_min": [25.0],
            "precipitation_probability_max": [20],
            "precipitation_sum": [0.0],
        },
    }
    reverse = {
        "features": [{"properties": {"geocoding": {"city": "黄浦区", "state": "上海市"}}}]
    }

    class CityClient(FakeClient):
        def get(self, url, **kwargs):
            if "geocoding-api" in url:
                return FakeResponse({"results": [{"latitude": 31.230, "longitude": 121.474}]})
            return super().get(url, **kwargs)

    monkeypatch.setattr(
        weather.httpx,
        "Client",
        lambda **kwargs: CityClient(forecast, reverse),
    )

    assert weather.get_weather(city="上海").city == "上海"


def test_weather_cache_uses_rounded_coordinate_key(monkeypatch) -> None:
    forecast = {
        "timezone": "Asia/Shanghai",
        "current": {
            "time": "2026-07-31T08:00",
            "temperature_2m": 27.1,
            "apparent_temperature": 30.2,
            "relative_humidity_2m": 81,
            "weather_code": 61,
            "wind_speed_10m": 8.0,
            "is_day": 1,
            "precipitation": 0.2,
            "rain": 0.2,
        },
        "hourly": {
            "time": ["2026-07-31T08:00"],
            "precipitation_probability": [20],
        },
        "daily": {
            "time": ["2026-07-31"],
            "temperature_2m_max": [31.0],
            "temperature_2m_min": [25.0],
            "precipitation_probability_max": [20],
            "precipitation_sum": [0.0],
        },
    }
    forecast_calls = []

    class CountingClient(FakeClient):
        def get(self, url, **kwargs):
            if "forecast" in url:
                forecast_calls.append(url)
            return super().get(url, **kwargs)

    weather._CACHE.clear()
    weather._REVERSE_CITY_CACHE.clear()
    monkeypatch.setattr(
        weather.httpx,
        "Client",
        lambda **kwargs: CountingClient(forecast, {"features": []}),
    )

    weather.get_weather(latitude=40.0001, longitude=116.0001)
    weather.get_weather(latitude=40.0004, longitude=116.0004)

    assert forecast_calls == ["https://api.open-meteo.com/v1/forecast"]


def test_weather_rounds_coordinates_before_provider_requests(monkeypatch) -> None:
    forecast = {
        "timezone": "Asia/Shanghai",
        "current": {
            "time": "2026-07-31T08:00",
            "temperature_2m": 27.1,
            "apparent_temperature": 30.2,
            "relative_humidity_2m": 81,
            "weather_code": 61,
            "wind_speed_10m": 8.0,
            "is_day": 1,
            "precipitation": 0.2,
            "rain": 0.2,
        },
        "hourly": {"time": ["2026-07-31T08:00"], "precipitation_probability": [20]},
        "daily": {
            "time": ["2026-07-31"],
            "temperature_2m_max": [31.0],
            "temperature_2m_min": [25.0],
            "precipitation_probability_max": [20],
            "precipitation_sum": [0.0],
        },
    }
    request_params = []

    class RecordingClient(FakeClient):
        def get(self, url, **kwargs):
            request_params.append((url, kwargs.get("params", {})))
            return super().get(url, **kwargs)

    weather._CACHE.clear()
    weather._REVERSE_CITY_CACHE.clear()
    monkeypatch.setattr(
        weather.httpx,
        "Client",
        lambda **kwargs: RecordingClient(forecast, {"features": []}),
    )

    weather.get_weather(latitude=31.230416, longitude=121.473701)

    for url, params in request_params:
        if "open-meteo.com/v1/forecast" in url:
            assert (params["latitude"], params["longitude"]) == (31.23, 121.474)
        if "nominatim.openstreetmap.org" in url:
            assert (params["lat"], params["lon"]) == (31.23, 121.474)


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
