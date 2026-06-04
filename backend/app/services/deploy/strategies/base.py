"""Deploy strategy base — shared utilities for all strategies."""
from __future__ import annotations

import logging
import urllib.request
from datetime import datetime

from app.core.config import CHINA_TZ
from app.models.deploy import DeployRecord

logger = logging.getLogger(__name__)


def check_health(url: str, timeout: int = 30) -> bool:
    """健康检查：GET URL，返回 2xx 视为成功。"""
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return 200 <= resp.status < 300
    except Exception as e:
        logger.debug("Health check failed: %s", e)
        return False


def poll_health(url: str, timeout: int = 30, interval: int = 3) -> bool:
    """轮询健康检查，直到成功或超时。"""
    deadline = datetime.now(CHINA_TZ).timestamp() + timeout
    while datetime.now(CHINA_TZ).timestamp() < deadline:
        if check_health(url):
            return True
        import time
        time.sleep(interval)
    return False
