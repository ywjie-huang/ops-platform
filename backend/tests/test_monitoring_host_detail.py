import asyncio
from types import SimpleNamespace

from app.api import monitoring
from app.services import assets


def test_host_detail_marks_prometheus_disconnected_when_health_check_fails(monkeypatch):
    asset = SimpleNamespace(
        id=8,
        name="ops-node-08",
        ip_address="10.0.0.8",
        status="使用中",
        owner="sre",
        spec="4C8G",
        os="Linux",
    )

    async def fake_get_host_metrics(_ip, _name="", _db=None):
        return {
            "prometheus_ok": True,
            "cpu": {"usage": 0, "cores": 0},
        }

    async def fake_check_prometheus_health(_db=None):
        return False

    monkeypatch.setattr(assets, "get_asset", lambda _db, _host_id: asset)
    monkeypatch.setattr(monitoring, "get_host_metrics", fake_get_host_metrics)
    monkeypatch.setattr(monitoring, "check_prometheus_health", fake_check_prometheus_health)

    response = asyncio.run(monitoring.api_host_detail(8, db=object(), _=object()))

    assert response["data"]["prometheus_ok"] is False
    assert "error" not in response["data"]
    assert response["data"]["cpu"] == {"usage": 0, "cores": 0}
