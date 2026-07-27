"""登录防爆破 — 按 用户名+IP 计数，超限锁定（Redis 优先，内存降级）。"""

from __future__ import annotations

import time

from app.db.redis import get_redis

_KEY_PREFIX = "login:fail:"
MAX_ATTEMPTS = 5        # 最大失败次数
LOCK_SECONDS = 900      # 锁定 15 分钟（计数窗口与锁定共用同一 TTL）

# 内存降级存储：key -> (count, expire_ts)
_store: dict[str, tuple[int, float]] = {}


def _key(username: str, ip: str) -> str:
    return f"{_KEY_PREFIX}{username.strip().lower()}:{ip}"


def _cleanup() -> None:
    now = time.time()
    expired = [k for k, v in _store.items() if v[1] < now]
    for k in expired:
        del _store[k]


def is_locked(username: str, ip: str) -> tuple[bool, int]:
    """返回 (是否锁定, 剩余秒数)。"""
    key = _key(username, ip)
    r = get_redis()
    if r is not None:
        count = r.get(key)
        if count is not None and int(count) >= MAX_ATTEMPTS:
            ttl = r.ttl(key)
            return True, max(ttl, 0)
        return False, 0

    _cleanup()
    entry = _store.get(key)
    if entry and entry[0] >= MAX_ATTEMPTS:
        return True, max(int(entry[1] - time.time()), 0)
    return False, 0


def record_failure(username: str, ip: str) -> int:
    """记录一次失败，返回累计次数。每次失败刷新 TTL。"""
    key = _key(username, ip)
    r = get_redis()
    if r is not None:
        pipe = r.pipeline()
        pipe.incr(key)
        pipe.expire(key, LOCK_SECONDS)
        count, _ = pipe.execute()
        return int(count)

    _cleanup()
    entry = _store.get(key)
    count = (entry[0] if entry else 0) + 1
    _store[key] = (count, time.time() + LOCK_SECONDS)
    return count


def clear(username: str, ip: str) -> None:
    """登录成功后清除失败计数。"""
    key = _key(username, ip)
    r = get_redis()
    if r is not None:
        r.delete(key)
    else:
        _store.pop(key, None)
