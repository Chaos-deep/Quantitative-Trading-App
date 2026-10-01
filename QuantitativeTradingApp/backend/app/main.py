"""FastAPI 入口。

- 路由统一挂载在 /api 前缀下
- 请求追踪：每次请求生成/透传 X-Request-ID
- 限流：slowapi（Redis 计数器），429 + Retry-After
- 调度：APScheduler（SCHEDULE_ENABLED 控制）
"""

from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.api import auth, recommendations, stocks, user_data
from app.core.config import get_settings
from app.core.database import init_engine
from app.core.dependencies import limiter
from app.services.scheduler import PipelineScheduler
from app.utils.logging import get_logger, setup_logging

logger = get_logger("main")

_scheduler: PipelineScheduler | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _scheduler
    settings = get_settings()
    if settings.schedule_enabled:
        _scheduler = PipelineScheduler()
        _scheduler.start()
    yield
    if _scheduler is not None:
        _scheduler.stop()


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging()
    init_engine()

    if settings.jwt_secret == "CHANGE_ME_IN_PRODUCTION":
        logger.warning(
            "JWT_SECRET 仍为占位值，请在 .env/环境变量中配置强随机密钥（openssl rand -hex 32）"
        )

    app = FastAPI(
        title=settings.app_name,
        version="0.5.0",
        lifespan=lifespan,
    )

    # 限流
    app.state.limiter = limiter

    @app.exception_handler(RateLimitExceeded)
    async def _rate_limit_handler(request: Request, exc: RateLimitExceeded):
        response = JSONResponse(
            status_code=429,
            content={"detail": "请求过于频繁，请稍后再试"},
        )
        # Retry-After：依据触发限流的窗口重置时间计算（slowapi headers_enabled 关闭，
        # 避免其对非 Response 返回值的兼容问题）
        current_limit = getattr(request.state, "view_rate_limit", None)
        if current_limit is not None:
            limit, args = current_limit
            try:
                reset_at, _ = request.app.state.limiter.limiter.get_window_stats(
                    limit, *args
                )
                response.headers["Retry-After"] = str(
                    max(1, int(reset_at - time.time()))
                )
            except Exception:
                pass
        return response

    # CORS
    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins if origins else ["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 请求追踪：X-Request-ID 贯穿日志
    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:16]
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        try:
            response = await call_next(request)
        finally:
            structlog.contextvars.unbind_contextvars("request_id")
        response.headers["X-Request-ID"] = request_id
        return response

    # 路由
    prefix = settings.api_prefix
    app.include_router(auth.router, prefix=prefix)
    app.include_router(recommendations.router, prefix=prefix)
    app.include_router(stocks.router, prefix=prefix)
    app.include_router(user_data.router, prefix=prefix)

    @app.get(prefix + "/health")
    def health_shortcut():
        return {"status": "ok"}

    return app


app = create_app()
