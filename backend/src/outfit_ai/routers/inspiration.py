from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..schemas import InspirationRequest
from ..services.inspiration import generate
from ..services.llm import LLMResponseError, LLMUnavailableError
from ..services.minimax_images import (
    MiniMaxQuotaError,
    MiniMaxResponseError,
    MiniMaxUnavailableError,
)

router = APIRouter(prefix="/inspiration", tags=["inspiration"])
DbSession = Annotated[Session, Depends(get_db)]


@router.post("/generate")
def generate_inspiration(payload: InspirationRequest, db: DbSession):
    try:
        return generate(db, payload)
    except (LLMUnavailableError, MiniMaxUnavailableError) as exc:
        raise HTTPException(503, str(exc)) from exc
    except MiniMaxQuotaError as exc:
        raise HTTPException(429, str(exc)) from exc
    except (LLMResponseError, MiniMaxResponseError) as exc:
        raise HTTPException(502, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
