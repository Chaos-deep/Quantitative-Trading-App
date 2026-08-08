"""限流测试：独立 slowapi 实例，验证 429 + Retry-After。

注意装饰器顺序：`@app.get` 必须在外层，`@limiter.limit` 紧贴函数，
否则 FastAPI 注册的是未包装的原始函数，限流不生效（与 app 内路由写法一致）。
"""

from __future__ import annotations

import time

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address


def _build_client():
    limiter = Limiter(key_func=get_remote_address, enabled=True)

    app = FastAPI()
    app.state.limiter = limiter

    @app.exception_handler(RateLimitExceeded)
    async def _handler(request: Request, exc: RateLimitExceeded):
        resp = JSONResponse(status_code=429, content={"detail": exc.detail})
        current_limit = getattr(request.state, "view_rate_limit", None)
        if current_limit is not None:
            limit, args = current_limit
            reset_at, _ = limiter.limiter.get_window_stats(limit, *args)
            resp.headers["Retry-After"] = str(max(1, int(reset_at - time.time())))
        return resp

    @app.get("/limited")
    @limiter.limit("2/minute")
    def limited(request: Request):
        return {"ok": True}

    return TestClient(app)


def test_rate_limit_enforces_and_returns_retry_after():
    client = _build_client()
    assert client.get("/limited").status_code == 200
    assert client.get("/limited").status_code == 200
    resp = client.get("/limited")
    assert resp.status_code == 429
    assert "Retry-After" in resp.headers
