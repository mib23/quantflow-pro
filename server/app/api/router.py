from fastapi import APIRouter

from app.api.routers.health import router as health_router
from app.modules.accounts.router import router as accounts_router
from app.modules.auth.router import router as auth_router
from app.modules.dashboard.router import router as dashboard_router
from app.modules.market_data.router import router as market_data_router
from app.modules.orders.router import router as orders_router
from app.modules.risk.router import router as risk_router

api_router = APIRouter()
api_router.include_router(health_router, prefix="/health", tags=["health"])
api_router.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
api_router.include_router(accounts_router, prefix="/api/v1/accounts", tags=["accounts"])
api_router.include_router(dashboard_router, prefix="/api/v1/dashboard", tags=["dashboard"])
api_router.include_router(market_data_router, prefix="/api/v1/market-data", tags=["market-data"])
api_router.include_router(orders_router, prefix="/api/v1/orders", tags=["orders"])
api_router.include_router(risk_router, prefix="/api/v1/risk", tags=["risk"])
