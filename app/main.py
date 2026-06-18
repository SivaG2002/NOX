import asyncio
import logging
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.api.router import api_router
from app.bot.client import StreamNotificationBot
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.rate_limit import RateLimitMiddleware
from app.core.security import CSRFMiddleware
from app.dashboard.routes import router as dashboard_router
from app.database.session import create_database_schema
from app.services.stream_monitor import StreamMonitor

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.auto_create_tables:
        await create_database_schema()

    bot: StreamNotificationBot | None = None
    bot_task: asyncio.Task | None = None
    monitor: StreamMonitor | None = None
    monitor_task: asyncio.Task | None = None

    token = settings.discord_bot_token.get_secret_value()
    if token:
        bot = StreamNotificationBot()
        app.state.discord_bot = bot
        bot_task = asyncio.create_task(bot.start(token), name="discord-bot")
        monitor = StreamMonitor(bot, settings=settings)
        app.state.stream_monitor = monitor
        monitor_task = asyncio.create_task(monitor.run(), name="stream-monitor")
    else:
        app.state.discord_bot = None
        logger.warning("discord_bot_token_missing")

    try:
        yield
    finally:
        if monitor:
            await monitor.stop()
        if monitor_task:
            monitor_task.cancel()
            with suppress(asyncio.CancelledError):
                await monitor_task
        if bot:
            await bot.close()
        if bot_task:
            bot_task.cancel()
            with suppress(asyncio.CancelledError):
                await bot_task


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
    app.mount("/static", StaticFiles(directory="app/static"), name="static")
    app.include_router(api_router)
    app.include_router(dashboard_router)

    app.add_middleware(CSRFMiddleware)
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key.get_secret_value(),
        session_cookie=settings.session_cookie_name,
        https_only=settings.is_production,
        same_site="lax",
        max_age=60 * 60 * 24 * 7,
    )
    app.add_middleware(RateLimitMiddleware, requests_per_minute=settings.rate_limit_per_minute)

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_: Request, exc: RequestValidationError):
        return JSONResponse(status_code=422, content={"detail": exc.errors()})

    return app


app = create_app()

