"""仪表盘数据构建服务。"""

import math
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import Date, cast, func, select
from sqlalchemy.orm import Session

from app.core.config import CHINA_TZ
from app.models.alert_event import AlertEvent
from app.models.asset import Asset
from app.models.audit import AuditLog
from app.models.dashboard import (
    DashboardActivityItem,
    DashboardDistributionItem,
    DashboardQuickStat,
    DashboardStats,
    DashboardSummary,
    DashboardTypeBreakdown,
)
from app.models.ticket import Ticket
from app.services.assets import (
    count_assets_by_status,
    count_assets_by_type,
    list_assets,
    list_recent_assets,
)
from app.services.roles import count_users_by_role, list_roles
from app.services.tickets import count_open_tickets, list_tickets
from app.services.users import count_new_users_since, list_recent_users, list_users


def _count_open_alert_events(db: Session) -> int:
    """统计当前未恢复的 Prometheus 告警事件。"""
    stmt = select(func.count(AlertEvent.id)).where(AlertEvent.status == "firing")
    return db.scalar(stmt) or 0


def _list_recent_alert_events(db: Session, limit: int = 5) -> list[tuple[AlertEvent, int]]:
    """取最近告警，按 fingerprint 合并：同一告警只保留最新状态，并返回窗口内合并条数。

    空 fingerprint 视为独立事件不参与合并。在 Python 层去重以兼容 MySQL 5.7 / 8.x，
    避免依赖窗口函数。窗口取 limit 的若干倍以保证高频告警的最新状态能被覆盖。
    """
    window = max(limit * 8, 50)
    rows = list(
        db.scalars(
            select(AlertEvent)
            .order_by(AlertEvent.received_at.desc(), AlertEvent.id.desc())
            .limit(window)
        ).all()
    )

    latest_by_fp: dict[str, tuple[AlertEvent, int]] = {}
    standalone: list[tuple[AlertEvent, int]] = []
    for event in rows:
        # rows 已按时间倒序，首次见到的 fingerprint 即该告警的最新状态
        if not event.fingerprint:
            standalone.append((event, 1))
            continue
        existing = latest_by_fp.get(event.fingerprint)
        if existing is None:
            latest_by_fp[event.fingerprint] = (event, 1)
        else:
            latest_event, count = existing
            latest_by_fp[event.fingerprint] = (latest_event, count + 1)

    merged = list(latest_by_fp.values()) + standalone
    merged.sort(key=lambda pair: (pair[0].received_at or datetime.min, pair[0].id), reverse=True)
    return merged[:limit]


def _format_ratio(numerator: int, denominator: int) -> str:
    if denominator <= 0:
        return "0%"
    return f"{round(numerator / denominator * 100)}%"


def _as_number(value: Any) -> float | None:
    """将 Prometheus 聚合值收敛为有限浮点数。"""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _nearest_rank_percentile(values: list[float], percentile: float) -> float | None:
    """按 nearest-rank 算法计算百分位，空样本返回 None。"""
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, math.ceil(percentile * len(ordered)))
    return round(ordered[rank - 1], 1)


def _weighted_usage(
    hosts: list[dict[str, Any]],
    usage_key: str,
    weight_key: str,
) -> tuple[float | None, float]:
    weighted_total = 0.0
    total_weight = 0.0
    for host in hosts:
        usage = _as_number(host.get(usage_key))
        weight = _as_number(host.get(weight_key))
        if usage is None or weight is None or weight <= 0:
            continue
        weighted_total += max(0.0, min(100.0, usage)) * weight
        total_weight += weight
    if total_weight <= 0:
        return None, 0.0
    return round(weighted_total / total_weight, 1), total_weight


def _capacity_usage(
    hosts: list[dict[str, Any]],
    total_key: str,
    available_key: str,
) -> tuple[float | None, float]:
    used_total = 0.0
    capacity_total = 0.0
    for host in hosts:
        total = _as_number(host.get(total_key))
        available = _as_number(host.get(available_key))
        if total is None or available is None or total <= 0:
            continue
        bounded_available = max(0.0, min(total, available))
        used_total += total - bounded_available
        capacity_total += total
    if capacity_total <= 0:
        return None, 0.0
    return round(used_total / capacity_total * 100, 1), capacity_total


def build_host_resource_health(hosts: list[dict[str, Any]]) -> dict[str, Any]:
    """构建主机池资源健康视图。

    CPU 按主机核心数进行容量加权；内存和根分区按总字节数汇总后再计算使用率。
    P95 与热点主机数使用单机百分比，避免总体平均掩盖局部过载。
    """
    total = len(hosts)
    monitored_hosts = [host for host in hosts if bool(host.get("prometheus_ok"))]
    monitored = len(monitored_hosts)

    cpu_usage, cpu_cores = _weighted_usage(monitored_hosts, "cpu", "cpu_cores")
    memory_usage, memory_total = _capacity_usage(
        monitored_hosts,
        "memory_total_bytes",
        "memory_available_bytes",
    )
    disk_usage, disk_total = _capacity_usage(
        monitored_hosts,
        "disk_total_bytes",
        "disk_available_bytes",
    )

    def samples(key: str) -> list[float]:
        values: list[float] = []
        for host in monitored_hosts:
            value = _as_number(host.get(key))
            if value is not None:
                values.append(max(0.0, min(100.0, value)))
        return values

    cpu_values = samples("cpu")
    memory_values = samples("memory")
    disk_values = samples("disk")
    coverage = round(monitored / total * 100, 1) if total else 0.0

    cpu_p95 = _nearest_rank_percentile(cpu_values, 0.95)
    memory_p95 = _nearest_rank_percentile(memory_values, 0.95)
    disk_p95 = _nearest_rank_percentile(disk_values, 0.95)
    cpu_hot_hosts = sum(value >= 80 for value in cpu_values)
    memory_hot_hosts = sum(value >= 85 for value in memory_values)
    disk_hot_hosts = sum(value >= 85 for value in disk_values)

    critical = (
        (total > 0 and coverage < 80)
        or any(value is not None and value >= 90 for value in (cpu_usage, memory_usage, disk_usage))
        or any(value is not None and value >= 95 for value in (cpu_p95, memory_p95, disk_p95))
    )
    warning = (
        (total > 0 and coverage < 100)
        or cpu_hot_hosts > 0
        or memory_hot_hosts > 0
        or disk_hot_hosts > 0
    )
    status = "unknown" if total == 0 else "critical" if critical else "warning" if warning else "healthy"

    return {
        "host_pool": {
            "total": total,
            "monitored": monitored,
            "unmonitored": total - monitored,
            "coverage": coverage,
            "status": status,
            "cpu_usage": cpu_usage,
            "cpu_p95": cpu_p95,
            "cpu_hot_hosts": cpu_hot_hosts,
            "cpu_cores": round(cpu_cores),
            "memory_usage": memory_usage,
            "memory_p95": memory_p95,
            "memory_hot_hosts": memory_hot_hosts,
            "memory_total_gb": round(memory_total / 1024**3, 1),
            "disk_usage": disk_usage,
            "disk_p95": disk_p95,
            "disk_hot_hosts": disk_hot_hosts,
            "disk_total_gb": round(disk_total / 1024**3, 1),
        }
    }


def build_dashboard_stats(db: Session) -> DashboardStats:
    assets = list_assets(db)
    users = list_users(db)
    roles = list_roles(db)
    status_counts = count_assets_by_status(db)
    return DashboardStats(
        asset_total=len(assets),
        online_hosts=status_counts.get("使用中", 0),
        open_alerts=_count_open_alert_events(db),
        pending_tickets=count_open_tickets(db),
        user_total=len(users),
        role_total=len(roles),
        offline_assets=status_counts.get("已删除", 0),
        maintenance_assets=status_counts.get("已关机", 0),
        user_growth_7d=count_new_users_since(db, 7),
    )


def build_dashboard_summary(db: Session) -> DashboardSummary:
    recent_assets = list_recent_assets(db, limit=5)
    recent_users = list_recent_users(db, limit=5)
    role_distribution = count_users_by_role(db)
    status_counts = count_assets_by_status(db)
    type_counts = count_assets_by_type(db)
    total_assets = len(list_assets(db))

    open_tickets = count_open_tickets(db)
    pending_alerts = _count_open_alert_events(db)

    quick_stats = [
        DashboardQuickStat("在线率", _format_ratio(status_counts.get("使用中", 0), total_assets), "按资产状态实时统计", "green"),
        DashboardQuickStat("待处理工单", str(open_tickets), "包含 open 和 in_progress 状态", "blue" if open_tickets == 0 else "orange"),
        DashboardQuickStat("未恢复告警", str(pending_alerts), "来自 Alertmanager 的 firing 事件", "green" if pending_alerts == 0 else "red"),
    ]

    TYPE_COLORS = {
        "云主机": "#3b82f6",
        "数据库": "#8b5cf6",
        "网络设备": "#06b6d4",
        "中间件": "#f59e0b",
        "其他": "#94a3b8",
    }
    type_breakdown = [
        DashboardTypeBreakdown(label=t, value=c, color=TYPE_COLORS.get(t, "#64748b"))
        for t, c in type_counts.items()
    ]
    max_type_value = max((item.value for item in type_breakdown), default=0)

    STATUS_TONES = {"使用中": "green", "已关机": "orange", "已删除": "red"}
    asset_changes = [
        DashboardActivityItem(
            title=asset.name,
            meta=f"{asset.asset_type} · {asset.ip_address}",
            detail=f"负责人 {asset.owner or '未填写'}，当前状态 {asset.status}",
            tag=asset.status,
            tone=STATUS_TONES.get(asset.status, "default"),
        )
        for asset in recent_assets
    ]
    if not asset_changes:
        asset_changes = [
            DashboardActivityItem("还没有资产记录", "先去资产管理页录入第一批资产", "录入后这里会展示最近变更", "空")
        ]

    user_items = [
        DashboardActivityItem(
            title=user.full_name,
            meta=f"{user.username} · {user.created_at.strftime('%Y-%m-%d %H:%M')}",
            detail=("角色：" + "、".join(role.name for role in user.roles)) if user.roles else "暂未分配角色",
            tag="新增",
            tone="blue",
        )
        for user in recent_users
    ]
    if not user_items:
        user_items = [
            DashboardActivityItem("还没有新增用户", "创建账号后这里会显示最近加入成员", "方便首页直接扫一眼人员变化", "空")
        ]

    recent_tickets = list_tickets(db)[:5]
    TICKET_TONES = {"open": "blue", "in_progress": "orange", "resolved": "green", "closed": "default"}
    ticket_items = [
        DashboardActivityItem(
            title=t.title,
            meta=f"{t.priority} · {t.assignee or '未指派'} · {t.created_at.strftime('%Y-%m-%d %H:%M')}",
            detail=t.description[:80] + "..." if len(t.description) > 80 else t.description,
            tag=t.status,
            tone=TICKET_TONES.get(t.status, "default"),
        )
        for t in recent_tickets
    ]

    recent_alert_pairs = _list_recent_alert_events(db, limit=5)
    ALERT_TONES = {"firing": "red", "resolved": "green"}
    alert_items = [
        DashboardActivityItem(
            title=a.alert_name or a.summary or "未命名告警",
            meta=f"{a.severity} · {a.instance or a.job or '未知实例'} · {a.received_at.strftime('%Y-%m-%d %H:%M') if a.received_at else '-'}",
            detail=(a.summary or a.description or "")[:80],
            tag=a.status,
            tone=ALERT_TONES.get(a.status, "default"),
            merged_count=count,
        )
        for a, count in recent_alert_pairs
    ]

    role_items = [
        DashboardDistributionItem(
            label=role.name,
            value=user_count,
            tone="primary" if role.is_system else "neutral",
        )
        for role, user_count in role_distribution[:6]
    ]
    if not role_items:
        role_items = [DashboardDistributionItem(label="暂无角色数据", value=0)]

    return DashboardSummary(
        quick_stats=quick_stats,
        recent_asset_changes=asset_changes,
        recent_users=user_items,
        role_distribution=role_items,
        type_breakdown=type_breakdown,
        max_type_value=max_type_value,
        recent_tickets=ticket_items,
        recent_alerts=alert_items,
    )


def build_sparkline_data(db: Session) -> dict:
    """返回近 7 天每日统计，用于 Sparkline 趋势图。"""
    today = datetime.now(CHINA_TZ).date()
    dates = [(today - timedelta(days=i)) for i in range(6, -1, -1)]
    date_strs = [d.strftime("%m-%d") for d in dates]

    # 资产总数（取每天的总量，无 created_at 按天分组则用当前总量）
    asset_total = db.scalar(select(func.count(Asset.id))) or 0

    # 在线主机数（状态为"使用中"）
    online_total = db.scalar(
        select(func.count(Asset.id)).where(Asset.status == "使用中")
    ) or 0

    # 告警：近 7 天每日新增告警数（alert_events 表）
    alert_rows = db.execute(
        select(
            cast(AlertEvent.received_at, Date).label("day"),
            func.count(AlertEvent.id),
        )
        .where(AlertEvent.received_at >= datetime.combine(dates[0], datetime.min.time()))
        .group_by(cast(AlertEvent.received_at, Date))
        .order_by(cast(AlertEvent.received_at, Date))
    ).all()
    alert_map = {str(row[0]): row[1] for row in alert_rows}

    # 工单：近 7 天每日新增工单数
    ticket_rows = db.execute(
        select(
            cast(Ticket.created_at, Date).label("day"),
            func.count(Ticket.id),
        )
        .where(Ticket.created_at >= datetime.combine(dates[0], datetime.min.time()))
        .group_by(cast(Ticket.created_at, Date))
        .order_by(cast(Ticket.created_at, Date))
    ).all()
    ticket_map = {str(row[0]): row[1] for row in ticket_rows}

    # 对于资产和在线数，无历史快照，用常量填充（后续可接入时序数据库）
    assets_series = [asset_total] * 7
    online_series = [online_total] * 7
    alerts_series = [alert_map.get(str(d), 0) for d in dates]
    tickets_series = [ticket_map.get(str(d), 0) for d in dates]

    return {
        "dates": date_strs,
        "series": {
            "assets": assets_series,
            "online": online_series,
            "alerts": alerts_series,
            "tickets": tickets_series,
        },
    }


# target_type 到前端分类的映射
_ACTIVITY_TYPE_MAP = {
    "asset": "asset",
    "ssh_key": "asset",
    "container": "asset",
    "docker_host": "asset",
    "pod": "asset",
    "deployment": "asset",
    "ticket": "ticket",
    "alert": "alert",
    "alert_event": "alert",
    "patrol": "patrol",
    "user": "user",
    "role": "user",
    "auth": "user",
    "settings": "system",
    "batch_exec": "system",
}

_ACTIVITY_LABEL_MAP = {
    "asset": "资产",
    "ticket": "工单",
    "alert": "告警",
    "patrol": "巡检",
    "user": "用户",
    "system": "系统",
}

_ACTION_MAP = {
    "create": "新增",
    "update": "更新",
    "delete": "删除",
    "login": "登录",
    "logout": "登出",
    "restart": "重启",
    "ssh_key_create": "新增密钥",
    "ssh_key_update": "更新密钥",
    "ssh_key_delete": "删除密钥",
    "ssh_connect": "SSH连接",
    "sftp_upload": "上传文件",
    "sftp_download": "下载文件",
    "sftp_delete": "删除文件",
}


def build_activities(db: Session, limit: int = 20, activity_type: str | None = None) -> list[dict]:
    """从审计日志构建活动时间线数据。"""
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc())

    if activity_type and activity_type != "all":
        # 反查 target_type
        target_types = [k for k, v in _ACTIVITY_TYPE_MAP.items() if v == activity_type]
        if target_types:
            stmt = stmt.where(AuditLog.target_type.in_(target_types))

    stmt = stmt.limit(limit)
    rows = db.scalars(stmt).all()

    items = []
    for row in rows:
        act_type = _ACTIVITY_TYPE_MAP.get(row.target_type, "system")
        action_label = _ACTION_MAP.get(row.action, row.action)
        items.append({
            "time": row.created_at.strftime("%Y-%m-%dT%H:%M:%S"),
            "description": f"{action_label} — {row.target_name}" if row.target_name else action_label,
            "detail": row.detail or "",
            "type": act_type,
            "type_label": _ACTIVITY_LABEL_MAP.get(act_type, "其他"),
            "username": row.username or "",
        })

    return items


def build_alert_trend(db: Session) -> dict:
    """返回近 7 天每日告警数量。"""
    today = datetime.now(CHINA_TZ).date()
    dates = [(today - timedelta(days=i)) for i in range(6, -1, -1)]
    date_strs = [d.strftime("%m-%d") for d in dates]

    rows = db.execute(
        select(
            cast(AlertEvent.received_at, Date).label("day"),
            func.count(AlertEvent.id),
        )
        .where(AlertEvent.received_at >= datetime.combine(dates[0], datetime.min.time()))
        .group_by(cast(AlertEvent.received_at, Date))
        .order_by(cast(AlertEvent.received_at, Date))
    ).all()
    count_map = {str(row[0]): row[1] for row in rows}

    return {
        "dates": date_strs,
        "counts": [count_map.get(str(d), 0) for d in dates],
    }
