"""Redis 连接池 — 懒加载单例，不可用时返回 None 供调用方降级。"""

from __future__ import annotations

import logging
from typing import Optional

import redis

from app.core.config import REDIS_DB, REDIS_HOST, REDIS_PASSWORD, REDIS_PORT

logger = logging.getLogger(__name__)

_pool: Optional[redis.ConnectionPool] = None
_client: Optional[redis.Redis] = None


def get_redis() -> Optional[redis.Redis]:
    """返回共享 Redis 客户端；连接失败时返回 None（调用方应降级为内存实现）。"""
    global _pool, _client
    if _client is not None:
        return _client
    try:
        _pool = redis.ConnectionPool(
            host=REDIS_HOST,
            port=REDIS_PORT,
            password=REDIS_PASSWORD or None,
            db=REDIS_DB,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
            max_connections=20,
        )
        client = redis.Redis(connection_pool=_pool)
        client.ping()
        _client = client
        logger.info("Redis connected: %s:%s/db%s", REDIS_HOST, REDIS_PORT, REDIS_DB)
        return _client
    except Exception as exc:  # noqa: BLE001 — 任何连接异常都降级
        logger.warning("Redis unavailable (%s), falling back to in-memory store", exc)
        _pool = None
        _client = None
        return None


def reset_redis() -> None:
    """重置连接（测试或配置变更后使用）。"""
    global _pool, _client
    if _client is not None:
        try:
            _client.close()
        except Exception:  # noqa: BLE001
            pass
    _pool = None
    _client = None
