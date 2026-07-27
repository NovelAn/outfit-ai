from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..schemas import RecommendRequest
from ..services.recommend import recommend
from ..services.weather import get_weather

router = APIRouter(tags=["recommend"])


@router.get("/weather")
def weather(
    city: str | None = None,
    latitude: float | None = Query(None, ge=-90, le=90),
    longitude: float | None = Query(None, ge=-180, le=180),
):
    try:
        return get_weather(city, latitude=latitude, longitude=longitude).model_dump()
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/recommend")
def recommendation(payload: RecommendRequest, db: Session = Depends(get_db)):
    try:
        return recommend(db, payload)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
