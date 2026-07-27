"""Redis 连接池 — 懒加载单例，不可用时返回 None 供调用方降级。"""

from __future__ import annotations

import logging
import os
import threading
import time
from typing import Optional

import redis

from app.core.config import REDIS_DB, REDIS_HOST, REDIS_PASSWORD, REDIS_PORT

logger = logging.getLogger(__name__)

_pool: Optional[redis.ConnectionPool] = None
_client: Optional[redis.Redis] = None
_state_lock = threading.Lock()

# Redis is optional for local development. Avoid making every authenticated
# request wait for a connection timeout while the service is stopped.
_CONNECT_TIMEOUT = float(os.environ.get("REDIS_CONNECT_TIMEOUT", "0.5"))
_SOCKET_TIMEOUT = float(os.environ.get("REDIS_SOCKET_TIMEOUT", "0.5"))
_RETRY_INTERVAL = float(os.environ.get("REDIS_RETRY_INTERVAL", "30"))
_retry_after = 0.0


def get_redis() -> Optional[redis.Redis]:
    """返回共享 Redis 客户端；连接失败时返回 None（调用方应降级为内存实现）。"""
    global _pool, _client, _retry_after
    if _client is not None:
        return _client

    # A stopped Redis is a normal local-development configuration. Once a
    # connection attempt fails, keep using the in-memory fallback until the
    # retry window expires instead of paying the socket timeout per request.
    if time.monotonic() < _retry_after:
        return None

    with _state_lock:
        if _client is not None:
            return _client
        if time.monotonic() < _retry_after:
            return None

        try:
            _pool = redis.ConnectionPool(
                host=REDIS_HOST,
                port=REDIS_PORT,
                password=REDIS_PASSWORD or None,
                db=REDIS_DB,
                decode_responses=True,
                socket_connect_timeout=_CONNECT_TIMEOUT,
                socket_timeout=_SOCKET_TIMEOUT,
                max_connections=20,
            )
            client = redis.Redis(connection_pool=_pool)
            client.ping()
            _client = client
            _retry_after = 0.0
            logger.info("Redis connected: %s:%s/db%s", REDIS_HOST, REDIS_PORT, REDIS_DB)
            return _client
        except Exception as exc:  # noqa: BLE001 — 任何连接异常都降级
            _pool = None
            _client = None
            _retry_after = time.monotonic() + max(_RETRY_INTERVAL, 0.0)
            logger.warning(
                "Redis unavailable (%s), falling back to in-memory store; retrying in %.0fs",
                exc,
                max(_RETRY_INTERVAL, 0.0),
            )
            return None


def reset_redis() -> None:
    """重置连接（测试或配置变更后使用）。"""
    global _pool, _client, _retry_after
    with _state_lock:
        if _client is not None:
            try:
                _client.close()
            except Exception:  # noqa: BLE001
                pass
        _pool = None
        _client = None
        _retry_after = 0.0
