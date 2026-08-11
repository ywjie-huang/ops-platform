import asyncio
from types import SimpleNamespace

from app.services.ai import dispatcher


def test_dispatch_tool_denies_without_required_permission(monkeypatch):
    """无所需权限时，工具执行被拒绝并提示权限码（RBAC 绕过防护回归）。"""
    asked = {}

    def fake_has_permission(user, code):
        asked["code"] = code
        asked["user"] = user
        return False

    monkeypatch.setattr(dispatcher, "has_permission", fake_has_permission)

    user = SimpleNamespace(id=3)
    result = asyncio.run(
        dispatcher.dispatch_tool(db=None, tool_name="query_assets", arguments={}, user=user)
    )

    assert result["ok"] is False
    assert "assets.view" in result["error"]
    assert asked == {"code": "assets.view", "user": user}


def test_dispatch_tool_maps_write_tool_to_execute_permission(monkeypatch):
    """写工具 execute_command 映射到 batch_exec.execute 权限码。"""
    asked = {}

    def fake_has_permission(_user, code):
        asked["code"] = code
        return False

    monkeypatch.setattr(dispatcher, "has_permission", fake_has_permission)

    asyncio.run(
        dispatcher.dispatch_tool(db=None, tool_name="execute_command", arguments={}, user=None)
    )

    assert asked["code"] == "batch_exec.execute"


def test_dispatch_tool_maps_query_logs_to_monitoring_view(monkeypatch):
    """query_logs 工具映射到 monitoring.view 权限码（与日志检索页/API 同源）。"""
    asked = {}

    def fake_has_permission(_user, code):
        asked["code"] = code
        return False

    monkeypatch.setattr(dispatcher, "has_permission", fake_has_permission)

    result = asyncio.run(
        dispatcher.dispatch_tool(db=None, tool_name="query_logs", arguments={}, user=None)
    )

    assert asked["code"] == "monitoring.view"
    assert result["ok"] is False
    assert "monitoring.view" in result["error"]
