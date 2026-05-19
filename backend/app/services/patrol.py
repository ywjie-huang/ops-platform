"""
巡检服务
执行巡检检查，生成报告。
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.patrol import PatrolItem, PatrolReport
from app.services.k8s import get_cluster_info
from app.services.prometheus import get_hosts_summary

logger = logging.getLogger(__name__)


def _get_thresholds(db: Session) -> dict[str, float]:
    """从 DB 读取巡检阈值，未配置则使用硬编码默认值。"""
    from app.core.settings import get_config_float
    return {
        "cpu_warning": get_config_float(db, "patrol.cpu_warning"),
        "cpu_critical": get_config_float(db, "patrol.cpu_critical"),
        "memory_warning": get_config_float(db, "patrol.memory_warning"),
        "memory_critical": get_config_float(db, "patrol.memory_critical"),
        "disk_warning": get_config_float(db, "patrol.disk_warning"),
        "disk_critical": get_config_float(db, "patrol.disk_critical"),
        "load_warning": get_config_float(db, "patrol.load_warning"),
        "load_critical": get_config_float(db, "patrol.load_critical"),
    }


# ─── 巡检执行 ───────────────────────────────────────────────


async def run_patrol(db: Session, operator: str = "") -> PatrolReport:
    """执行一次完整巡检，返回报告。"""
    items: list[dict[str, Any]] = []
    thresholds = _get_thresholds(db)

    # 1. 主机巡检（Prometheus）
    host_items = await _check_hosts(db, thresholds)
    items.extend(host_items)

    # 2. K8s 集群巡检
    k8s_items = _check_k8s_clusters(db)
    items.extend(k8s_items)

    # 3. 资产状态巡检
    asset_items = _check_assets(db)
    items.extend(asset_items)

    # 统计
    normal = sum(1 for i in items if i["status"] == "normal")
    warning = sum(1 for i in items if i["status"] == "warning")
    critical = sum(1 for i in items if i["status"] == "critical")

    # 确定总体状态
    if critical > 0:
        report_status = "critical"
    elif warning > 0:
        report_status = "warning"
    else:
        report_status = "normal"

    # 生成摘要
    summary_parts = []
    if critical > 0:
        summary_parts.append(f"严重问题 {critical} 项")
    if warning > 0:
        summary_parts.append(f"警告 {warning} 项")
    if normal > 0:
        summary_parts.append(f"正常 {normal} 项")
    summary = "，".join(summary_parts) if summary_parts else "无巡检项"

    # 保存报告
    report = PatrolReport(
        title=f"巡检报告 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        status=report_status,
        total_checks=len(items),
        normal_count=normal,
        warning_count=warning,
        critical_count=critical,
        summary=summary,
        operator=operator,
    )
    db.add(report)
    db.flush()

    # 保存巡检项
    for item_data in items:
        item = PatrolItem(
            report_id=report.id,
            category=item_data["category"],
            target_name=item_data["target_name"],
            target_ip=item_data.get("target_ip", ""),
            check_name=item_data["check_name"],
            status=item_data["status"],
            value=item_data.get("value", ""),
            threshold=item_data.get("threshold", ""),
            detail=item_data.get("detail", ""),
        )
        db.add(item)

    db.commit()
    db.refresh(report)
    return report


# ─── 主机巡检 ───────────────────────────────────────────────


async def _check_hosts(db: Session, thresholds: dict[str, float]) -> list[dict[str, Any]]:
    """通过 Prometheus 检查所有主机指标。"""
    items = []
    assets = list(db.scalars(select(Asset).where(Asset.status == "使用中")).all())
    if not assets:
        return items

    try:
        summaries = await get_hosts_summary(assets, db)
    except Exception as e:
        logger.error("Patrol host check failed: %s", e)
        return items

    for s in summaries:
        name = s.get("name", "unknown")
        ip = s.get("ip_address", "")

        if not s.get("prometheus_ok"):
            items.append({
                "category": "host", "target_name": name, "target_ip": ip,
                "check_name": "Prometheus 连接", "status": "warning",
                "value": "无法连接", "detail": "该主机未被 Prometheus 采集或无法连接",
            })
            continue

        # CPU
        cpu = s.get("cpu", 0)
        items.append(_make_check("host", name, ip, "CPU 使用率", cpu, "%",
                                 thresholds["cpu_warning"], thresholds["cpu_critical"]))

        # 内存
        mem = s.get("memory", 0)
        items.append(_make_check("host", name, ip, "内存使用率", mem, "%",
                                 thresholds["memory_warning"], thresholds["memory_critical"]))

        # 磁盘
        disk = s.get("disk", 0)
        items.append(_make_check("host", name, ip, "磁盘使用率", disk, "%",
                                 thresholds["disk_warning"], thresholds["disk_critical"]))

        # 负载
        load = s.get("load", 0)
        items.append(_make_check("host", name, ip, "系统负载", load, "",
                                 thresholds["load_warning"], thresholds["load_critical"]))

    return items


# ─── K8s 集群巡检 ───────────────────────────────────────────


def _check_k8s_clusters(db: Session) -> list[dict[str, Any]]:
    """检查 K8s 集群状态。"""
    from app.models.container import ContainerCluster
    items = []

    clusters = list(db.scalars(select(ContainerCluster).where(ContainerCluster.token != "")).all())
    for cluster in clusters:
        try:
            info = get_cluster_info(cluster.endpoint, cluster.token)
        except Exception as e:
            items.append({
                "category": "k8s", "target_name": cluster.name,
                "check_name": "集群连接", "status": "critical",
                "value": "连接失败", "detail": str(e),
            })
            continue

        if not info.get("connected"):
            items.append({
                "category": "k8s", "target_name": cluster.name,
                "check_name": "集群连接", "status": "critical",
                "value": "断开", "detail": info.get("error", ""),
            })
            continue

        # 节点状态
        nodes = info.get("nodes", [])
        not_ready = [n for n in nodes if n.get("status") != "Ready"]
        if not_ready:
            names = ", ".join(n["name"] for n in not_ready)
            items.append({
                "category": "k8s", "target_name": cluster.name,
                "check_name": "节点状态", "status": "critical",
                "value": f"{len(not_ready)} 个 NotReady",
                "detail": f"异常节点: {names}",
            })
        else:
            items.append({
                "category": "k8s", "target_name": cluster.name,
                "check_name": "节点状态", "status": "normal",
                "value": f"{len(nodes)} 个节点全部 Ready",
            })

        # 异常 Pod
        pods = info.get("pods", [])
        failed_pods = [p for p in pods if p.get("status") in ("Failed", "Unknown")]
        pending_pods = [p for p in pods if p.get("status") == "Pending"]
        high_restart_pods = [p for p in pods if p.get("restarts", 0) > 5]

        if failed_pods:
            names = ", ".join(p["name"] for p in failed_pods[:5])
            items.append({
                "category": "k8s", "target_name": cluster.name,
                "check_name": "异常 Pod", "status": "critical",
                "value": f"{len(failed_pods)} 个 Pod 异常",
                "detail": f"Failed/Unknown: {names}",
            })

        if pending_pods:
            items.append({
                "category": "k8s", "target_name": cluster.name,
                "check_name": "等待中 Pod", "status": "warning",
                "value": f"{len(pending_pods)} 个 Pod Pending",
            })

        if high_restart_pods:
            names = ", ".join(p["name"] for p in high_restart_pods[:5])
            items.append({
                "category": "k8s", "target_name": cluster.name,
                "check_name": "频繁重启 Pod", "status": "warning",
                "value": f"{len(high_restart_pods)} 个 Pod 重启 > 5 次",
                "detail": f"Pod: {names}",
            })

        # 集群资源概览
        ready_nodes = info.get("ready_nodes", 0)
        total_nodes = info.get("node_count", 0)
        items.append({
            "category": "k8s", "target_name": cluster.name,
            "check_name": "集群概览", "status": "normal",
            "value": f"{ready_nodes}/{total_nodes} 节点就绪，{info.get('pod_count', 0)} Pods，{info.get('deployment_count', 0)} Deployments",
        })

    return items


# ─── 资产状态巡检 ───────────────────────────────────────────


def _check_assets(db: Session) -> list[dict[str, Any]]:
    """检查资产状态。"""
    items = []
    assets = list(db.scalars(select(Asset)).all())

    online = sum(1 for a in assets if a.status == "使用中")
    offline = sum(1 for a in assets if a.status == "已关机")
    deleted = sum(1 for a in assets if a.status == "已删除")

    # 资产总览
    items.append({
        "category": "asset", "target_name": "资产总览",
        "check_name": "资产统计", "status": "normal",
        "value": f"共 {len(assets)} 台：使用中 {online}，已关机 {offline}，已删除 {deleted}",
    })

    # 已关机资产（警告）
    for a in assets:
        if a.status == "已关机":
            items.append({
                "category": "asset", "target_name": a.name, "target_ip": a.ip_address,
                "check_name": "资产状态", "status": "warning",
                "value": "已关机", "detail": f"负责人: {a.owner or '未分配'}",
            })

    return items


# ─── 工具函数 ───────────────────────────────────────────────


def _make_check(category: str, target: str, ip: str, check: str,
                value: float, unit: str, warn: float, crit: float) -> dict:
    """根据阈值生成巡检项。"""
    if value >= crit:
        status = "critical"
    elif value >= warn:
        status = "warning"
    else:
        status = "normal"

    return {
        "category": category, "target_name": target, "target_ip": ip,
        "check_name": check, "status": status,
        "value": f"{value}{unit}",
        "threshold": f"警告 ≥{warn}{unit}，严重 ≥{crit}{unit}",
    }


# ─── 查询 ───────────────────────────────────────────────────


def list_reports(db: Session, *, status: str = "", limit: int = 50, offset: int = 0) -> tuple[list[PatrolReport], int]:
    """查询巡检报告列表。"""
    stmt = select(PatrolReport)
    count_stmt = select(PatrolReport)

    if status:
        stmt = stmt.where(PatrolReport.status == status)
        count_stmt = count_stmt.where(PatrolReport.status == status)

    total = db.scalar(select(func.count()).select_from(count_stmt.subquery())) or 0
    stmt = stmt.order_by(PatrolReport.id.desc()).offset(offset).limit(limit)
    items = list(db.scalars(stmt).all())
    return items, total


def get_report(db: Session, report_id: int) -> PatrolReport | None:
    return db.scalar(select(PatrolReport).where(PatrolReport.id == report_id))


def get_report_items(db: Session, report_id: int) -> list[PatrolItem]:
    return list(db.scalars(
        select(PatrolItem).where(PatrolItem.report_id == report_id).order_by(
            PatrolItem.status.desc(), PatrolItem.id.asc()
        )
    ).all())


def delete_report(db: Session, report: PatrolReport) -> None:
    # 先删关联项
    items = db.scalars(select(PatrolItem).where(PatrolItem.report_id == report.id)).all()
    for item in items:
        db.delete(item)
    db.delete(report)
    db.commit()
