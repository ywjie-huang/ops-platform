"""发布总览聚合 — 状态矩阵 / KPI / 动态 / 待审批（模式 B 页面数据源）。

聚合逻辑集中在服务层，便于 sqlite 内存库直接测试。
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session, noload, selectinload

from app.core.config import CHINA_TZ
from app.models.deploy import (
    DeployAppEnv,
    DeployApproval,
    DeployApplication,
    DeployEnvironment,
    DeployRecord,
)

ACTIVE_STATUSES = ("pending", "building", "deploying", "triggering")


def _now() -> datetime:
    """当前时间（与库中 naive 中国时间对齐）。"""
    return datetime.now(CHINA_TZ).replace(tzinfo=None)


def latest_records_by_pair(db: Session) -> dict[tuple[int, int], DeployRecord]:
    """每个 (app_id, env_id) 取最新一条部署记录。"""
    max_ids = (
        select(func.max(DeployRecord.id))
        .group_by(DeployRecord.app_id, DeployRecord.env_id)
        .scalar_subquery()
    )
    stmt = (
        select(DeployRecord)
        .options(
            selectinload(DeployRecord.application),
            selectinload(DeployRecord.environment),
            selectinload(DeployRecord.trigger_user),
        )
        .where(DeployRecord.id.in_(max_ids))
    )
    result: dict[tuple[int, int], DeployRecord] = {}
    for r in db.scalars(stmt).unique().all():
        if r.env_id is not None:
            result[(r.app_id, r.env_id)] = r
    return result


def latest_records_by_app(db: Session) -> dict[int, DeployRecord]:
    """每个应用取最新一条部署记录（不限环境）。"""
    max_ids = (
        select(func.max(DeployRecord.id))
        .group_by(DeployRecord.app_id)
        .scalar_subquery()
    )
    stmt = (
        select(DeployRecord)
        .options(
            selectinload(DeployRecord.application),
            selectinload(DeployRecord.environment),
            selectinload(DeployRecord.trigger_user),
        )
        .where(DeployRecord.id.in_(max_ids))
    )
    return {r.app_id: r for r in db.scalars(stmt).unique().all()}


def record_brief(r: DeployRecord | None) -> dict | None:
    """矩阵单元格/列表行内嵌的轻量记录视图。"""
    if r is None:
        return None
    build_url = ""
    build_number = None
    if r.deploy_config:
        try:
            snap = json.loads(r.deploy_config)
            build_url = snap.get("jenkins_build_url") or ""
            build_number = snap.get("jenkins_build_number")
        except (ValueError, TypeError):
            pass
    return {
        "id": r.id,
        "env_id": r.env_id,
        "env_name": r.environment.name if r.environment else None,
        "version": r.version,
        "status": r.status,
        "trigger_type": r.trigger_type,
        "duration": r.duration,
        "trigger_user_name": r.trigger_user.username if r.trigger_user else None,
        "jenkins_build_url": build_url,
        "jenkins_build_number": build_number,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


def get_kpi(db: Session) -> dict:
    """总览 KPI：进行中 / 待审批 / 今日部署 / 本周失败。"""
    running = db.scalar(
        select(func.count(DeployRecord.id)).where(DeployRecord.status.in_(ACTIVE_STATUSES))
    ) or 0
    pending_approvals = db.scalar(
        select(func.count(DeployApproval.id)).where(DeployApproval.status == "pending")
    ) or 0

    today_start = _now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_rows = db.execute(
        select(DeployRecord.status, func.count(DeployRecord.id))
        .where(DeployRecord.created_at >= today_start)
        .group_by(DeployRecord.status)
    ).all()
    today_by_status = {row[0]: row[1] for row in today_rows}

    week_start = today_start - timedelta(days=7)
    week_failed = db.scalar(
        select(func.count(DeployRecord.id))
        .where(DeployRecord.status == "failed", DeployRecord.created_at >= week_start)
    ) or 0

    return {
        "running": running,
        "pending_approvals": pending_approvals,
        "today_total": sum(today_by_status.values()),
        "today_success": today_by_status.get("success", 0),
        "today_failed": today_by_status.get("failed", 0),
        "week_failed": week_failed,
    }


def get_matrix(db: Session) -> dict:
    """状态矩阵：全部环境（列）× 全部应用（行），单元格为该环境最新记录。"""
    envs = list(db.scalars(select(DeployEnvironment).order_by(DeployEnvironment.sort_order, DeployEnvironment.id)))
    apps = list(db.scalars(
        select(DeployApplication)
        .where(DeployApplication.status != "archived")
        .order_by(DeployApplication.id)
    ))
    app_envs = list(db.scalars(
        select(DeployAppEnv).options(
            # 矩阵只需 enabled 与环境名，剥离 Asset/Cluster 的 joined 关系避免无谓 JOIN
            noload(DeployAppEnv.ssh_asset),
            noload(DeployAppEnv.docker_host),
            noload(DeployAppEnv.k8s_cluster),
            selectinload(DeployAppEnv.environment),
        )
    ))
    enabled_map = {(ae.app_id, ae.env_id): ae.enabled for ae in app_envs}
    latest_map = latest_records_by_pair(db)

    app_items = []
    for app in apps:
        env_cells = {}
        for env in envs:
            key = (app.id, env.id)
            # 未添加该环境配置 → None（前端渲染"未启用"）；已添加但无记录 → record=None
            if key not in enabled_map:
                continue
            env_cells[str(env.id)] = {
                "enabled": enabled_map[key],
                "record": record_brief(latest_map.get(key)),
            }
        app_items.append({
            "id": app.id,
            "name": app.name,
            "display_name": app.display_name,
            "app_type": app.app_type,
            "jenkins_job_name": app.jenkins_job_name,
            "envs": env_cells,
        })

    return {
        "envs": [
            {
                "id": e.id,
                "name": e.name,
                "display_name": e.display_name,
                "approval_required": e.approval_required,
            }
            for e in envs
        ],
        "apps": app_items,
    }


def get_feed(db: Session, limit: int = 10) -> list[DeployRecord]:
    """最近动态：最新 N 条部署记录。"""
    stmt = (
        select(DeployRecord)
        .options(
            selectinload(DeployRecord.application),
            selectinload(DeployRecord.environment),
            selectinload(DeployRecord.trigger_user),
        )
        .order_by(DeployRecord.id.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt).unique().all())


def current_version_for(db: Session, app_id: int, env_id: int | None, before_id: int) -> str:
    """审批对比用：该应用在该环境、此记录之前的最近一次成功版本（线上版本）。"""
    stmt = (
        select(DeployRecord)
        .where(
            DeployRecord.app_id == app_id,
            DeployRecord.env_id == env_id,
            DeployRecord.status == "success",
            DeployRecord.id < before_id,
        )
        .order_by(DeployRecord.id.desc())
        .limit(1)
    )
    prev = db.scalar(stmt)
    return prev.version if prev else ""
