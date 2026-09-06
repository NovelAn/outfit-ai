import sys
from time import sleep

from .config import settings
from .db import SessionLocal
from .models import Profile
from .schemas import RecommendRequest
from .services.llm import LLMResponseError, LLMUnavailableError, require_api_key
from .services.profile_state import decode_profile_state
from .services.recommend import recommend
from .services.weather import WeatherServiceError

_PRECOMPUTE_MAX_ATTEMPTS = 2
_PRECOMPUTE_RETRY_DELAY_SECONDS = 15


def _recommend_with_retry(db, request):
    # ponytail: cap at two attempts to limit scheduler latency and provider load.
    for attempt in range(1, _PRECOMPUTE_MAX_ATTEMPTS + 1):
        try:
            return recommend(db, request, history_action="prepared")
        except (LLMUnavailableError, LLMResponseError) as exc:
            db.rollback()
            if attempt == _PRECOMPUTE_MAX_ATTEMPTS:
                raise
            print(
                f"每日预生成第 {attempt}/{_PRECOMPUTE_MAX_ATTEMPTS} 次失败，"
                f"{_PRECOMPUTE_RETRY_DELAY_SECONDS} 秒后重试：{exc}",
                file=sys.stderr,
            )
            sleep(_PRECOMPUTE_RETRY_DELAY_SECONDS)


def main() -> int:
    with SessionLocal() as db:
        profile = db.get(Profile, settings.user_id)
        state = decode_profile_state(profile.learned_from_feedback_json) if profile else {}
        location = state.get("last_location") or {}
        latitude, longitude = location.get("latitude"), location.get("longitude")
        city = location.get("city") if isinstance(location.get("city"), str) else None
        city = city or (profile.city if profile else None)
        if (
            not isinstance(latitude, int | float)
            or isinstance(latitude, bool)
            or not isinstance(longitude, int | float)
            or isinstance(longitude, bool)
            or not -90 <= latitude <= 90
            or not -180 <= longitude <= 180
        ):
            latitude = longitude = None
        if latitude is None and not city:
            print("每日预生成失败：未设置城市或定位", file=sys.stderr)
            return 1
        try:
            require_api_key()
            result = _recommend_with_retry(
                db,
                RecommendRequest(
                    city=city,
                    latitude=latitude,
                    longitude=longitude,
                    force_refresh=True,
                ),
            )
        except (LLMUnavailableError, LLMResponseError, ValueError, WeatherServiceError) as exc:
            print(f"每日预生成失败：{exc}", file=sys.stderr)
            return 1
    weather = result["weather"]
    local_date = weather["local_date"] if isinstance(weather, dict) else weather.local_date
    result_city = (weather.get("city") if isinstance(weather, dict) else weather.city) or city
    print(f"每日预生成完成：{local_date} {result_city}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
