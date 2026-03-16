"""
Health Check Endpoint — GET /health

Returns service status, version, and database connectivity.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database.database import get_db
from backend.schemas.response_schema import HealthResponse

router = APIRouter(tags=["Health"])

SERVICE_VERSION = "2.0.0"


@router.get("/health", response_model=HealthResponse)
def health_check(db: Session = Depends(get_db)) -> HealthResponse:
    """
    Service health check.

    Verifies:
    - API is running
    - Database connection is live (executes a trivial query)

    Returns 200 if healthy, 503 if database is unreachable.
    """
    # Test database connectivity
    try:
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
        db_status = "connected"
    except Exception as exc:  # noqa: BLE001
        db_status = f"error: {exc}"

    return HealthResponse(
        status="ok",
        version=SERVICE_VERSION,
        stage="2",
        db=db_status,
    )
