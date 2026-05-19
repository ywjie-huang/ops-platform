"""系统配置读取工具 — DB 优先，fallback 到 config.py 常量。"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.system_config import SystemConfig

# 默认值（来自原 config.py）
_DEFAULTS: dict[str, str] = {
    "prometheus.url": "http://172.16.24.31:30001",
    "alertmanager.url": "http://172.16.24.31:30093",
    # 巡检阈值
    "patrol.cpu_warning": "80",
    "patrol.cpu_critical": "95",
    "patrol.memory_warning": "85",
    "patrol.memory_critical": "95",
    "patrol.disk_warning": "85",
    "patrol.disk_critical": "95",
    "patrol.load_warning": "5",
    "patrol.load_critical": "10",
}


def get_config_float(db: Session, key: str) -> float:
    """读取配置并转为 float，失败返回默认值。"""
    val = get_config(db, key)
    try:
        return float(val)
    except (ValueError, TypeError):
        return float(_DEFAULTS.get(key, "0"))


def get_config(db: Session, key: str) -> str:
    """从 DB 读取配置，不存在则返回默认值。"""
    row = db.scalar(select(SystemConfig).where(SystemConfig.key == key))
    if row and row.value:
        return row.value
    return _DEFAULTS.get(key, "")


def get_prometheus_url(db: Session) -> str:
    return get_config(db, "prometheus.url")


def get_alertmanager_url(db: Session) -> str:
    return get_config(db, "alertmanager.url")


def set_config(db: Session, key: str, value: str, description: str = "") -> SystemConfig:
    """写入或更新配置。"""
    row = db.scalar(select(SystemConfig).where(SystemConfig.key == key))
    if row:
        row.value = value
        if description:
            row.description = description
    else:
        row = SystemConfig(key=key, value=value, description=description)
        db.add(row)
    db.flush()
    return row
