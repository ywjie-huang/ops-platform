"""
Prometheus 查询服务
封装对 Prometheus HTTP API 的调用，提供主机监控数据。
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx

from app.core.config import PROMETHEUS_URL
from app.core.settings import get_prometheus_url

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(connect=5, read=10, write=5, pool=5)

# instance 标签缓存
_instance_cache: dict[str, str] = {}
_instance_cache_ts: float = 0
_INSTANCE_CACHE_TTL = 60  # 60 秒刷新一次


async def _query_batch(exprs: dict[str, str], prom_url: str = "") -> dict[str, dict]:
    """批量并发查询，共享一个 HTTP 客户端。"""
    base_url = prom_url or PROMETHEUS_URL
    url = f"{base_url}/api/v1/query"
    results: dict[str, dict] = {}

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        async def _do(name: str, expr: str):
            try:
                resp = await client.get(url, params={"query": expr})
                resp.raise_for_status()
                data = resp.json()
                if data.get("status") == "success":
                    results[name] = data.get("data", {})
                else:
                    results[name] = {"resultType": "vector", "result": []}
            except httpx.TimeoutException:
                logger.warning("Prometheus query timeout: %s", name)
                results[name] = {"resultType": "vector", "result": []}
            except Exception as e:
                logger.warning("Prometheus query error [%s]: %s", name, e)
                results[name] = {"resultType": "vector", "result": []}

        await asyncio.gather(*[_do(n, e) for n, e in exprs.items()])

    return results


def _extract_scalar(result: dict) -> float:
    try:
        if result.get("resultType") == "vector" and result.get("result"):
            return float(result["result"][0]["value"][1])
    except (IndexError, KeyError, ValueError, TypeError):
        pass
    return 0.0


async def _discover_instances(prom_url: str = "") -> dict[str, str]:
    """从 Prometheus targets 发现 instance 标签，带缓存。"""
    global _instance_cache, _instance_cache_ts
    now = time.time()
    if _instance_cache and (now - _instance_cache_ts) < _INSTANCE_CACHE_TTL:
        return _instance_cache

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            base_url = prom_url or PROMETHEUS_URL
            resp = await client.get(f"{base_url}/api/v1/targets")
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") != "success":
                return _instance_cache

            mapping: dict[str, str] = {}
            for target in data.get("data", {}).get("activeTargets", []):
                labels = target.get("labels", {})
                instance = labels.get("instance", "")
                discovered = target.get("discoveredLabels", {})
                address = discovered.get("__address__", instance)
                if not instance:
                    continue
                clean_addr = address.split(":")[0] if ":" in address else address
                clean_instance = instance.split(":")[0] if ":" in instance else instance
                mapping[clean_addr] = instance
                mapping[clean_instance] = instance
                mapping[instance] = instance

            _instance_cache = mapping
            _instance_cache_ts = now
            logger.info("Discovered %d Prometheus instances", len(mapping))
            return mapping
    except Exception as e:
        logger.error("Failed to discover instances: %s", e)
        return _instance_cache


def _find_instance(ip: str, name: str, instances: dict[str, str]) -> str | None:
    if ip in instances:
        return instances[ip]
    if name and name in instances:
        return instances[name]
    for key, inst in instances.items():
        if ip in key or (name and name in key):
            return inst
    return None


async def get_hosts_summary(assets: list, db=None) -> list[dict[str, Any]]:
    """批量查询所有主机摘要，一次并发完成。"""
    prom_url = get_prometheus_url(db) if db else ""
    instances = await _discover_instances(prom_url)

    # 构建所有查询
    all_exprs: dict[str, str] = {}  # key: "asset_0_cpu" -> expr
    asset_map: list[tuple[Any, str | None]] = []  # (asset, instance)

    for i, asset in enumerate(assets):
        if asset.status in ("已关机", "已删除"):
            asset_map.append((asset, None))
            continue
        inst = _find_instance(asset.ip_address, asset.name, instances)
        asset_map.append((asset, inst))
        if not inst:
            continue
        s = f'instance="{inst}"'
        prefix = f"a{i}"
        all_exprs[f"{prefix}_cpu"] = f'100 - (avg by(instance)(rate(node_cpu_seconds_total{{mode="idle",{s}}}[5m])) * 100)'
        all_exprs[f"{prefix}_mem"] = f'(1 - node_memory_MemAvailable_bytes{{{s}}} / node_memory_MemTotal_bytes{{{s}}}) * 100'
        all_exprs[f"{prefix}_disk"] = f'(1 - node_filesystem_avail_bytes{{mountpoint="/",{s}}} / node_filesystem_size_bytes{{mountpoint="/",{s}}}) * 100'
        all_exprs[f"{prefix}_netin"] = f'rate(node_network_receive_bytes_total{{{s}}}[5m]) * 8'
        all_exprs[f"{prefix}_netout"] = f'rate(node_network_transmit_bytes_total{{{s}}}[5m]) * 8'
        all_exprs[f"{prefix}_load"] = f'node_load1{{{s}}}'

    # 一次并发查完所有
    query_results = await _query_batch(all_exprs, prom_url) if all_exprs else {}

    # 组装结果
    results = []
    for i, (asset, inst) in enumerate(asset_map):
        if not inst:
            results.append({
                "id": asset.id, "name": asset.name, "ip_address": asset.ip_address,
                "owner": asset.owner or "", "status": asset.status,
                "cpu": 0, "memory": 0, "disk": 0,
                "network_in": 0, "network_out": 0, "load": 0,
                "prometheus_ok": False,
            })
            continue

        prefix = f"a{i}"
        def val(key: str) -> float:
            return _extract_scalar(query_results.get(f"{prefix}_{key}", {}))

        results.append({
            "id": asset.id, "name": asset.name, "ip_address": asset.ip_address,
            "owner": asset.owner or "", "status": asset.status,
            "cpu": round(val("cpu"), 1),
            "memory": round(val("mem"), 1),
            "disk": round(val("disk"), 1),
            "network_in": round(val("netin") / (1024 ** 2), 1),
            "network_out": round(val("netout") / (1024 ** 2), 1),
            "load": round(val("load"), 2),
            "prometheus_ok": True,
        })

    return results


async def get_host_metrics(ip: str, name: str = "", db=None) -> dict[str, Any]:
    """查询单台主机的全部监控指标。"""
    prom_url = get_prometheus_url(db) if db else ""
    instances = await _discover_instances(prom_url)
    inst = _find_instance(ip, name, instances)
    if not inst:
        return _empty_metrics()

    s = f'instance="{inst}"'
    exprs = {
        "cpu_usage": f'100 - (avg by(instance)(rate(node_cpu_seconds_total{{mode="idle",{s}}}[5m])) * 100)',
        "memory_usage": f'(1 - node_memory_MemAvailable_bytes{{{s}}} / node_memory_MemTotal_bytes{{{s}}}) * 100',
        "memory_total": f'node_memory_MemTotal_bytes{{{s}}}',
        "memory_available": f'node_memory_MemAvailable_bytes{{{s}}}',
        "disk_usage": f'(1 - node_filesystem_avail_bytes{{mountpoint="/",{s}}} / node_filesystem_size_bytes{{mountpoint="/",{s}}}) * 100',
        "disk_total": f'node_filesystem_size_bytes{{mountpoint="/",{s}}}',
        "disk_read": f'rate(node_disk_read_bytes_total{{{s}}}[5m])',
        "disk_write": f'rate(node_disk_written_bytes_total{{{s}}}[5m])',
        "net_in": f'rate(node_network_receive_bytes_total{{{s}}}[5m]) * 8',
        "net_out": f'rate(node_network_transmit_bytes_total{{{s}}}[5m]) * 8',
        "load_1m": f'node_load1{{{s}}}',
        "load_5m": f'node_load5{{{s}}}',
        "load_15m": f'node_load15{{{s}}}',
        "tcp_connections": f'node_netstat_Tcp_CurrEstab{{{s}}}',
        "processes": f'node_procs_running{{{s}}}',
        "uptime": f'node_time_seconds{{{s}}} - node_boot_time_seconds{{{s}}}',
        "cpu_cores": f'count(node_cpu_seconds_total{{mode="idle",{s}}}) without(cpu,mode)',
    }

    results = await _query_batch(exprs, prom_url)

    def val(key: str) -> float:
        return _extract_scalar(results.get(key, {}))

    def bytes_to_gb(b: float) -> float:
        return round(b / (1024 ** 3), 1)

    def bits_to_mbps(b: float) -> float:
        return round(b / (1024 ** 2), 1)

    def seconds_to_hours(s_val: float) -> int:
        return int(s_val / 3600)

    return {
        "cpu": {"usage": round(val("cpu_usage"), 1), "cores": int(val("cpu_cores"))},
        "memory": {
            "usage": round(val("memory_usage"), 1),
            "total_gb": bytes_to_gb(val("memory_total")),
            "used_gb": bytes_to_gb(val("memory_total") - val("memory_available")),
            "available_gb": bytes_to_gb(val("memory_available")),
        },
        "disk": {
            "usage": round(val("disk_usage"), 1),
            "total_gb": bytes_to_gb(val("disk_total")),
            "read_mb_s": round(val("disk_read") / (1024 ** 2), 1),
            "write_mb_s": round(val("disk_write") / (1024 ** 2), 1),
        },
        "network": {"in_mbps": bits_to_mbps(val("net_in")), "out_mbps": bits_to_mbps(val("net_out"))},
        "load": {"1m": round(val("load_1m"), 2), "5m": round(val("load_5m"), 2), "15m": round(val("load_15m"), 2)},
        "tcp_connections": int(val("tcp_connections")),
        "processes": {"running": int(val("processes"))},
        "uptime_hours": seconds_to_hours(val("uptime")),
    }


async def check_prometheus_health(db=None) -> bool:
    prom_url = get_prometheus_url(db) if db else PROMETHEUS_URL
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(f"{prom_url}/api/v1/status/config")
            return resp.status_code == 200
    except Exception:
        return False


async def get_targets(db=None) -> list[dict[str, Any]]:
    prom_url = get_prometheus_url(db) if db else PROMETHEUS_URL
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(f"{prom_url}/api/v1/targets")
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") == "success":
                return [
                    {
                        "instance": t.get("labels", {}).get("instance", ""),
                        "job": t.get("labels", {}).get("job", ""),
                        "health": t.get("health", ""),
                        "last_scrape": t.get("lastScrape", ""),
                        "scrape_error": t.get("lastError", ""),
                    }
                    for t in data["data"].get("activeTargets", [])
                ]
    except Exception as e:
        logger.error("Failed to get targets: %s", e)
    return []


def _empty_metrics() -> dict[str, Any]:
    return {
        "cpu": {"usage": 0, "cores": 0},
        "memory": {"usage": 0, "total_gb": 0, "used_gb": 0, "available_gb": 0},
        "disk": {"usage": 0, "total_gb": 0, "read_mb_s": 0, "write_mb_s": 0},
        "network": {"in_mbps": 0, "out_mbps": 0},
        "load": {"1m": 0, "5m": 0, "15m": 0},
        "tcp_connections": 0,
        "processes": {"running": 0},
        "uptime_hours": 0,
    }
