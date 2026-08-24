"""Deploy record service — create, update status, append logs, query."""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import CHINA_TZ
from app.db.database import SessionLocal
from app.models.deploy import DeployAppEnv, DeployApplication, DeployBuild, DeployEnvironment, DeployRecord


# ── 部署取消标志（内存中，按 record_id 索引） ──
_cancel_flags: dict[int, threading.Event] = {}


def is_cancelled(record_id: int) -> bool:
    """检查部署是否已被取消。"""
    return record_id in _cancel_flags and _cancel_flags[record_id].is_set()


def request_cancel(record_id: int) -> None:
    """请求取消部署。"""
    if record_id in _cancel_flags:
        _cancel_flags[record_id].set()


def register_cancel_handle(record_id: int) -> threading.Event:
    """注册一个取消事件，返回 Event 对象。"""
    evt = threading.Event()
    _cancel_flags[record_id] = evt
    return evt


def unregister_cancel_handle(record_id: int) -> None:
    """清理取消事件。"""
    _cancel_flags.pop(record_id, None)


# ── 记录 CRUD ──


def list_records(
    db: Session,
    *,
    app_id: int | None = None,
    env_id: int | None = None,
    status: str = "",
    trigger_type: str = "",
    version_kw: str = "",
) -> list[DeployRecord]:
    """查询部署记录列表。"""
    stmt = select(DeployRecord).options(
        selectinload(DeployRecord.application),
        selectinload(DeployRecord.environment),
        selectinload(DeployRecord.trigger_user),
    )
    if app_id:
        stmt = stmt.where(DeployRecord.app_id == app_id)
    if env_id:
        stmt = stmt.where(DeployRecord.env_id == env_id)
    if status == "active":
        stmt = stmt.where(DeployRecord.status.in_(["pending", "building", "deploying", "triggering"]))
    elif status:
        stmt = stmt.where(DeployRecord.status == status)
    if trigger_type:
        stmt = stmt.where(DeployRecord.trigger_type == trigger_type)
    if version_kw.strip():
        stmt = stmt.where(DeployRecord.version.ilike(f"%{version_kw.strip()}%"))
    stmt = stmt.order_by(DeployRecord.id.desc())
    return list(db.scalars(stmt).unique().all())


def get_record(db: Session, record_id: int) -> DeployRecord | None:
    """获取单条部署记录。"""
    stmt = select(DeployRecord).options(
        selectinload(DeployRecord.application),
        selectinload(DeployRecord.environment),
        selectinload(DeployRecord.trigger_user),
    ).where(DeployRecord.id == record_id)
    return db.scalar(stmt)


def create_record(
    db: Session,
    *,
    app_id: int,
    env_id: int,
    app_env_id: int | None = None,
    version: str = "",
    trigger_type: str = "manual",
    trigger_user_id: int | None = None,
    deploy_config: str = "",
) -> DeployRecord:
    """创建部署记录（状态=pending）。"""
    record = DeployRecord(
        app_id=app_id,
        env_id=env_id,
        app_env_id=app_env_id,
        version=version,
        status="pending",
        trigger_type=trigger_type,
        trigger_user_id=trigger_user_id,
        deploy_config=deploy_config,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def update_status(db: Session, record: DeployRecord, status: str) -> None:
    """更新部署状态。"""
    record.status = status
    if status in ("deploying", "building") and record.started_at is None:
        record.started_at = datetime.now(CHINA_TZ)
    if status in ("success", "failed", "cancelled"):
        record.finished_at = datetime.now(CHINA_TZ)
        if record.started_at:
            started = record.started_at.replace(tzinfo=None) if record.started_at.tzinfo else record.started_at
            finished = record.finished_at.replace(tzinfo=None) if record.finished_at.tzinfo else record.finished_at
            record.duration = (finished - started).total_seconds()
    db.commit()


def append_log(db: Session, record: DeployRecord, line: str) -> None:
    """追加一行日志。"""
    ts = datetime.now(CHINA_TZ).strftime("%H:%M:%S")
    entry = f"[{ts}] {line}\n"
    record.log = (record.log or "") + entry
    db.commit()


def set_error(db: Session, record: DeployRecord, msg: str) -> None:
    """设置错误信息。"""
    record.error_message = msg
    db.commit()
