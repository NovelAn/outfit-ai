from datetime import date, datetime, timedelta

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
_REVERSE_CITY_CACHE: dict[str, tuple[datetime, str | None]] = {}


class WeatherInputError(ValueError):
    pass


class WeatherAmbiguousError(WeatherInputError):
    def __init__(self, candidates: list[dict]):
        super().__init__("城市匹配到多个候选，请先选择具体城市或区县")
        self.candidates = candidates


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
    city: str | None
    local_date: date
    timezone: str
    precipitation: float
    rain: float
    precipitation_probability_max: int
    precipitation_sum: float
    rain_window: str | None
    target_date: date | None = None


def _coordinate_key(latitude: float, longitude: float) -> str:
    return f"{latitude:.3f}:{longitude:.3f}"


def _reverse_city(client: httpx.Client, latitude: float, longitude: float) -> str | None:
    key = _coordinate_key(latitude, longitude)
    cached = _REVERSE_CITY_CACHE.get(key)
    if cached and datetime.now() - cached[0] < timedelta(hours=24):
        return cached[1]
    city = None
    try:
        geocoding = (
            client.get(
                "https://nominatim.openstreetmap.org/reverse",
                params={
                    "lat": latitude,
                    "lon": longitude,
                    "format": "geocodejson",
                    "zoom": 10,
                    "accept-language": "zh-CN",
                },
                headers={"User-Agent": "Outfit-AI/0.1"},
            )
            .raise_for_status()
            .json()["features"][0]["properties"]["geocoding"]
        )
        city = next(
            (
                geocoding[name]
                for name in ("city", "locality", "county", "state")
                if geocoding.get(name)
            ),
            None,
        )
        state = geocoding.get("state")
        if city and city.endswith(("区", "县")) and isinstance(state, str) and state.endswith("市"):
            city = state
    except (AttributeError, httpx.HTTPError, IndexError, KeyError, TypeError, ValueError):
        pass
    _REVERSE_CITY_CACHE[key] = (datetime.now(), city)
    return city


def _rain_window(current_time: str, hourly: dict) -> str | None:
    start = datetime.fromisoformat(current_time)
    end = start + timedelta(hours=12)
    first = last = None
    for raw_time, probability in zip(
        hourly.get("time", []), hourly.get("precipitation_probability", []), strict=True
    ):
        point = datetime.fromisoformat(raw_time)
        if point <= start or point > end:
            continue
        if probability >= 50:
            if first is None:
                first = point
            last = point
        elif first is not None:
            break
    if first is None or last is None:
        return None
    return f"{first:%H:%M}–{last:%H:%M}"


def get_weather(
    city: str | None = None,
    *,
    latitude: float | None = None,
    longitude: float | None = None,
    target_date: date | None = None,
) -> WeatherData:
    if target_date is not None:
        today = date.today()
        if target_date < today or target_date > today + timedelta(days=14):
            raise WeatherInputError("target_date 只能是今天或未来 14 天内")
    latitude = round(latitude, 3) if latitude is not None else None
    longitude = round(longitude, 3) if longitude is not None else None
    target_key = target_date.isoformat() if target_date else "current"
    key = (
        _coordinate_key(latitude, longitude)
        if latitude is not None and longitude is not None
        else city or ""
    )
    key = f"{key}|{target_key}"
    cached = _CACHE.get(key)
    if cached and datetime.now() - cached[0] < timedelta(minutes=30):
        return cached[1]
    try:
        # Weather providers are public endpoints; do not inherit a developer's
        # local SOCKS/HTTP proxy configuration into the backend runtime.
        with httpx.Client(timeout=10, trust_env=False) as client:
            if latitude is None or longitude is None:
                if not city:
                    raise WeatherInputError("需要城市或经纬度")
                result = (
                    client.get(
                        "https://geocoding-api.open-meteo.com/v1/search",
                        params={"name": city, "count": 5, "language": "zh"},
                    )
                    .raise_for_status()
                    .json()
                    .get("results", [])
                )
                if not result:
                    raise WeatherInputError(f"找不到城市：{city}")
                if len(result) > 1:
                    raise WeatherAmbiguousError(
                        [
                            {
                                key: candidate[key]
                                for key in (
                                    "name",
                                    "latitude",
                                    "longitude",
                                    "admin1",
                                    "admin2",
                                    "country",
                                )
                                if candidate.get(key) is not None
                            }
                            for candidate in result
                        ]
                    )
                latitude, longitude = result[0]["latitude"], result[0]["longitude"]
                latitude, longitude = round(latitude, 3), round(longitude, 3)
            payload = (
                client.get(
                    "https://api.open-meteo.com/v1/forecast",
                    params={
                        "latitude": latitude,
                        "longitude": longitude,
                        "current": "temperature_2m,apparent_temperature,"
                        "relative_humidity_2m,weather_code,wind_speed_10m,is_day,"
                        "precipitation,rain",
                        "hourly": "precipitation_probability",
                        "daily": "temperature_2m_max,temperature_2m_min,"
                        "precipitation_probability_max,precipitation_sum,weather_code",
                        "forecast_days": 16 if target_date else 1,
                        "timezone": "auto",
                    },
                )
                .raise_for_status()
                .json()
            )
            reverse_city = _reverse_city(client, latitude, longitude)
        current, daily = payload["current"], payload["daily"]
        current_date = datetime.fromisoformat(current["time"]).date()
        wanted_date = target_date or current_date
        daily_index = daily.get("time", []).index(wanted_date.isoformat())
        hourly = payload["hourly"]
        target_current = (
            current
            if wanted_date == current_date
            else {
                "temperature_2m": (
                    (daily.get("temperature_2m_max") or [])[daily_index]
                    + (daily.get("temperature_2m_min") or [])[daily_index]
                )
                / 2,
                "apparent_temperature": (daily.get("temperature_2m_max") or [])[daily_index],
                "relative_humidity_2m": current["relative_humidity_2m"],
                "weather_code": current["weather_code"],
                "wind_speed_10m": current["wind_speed_10m"],
                "is_day": current["is_day"],
                "precipitation": daily.get("precipitation_sum", [0])[daily_index],
                "rain": daily.get("precipitation_sum", [0])[daily_index],
            }
        )
        if wanted_date != current_date and daily.get("weather_code"):
            target_current["weather_code"] = daily["weather_code"][daily_index]
        weather = WeatherData(
            temp=target_current["temperature_2m"],
            feels_like=target_current["apparent_temperature"],
            condition=_WMO_CONDITION.get(target_current["weather_code"], "未知"),
            humidity=target_current["relative_humidity_2m"],
            wind_speed=target_current["wind_speed_10m"],
            is_daytime=bool(target_current["is_day"]),
            temp_max=daily["temperature_2m_max"][daily_index],
            temp_min=daily["temperature_2m_min"][daily_index],
            city=city.strip() if city else reverse_city,
            local_date=current_date,
            timezone=payload["timezone"],
            precipitation=target_current["precipitation"],
            rain=target_current["rain"],
            precipitation_probability_max=daily["precipitation_probability_max"][daily_index],
            precipitation_sum=daily["precipitation_sum"][daily_index],
            rain_window=_rain_window(current["time"], hourly)
            if wanted_date == current_date
            else None,
            target_date=wanted_date,
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
