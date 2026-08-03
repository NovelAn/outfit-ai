from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..schemas import RecommendRequest
from ..services.llm import LLMResponseError, LLMUnavailableError
from ..services.recommend import recommend
from ..services.weather import WeatherData, WeatherInputError, WeatherServiceError, get_weather

router = APIRouter(tags=["recommend"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/weather", response_model=WeatherData)
def weather(
    city: str | None = None,
    latitude: float | None = Query(None, ge=-90, le=90),
    longitude: float | None = Query(None, ge=-180, le=180),
):
    try:
        return get_weather(city, latitude=latitude, longitude=longitude).model_dump()
    except WeatherInputError as exc:
        raise HTTPException(400, str(exc)) from exc
    except WeatherServiceError as exc:
        raise HTTPException(502, str(exc)) from exc


@router.post("/recommend")
def recommendation(payload: RecommendRequest, db: DbSession):
    try:
        return recommend(db, payload, history_action="shown")
    except LLMUnavailableError as exc:
        raise HTTPException(503, str(exc)) from exc
    except LLMResponseError as exc:
        raise HTTPException(502, str(exc)) from exc
    except WeatherServiceError as exc:
        raise HTTPException(502, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
