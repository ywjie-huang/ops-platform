import asyncio

from app.services import prometheus


def test_host_metrics_marks_prometheus_unavailable_when_target_is_missing(monkeypatch):
    async def fake_discover_instances(_prom_url=""):
        return {}

    monkeypatch.setattr(prometheus, "discover_instances", fake_discover_instances)

    result = asyncio.run(prometheus.get_host_metrics("10.0.0.8", "ops-node-08"))

    assert result["prometheus_ok"] is False


def test_host_metrics_marks_prometheus_available_when_target_is_found(monkeypatch):
    async def fake_discover_instances(_prom_url=""):
        return {"10.0.0.8": "10.0.0.8:9100"}

    async def fake_query_batch(_exprs, _prom_url=""):
        return {}

    monkeypatch.setattr(prometheus, "discover_instances", fake_discover_instances)
    monkeypatch.setattr(prometheus, "_query_batch", fake_query_batch)

    result = asyncio.run(prometheus.get_host_metrics("10.0.0.8", "ops-node-08"))

    assert result["prometheus_ok"] is True


def test_host_metrics_rejects_name_match_when_scrape_ip_differs(monkeypatch):
    """服务器换 IP 后：资产名命中 instance，但刮削 IP 与资产 IP 不一致 → 视为离线。"""
    async def fake_discover_instances(_prom_url=""):
        return {
            "172.16.24.100": {
                "instance": "lczy-ops",
                "address_ip": "172.16.24.100",
                "health": "up",
                "last_scrape": "",
            },
            "lczy-ops": {
                "instance": "lczy-ops",
                "address_ip": "172.16.24.100",
                "health": "up",
                "last_scrape": "",
            },
        }

    monkeypatch.setattr(prometheus, "discover_instances", fake_discover_instances)

    result = asyncio.run(prometheus.get_host_metrics("172.16.100.1", "lczy-ops"))

    assert result["prometheus_ok"] is False


def test_host_metrics_marks_unavailable_when_target_is_down(monkeypatch):
    """instance 匹配成功但 target health=down → 视为离线。"""
    async def fake_discover_instances(_prom_url=""):
        return {
            "10.0.0.9": {
                "instance": "10.0.0.9:9100",
                "address_ip": "10.0.0.9",
                "health": "down",
                "last_scrape": "",
            },
        }

    monkeypatch.setattr(prometheus, "discover_instances", fake_discover_instances)

    result = asyncio.run(prometheus.get_host_metrics("10.0.0.9", "ops-node-09"))

    assert result["prometheus_ok"] is False
