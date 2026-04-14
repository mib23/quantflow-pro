from fastapi import APIRouter

from app.core.cache import check_redis_connection
from app.core.database import check_database_connection
from app.core.settings import get_settings

router = APIRouter()


@router.get("/liveness")
def liveness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readiness")
def readiness() -> dict[str, object]:
    settings = get_settings()
    database_ok = check_database_connection(settings.database_url)
    redis_ok = check_redis_connection(settings.redis_url)
    return {
        "status": "ok" if database_ok and redis_ok else "degraded",
        "checks": {
            "database": database_ok,
            "redis": redis_ok,
        },
    }
