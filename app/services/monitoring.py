"""
监控告警服务层
管理监控指标、数据采集、主机监控数据。
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.monitoring import MonitoringMetric, MonitoringData


# ─── 指标管理 ───────────────────────────────────────────────

DEFAULT_METRICS = [
    {"name": "CPU 利用率", "code": "cpu_usage", "unit": "%", "category": "系统", "threshold_warning": 80.0, "threshold_critical": 95.0, "is_system": True},
    {"name": "内存使用率", "code": "memory_usage", "unit": "%", "category": "系统", "threshold_warning": 85.0, "threshold_critical": 95.0, "is_system": True},
    {"name": "磁盘使用率", "code": "disk_usage", "unit": "%", "category": "系统", "threshold_warning": 85.0, "threshold_critical": 95.0, "is_system": True},
    {"name": "磁盘读取速率", "code": "disk_read", "unit": "MB/s", "category": "系统", "threshold_warning": 100.0, "threshold_critical": 200.0, "is_system": True},
    {"name": "磁盘写入速率", "code": "disk_write", "unit": "MB/s", "category": "系统", "threshold_warning": 100.0, "threshold_critical": 200.0, "is_system": True},
    {"name": "网络入流量", "code": "net_in", "unit": "Mbps", "category": "网络", "threshold_warning": 800.0, "threshold_critical": 950.0, "is_system": True},
    {"name": "网络出流量", "code": "net_out", "unit": "Mbps", "category": "网络", "threshold_warning": 800.0, "threshold_critical": 950.0, "is_system": True},
    {"name": "TCP 连接数", "code": "tcp_connections", "unit": "个", "category": "网络", "threshold_warning": 5000.0, "threshold_critical": 10000.0, "is_system": True},
    {"name": "系统负载 (1min)", "code": "load_1m", "unit": "", "category": "系统", "threshold_warning": 4.0, "threshold_critical": 8.0, "is_system": True},
    {"name": "系统负载 (5min)", "code": "load_5m", "unit": "", "category": "系统", "threshold_warning": 3.0, "threshold_critical": 6.0, "is_system": True},
    {"name": "进程数", "code": "process_count", "unit": "个", "category": "系统", "threshold_warning": 500.0, "threshold_critical": 1000.0, "is_system": True},
    {"name": "系统运行时间", "code": "uptime", "unit": "小时", "category": "系统", "threshold_warning": 999999.0, "threshold_critical": 999999.0, "is_system": True},
]


def seed_default_metrics(db: Session) -> None:
    """初始化默认监控指标。"""
    for spec in DEFAULT_METRICS:
        existing = db.scalar(select(MonitoringMetric).where(MonitoringMetric.code == spec["code"]))
        if existing is None:
            db.add(MonitoringMetric(**spec))
    db.flush()


def list_metrics(db: Session, *, keyword: str = "", category: str = "", enabled_only: bool = False) -> list[MonitoringMetric]:
    stmt = select(MonitoringMetric)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(or_(MonitoringMetric.name.ilike(like), MonitoringMetric.code.ilike(like)))
    if category:
        stmt = stmt.where(MonitoringMetric.category == category)
    if enabled_only:
        stmt = stmt.where(MonitoringMetric.is_enabled.is_(True))
    stmt = stmt.order_by(MonitoringMetric.category.asc(), MonitoringMetric.id.asc())
    return list(db.scalars(stmt).all())


def get_metric(db: Session, metric_id: int) -> MonitoringMetric | None:
    return db.scalar(select(MonitoringMetric).where(MonitoringMetric.id == metric_id))


def get_metric_by_code(db: Session, code: str) -> MonitoringMetric | None:
    return db.scalar(select(MonitoringMetric).where(MonitoringMetric.code == code))


def create_metric(db: Session, **kwargs) -> MonitoringMetric:
    obj = MonitoringMetric(**kwargs)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_metric(db: Session, obj: MonitoringMetric, **kwargs) -> MonitoringMetric:
    for k, v in kwargs.items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


def delete_metric(db: Session, obj: MonitoringMetric) -> None:
    db.delete(obj)
    db.commit()


# ─── 主机监控模拟数据 ───────────────────────────────────────

def get_host_monitoring_list(assets: list) -> list[dict[str, Any]]:
    """
    根据资产列表生成每台主机的监控摘要（模拟）。
    生产环境应对接 Prometheus / node_exporter / Zabbix 等。
    """
    result = []
    for asset in assets:
        if asset.status == '离线':
            result.append({
                "asset_id": asset.id,
                "name": asset.name,
                "ip": asset.ip_address,
                "status": "offline",
                "cpu": 0,
                "memory": 0,
                "disk": 0,
                "net_in": 0,
                "net_out": 0,
                "load": 0,
                "owner": asset.owner or '',
            })
        else:
            result.append({
                "asset_id": asset.id,
                "name": asset.name,
                "ip": asset.ip_address,
                "status": "online",
                "cpu": round(random.uniform(10, 85), 1),
                "memory": round(random.uniform(30, 90), 1),
                "disk": round(random.uniform(20, 80), 1),
                "net_in": round(random.uniform(10, 500), 1),
                "net_out": round(random.uniform(5, 300), 1),
                "load": round(random.uniform(0.5, 6.0), 2),
                "owner": asset.owner or '',
            })
    return result


def get_host_detail(asset_id: int, asset_name: str, asset_ip: str) -> dict[str, Any]:
    """
    获取单台主机详细监控数据（模拟）。
    生产环境应根据 asset_id 从 Prometheus 等数据源查询。
    """
    return {
        "asset_id": asset_id,
        "hostname": asset_name,
        "ip": asset_ip,
        "os": "Ubuntu 22.04 LTS",
        "kernel": "5.15.0-91-generic",
        "uptime_hours": random.randint(100, 8760),
        "cpu": {
            "usage": round(random.uniform(15, 85), 1),
            "cores": random.choice([4, 8, 16, 32]),
            "model": random.choice(["Intel Xeon E5-2680", "AMD EPYC 7742", "Intel i7-12700"]),
            "frequency": random.choice(["2.40GHz", "3.20GHz", "2.10GHz"]),
        },
        "memory": {
            "usage": round(random.uniform(40, 90), 1),
            "total_gb": random.choice([16, 32, 64, 128]),
            "used_gb": round(random.uniform(8, 56), 1),
            "cached_gb": round(random.uniform(2, 12), 1),
        },
        "disk": {
            "usage": round(random.uniform(30, 80), 1),
            "total_gb": random.choice([250, 500, 1000, 2000]),
            "used_gb": round(random.uniform(100, 800), 1),
            "read_mb": round(random.uniform(0, 150), 1),
            "write_mb": round(random.uniform(0, 100), 1),
        },
        "network": {
            "in_mbps": round(random.uniform(10, 500), 1),
            "out_mbps": round(random.uniform(5, 300), 1),
            "tcp_connections": random.randint(100, 3000),
            "packets_in": random.randint(10000, 999999),
            "packets_out": random.randint(5000, 500000),
        },
        "load": {
            "1m": round(random.uniform(0.5, 6.0), 2),
            "5m": round(random.uniform(0.3, 4.0), 2),
            "15m": round(random.uniform(0.2, 3.0), 2),
        },
        "processes": {
            "total": random.randint(100, 400),
            "running": random.randint(1, 20),
            "sleeping": random.randint(80, 350),
        },
    }


def get_metric_categories(db: Session) -> list[str]:
    """获取所有指标分类。"""
    rows = db.execute(
        select(MonitoringMetric.category).distinct().order_by(MonitoringMetric.category)
    ).all()
    return [r[0] for r in rows]
