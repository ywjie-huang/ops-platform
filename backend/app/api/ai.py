"""
AI 运维助手 API
当前为 stub 实现，预留 LLM 接口。
对接 LLM 后，可通过 function calling 调用运维 API 获取实时数据。
"""

from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_api_user
from app.db.database import get_db
from app.models.alert import Alert
from app.models.alert_event import AlertEvent
from app.models.asset import Asset
from app.models.ticket import Ticket
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI 助手"])


class ChatRequest(BaseModel):
    message: str
    conversation_id: str = ""


@router.post("/chat")
def api_chat(
    body: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_api_user),
):
    """
    AI 对话接口。
    当前为基于关键词的 stub 实现，后续对接 LLM API。
    """
    msg = body.message.strip()
    if not msg:
        return {"code": 0, "data": {"reply": "请输入你的问题。"}}

    reply = _handle_query(db, msg)
    return {"code": 0, "data": {"reply": reply, "conversation_id": body.conversation_id or "default"}}


# ─── 基于关键词的 stub 实现 ────────────────────────────────


def _handle_query(db: Session, msg: str) -> str:
    """根据关键词路由到对应的查询逻辑。"""

    # 告警相关
    if any(kw in msg for kw in ["告警", "报警", "alert"]):
        return _query_alerts(db, msg)

    # 资产/服务器相关
    if any(kw in msg for kw in ["服务器", "主机", "资产", "server", "host"]):
        return _query_assets(db, msg)

    # 工单相关
    if any(kw in msg for kw in ["工单", "ticket"]):
        return _query_tickets(db, msg)

    # K8s/容器相关
    if any(kw in msg for kw in ["k8s", "kubernetes", "集群", "容器", "pod", "container"]):
        return _query_k8s(db, msg)

    # 巡检相关
    if any(kw in msg for kw in ["巡检", "检查", "patrol", "巡检"]):
        return _query_patrol(db)

    # 资源异常
    if any(kw in msg for kw in ["异常", "问题", "故障", "error"]):
        return _query_abnormal(db)

    # 默认回复
    return (
        "我可以帮你查询以下信息：\n\n"
        "**告警** — 最近的告警事件和状态\n"
        "**服务器** — 资产列表和在线状态\n"
        "**工单** — 工单统计和待处理工单\n"
        "**K8s** — 集群和容器状态\n"
        "**巡检** — 最近的巡检报告\n\n"
        "试试问我：「最近有什么告警？」或「哪台服务器资源异常？」"
    )


def _query_alerts(db: Session, msg: str) -> str:
    """查询告警信息。"""
    # 最近告警事件
    total = db.scalar(select(func.count(AlertEvent.id))) or 0
    if total == 0:
        return "目前没有告警事件记录。系统运行正常 ✅"

    # 按严重程度统计
    severity_stats = db.execute(
        select(AlertEvent.severity, func.count(AlertEvent.id))
        .group_by(AlertEvent.severity)
    ).all()

    # 最近 5 条
    recent = list(db.scalars(
        select(AlertEvent).order_by(AlertEvent.id.desc()).limit(5)
    ).all())

    lines = [f"📊 **告警概况**（共 {total} 条）\n"]
    for sev, count in severity_stats:
        emoji = {"critical": "🔴", "warning": "🟡", "info": "🔵"}.get(sev, "⚪")
        lines.append(f"- {emoji} {sev}：{count} 条")

    lines.append(f"\n📋 **最近告警：**")
    for e in recent:
        lines.append(f"- [{e.severity}] {e.alert_name} — {e.instance or 'N/A'}（{e.status}）")

    return "\n".join(lines)


def _query_assets(db: Session, msg: str) -> str:
    """查询资产信息。"""
    total = db.scalar(select(func.count(Asset.id))) or 0
    if total == 0:
        return "暂无资产记录。"

    online = db.scalar(select(func.count(Asset.id)).where(Asset.status == "使用中")) or 0
    offline = db.scalar(select(func.count(Asset.id)).where(Asset.status == "已关机")) or 0

    lines = [
        f"🖥️ **资产概况**（共 {total} 台）\n",
        f"- ✅ 使用中：{online} 台",
        f"- ⚪ 已关机：{offline} 台",
    ]

    # 如果问的是"异常"或"离线"
    if any(kw in msg for kw in ["异常", "离线", "关机", "offline"]):
        offline_assets = list(db.scalars(
            select(Asset).where(Asset.status != "使用中")
        ).all())
        if offline_assets:
            lines.append(f"\n⚠️ **异常资产：**")
            for a in offline_assets:
                lines.append(f"- {a.name}（{a.ip_address}）— {a.status}")
        else:
            lines.append("\n✅ 所有资产状态正常")

    return "\n".join(lines)


def _query_tickets(db: Session, msg: str) -> str:
    """查询工单信息。"""
    total = db.scalar(select(func.count(Ticket.id))) or 0
    if total == 0:
        return "暂无工单记录。"

    open_count = db.scalar(select(func.count(Ticket.id)).where(Ticket.status == "open")) or 0
    in_progress = db.scalar(select(func.count(Ticket.id)).where(Ticket.status == "in_progress")) or 0

    lines = [
        f"📝 **工单概况**（共 {total} 个）\n",
        f"- 📋 待处理：{open_count} 个",
        f"- 🔧 处理中：{in_progress} 个",
    ]

    if open_count > 0:
        open_tickets = list(db.scalars(
            select(Ticket).where(Ticket.status == "open").order_by(Ticket.id.desc()).limit(5)
        ).all())
        lines.append(f"\n📋 **待处理工单：**")
        for t in open_tickets:
            lines.append(f"- [{t.priority}] {t.title} — {t.assignee or '未分配'}")

    return "\n".join(lines)


def _query_k8s(db: Session, msg: str) -> str:
    """查询 K8s 集群信息。"""
    from app.models.container import ContainerCluster
    clusters = list(db.scalars(select(ContainerCluster)).all())
    if not clusters:
        return "暂未接入 K8s 集群。请在「容器管理」中接入集群。"

    lines = [f"☸️ **K8s 集群概况**（共 {len(clusters)} 个）\n"]
    for c in clusters:
        status_emoji = "✅" if c.status == "running" else "❌"
        lines.append(f"- {status_emoji} **{c.name}** — {c.version or '未知版本'}，{c.node_count} 个节点（{c.status}）")

    return "\n".join(lines)


def _query_patrol(db: Session) -> str:
    """查询最近巡检报告。"""
    from app.models.patrol import PatrolReport
    report = db.scalar(select(PatrolReport).order_by(PatrolReport.id.desc()))
    if not report:
        return "暂无巡检报告。请在「巡检中心」中执行巡检。"

    status_emoji = {"normal": "✅", "warning": "⚠️", "critical": "🔴"}.get(report.status, "❓")
    return (
        f"🔍 **最近巡检报告**\n\n"
        f"- 标题：{report.title}\n"
        f"- 状态：{status_emoji} {report.status}\n"
        f"- 正常：{report.normal_count}，警告：{report.warning_count}，严重：{report.critical_count}\n"
        f"- 时间：{report.created_at.strftime('%Y-%m-%d %H:%M') if report.created_at else 'N/A'}\n"
        f"- 操作人：{report.operator or '系统'}"
    )


def _query_abnormal(db: Session) -> str:
    """综合查询异常信息。"""
    parts = []

    # 异常资产
    offline = db.scalar(select(func.count(Asset.id)).where(Asset.status != "使用中")) or 0
    if offline:
        parts.append(f"🖥️ {offline} 台资产非在线状态")

    # 最近告警
    alert_count = db.scalar(select(func.count(AlertEvent.id))) or 0
    if alert_count:
        parts.append(f"🔔 共 {alert_count} 条告警事件")

    # 待处理工单
    open_tickets = db.scalar(select(func.count(Ticket.id)).where(Ticket.status == "open")) or 0
    if open_tickets:
        parts.append(f"📝 {open_tickets} 个待处理工单")

    if not parts:
        return "✅ 系统一切正常，没有发现异常。"

    return "⚠️ **发现以下异常：**\n\n" + "\n".join(f"- {p}" for p in parts)
