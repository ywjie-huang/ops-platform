"""JWT 黑名单 — 登出/吊销的 token 在剩余有效期内拒绝访问（Redis 优先，内存降级）。"""

from __future__ import annotations

import time

from app.db.redis import get_redis

_KEY_PREFIX = "jwt:blacklist:"

# 内存降级存储：jti -> expire_ts
_store: dict[str, float] = {}


def _cleanup() -> None:
    now = time.time()
    expired = [k for k, v in _store.items() if v < now]
    for k in expired:
        del _store[k]


def revoke(jti: str, token_exp_ts: float) -> None:
    """将 token 加入黑名单，TTL 为 token 剩余有效期。"""
    if not jti:
        return
    ttl = int(token_exp_ts - time.time())
    if ttl <= 0:
        return  # 已过期，无需拉黑

    r = get_redis()
    if r is not None:
        r.setex(f"{_KEY_PREFIX}{jti}", ttl, "1")
    else:
        _cleanup()
        _store[jti] = token_exp_ts


def is_revoked(jti: str | None) -> bool:
    """检查 token 是否已被吊销（无 jti 的旧 token 视为未吊销，兼容存量登录）。"""
    if not jti:
        return False

    r = get_redis()
    if r is not None:
        return r.exists(f"{_KEY_PREFIX}{jti}") > 0

    exp_ts = _store.get(jti)
    if exp_ts is None:
        return False
    if exp_ts < time.time():
        del _store[jti]
        return False
    return True
