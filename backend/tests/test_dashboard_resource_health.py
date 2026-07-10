import asyncio
from types import SimpleNamespace

import pytest

from app.services.dashboard import build_host_resource_health
from app.services import prometheus


def test_resource_health_uses_capacity_weighted_cpu_and_memory():
    hosts = [
        {
            "prometheus_ok": True,
            "cpu": 80,
            "cpu_cores": 8,
            "memory": 80,
            "memory_total_bytes": 16 * 1024**3,
            "memory_available_bytes": 3.2 * 1024**3,
            "disk": 60,
            "disk_total_bytes": 100 * 1024**3,
            "disk_available_bytes": 40 * 1024**3,
        },
        {
            "prometheus_ok": True,
            "cpu": 20,
            "cpu_cores": 32,
            "memory": 20,
            "memory_total_bytes": 128 * 1024**3,
            "memory_available_bytes": 102.4 * 1024**3,
            "disk": 20,
            "disk_total_bytes": 900 * 1024**3,
            "disk_available_bytes": 720 * 1024**3,
        },
    ]

    pool = build_host_resource_health(hosts)["host_pool"]

    assert pool["cpu_usage"] == pytest.approx(32.0)
    assert pool["cpu_cores"] == 40
    assert pool["memory_usage"] == pytest.approx(26.7)
    assert pool["memory_total_gb"] == pytest.approx(144.0)
    assert pool["disk_usage"] == pytest.approx(24.0)
    assert pool["disk_total_gb"] == pytest.approx(1000.0)


def test_resource_health_reports_p95_hot_hosts_and_monitoring_coverage():
    cpu_values = [10, 20, 30, 40, 50, 60, 70, 80, 90, 99]
    hosts = [
        {
            "prometheus_ok": True,
            "cpu": value,
            "cpu_cores": 4,
            "memory": value,
            "memory_total_bytes": 8 * 1024**3,
            "memory_available_bytes": 8 * 1024**3 * (1 - value / 100),
            "disk": value,
            "disk_total_bytes": 100 * 1024**3,
            "disk_available_bytes": 100 * 1024**3 * (1 - value / 100),
        }
        for value in cpu_values
    ]
    hosts.append({"prometheus_ok": False, "cpu": 0, "memory": 0, "disk": 0})

    pool = build_host_resource_health(hosts)["host_pool"]

    assert pool["total"] == 11
    assert pool["monitored"] == 10
    assert pool["unmonitored"] == 1
    assert pool["coverage"] == pytest.approx(90.9)
    assert pool["cpu_p95"] == pytest.approx(99.0)
    assert pool["cpu_hot_hosts"] == 3
    assert pool["memory_hot_hosts"] == 2
    assert pool["disk_hot_hosts"] == 2


def test_resource_health_handles_empty_weighted_denominators_safely():
    pool = build_host_resource_health(
        [
            {"prometheus_ok": True, "cpu": 65, "memory": 70, "disk": 75},
            {"prometheus_ok": False},
        ]
    )["host_pool"]

    assert pool["total"] == 2
    assert pool["monitored"] == 1
    assert pool["cpu_usage"] is None
    assert pool["memory_usage"] is None
    assert pool["disk_usage"] is None
    assert pool["cpu_cores"] == 0
    assert pool["memory_total_gb"] == 0


def test_hosts_summary_exposes_capacity_dimensions(monkeypatch):
    asset = SimpleNamespace(
        id=7,
        name="ops-node-07",
        ip_address="10.0.0.7",
        owner="sre",
        status="使用中",
    )

    async def fake_discover_instances(_prom_url=""):
        return {"10.0.0.7": "10.0.0.7:9100"}

    async def fake_query_batch(exprs, _prom_url=""):
        assert any(key.endswith("_cpu_cores") for key in exprs)
        assert any(key.endswith("_mem_total") for key in exprs)
        assert any(key.endswith("_mem_available") for key in exprs)
        assert any(key.endswith("_disk_total") for key in exprs)
        assert any(key.endswith("_disk_available") for key in exprs)

        values = {
            "cpu": 42.5,
            "cpu_cores": 16,
            "mem": 68,
            "mem_total": 64 * 1024**3,
            "mem_available": 20.48 * 1024**3,
            "disk": 51,
            "disk_total": 500 * 1024**3,
            "disk_available": 245 * 1024**3,
            "netin": 0,
            "netout": 0,
            "load": 1.2,
        }
        result = {}
        for key in exprs:
            suffix = key.removeprefix("a0_")
            result[key] = {
                "resultType": "vector",
                "result": [{"value": [0, str(values[suffix])]}],
            }
        return result

    monkeypatch.setattr(prometheus, "discover_instances", fake_discover_instances)
    monkeypatch.setattr(prometheus, "_query_batch", fake_query_batch)

    result = asyncio.run(prometheus.get_hosts_summary([asset]))

    assert result[0]["cpu_cores"] == 16
    assert result[0]["memory_total_bytes"] == pytest.approx(64 * 1024**3)
    assert result[0]["memory_available_bytes"] == pytest.approx(20.48 * 1024**3)
    assert result[0]["disk_total_bytes"] == pytest.approx(500 * 1024**3)
    assert result[0]["disk_available_bytes"] == pytest.approx(245 * 1024**3)
