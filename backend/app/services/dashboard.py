"""仪表盘数据构建服务。"""
from datetime import datetime, timedelta

from sqlalchemy import func, select, cast, Date
from sqlalchemy.orm import Session

from app.models.alert_event import AlertEvent
from app.models.asset import Asset
from app.models.ticket import Ticket
from app.models.dashboard import (
    DashboardActivityItem,
    DashboardDistributionItem,
    DashboardQuickStat,
    DashboardStats,
    DashboardSummary,
    DashboardTypeBreakdown,
)
from app.services.alerts import count_pending_alerts, list_alerts
from app.services.assets import count_assets_by_status, count_assets_by_type, list_assets, list_recent_assets
from app.services.roles import count_users_by_role, list_roles
from app.services.tickets import count_open_tickets, list_tickets
from app.services.users import count_new_users_since, list_recent_users, list_users


def _format_ratio(numerator: int, denominator: int) -> str:
    if denominator <= 0:
        return "0%"
    return f"{round(numerator / denominator * 100)}%"


def build_dashboard_stats(db: Session) -> DashboardStats:
    assets = list_assets(db)
    users = list_users(db)
    roles = list_roles(db)
    status_counts = count_assets_by_status(db)
    return DashboardStats(
        asset_total=len(assets),
        online_hosts=status_counts.get("使用中", 0),
        open_alerts=count_pending_alerts(db),
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
    pending_alerts = count_pending_alerts(db)

    quick_stats = [
        DashboardQuickStat("在线率", _format_ratio(status_counts.get("使用中", 0), total_assets), "按资产状态实时统计", "green"),
        DashboardQuickStat("待处理工单", str(open_tickets), "包含 open 和 in_progress 状态", "blue" if open_tickets == 0 else "orange"),
        DashboardQuickStat("待处理告警", str(pending_alerts), "包含待确认和已确认告警", "green" if pending_alerts == 0 else "red"),
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

    recent_alerts_list = list_alerts(db)[:5]
    ALERT_TONES = {"pending": "red", "confirmed": "orange", "resolved": "green", "ignored": "default"}
    alert_items = [
        DashboardActivityItem(
            title=a.title,
            meta=f"{a.level} · {a.source or '未知来源'} · {a.created_at.strftime('%Y-%m-%d %H:%M')}",
            detail=a.description[:80] + "..." if len(a.description) > 80 else a.description,
            tag=a.status,
            tone=ALERT_TONES.get(a.status, "default"),
        )
        for a in recent_alerts_list
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
    today = datetime.utcnow().date()
    dates = [(today - timedelta(days=i)) for i in range(6, -1, -1)]
    date_strs = [d.strftime("%m-%d") for d in dates]

    # 资产总数（取每天的总量，无 created_at 按天分组则用当前总量）
    asset_total = db.scalar(select(func.count(Asset.id))) or 0

    # 在线主机数（状态为"使用中"）
    online_total = db.scalar(
        select(func.count(Asset.id)).where(Asset.status == "使用中")
    ) or 0

    # 告警：近 7 天每日新增告警数（alert_events 表）
    alert_rows = db.scalars(
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
    ticket_rows = db.scalars(
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
