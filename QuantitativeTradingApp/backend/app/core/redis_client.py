"""Redis 客户端与 JWT 黑名单 / token_version 操作。

存储语义（docs/appendices/api/auth/jwt.md）：
- 黑名单：`refresh_token:{jti}` → User ID，TTL = 该 token 剩余有效期（≤7 天）。
- 全设备踢出：`user:{id}:token_version` 递增计数。
- 分布式锁：`daily_pipeline_lock` → run_id，TTL 7200s。
"""

from __future__ import annotations

import uuid
from typing import Optional

import redis

from app.core.config import get_settings

_redis: redis.Redis | None = None

# Lua：仅当 value 等于持有者标记时才删除（防止锁超时后误删他人锁）
_RELEASE_SCRIPT = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""


def get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.Redis.from_url(get_settings().redis_url, decode_responses=True)
    return _redis


def close_redis() -> None:
    global _redis
    if _redis is not None:
        _redis.close()
        _redis = None


def _redis_key(kind: str, value: str) -> str:
    return f"{kind}:{value}"


# ---------- JWT 黑名单 ----------

def blacklist_refresh(jti: str, user_id: int, ttl: int) -> None:
    """将 refresh token 的 jti 写入黑名单（写，不是删）。"""
    r = get_redis()
    r.set(_redis_key("refresh_token", jti), str(user_id), ex=ttl)


def is_refresh_blacklisted(jti: str) -> bool:
    r = get_redis()
    return r.exists(_redis_key("refresh_token", jti)) > 0


# ---------- 全设备踢出（token_version） ----------

def get_token_version(user_id: int) -> int:
    r = get_redis()
    val = r.get(_redis_key("user", f"{user_id}:token_version"))
    return int(val) if val else 0


def increment_token_version(user_id: int) -> int:
    """全设备踢出：递增后，旧 token 的 ver 声明全部失效。"""
    r = get_redis()
    return r.incr(_redis_key("user", f"{user_id}:token_version"))


# ---------- 分布式锁 ----------

def acquire_lock(lock_key: str, ttl: int) -> str | None:
    """SET NX EX，返回锁标识（uuid）；失败返回 None。"""
    token = str(uuid.uuid4())
    r = get_redis()
    ok = r.set(lock_key, token, nx=True, ex=ttl)
    return token if ok else None


def release_lock(lock_key: str, token: str) -> bool:
    """Lua 原子释放：仅当 value == token 时删除。"""
    r = get_redis()
    return bool(r.eval(_RELEASE_SCRIPT, 1, lock_key, token))


def ping() -> bool:
    try:
        return bool(get_redis().ping())
    except redis.RedisError:
        return False
