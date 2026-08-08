"""密码哈希与 JWT 令牌签发/校验。"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import get_settings

ACCESS = "access"
REFRESH = "refresh"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def _create_token(
    subject: str,
    token_type: str,
    ttl: int,
    token_version: int,
    jti: str | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "ver": token_version,
        "iat": now,
        "exp": now + timedelta(seconds=ttl),
    }
    if jti is not None:
        payload["jti"] = jti
    return jwt.encode(payload, get_settings().jwt_secret, algorithm=get_settings().jwt_algorithm)


def create_access_token(user_id: int, token_version: int) -> str:
    s = get_settings()
    return _create_token(str(user_id), ACCESS, s.jwt_access_ttl, token_version)


def create_refresh_token(user_id: int, token_version: int, jti: str | None = None) -> tuple[str, str]:
    """签发 refresh token，返回 (token, jti)。jti 由调用方传入（用于登出黑名单回写）。"""
    s = get_settings()
    jti = jti or str(uuid.uuid4())
    token = _create_token(str(user_id), REFRESH, s.jwt_refresh_ttl, token_version, jti=jti)
    return token, jti


def decode_token(token: str, expected_type: str) -> dict[str, Any]:
    """验签并校验类型；失败抛 jose.JWTError。"""
    payload = jwt.decode(
        token,
        get_settings().jwt_secret,
        algorithms=[get_settings().jwt_algorithm],
    )
    if payload.get("type") != expected_type:
        raise JWTError("unexpected token type")
    return payload
