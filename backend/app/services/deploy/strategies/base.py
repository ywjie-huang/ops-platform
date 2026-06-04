"""Deploy strategy base — shared utilities for all strategies."""
from __future__ import annotations

import logging
import time
import urllib.request
from datetime import datetime

import paramiko

from app.core.config import CHINA_TZ
from app.models.deploy import DeployRecord

logger = logging.getLogger(__name__)


def ssh_exec(
    ssh: paramiko.SSHClient,
    command: str,
    timeout: int = 60,
) -> tuple[int, str, str]:
    """执行 SSH 命令，返回 (exit_code, stdout, stderr)。"""
    stdin, stdout, stderr = ssh.exec_command(command, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    exit_code = stdout.channel.recv_exit_status()
    return exit_code, out, err


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
        time.sleep(interval)
    return False
