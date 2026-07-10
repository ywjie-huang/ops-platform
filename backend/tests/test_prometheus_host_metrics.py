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
