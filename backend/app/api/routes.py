from datetime import UTC, datetime

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import get_settings

router = APIRouter(prefix="/api/v1")


class HealthResponse(BaseModel):
    status: str
    service: str
    environment: str
    demo_mode: bool
    timestamp: datetime


@router.get("/health", response_model=HealthResponse, tags=["system"])
def health_check() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        environment=settings.app_env,
        demo_mode=settings.demo_mode,
        timestamp=datetime.now(UTC),
    )
