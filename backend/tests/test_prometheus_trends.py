import asyncio


def test_get_host_trends_returns_normalized_series(monkeypatch):
    from app.services import prometheus

    async def fake_discover_instances(_url=""):
        return {"10.0.0.1": "10.0.0.1:9100"}

    monkeypatch.setattr(prometheus, "discover_instances", fake_discover_instances)

    async def fake_query_range_batch(exprs, prom_url, start, end, step):
        assert {"cpu", "memory", "load", "network_in"}.issubset(exprs.keys())
        return {
            "cpu": {"resultType": "matrix", "result": [{"values": [[1000, "12.34"], [1060, "24.56"]]}]},
            "memory": {"resultType": "matrix", "result": [{"values": [[1000, "55.1"]]}]},
            "load": {"resultType": "matrix", "result": [{"values": [[1000, "0.42"]]}]},
            "network_in": {"resultType": "matrix", "result": [{"values": [[1000, "2.5"]]}]},
        }

    monkeypatch.setattr(prometheus, "_query_range_batch", fake_query_range_batch)

    trends = asyncio.run(prometheus.get_host_trends("10.0.0.1", "web-01", minutes=60, step_seconds=60))

    assert trends["range_minutes"] == 60
    assert trends["step_seconds"] == 60
    assert [series["key"] for series in trends["series"]] == ["cpu", "memory", "load", "network_in"]
    assert trends["series"][0]["points"] == [
        {"timestamp": 1000, "value": 12.3},
        {"timestamp": 1060, "value": 24.6},
    ]


def test_get_host_trends_returns_empty_series_when_instance_missing(monkeypatch):
    from app.services import prometheus

    async def fake_discover_instances(_url=""):
        return {}

    monkeypatch.setattr(prometheus, "discover_instances", fake_discover_instances)

    trends = asyncio.run(prometheus.get_host_trends("10.0.0.1", "web-01"))

    assert all(series["points"] == [] for series in trends["series"])
