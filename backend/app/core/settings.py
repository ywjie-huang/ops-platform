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
    # LLM 配置
    "llm.base_url": "",
    "llm.api_key": "",
    "llm.model": "",
    "llm.api_mode": "chat_completions",
    "llm.reasoning_effort": "",
    "llm.temperature": "0.7",
    "llm.max_tokens": "4096",
    "llm.top_p": "1.0",
    "llm.system_prompt": "",
    "llm.profiles": "[]",
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


def get_llm_config(db: Session) -> dict[str, str]:
    """读取 LLM 配置，返回 {base_url, api_key, model, temperature, max_tokens, top_p, system_prompt}。"""
    return {
        "base_url": get_config(db, "llm.base_url"),
        "api_key": get_config(db, "llm.api_key"),
        "model": get_config(db, "llm.model"),
        "api_mode": get_config(db, "llm.api_mode"),
        "reasoning_effort": get_config(db, "llm.reasoning_effort"),
        "temperature": get_config(db, "llm.temperature"),
        "max_tokens": get_config(db, "llm.max_tokens"),
        "top_p": get_config(db, "llm.top_p"),
        "system_prompt": get_config(db, "llm.system_prompt"),
    }


def get_llm_profiles(db: Session) -> list[dict[str, str]]:
    """读取 LLM 配置列表。"""
    import json
    raw = get_config(db, "llm.profiles")
    try:
        return json.loads(raw) if raw else []
    except (json.JSONDecodeError, TypeError):
        return []


def set_llm_profiles(db: Session, profiles: list[dict[str, str]]) -> None:
    """写入 LLM 配置列表。"""
    import json
    set_config(db, "llm.profiles", json.dumps(profiles, ensure_ascii=False), "LLM 模型配置列表")


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
