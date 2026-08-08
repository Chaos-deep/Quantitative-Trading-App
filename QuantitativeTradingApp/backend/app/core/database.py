"""数据库引擎与会话。"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

engine: Engine | None = None
SessionLocal: sessionmaker[Session] | None = None


def init_engine(database_url: str | None = None) -> Engine:
    """创建引擎（首次调用后缓存；测试环境可传入 SQLite URL）。"""
    global engine, SessionLocal
    url = database_url or get_settings().database_url
    kwargs: dict = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    engine = create_engine(url, **kwargs)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return engine


def get_engine() -> Engine:
    if engine is None:
        init_engine()
    assert engine is not None
    return engine


def get_db():
    """FastAPI 依赖：请求级数据库会话。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
