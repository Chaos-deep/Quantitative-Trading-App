"""结构化日志（structlog JSON）+ 按天滚动文件（保留 7 天）。"""

from __future__ import annotations

import logging
import sys
from logging.handlers import TimedRotatingFileHandler

import structlog

from app.core.config import get_settings


def setup_logging() -> None:
    settings = get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    handlers: list[logging.Handler] = []
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    handlers.append(console)

    if settings.log_dir_path is not None:
        log_dir = settings.log_dir_path
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = TimedRotatingFileHandler(
            log_dir / "backend.log",
            when="midnight",
            backupCount=7,  # 保留 7 天
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        handlers.append(file_handler)

    logging.basicConfig(level=level, handlers=handlers, format="%(message)s")

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=False),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(ensure_ascii=False),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "app"):
    return structlog.get_logger(name)
