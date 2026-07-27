from datetime import datetime, timedelta

import httpx
from pydantic import BaseModel, ConfigDict

_WMO_CONDITION = {
    0: "晴",
    1: "大致晴朗",
    2: "多云",
    3: "阴",
    45: "雾",
    48: "雾",
    51: "毛毛雨",
    53: "毛毛雨",
    55: "毛毛雨",
    56: "冻毛毛雨",
    57: "冻毛毛雨",
    61: "小雨",
    63: "中雨",
    65: "大雨",
    66: "冻雨",
    67: "冻雨",
    71: "小雪",
    73: "中雪",
    75: "大雪",
    77: "米雪",
    80: "阵雨",
    81: "阵雨",
    82: "强阵雨",
    85: "阵雪",
    86: "强阵雪",
    95: "雷暴",
    96: "雷暴伴冰雹",
    99: "强雷暴伴冰雹",
}
_CACHE: dict[str, tuple[datetime, "WeatherData"]] = {}


class WeatherInputError(ValueError):
    pass


class WeatherServiceError(RuntimeError):
    pass


class WeatherData(BaseModel):
    model_config = ConfigDict(frozen=True)

    temp: float
    feels_like: float
    condition: str
    humidity: int
    wind_speed: float
    is_daytime: bool
    temp_max: float
    temp_min: float


def get_weather(
    city: str | None = None,
    *,
    latitude: float | None = None,
    longitude: float | None = None,
) -> WeatherData:
    key = f"{city}:{latitude}:{longitude}"
    cached = _CACHE.get(key)
    if cached and datetime.now() - cached[0] < timedelta(minutes=30):
        return cached[1]
    try:
        with httpx.Client(timeout=10) as client:
            if latitude is None or longitude is None:
                if not city:
                    raise WeatherInputError("需要城市或经纬度")
                result = (
                    client.get(
                        "https://geocoding-api.open-meteo.com/v1/search",
                        params={"name": city, "count": 1, "language": "zh"},
                    )
                    .raise_for_status()
                    .json()
                    .get("results", [])
                )
                if not result:
                    raise WeatherInputError(f"找不到城市：{city}")
                latitude, longitude = result[0]["latitude"], result[0]["longitude"]
            payload = (
                client.get(
                    "https://api.open-meteo.com/v1/forecast",
                    params={
                        "latitude": latitude,
                        "longitude": longitude,
                        "current": "temperature_2m,apparent_temperature,"
                        "relative_humidity_2m,weather_code,wind_speed_10m,is_day",
                        "daily": "temperature_2m_max,temperature_2m_min",
                        "forecast_days": 1,
                        "timezone": "auto",
                    },
                )
                .raise_for_status()
                .json()
            )
        current, daily = payload["current"], payload["daily"]
        weather = WeatherData(
            temp=current["temperature_2m"],
            feels_like=current["apparent_temperature"],
            condition=_WMO_CONDITION.get(current["weather_code"], "未知"),
            humidity=current["relative_humidity_2m"],
            wind_speed=current["wind_speed_10m"],
            is_daytime=bool(current["is_day"]),
            temp_max=daily["temperature_2m_max"][0],
            temp_min=daily["temperature_2m_min"][0],
        )
    except WeatherInputError:
        raise
    except (
        AttributeError,
        httpx.HTTPError,
        KeyError,
        IndexError,
        TypeError,
        ValueError,
    ) as exc:
        raise WeatherServiceError("天气服务暂时不可用") from exc
    _CACHE[key] = (datetime.now(), weather)
    return weather
