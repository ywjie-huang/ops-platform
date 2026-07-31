#!/usr/bin/env python3
"""
Docker 容器监控 Agent
====================
暴露 HTTP API 供运维平台主动拉取容器和系统指标。

部署流程：
    1. 在仓库 agent 目录构建镜像并推送到自己的镜像仓库。
    2. 在目标 Docker 主机拉取镜像，并将 9001 端口绑定到管理网 IP。
    3. 在平台填写“管理网 IP:9001”完成主机注册。

完整命令和网络安全注意事项见 agent/README.md。

环境变量：
    AGENT_PORT  - 监听端口，默认 9001
"""

from __future__ import annotations

import json
import logging
import os
import platform
import re
import time
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Lock
from typing import Any
from urllib.parse import parse_qs, urlparse

import docker
import psutil

# ─── 配置 ──────────────────────────────────────────────────

AGENT_PORT = int(os.environ.get("AGENT_PORT", "9001"))
DEFAULT_LOG_TAIL = 300
MAX_LOG_TAIL = 1000
MAX_LOG_TAIL_WITH_SINCE = 5000  # 时间段模式：时间窗做主过滤后，行数上限放宽

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("ops-agent")

# ─── 全局状态（后台线程更新，HTTP 线程读取）────────────────

_data_lock = Lock()
_cached_data: dict[str, Any] = {}
_docker_client: docker.DockerClient | None = None


# ─── 系统指标采集 ──────────────────────────────────────────

def _get_host_ip() -> str:
    try:
        for iface_addrs in psutil.net_if_addrs().values():
            for addr in iface_addrs:
                if addr.family.name == "AF_INET" and not addr.address.startswith("127."):
                    return addr.address
    except Exception:
        pass
    return ""


def collect_host_info() -> dict[str, Any]:
    cpu_percent = psutil.cpu_percent(interval=0.5)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    docker_version = ""
    try:
        if _docker_client:
            info = _docker_client.version()
            docker_version = info.get("Version", "")
    except Exception:
        pass

    return {
        "os": f"{platform.system()} {platform.release()} {platform.machine()}",
        "ip": _get_host_ip(),
        "docker_version": docker_version,
        "cpu_count": psutil.cpu_count(),
        "memory_total": memory.total,
        "cpu_percent": cpu_percent,
        "memory_percent": memory.percent,
        "disk_usage": {
            "total": disk.total,
            "used": disk.used,
            "percent": disk.percent,
        },
    }


# ─── 容器指标采集 ──────────────────────────────────────────

def collect_containers() -> list[dict[str, Any]]:
    if not _docker_client:
        return []

    containers = []
    try:
        all_containers = _docker_client.containers.list(all=True)
    except Exception as e:
        log.error("列出容器失败: %s", e)
        return containers

    for c in all_containers:
        try:
            info = _collect_one_container(c)
            containers.append(info)
        except Exception as e:
            log.warning("采集容器 %s 失败: %s", c.name, e)

    return containers


def _collect_one_container(c) -> dict[str, Any]:
    c.reload()
    attrs = c.attrs or {}

    info: dict[str, Any] = {
        "id": c.id,
        "name": c.name,
        "image": _get_image_name(attrs),
        "status": c.status,
        "state": (attrs.get("State") or {}).get("Status", c.status),
        "ports": attrs.get("NetworkSettings", {}).get("Ports", {}),
        "restart_count": (attrs.get("RestartCount") or 0),
        "started_at": (attrs.get("State") or {}).get("StartedAt", ""),
        "cpu_percent": 0.0,
        "memory_usage": 0,
        "memory_limit": 0,
        "memory_percent": 0.0,
        "net_rx_bytes": 0,
        "net_tx_bytes": 0,
        "block_read": 0,
        "block_write": 0,
    }

    if c.status == "running":
        try:
            stats = c.stats(stream=False)
            _fill_stats(info, stats)
        except Exception:
            pass

    return info


def _get_image_name(attrs: dict) -> str:
    config = attrs.get("Config", {})
    image = config.get("Image", "")
    if not image:
        repo_tags = (attrs.get("Image") or {})
        if isinstance(repo_tags, dict):
            image = ", ".join(repo_tags.get("RepoTags") or [])
    return image


def _fill_stats(info: dict, stats: dict) -> None:
    cpu_delta = (stats.get("cpu_stats", {}).get("cpu_usage", {}).get("total_usage", 0) -
                 stats.get("precpu_stats", {}).get("cpu_usage", {}).get("total_usage", 0))
    system_delta = (stats.get("cpu_stats", {}).get("system_cpu_usage", 0) -
                    stats.get("precpu_stats", {}).get("system_cpu_usage", 0))
    cpu_count = len(stats.get("cpu_stats", {}).get("cpu_usage", {}).get("percpu_usage", []) or [1])

    if system_delta > 0:
        info["cpu_percent"] = round((cpu_delta / system_delta) * cpu_count * 100.0, 2)

    mem_stats = stats.get("memory_stats", {})
    info["memory_usage"] = mem_stats.get("usage", 0)
    info["memory_limit"] = mem_stats.get("limit", 0)
    if info["memory_limit"] > 0:
        info["memory_percent"] = round((info["memory_usage"] / info["memory_limit"]) * 100.0, 2)

    for net_data in (stats.get("networks") or {}).values():
        info["net_rx_bytes"] += net_data.get("rx_bytes", 0)
        info["net_tx_bytes"] += net_data.get("tx_bytes", 0)

    blkio = stats.get("blkio_stats", {}).get("io_service_bytes_recursive") or []
    for entry in blkio:
        op = entry.get("op", "").lower()
        if op == "read":
            info["block_read"] += entry.get("value", 0)
        elif op == "write":
            info["block_write"] += entry.get("value", 0)


def normalize_tail_lines(value: Any, default: int = DEFAULT_LOG_TAIL) -> int:
    try:
        tail_lines = int(value)
    except (TypeError, ValueError):
        tail_lines = default
    return max(1, min(tail_lines, MAX_LOG_TAIL))


def _parse_log_time(value: Any) -> datetime | None:
    """把 since/until 解析为 tz-aware UTC datetime；失败返回 None。

    接受：unix 秒(int/str)（主路径，后端/前端都传秒），或 ISO8601 字符串(带/不带 Z)。
    """
    if value is None:
        return None
    # 1) unix 秒
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        pass
    # 2) ISO8601 字符串
    if isinstance(value, str):
        text = value.strip()
        if text:
            try:
                dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                return None
    return None


def read_container_logs(
    container_id: str,
    tail_lines: Any = DEFAULT_LOG_TAIL,
    since: Any = None,
    until: Any = None,
) -> str:
    if not _docker_client:
        raise RuntimeError("docker client not available")

    since_dt = _parse_log_time(since)
    until_dt = _parse_log_time(until)

    if since_dt is None:
        # 纯按行数模式：tail 钳到 [1, MAX_LOG_TAIL]
        tail = normalize_tail_lines(tail_lines)
    else:
        # 时间段模式：时间窗做主过滤，tail 放宽上限到 MAX_LOG_TAIL_WITH_SINCE
        try:
            tail = max(1, min(int(tail_lines or MAX_LOG_TAIL_WITH_SINCE), MAX_LOG_TAIL_WITH_SINCE))
        except (TypeError, ValueError):
            tail = MAX_LOG_TAIL_WITH_SINCE

    kwargs: dict[str, Any] = {
        "stdout": True,
        "stderr": True,
        "timestamps": True,
        "tail": tail,
    }
    if since_dt is not None:
        kwargs["since"] = since_dt
    if until_dt is not None:
        kwargs["until"] = until_dt

    container = _docker_client.containers.get(container_id)
    raw = container.logs(**kwargs)
    if isinstance(raw, bytes):
        return raw.decode("utf-8", errors="replace")
    return str(raw or "")


# ─── 后台采集线程 ──────────────────────────────────────────

def _background_collector():
    """后台线程，每 5 秒采集一次数据到缓存。"""
    global _cached_data
    while True:
        try:
            host_info = collect_host_info()
            containers = collect_containers()
            with _data_lock:
                _cached_data = {
                    "host_info": host_info,
                    "containers": containers,
                    "collected_at": time.time(),
                }
        except Exception as e:
            log.error("后台采集失败: %s", e)
        time.sleep(5)


# ─── HTTP 服务 ─────────────────────────────────────────────

class AgentHandler(BaseHTTPRequestHandler):
    """Agent HTTP API。"""

    def log_message(self, format, *args):
        # 用自定义 logger 替代默认 stderr 输出
        log.debug(format, *args)

    def _json_response(self, data: dict, status: int = 200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/ping":
            self._json_response({"status": "ok"})

        elif path == "/info":
            with _data_lock:
                data = _cached_data.get("host_info", {})
            self._json_response(data)

        elif path == "/containers":
            with _data_lock:
                data = _cached_data.get("containers", [])
            self._json_response(data)

        elif path == "/snapshot":
            # 一次性返回所有数据（平台用这个接口拉取）
            with _data_lock:
                data = dict(_cached_data)
            self._json_response(data)

        elif m := re.match(r'^/containers/([a-f0-9]{12,64})/logs$', path):
            query = parse_qs(parsed.query)
            tail_raw = (query.get("tail") or [None])[0]
            since_raw = (query.get("since") or [None])[0]
            until_raw = (query.get("until") or [None])[0]
            try:
                logs = read_container_logs(
                    m.group(1), tail_lines=tail_raw, since=since_raw, until=until_raw
                )
                self._json_response({
                    "status": "ok",
                    "logs": logs,
                    "tail": tail_raw,
                    "since": since_raw,
                    "until": until_raw,
                })
            except docker.errors.NotFound:
                self._json_response({"error": f"容器 {m.group(1)} 不存在"}, 404)
            except Exception as e:
                self._json_response({"error": str(e)}, 500)

        else:
            self._json_response({"error": "not found"}, 404)

    def do_POST(self):
        """处理容器操作请求。"""
        # POST /containers/<id>/<action>  (action: start|stop|restart|delete)
        m = re.match(r'^/containers/([a-f0-9]{12,64})/(start|stop|restart|delete)$', self.path)
        if not m:
            self._json_response({"error": "not found"}, 404)
            return

        container_id = m.group(1)
        action = m.group(2)

        if not _docker_client:
            self._json_response({"error": "docker client not available"}, 503)
            return

        try:
            container = _docker_client.containers.get(container_id)
        except docker.errors.NotFound:
            self._json_response({"error": f"容器 {container_id} 不存在"}, 404)
            return
        except Exception as e:
            self._json_response({"error": str(e)}, 500)
            return

        try:
            if action == "start":
                container.start()
                msg = "容器已启动"
            elif action == "stop":
                container.stop(timeout=10)
                msg = "容器已停止"
            elif action == "restart":
                container.restart(timeout=10)
                msg = "容器已重启"
            elif action == "delete":
                container.remove(force=True)
                msg = "容器已删除"
            else:
                self._json_response({"error": "unknown action"}, 400)
                return

            self._json_response({"status": "ok", "message": msg})
        except Exception as e:
            self._json_response({"error": str(e)}, 500)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()


# ─── 启动 ──────────────────────────────────────────────────

def main():
    global _docker_client

    log.info("=" * 50)
    log.info("Docker 容器监控 Agent 启动")
    log.info("监听端口: %d", AGENT_PORT)
    log.info("=" * 50)

    # 连接 Docker
    try:
        _docker_client = docker.from_env()
        _docker_client.ping()
        log.info("Docker 连接成功")
    except Exception as e:
        log.error("无法连接 Docker: %s", e)
        log.error("请确保已挂载 /var/run/docker.sock")
        import sys
        sys.exit(1)

    # 启动后台采集线程
    import threading
    collector_thread = threading.Thread(target=_background_collector, daemon=True)
    collector_thread.start()
    log.info("后台采集线程已启动（每 5 秒）")

    # 启动 HTTP 服务
    server = HTTPServer(("0.0.0.0", AGENT_PORT), AgentHandler)
    log.info("HTTP 服务已启动，等待连接…")
    log.info("在平台注册主机时填入: <本机IP>:%d", AGENT_PORT)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("Agent 已停止")
        server.server_close()


if __name__ == "__main__":
    main()
