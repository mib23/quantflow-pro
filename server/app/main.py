import asyncio
import contextlib
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.api.ws import ws_router
from app.core.bootstrap import ensure_local_baseline
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware
from app.core.settings import get_settings
from app.modules.runtime.service import get_runtime_service

logger = logging.getLogger(__name__)
RUNTIME_HEALTH_MONITOR_INTERVAL_SECONDS = 30


async def _run_runtime_health_monitor(stop_event: asyncio.Event) -> None:
    while not stop_event.is_set():
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=RUNTIME_HEALTH_MONITOR_INTERVAL_SECONDS)
            break
        except asyncio.TimeoutError:
            try:
                get_runtime_service().sweep_stale_instances()
            except Exception:
                logger.exception("Runtime heartbeat sweep failed.")


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        debug=settings.debug,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.add_middleware(RequestContextMiddleware)

    @application.on_event("startup")
    async def startup() -> None:
        if settings.env in {"local", "test"}:
            ensure_local_baseline()
        if settings.env != "test":
            stop_event = asyncio.Event()
            application.state.runtime_health_monitor_stop_event = stop_event
            application.state.runtime_health_monitor_task = asyncio.create_task(_run_runtime_health_monitor(stop_event))

    @application.on_event("shutdown")
    async def shutdown() -> None:
        stop_event = getattr(application.state, "runtime_health_monitor_stop_event", None)
        task = getattr(application.state, "runtime_health_monitor_task", None)
        if stop_event is not None:
            stop_event.set()
        if task is not None:
            with contextlib.suppress(asyncio.CancelledError):
                await task

    register_exception_handlers(application)
    application.include_router(api_router)
    application.include_router(ws_router)

    return application


app = create_app()
