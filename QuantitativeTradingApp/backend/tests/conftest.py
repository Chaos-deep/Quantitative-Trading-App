"""pytest 共享夹具：SQLite 内存库 + 独立 FastAPI 实例。"""

from __future__ import annotations

import os

os.environ.setdefault("RATE_LIMIT_ENABLED", "false")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("APP_ENV", "test")

import fakeredis
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.main import create_app
from app.models import Base, Stock, User, UserPreference, UserPosition
from app.core.security import hash_password

# 测试夹具口令（仅用于测试，非任何环境的真实凭据）
TEST_FIXTURE_PASSWORD = "test-fixture-password"


@pytest.fixture(autouse=True)
def _fake_redis(monkeypatch):
    """替换真实 Redis：JWT 黑名单 / token_version / 锁在测试中走内存 fake。"""
    fake = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("app.core.redis_client.get_redis", lambda: fake)
    return fake


@pytest.fixture()
def engine():
    e = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(e)
    return e


@pytest.fixture()
def db_session(engine):
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def client(engine):
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    app = create_app()

    def _override_get_db():
        session = Session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override_get_db
    return TestClient(app)


@pytest.fixture()
def stock_factory(db_session):
    """向测试库写入股票与日线数据。"""

    def _make(
        code: str,
        name: str,
        market: str = "SH",
        closes: list[float] | None = None,
        dates: list[str] | None = None,
    ) -> Stock:
        stock = db_session.get(Stock, code)
        if stock is None:
            stock = Stock(code=code, name=name, market=market, status="active")
            db_session.add(stock)
            db_session.flush()
        if closes and dates:
            from app.models import DailyBar

            n = min(len(closes), len(dates))
            for i in range(n):
                db_session.add(
                    DailyBar(
                        stock_code=code,
                        date=dates[i],
                        open=closes[i],
                        high=max(closes[i], closes[i] if i == 0 else closes[i - 1]),
                        low=min(closes[i], closes[i] if i == 0 else closes[i - 1]),
                        close=closes[i],
                        volume=10000,
                    )
                )
            db_session.flush()
        return stock

    return _make


@pytest.fixture()
def user_factory(db_session):
    def _make(username: str = "tester", password: str = TEST_FIXTURE_PASSWORD):
        user = db_session.scalar(
            db_session.query(User).filter(User.username == username)
        )
        if user is None:
            user = User(username=username, password_hash=hash_password(password))
            db_session.add(user)
            db_session.flush()
        pref = UserPreference(
            user_id=user.id, risk_level="moderate", total_capital=None
        )
        db_session.add(pref)
        db_session.flush()
        return user

    return _make


@pytest.fixture()
def auth_headers(client):
    """注册 + 登录，返回带 Authorization 的请求头。"""

    def _headers(username: str = "tester", password: str = TEST_FIXTURE_PASSWORD):
        client.post(
            "/api/auth/register",
            json={"username": username, "password": password},
        )
        resp = client.post(
            "/api/auth/login",
            json={"username": username, "password": password},
        )
        token = resp.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _headers
