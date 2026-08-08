"""FastAPI 依赖：数据库会话、当前用户、限流（slowapi + XFF 信任）。"""

from __future__ import annotations

from typing import Generator

from fastapi import Depends, HTTPException, Request, status
from jose import JWTError
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.redis_client import get_token_version
from app.core.security import ACCESS, decode_token
from app.models import User

settings = get_settings()


def get_client_ip(request: Request) -> str:
    """真实客户端 IP。

    信任 Nginx 透传的 X-Forwarded-For（限流按真实 IP 计），取最左端元素
    （nginx 追加在末尾，最左端为真实客户端）。仅当 trust_xff 开启时信任。
    """
    if settings.trust_xff:
        xff = request.headers.get("X-Forwarded-For")
        if xff:
            first = xff.split(",")[0].strip()
            if first:
                return first
    if request.client is not None:
        return request.client.host
    return "unknown"


def _user_id_from_request(request: Request) -> int | None:
    """从 Authorization 头尽力解析用户 id（用于按用户限流）。"""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    try:
        payload = decode_token(auth[7:].strip(), ACCESS)
        return int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        return None


def _client_rate_key(request: Request) -> str:
    return f"ip:{get_client_ip(request)}"


def _user_rate_key(request: Request) -> str:
    uid = _user_id_from_request(request)
    if uid is not None:
        return f"user:{uid}"
    return _client_rate_key(request)


# headers_enabled=False：slowapi 的 header 注入要求端点返回 starlette.Response，
# 而本项目端点返回 Pydantic 模型/dict；Retry-After 在 429 异常处理器中手动计算
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.rate_limit_storage_uri,
    headers_enabled=False,
    enabled=settings.rate_limit_enabled,
)


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Bearer access token → 当前用户（含 token_version 校验）。"""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供或格式错误的认证凭据",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_token(auth[7:].strip(), ACCESS)
        user_id = int(payload["sub"])
        ver = payload.get("ver", 0)
    except (JWTError, KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌无效或已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # 全设备踢出校验：token_version 不匹配即拒绝
    if get_token_version(user_id) != ver:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌已作废，请重新登录",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    request.state.current_user = user
    return user
