from fastapi import APIRouter, HTTPException
from app.models import HealthCheck
from app.config import get_settings

router = APIRouter(prefix="/health", tags=["health"])
settings = get_settings()

@router.get("", response_model=HealthCheck)
async def health_check():
    """Check API health status"""
    return HealthCheck(
        status="ok",
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
    )

@router.get("/ready")
async def readiness_check():
    """Readiness probe for orchestration"""
    # Add actual readiness checks (DB, cache, etc.)
    return {"status": "ready"}
