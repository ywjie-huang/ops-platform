"""
报表中心服务层
提供预置报表数据、自定义报表、导出等能力。
"""

from __future__ import annotations

import csv
import io
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select, and_
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.ticket import Ticket
from app.models.alert import Alert
from app.models.user import User
from app.models.audit import AuditLog


# ─── 预置报表定义 ───────────────────────────────────────────

PRESET_REPORTS = [
    {
        "id": "asset_summary",
        "name": "资产统计报表",
        "description": "按类型、状态统计资产分布情况",
        "icon": "🖥️",
        "category": "资产",
    },
    {
        "id": "asset_status_trend",
        "name": "资产状态趋势",
        "description": "近 30 天资产使用中/已关机/已删除状态变化",
        "icon": "📈",
        "category": "资产",
    },
    {
        "id": "ticket_summary",
        "name": "工单统计报表",
        "description": "按状态、优先级统计工单处理情况",
        "icon": "📋",
        "category": "工单",
    },
    {
        "id": "ticket_efficiency",
        "name": "工单处理效率",
        "description": "工单平均处理时长、解决率统计",
        "icon": "⚡",
        "category": "工单",
    },
    {
        "id": "alert_summary",
        "name": "告警统计报表",
        "description": "按级别、状态统计告警分布",
        "icon": "🔔",
        "category": "告警",
    },
    {
        "id": "alert_trend",
        "name": "告警趋势分析",
        "description": "近 30 天告警数量变化趋势",
        "icon": "📊",
        "category": "告警",
    },
    {
        "id": "user_activity",
        "name": "用户活跃度报表",
        "description": "用户操作频次、登录统计",
        "icon": "👥",
        "category": "用户",
    },
    {
        "id": "audit_overview",
        "name": "审计概览报表",
        "description": "按操作类型统计系统操作分布",
        "icon": "📜",
        "category": "审计",
    },
]


# ─── 报表数据查询 ───────────────────────────────────────────


def list_preset_reports() -> list[dict[str, Any]]:
    """返回所有预置报表列表。"""
    return PRESET_REPORTS


def get_preset_report(report_id: str) -> dict[str, Any] | None:
    """根据 ID 获取预置报表定义。"""
    for r in PRESET_REPORTS:
        if r["id"] == report_id:
            return r
    return None


def query_report_data(db: Session, report_id: str, days: int = 30) -> dict[str, Any]:
    """查询预置报表数据，返回结构化结果。"""
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=days)

    if report_id == "asset_summary":
        return _asset_summary(db)
    elif report_id == "asset_status_trend":
        return _asset_status_trend(db, since)
    elif report_id == "ticket_summary":
        return _ticket_summary(db)
    elif report_id == "ticket_efficiency":
        return _ticket_efficiency(db, since)
    elif report_id == "alert_summary":
        return _alert_summary(db)
    elif report_id == "alert_trend":
        return _alert_trend(db, since)
    elif report_id == "user_activity":
        return _user_activity(db, since)
    elif report_id == "audit_overview":
        return _audit_overview(db, since)
    else:
        return {"error": "未知报表类型"}


# ─── 自定义报表 ─────────────────────────────────────────────

DATA_SOURCES = [
    {"id": "assets", "name": "资产", "model": "Asset"},
    {"id": "tickets", "name": "工单", "model": "Ticket"},
    {"id": "alerts", "name": "告警", "model": "Alert"},
    {"id": "users", "name": "用户", "model": "User"},
    {"id": "audit_logs", "name": "审计日志", "model": "AuditLog"},
]

DIMENSIONS = {
    "assets": [
        {"id": "asset_type", "name": "资产类型"},
        {"id": "status", "name": "状态"},
        {"id": "owner", "name": "负责人"},
    ],
    "tickets": [
        {"id": "status", "name": "状态"},
        {"id": "priority", "name": "优先级"},
        {"id": "assignee", "name": "负责人"},
    ],
    "alerts": [
        {"id": "level", "name": "级别"},
        {"id": "status", "name": "状态"},
        {"id": "source", "name": "来源"},
    ],
    "users": [
        {"id": "username", "name": "用户名"},
    ],
    "audit_logs": [
        {"id": "action", "name": "操作类型"},
        {"id": "target_type", "name": "对象类型"},
    ],
}


def list_data_sources() -> list[dict[str, Any]]:
    return DATA_SOURCES


def list_dimensions(source_id: str) -> list[dict[str, Any]]:
    return DIMENSIONS.get(source_id, [])


def query_custom_report(
    db: Session,
    source_id: str,
    dimension: str,
    days: int = 30,
) -> dict[str, Any]:
    """执行自定义报表查询。"""
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=days)

    if source_id == "assets":
        return _custom_assets(db, dimension)
    elif source_id == "tickets":
        return _custom_tickets(db, dimension, since)
    elif source_id == "alerts":
        return _custom_alerts(db, dimension, since)
    elif source_id == "users":
        return _custom_users(db, dimension)
    elif source_id == "audit_logs":
        return _custom_audit_logs(db, dimension, since)
    else:
        return {"error": "未知数据源"}


# ─── CSV 导出 ────────────────────────────────────────────────


def export_csv(db: Session, report_id: str, days: int = 30) -> str:
    """导出报表为 CSV 格式字符串。"""
    data = query_report_data(db, report_id, days)
    if "error" in data:
        return ""

    output = io.StringIO()
    writer = csv.writer(output)

    # 写表头
    if "columns" in data and "rows" in data:
        writer.writerow(data["columns"])
        for row in data["rows"]:
            writer.writerow(row)
    elif "items" in data:
        items = data["items"]
        if items:
            writer.writerow(items[0].keys())
            for item in items:
                writer.writerow(item.values())

    return output.getvalue()


# ─── 内部实现 ────────────────────────────────────────────────


def _asset_summary(db: Session) -> dict[str, Any]:
    """资产按类型和状态统计。"""
    type_rows = db.execute(
        select(Asset.asset_type, func.count(Asset.id)).group_by(Asset.asset_type).order_by(func.count(Asset.id).desc())
    ).all()

    status_rows = db.execute(
        select(Asset.status, func.count(Asset.id)).group_by(Asset.status)
    ).all()

    return {
        "title": "资产统计报表",
        "by_type": {"columns": ["类型", "数量"], "rows": [[r[0], r[1]] for r in type_rows]},
        "by_status": {"columns": ["状态", "数量"], "rows": [[r[0], r[1]] for r in status_rows]},
        "total": db.scalar(select(func.count(Asset.id))) or 0,
    }


def _asset_status_trend(db: Session, since: datetime) -> dict[str, Any]:
    """资产状态趋势（简化：当前快照，无历史表则用当前数据）。"""
    rows = db.execute(
        select(Asset.status, func.count(Asset.id)).group_by(Asset.status)
    ).all()

    return {
        "title": "资产状态趋势",
        "current": {"columns": ["状态", "数量"], "rows": [[r[0], r[1]] for r in rows]},
        "note": "当前为快照数据，需历史表支持完整趋势",
    }


def _ticket_summary(db: Session) -> dict[str, Any]:
    """工单按状态和优先级统计。"""
    status_rows = db.execute(
        select(Ticket.status, func.count(Ticket.id)).group_by(Ticket.status)
    ).all()

    priority_rows = db.execute(
        select(Ticket.priority, func.count(Ticket.id)).group_by(Ticket.priority)
    ).all()

    total = db.scalar(select(func.count(Ticket.id))) or 0
    resolved = db.scalar(select(func.count(Ticket.id)).where(Ticket.status == "resolved")) or 0

    return {
        "title": "工单统计报表",
        "by_status": {"columns": ["状态", "数量"], "rows": [[r[0], r[1]] for r in status_rows]},
        "by_priority": {"columns": ["优先级", "数量"], "rows": [[r[0], r[1]] for r in priority_rows]},
        "total": total,
        "resolved": resolved,
        "resolution_rate": f"{resolved / total * 100:.1f}%" if total > 0 else "N/A",
    }


def _ticket_efficiency(db: Session, since: datetime) -> dict[str, Any]:
    """工单处理效率（简化统计）。"""
    total = db.scalar(select(func.count(Ticket.id))) or 0
    open_count = db.scalar(select(func.count(Ticket.id)).where(Ticket.status == "open")) or 0
    in_progress = db.scalar(select(func.count(Ticket.id)).where(Ticket.status == "in_progress")) or 0
    resolved = db.scalar(select(func.count(Ticket.id)).where(Ticket.status == "resolved")) or 0
    closed = db.scalar(select(func.count(Ticket.id)).where(Ticket.status == "closed")) or 0

    return {
        "title": "工单处理效率",
        "metrics": {
            "total": total,
            "open": open_count,
            "in_progress": in_progress,
            "resolved": resolved,
            "closed": closed,
            "completion_rate": f"{(resolved + closed) / total * 100:.1f}%" if total > 0 else "N/A",
        },
    }


def _alert_summary(db: Session) -> dict[str, Any]:
    """告警按级别和状态统计。"""
    level_rows = db.execute(
        select(Alert.level, func.count(Alert.id)).group_by(Alert.level)
    ).all()

    status_rows = db.execute(
        select(Alert.status, func.count(Alert.id)).group_by(Alert.status)
    ).all()

    return {
        "title": "告警统计报表",
        "by_level": {"columns": ["级别", "数量"], "rows": [[r[0], r[1]] for r in level_rows]},
        "by_status": {"columns": ["状态", "数量"], "rows": [[r[0], r[1]] for r in status_rows]},
        "total": db.scalar(select(func.count(Alert.id))) or 0,
    }


def _alert_trend(db: Session, since: datetime) -> dict[str, Any]:
    """告警趋势（当前快照）。"""
    rows = db.execute(
        select(Alert.level, func.count(Alert.id)).group_by(Alert.level)
    ).all()

    return {
        "title": "告警趋势分析",
        "current": {"columns": ["级别", "数量"], "rows": [[r[0], r[1]] for r in rows]},
        "note": "当前为快照数据，需历史表支持完整趋势",
    }


def _user_activity(db: Session, since: datetime) -> dict[str, Any]:
    """用户活跃度（基于审计日志）。"""
    rows = db.execute(
        select(AuditLog.username, func.count(AuditLog.id))
        .where(AuditLog.created_at >= since)
        .group_by(AuditLog.username)
        .order_by(func.count(AuditLog.id).desc())
        .limit(20)
    ).all()

    return {
        "title": "用户活跃度报表",
        "period": f"最近 { (datetime.now(timezone.utc) - since).days } 天",
        "columns": ["用户", "操作次数"],
        "rows": [[r[0], r[1]] for r in rows],
    }


def _audit_overview(db: Session, since: datetime) -> dict[str, Any]:
    """审计概览。"""
    action_rows = db.execute(
        select(AuditLog.action, func.count(AuditLog.id))
        .where(AuditLog.created_at >= since)
        .group_by(AuditLog.action)
        .order_by(func.count(AuditLog.id).desc())
    ).all()

    target_rows = db.execute(
        select(AuditLog.target_type, func.count(AuditLog.id))
        .where(AuditLog.created_at >= since)
        .group_by(AuditLog.target_type)
        .order_by(func.count(AuditLog.id).desc())
    ).all()

    return {
        "title": "审计概览报表",
        "period": f"最近 { (datetime.now(timezone.utc) - since).days } 天",
        "by_action": {"columns": ["操作类型", "次数"], "rows": [[r[0], r[1]] for r in action_rows]},
        "by_target": {"columns": ["对象类型", "次数"], "rows": [[r[0], r[1]] for r in target_rows]},
    }


def _custom_assets(db: Session, dimension: str) -> dict[str, Any]:
    if dimension == "asset_type":
        col = Asset.asset_type
    elif dimension == "status":
        col = Asset.status
    elif dimension == "owner":
        col = Asset.owner
    else:
        return {"error": f"不支持的维度: {dimension}"}

    rows = db.execute(
        select(col, func.count(Asset.id)).group_by(col).order_by(func.count(Asset.id).desc())
    ).all()

    return {
        "title": f"资产按{dimension}统计",
        "columns": [dimension, "数量"],
        "rows": [[str(r[0]) if r[0] else "未设置", r[1]] for r in rows],
    }


def _custom_tickets(db: Session, dimension: str, since: datetime) -> dict[str, Any]:
    if dimension == "status":
        col = Ticket.status
    elif dimension == "priority":
        col = Ticket.priority
    elif dimension == "assignee":
        col = Ticket.assignee
    else:
        return {"error": f"不支持的维度: {dimension}"}

    rows = db.execute(
        select(col, func.count(Ticket.id))
        .where(Ticket.created_at >= since)
        .group_by(col)
        .order_by(func.count(Ticket.id).desc())
    ).all()

    return {
        "title": f"工单按{dimension}统计",
        "columns": [dimension, "数量"],
        "rows": [[str(r[0]) if r[0] else "未设置", r[1]] for r in rows],
    }


def _custom_alerts(db: Session, dimension: str, since: datetime) -> dict[str, Any]:
    if dimension == "level":
        col = Alert.level
    elif dimension == "status":
        col = Alert.status
    elif dimension == "source":
        col = Alert.source
    else:
        return {"error": f"不支持的维度: {dimension}"}

    rows = db.execute(
        select(col, func.count(Alert.id))
        .where(Alert.created_at >= since)
        .group_by(col)
        .order_by(func.count(Alert.id).desc())
    ).all()

    return {
        "title": f"告警按{dimension}统计",
        "columns": [dimension, "数量"],
        "rows": [[str(r[0]) if r[0] else "未设置", r[1]] for r in rows],
    }


def _custom_users(db: Session, dimension: str) -> dict[str, Any]:
    if dimension == "username":
        rows = db.execute(
            select(User.username, func.count(User.id)).group_by(User.username)
        ).all()
    else:
        return {"error": f"不支持的维度: {dimension}"}

    return {
        "title": f"用户按{dimension}统计",
        "columns": [dimension, "数量"],
        "rows": [[str(r[0]) if r[0] else "未设置", r[1]] for r in rows],
    }


def _custom_audit_logs(db: Session, dimension: str, since: datetime) -> dict[str, Any]:
    if dimension == "action":
        col = AuditLog.action
    elif dimension == "target_type":
        col = AuditLog.target_type
    else:
        return {"error": f"不支持的维度: {dimension}"}

    rows = db.execute(
        select(col, func.count(AuditLog.id))
        .where(AuditLog.created_at >= since)
        .group_by(col)
        .order_by(func.count(AuditLog.id).desc())
    ).all()

    return {
        "title": f"审计日志按{dimension}统计",
        "columns": [dimension, "次数"],
        "rows": [[str(r[0]) if r[0] else "未设置", r[1]] for r in rows],
    }
