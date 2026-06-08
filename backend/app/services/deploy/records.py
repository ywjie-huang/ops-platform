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
from app.models.deploy import DeployAppEnv, DeployApplication, DeployEnvironment, DeployRecord


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
    if status:
        stmt = stmt.where(DeployRecord.status == status)
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


def execute_deploy(record_id: int) -> None:
    """在线程中执行部署（从 app_env 配置路由到对应策略）。"""
    db = SessionLocal()
    try:
        record = get_record(db, record_id)
        if record is None:
            return

        # 注册取消句柄
        register_cancel_handle(record_id)

        try:
            # 加载应用和环境配置
            app = record.application
            if app is None:
                update_status(db, record, "failed")
                set_error(db, record, "应用不存在")
                return

            # 查找 app_env 配置
            app_env = None
            if record.app_env_id:
                app_env = db.get(DeployAppEnv, record.app_env_id)
            if app_env is None:
                stmt = select(DeployAppEnv).where(
                    DeployAppEnv.app_id == record.app_id,
                    DeployAppEnv.env_id == record.env_id,
                )
                app_env = db.scalar(stmt)

            if app_env is None:
                update_status(db, record, "failed")
                set_error(db, record, "未找到环境配置，请先配置部署目标")
                return

            # ── 回滚：从快照恢复产物路径 ──
            if record.trigger_type == "rollback" and record.deploy_config:
                try:
                    snapshot = json.loads(record.deploy_config)
                    snap_artifact = snapshot.get("artifact_path", "")
                    snap_filename = snapshot.get("artifact_filename", "")
                    if snap_artifact and os.path.isfile(snap_artifact):
                        app.artifact_path = snap_artifact
                        app.artifact_filename = snap_filename
                        append_log(db, record, f"回滚: 使用原部署产物 {snap_filename or snap_artifact}")
                    elif snap_artifact:
                        update_status(db, record, "failed")
                        set_error(db, record, f"回滚失败: 原部署产物已被清理 ({snap_filename or snap_artifact})，请重新上传后部署")
                        return
                except (json.JSONDecodeError, KeyError):
                    pass

            # ── 构建阶段 ──
            build_mode = app.build_mode or "upload"
            has_build = (
                (build_mode == "upload" and app.artifact_path)
                or (build_mode == "jenkins" and app.jenkins_job_name)
                or (build_mode == "local" and app.build_command)
            )
            if has_build:
                update_status(db, record, "building")
                append_log(db, record, "开始构建…")
                from app.services.deploy.builder import execute_build
                artifact = execute_build(db, record, app, app_env)
                if is_cancelled(record.id):
                    update_status(db, record, "cancelled")
                    return
                if artifact is None and build_mode in ("jenkins", "upload"):
                    # Jenkins 构建失败 / upload 模式无产物 → 中止
                    if record.status != "failed":
                        update_status(db, record, "failed")
                        set_error(db, record, "构建失败" if build_mode == "jenkins" else "未上传构建产物")
                    return
                # 将构建产物路径临时写入 app（不持久化）
                if artifact:
                    app.artifact_path = artifact

            # ── 部署阶段 ──
            strategy = app.deploy_strategy
            if strategy == "ssh":
                from app.services.deploy.strategies.ssh_strategy import execute_ssh_deploy
                execute_ssh_deploy(db, record, app, app_env)
            elif strategy == "docker":
                from app.services.deploy.strategies.docker_strategy import execute_docker_deploy
                execute_docker_deploy(db, record, app, app_env)
            elif strategy == "k8s":
                from app.services.deploy.strategies.k8s_strategy import execute_k8s_deploy
                execute_k8s_deploy(db, record, app, app_env)
            else:
                update_status(db, record, "failed")
                set_error(db, record, f"暂不支持 {strategy} 策略")

        except Exception as e:
            update_status(db, record, "failed")
            set_error(db, record, str(e))
            append_log(db, record, f"部署异常: {e}")

        finally:
            unregister_cancel_handle(record_id)

    finally:
        db.close()
