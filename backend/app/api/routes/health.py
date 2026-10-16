from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.errors import APIError


router = APIRouter()


@router.get("/live", summary="Liveness check")
def liveness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready", summary="Database readiness check")
def readiness(session: Session = Depends(get_db)) -> dict[str, str]:
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise APIError(503, "database_unavailable", "The database is unavailable") from None
    return {"status": "ready", "database": "available"}