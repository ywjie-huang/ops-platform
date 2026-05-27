"""AI 工具定义 — schema + handler 函数。"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.alert_event import AlertEvent
from app.models.asset import Asset
from app.models.patrol import PatrolReport
from app.models.ticket import Ticket

logger = logging.getLogger(__name__)

# ─── OpenAI function calling 格式的工具 schema ──────────────

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "query_assets",
            "description": "查询服务器/资产列表。可按关键词（名称、IP）、状态过滤。返回资产 ID、名称、IP、状态等信息。",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "搜索关键词，匹配名称或 IP",
                    },
                    "status": {
                        "type": "string",
                        "description": "资产状态过滤：使用中、已关机、已删除",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_host_metrics",
            "description": "查询指定服务器的实时性能指标（CPU、内存、磁盘、网络、负载）。需要 asset_id，可通过 query_assets 获取。",
            "parameters": {
                "type": "object",
                "properties": {
                    "asset_id": {
                        "type": "integer",
                        "description": "资产 ID",
                    },
                },
                "required": ["asset_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_alerts",
            "description": "查询告警事件列表。可按严重级别过滤。",
            "parameters": {
                "type": "object",
                "properties": {
                    "severity": {
                        "type": "string",
                        "description": "严重级别：critical、warning、info",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回数量，默认 10",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_containers",
            "description": "查询 Docker 容器列表和状态。",
            "parameters": {
                "type": "object",
                "properties": {
                    "host_id": {
                        "type": "integer",
                        "description": "Docker 主机 ID",
                    },
                    "keyword": {
                        "type": "string",
                        "description": "搜索关键词",
                    },
                    "status": {
                        "type": "string",
                        "description": "容器状态过滤：running、stopped 等",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_k8s",
            "description": "查询 Kubernetes 集群状态，包括节点和 Pod 信息。",
            "parameters": {
                "type": "object",
                "properties": {
                    "cluster_id": {
                        "type": "integer",
                        "description": "K8s 集群 ID",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_tickets",
            "description": "查询工单列表和统计。",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "工单状态：open、in_progress、resolved、closed",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回数量，默认 10",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_patrol_reports",
            "description": "查询巡检报告列表。",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "返回数量，默认 5",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "execute_command",
            "description": "在指定服务器上通过 SSH 执行 shell 命令。可用于部署服务、查看日志、管理容器等操作。这是一个写操作，需要用户确认。",
            "parameters": {
                "type": "object",
                "properties": {
                    "asset_id": {
                        "type": "integer",
                        "description": "目标服务器的资产 ID",
                    },
                    "command": {
                        "type": "string",
                        "description": "要执行的 shell 命令",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "超时秒数，默认 30",
                    },
                },
                "required": ["asset_id", "command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_patrol",
            "description": "执行一次全量巡检，检查所有服务器的 CPU、内存、磁盘等指标。这是一个写操作，需要用户确认。",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_ticket",
            "description": "创建一个新工单。这是一个写操作，需要用户确认。",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "工单标题",
                    },
                    "description": {
                        "type": "string",
                        "description": "工单描述",
                    },
                    "priority": {
                        "type": "string",
                        "description": "优先级：low、medium、high、urgent",
                    },
                },
                "required": ["title"],
            },
        },
    },
]

# ─── 只读工具集合 ──────────────────────────────────────────

READONLY_TOOLS = {
    "query_assets",
    "query_host_metrics",
    "query_alerts",
    "query_containers",
    "query_k8s",
    "query_tickets",
    "get_patrol_reports",
}

# ─── 工具 handler 函数映射 ──────────────────────────────────

TOOL_HANDLERS: dict[str, str] = {
    "query_assets": "app.services.ai.tools.handle_query_assets",
    "query_host_metrics": "app.services.ai.tools.handle_query_host_metrics",
    "query_alerts": "app.services.ai.tools.handle_query_alerts",
    "query_containers": "app.services.ai.tools.handle_query_containers",
    "query_k8s": "app.services.ai.tools.handle_query_k8s",
    "query_tickets": "app.services.ai.tools.handle_query_tickets",
    "get_patrol_reports": "app.services.ai.tools.handle_get_patrol_reports",
    "execute_command": "app.services.ai.tools.handle_execute_command",
    "run_patrol": "app.services.ai.tools.handle_run_patrol",
    "create_ticket": "app.services.ai.tools.handle_create_ticket",
}


# ─── 工具 handler 函数 ──────────────────────────────────────


def handle_query_assets(db: Session, args: dict[str, Any]) -> str:
    """查询资产列表。"""
    from app.services.assets import list_assets

    keyword = args.get("keyword", "")
    status = args.get("status", "")
    assets = list_assets(db, keyword=keyword, status=status)

    if not assets:
        return "未找到匹配的资产。"

    lines = [f"共找到 {len(assets)} 台资产："]
    for a in assets[:20]:
        lines.append(f"ID: {a.id}, 名称: {a.name}, IP: {a.ip_address}, 状态: {a.status}, 类型: {a.asset_type or 'N/A'}")
    if len(assets) > 20:
        lines.append(f"... 还有 {len(assets) - 20} 台未显示")
    return "\n".join(lines)


async def handle_query_host_metrics(db: Session, args: dict[str, Any]) -> str:
    """查询单台主机的实时指标。"""
    from app.services.prometheus import get_hosts_summary

    asset_id = args.get("asset_id")
    if not asset_id:
        return "缺少 asset_id 参数。"

    asset = db.get(Asset, asset_id)
    if not asset:
        return f"未找到 ID 为 {asset_id} 的资产。"

    results = await get_hosts_summary([asset], db)
    if not results:
        return f"无法获取 {asset.name}({asset.ip_address}) 的指标数据，请检查 Prometheus 配置和 node_exporter。"

    r = results[0]
    if not r.get("prometheus_ok"):
        return f"{asset.name} ({asset.ip_address}) 未采集到 Prometheus 指标，请检查 node_exporter 是否运行。"

    return (
        f"{asset.name} ({asset.ip_address}) 实时指标：\n"
        f"CPU: {r['cpu']}%, 内存: {r['memory']}%, 磁盘: {r['disk']}%, "
        f"负载: {r['load']}, 网络入: {r['network_in']} Mbps, 网络出: {r['network_out']} Mbps"
    )


def handle_query_alerts(db: Session, args: dict[str, Any]) -> str:
    """查询告警事件。"""
    severity = args.get("severity", "")
    limit = args.get("limit", 10)

    stmt = select(AlertEvent)
    if severity:
        stmt = stmt.where(AlertEvent.severity == severity)
    stmt = stmt.order_by(AlertEvent.id.desc()).limit(limit)

    alerts = list(db.scalars(stmt).all())
    if not alerts:
        return "没有告警事件。"

    lines = [f"最近 {len(alerts)} 条告警："]
    for a in alerts:
        lines.append(f"[{a.severity}] {a.alert_name}, 实例: {a.instance or 'N/A'}, 状态: {a.status}")
    return "\n".join(lines)


def handle_query_containers(db: Session, args: dict[str, Any]) -> str:
    """查询 Docker 容器。"""
    from app.services.docker_agent import list_docker_containers

    host_id = args.get("host_id")
    keyword = args.get("keyword", "")
    status = args.get("status", "")

    containers = list_docker_containers(db, host_id=host_id, keyword=keyword, status=status)
    if not containers:
        return "没有找到容器。"

    lines = [f"共 {len(containers)} 个容器："]
    for c in containers[:20]:
        lines.append(f"名称: {c.name}, 镜像: {c.image}, 状态: {c.status}, CPU: {c.cpu_percent}%, 内存: {c.memory_usage}")
    if len(containers) > 20:
        lines.append(f"... 还有 {len(containers) - 20} 个未显示")
    return "\n".join(lines)


def handle_query_k8s(db: Session, args: dict[str, Any]) -> str:
    """查询 K8s 集群状态。"""
    from app.models.container import ContainerCluster
    from app.services.k8s import get_cluster_info

    cluster_id = args.get("cluster_id")

    if cluster_id:
        cluster = db.get(ContainerCluster, cluster_id)
        if not cluster:
            return f"未找到 ID 为 {cluster_id} 的集群。"
        clusters = [cluster]
    else:
        clusters = list(db.scalars(select(ContainerCluster)).all())

    if not clusters:
        return "暂未接入 K8s 集群。"

    lines = []
    for c in clusters:
        if not c.agent_key:
            lines.append(f"{c.name}: 未配置 token，跳过")
            continue
        info = get_cluster_info(c.api_endpoint or "", c.agent_key)
        status = "正常" if info.get("ok") else "异常"
        lines.append(f"{c.name}: {status}")
        if info.get("nodes"):
            for n in info["nodes"][:5]:
                lines.append(f"  节点 {n.get('name', '?')}: {n.get('status', '?')}")
        if info.get("pods_failed"):
            lines.append(f"  {info['pods_failed']} 个 Pod 异常")
    return "\n".join(lines)


def handle_query_tickets(db: Session, args: dict[str, Any]) -> str:
    """查询工单。"""
    status = args.get("status", "")
    limit = args.get("limit", 10)

    stmt = select(Ticket)
    if status:
        stmt = stmt.where(Ticket.status == status)
    stmt = stmt.order_by(Ticket.id.desc()).limit(limit)

    tickets = list(db.scalars(stmt).all())
    if not tickets:
        return "没有工单记录。"

    lines = [f"最近 {len(tickets)} 个工单："]
    for t in tickets:
        lines.append(f"[{t.priority}] {t.title}, 状态: {t.status}, 负责人: {t.assignee or '未分配'}")
    return "\n".join(lines)


def handle_get_patrol_reports(db: Session, args: dict[str, Any]) -> str:
    """查询巡检报告。"""
    limit = args.get("limit", 5)
    reports = list(db.scalars(
        select(PatrolReport).order_by(PatrolReport.id.desc()).limit(limit)
    ).all())

    if not reports:
        return "暂无巡检报告。"

    lines = [f"最近 {len(reports)} 份巡检报告："]
    for r in reports:
        time_str = r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "N/A"
        lines.append(f"{r.title}, 状态: {r.status}, 正常: {r.normal_count}, 警告: {r.warning_count}, 严重: {r.critical_count}, 时间: {time_str}")
    return "\n".join(lines)


def handle_execute_command(db: Session, args: dict[str, Any]) -> str:
    """在服务器上执行命令（写操作）。"""
    from app.services.batch_exec import _ssh_exec
    from app.api.ssh_common import _build_ssh_client

    asset_id = args.get("asset_id")
    command = args.get("command", "")
    timeout = args.get("timeout", 30)

    if not asset_id or not command:
        return "缺少 asset_id 或 command 参数。"

    asset = db.get(Asset, asset_id)
    if not asset:
        return f"未找到 ID 为 {asset_id} 的资产。"

    if not asset.ssh_password and not asset.ssh_key_id:
        return f"资产 {asset.name} 未配置 SSH 凭据，无法执行命令。"

    # 测试 SSH 连接
    try:
        ssh_client, username, hostname = _build_ssh_client(asset, {
            "key_id": asset.ssh_key_id,
            "port": asset.ssh_port or 22,
            "username": asset.ssh_username or "root",
            "password": asset.ssh_password,
        })
        ssh_client.close()
    except Exception as e:
        return f"SSH 连接失败: {e}"

    result = _ssh_exec(
        host=asset.ip_address,
        port=asset.ssh_port or 22,
        username=asset.ssh_username or "root",
        password=asset.ssh_password or "",
        command=command,
        timeout=timeout,
    )

    lines = [f"在 {asset.name} ({asset.ip_address}) 上执行: {command}"]
    if result["ok"]:
        lines.append(f"退出码: {result['exit_code']}")
        if result["stdout"]:
            lines.append(f"输出:\n{result['stdout'][:3000]}")
        if result["stderr"]:
            lines.append(f"错误输出:\n{result['stderr'][:1000]}")
    else:
        lines.append(f"执行失败: {result['stderr']}")

    return "\n".join(lines)


async def handle_run_patrol(db: Session, args: dict[str, Any]) -> str:
    """执行全量巡检（写操作）。"""
    from app.services.patrol import run_patrol

    report = await run_patrol(db, operator="AI助手")
    db.commit()

    return (
        f"巡检完成，状态: {report.status}\n"
        f"正常: {report.normal_count}, 警告: {report.warning_count}, 严重: {report.critical_count}\n"
        f"报告 ID: {report.id}，可在巡检中心查看详情。"
    )


def handle_create_ticket(db: Session, args: dict[str, Any]) -> str:
    """创建工单（写操作）。"""
    title = args.get("title", "")
    if not title:
        return "工单标题不能为空。"

    ticket = Ticket(
        title=title,
        description=args.get("description", ""),
        priority=args.get("priority", "medium"),
        status="open",
    )
    db.add(ticket)
    db.flush()

    return f"工单已创建: #{ticket.id} {title}, 优先级: {ticket.priority}"
