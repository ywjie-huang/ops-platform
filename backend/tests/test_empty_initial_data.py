import asyncio
import importlib

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.api.settings import _CONFIG_SPECS
from app.core import config, settings
from app.models.asset import Asset
from app.models.container import ContainerCluster  # noqa: F401
from app.models.ssh_key import SSHKey
from app.models.ticket import Ticket
from app.models.user import User
from app.services import alertmanager, prometheus


LEGACY_ASSETS = (
    {
        "name": "web-prod-01",
        "asset_type": "云主机",
        "ip_address": "10.10.1.12",
        "status": "使用中",
        "owner": "平台组",
        "spec": "4C8G",
        "os": "Ubuntu 22.04",
        "description": "核心业务 Web 节点",
    },
    {
        "name": "db-prod-01",
        "asset_type": "数据库",
        "ip_address": "10.10.1.21",
        "status": "使用中",
        "owner": "DBA",
        "spec": "8C16G",
        "os": "CentOS 7.9",
        "description": "主数据库实例",
    },
    {
        "name": "waf-gateway",
        "asset_type": "网络设备",
        "ip_address": "10.10.1.2",
        "status": "已关机",
        "owner": "安全组",
        "spec": "2C4G",
        "os": "Debian 11",
        "description": "统一入口网关",
    },
)

LEGACY_TICKETS = (
    {
        "title": "新增监控项配置",
        "description": "需要为 web-prod-01 添加 CPU、内存、磁盘监控告警规则",
        "priority": "normal",
        "status": "in_progress",
        "assignee": "张三",
    },
    {
        "title": "数据库慢查询排查",
        "description": "近期 db-prod-01 出现多条慢查询，需要排查优化",
        "priority": "high",
        "status": "open",
        "assignee": "李四",
    },
    {
        "title": "SSL 证书续期",
        "description": "api.example.com 证书将在 7 天后到期，需要续期并部署",
        "priority": "critical",
        "status": "open",
        "assignee": "王五",
    },
)


def _sqlite_session() -> tuple[Session, object]:
    engine = create_engine("sqlite://")
    SSHKey.__table__.create(engine)
    User.__table__.create(engine)
    Asset.__table__.create(engine)
    Ticket.__table__.create(engine)
    return Session(engine), engine


class _FailIfHttpClientIsCreated:
    created = 0

    def __init__(self, *args, **kwargs):
        type(self).created += 1
        raise AssertionError("HTTP client must not be created without a configured endpoint")


def test_cleanup_removes_untouched_legacy_demo_records():
    from app.db.init_db import _cleanup_legacy_demo_data

    db, engine = _sqlite_session()
    try:
        db.add_all(Asset(**spec) for spec in LEGACY_ASSETS)
        db.add_all(Ticket(**spec) for spec in LEGACY_TICKETS)
        db.commit()

        _cleanup_legacy_demo_data(db)
        db.commit()

        assert list(db.scalars(select(Asset)).all()) == []
        assert list(db.scalars(select(Ticket)).all()) == []
    finally:
        db.close()
        engine.dispose()


def test_cleanup_preserves_modified_legacy_named_records():
    from app.db.init_db import _cleanup_legacy_demo_data

    db, engine = _sqlite_session()
    try:
        modified_asset = Asset(**{**LEGACY_ASSETS[0], "owner": "真实业务组"})
        modified_ticket = Ticket(**{**LEGACY_TICKETS[0], "status": "resolved"})
        db.add_all([modified_asset, modified_ticket])
        db.commit()

        _cleanup_legacy_demo_data(db)
        db.commit()

        assert db.scalar(select(Asset).where(Asset.id == modified_asset.id)) is not None
        assert db.scalar(select(Ticket).where(Ticket.id == modified_ticket.id)) is not None
    finally:
        db.close()
        engine.dispose()


def test_cleanup_preserves_demo_asset_adopted_by_a_real_ticket():
    from app.db.init_db import _cleanup_legacy_demo_data

    db, engine = _sqlite_session()
    try:
        adopted_asset = Asset(**LEGACY_ASSETS[0])
        db.add(adopted_asset)
        db.flush()
        real_ticket = Ticket(
            title="生产故障处理",
            description="用户创建的真实工单",
            priority="high",
            status="open",
            assignee="值班人员",
            asset_id=adopted_asset.id,
        )
        db.add(real_ticket)
        db.commit()
        adopted_asset_id = adopted_asset.id
        real_ticket_id = real_ticket.id

        _cleanup_legacy_demo_data(db)
        db.commit()

        assert db.scalar(select(Asset).where(Asset.id == adopted_asset_id)) is not None
        assert db.scalar(select(Ticket).where(Ticket.id == real_ticket_id)).asset_id == adopted_asset_id
    finally:
        db.close()
        engine.dispose()


def test_monitoring_integration_defaults_are_empty(monkeypatch):
    monkeypatch.delenv("PROMETHEUS_URL", raising=False)
    monkeypatch.delenv("ALERTMANAGER_URL", raising=False)
    importlib.reload(config)

    assert config.PROMETHEUS_URL == ""
    assert config.ALERTMANAGER_URL == ""
    assert settings._DEFAULTS["prometheus.url"] == ""
    assert settings._DEFAULTS["alertmanager.url"] == ""
    assert "172.16.24.31" not in _CONFIG_SPECS["prometheus.url"]
    assert "172.16.24.31" not in _CONFIG_SPECS["alertmanager.url"]


def test_unconfigured_alertmanager_returns_empty_without_http(monkeypatch):
    _FailIfHttpClientIsCreated.created = 0
    monkeypatch.setattr(alertmanager, "get_alertmanager_url", lambda db: "")
    monkeypatch.setattr(alertmanager, "get_prometheus_url", lambda db: "")
    monkeypatch.setattr(alertmanager.httpx, "AsyncClient", _FailIfHttpClientIsCreated)

    assert asyncio.run(alertmanager.check_alertmanager_health(object())) is False
    assert asyncio.run(alertmanager.get_alerts(object())) == []
    assert asyncio.run(alertmanager.get_rules(object())) == []
    assert _FailIfHttpClientIsCreated.created == 0


def test_unconfigured_prometheus_returns_empty_without_http(monkeypatch):
    _FailIfHttpClientIsCreated.created = 0
    prometheus._instance_cache = {}
    prometheus._instance_cache_ts = 0
    monkeypatch.setattr(prometheus, "get_prometheus_url", lambda db: "")
    monkeypatch.setattr(prometheus, "PROMETHEUS_URL", "")
    monkeypatch.setattr(prometheus.httpx, "AsyncClient", _FailIfHttpClientIsCreated)

    assert asyncio.run(prometheus.check_prometheus_health(object())) is False
    assert asyncio.run(prometheus.get_targets(object())) == []
    assert asyncio.run(prometheus.discover_instances()) == {}
    assert _FailIfHttpClientIsCreated.created == 0
