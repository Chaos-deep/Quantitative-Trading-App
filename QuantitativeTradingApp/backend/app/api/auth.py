"""认证端点：register / login / logout / refresh / me。

JWT 严格黑名单语义见 docs/appendices/api/auth/jwt.md：
登出 = 将 refresh 的 jti 写入黑名单；刷新按严格 5 步顺序执行。
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import JWTError
from slowapi.errors import RateLimitExceeded
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import _client_rate_key, get_current_user, limiter
from app.core.redis_client import (
    blacklist_refresh,
    get_token_version,
    is_refresh_blacklisted,
)
from app.core.security import (
    REFRESH,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models import User
from app.schemas.schemas import (
    LoginIn,
    LogoutIn,
    RefreshIn,
    RegisterIn,
    TokenResponse,
    UserOut,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=UserOut)
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    exists = db.scalar(select(User).where(User.username == payload.username))
    if exists is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="用户名已存在")
    user = User(username=payload.username, password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute", key_func=_client_rate_key)
def login(request: Request, payload: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == payload.username))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    ver = get_token_version(user.id)
    access = create_access_token(user.id, ver)
    refresh, _ = create_refresh_token(user.id, ver)
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    payload: LogoutIn,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    # 提取 jti 写入黑名单（写，不是删）；重复提交无害（幂等）
    try:
        data = decode_token(payload.refresh_token, REFRESH)
        jti = data["jti"]
        exp = data.get("exp", 0)
        remaining = max(1, exp - int(datetime.now(timezone.utc).timestamp()))
        blacklist_refresh(jti, current.id, remaining)
    except (JWTError, KeyError):
        # 无效 token 也返回 204（幂等，不做任何事）
        pass
    return None


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshIn, db: Session = Depends(get_db)):
    """严格 5 步顺序（顺序不可颠倒，见 docs/appendices/api/auth/jwt.md）。"""
    # ① 验签（签名无效 → 401）
    try:
        data = decode_token(payload.refresh_token, REFRESH)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="refresh token 无效或已过期")

    # ② 解码提取 jti 与 ver
    jti = data.get("jti")
    ver = data.get("ver", 0)
    try:
        user_id = int(data["sub"])
    except (KeyError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="refresh token 无效")

    # ③ 查 Redis 黑名单：jti 存在即拒绝（已吊销）
    if not jti or is_refresh_blacklisted(jti):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="refresh token 已吊销")

    # ④ 查 token_version 是否等于 ver（不等 → 全设备已作废，立即拒绝）
    if get_token_version(user_id) != ver:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="令牌已作废，请重新登录")

    # ⑤ 全部通过 → 轮换新 token，旧 jti 写入黑名单（防重放）
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")

    exp = data.get("exp", 0)
    remaining = max(1, exp - int(datetime.now(timezone.utc).timestamp()))
    blacklist_refresh(jti, user_id, remaining)

    new_access = create_access_token(user_id, ver)
    new_refresh, _ = create_refresh_token(user_id, ver)
    return TokenResponse(access_token=new_access, refresh_token=new_refresh)


@router.get("/me", response_model=UserOut)
def me(current: User = Depends(get_current_user)):
    return current
