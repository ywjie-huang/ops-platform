"""Docker Agent 服务层 — 平台主动从 Agent 拉取数据。"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any

import requests
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.container import ContainerCluster, DockerContainer

logger = logging.getLogger(__name__)

# Agent 拉取超时（秒）
PULL_TIMEOUT = 10
# Agent 离线判定（秒）：超过此时间未成功拉取
OFFLINE_TIMEOUT = 60


# ─── Docker 主机管理 ──────────────────────────────────────

def list_docker_hosts(db: Session, *, keyword: str = "") -> list[ContainerCluster]:
    stmt = select(ContainerCluster).where(ContainerCluster.provider == "docker")
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(
            or_(ContainerCluster.name.ilike(like), ContainerCluster.endpoint.ilike(like))
        )
    stmt = stmt.order_by(ContainerCluster.id.desc())
    return list(db.scalars(stmt).all())


def get_docker_host(db: Session, host_id: int) -> ContainerCluster | None:
    host = db.scalar(select(ContainerCluster).where(ContainerCluster.id == host_id))
    if host and host.provider == "docker":
        return host
    return None


def create_docker_host(
    db: Session,
    *,
    name: str,
    endpoint: str,
    description: str = "",
) -> ContainerCluster:
    """创建 Docker 主机，endpoint 格式为 IP:端口。"""
    host = ContainerCluster(
        name=name,
        provider="docker",
        endpoint=endpoint.strip(),
        description=description,
    )
    db.add(host)
    db.commit()
    db.refresh(host)
    return host


def update_docker_host(db: Session, host: ContainerCluster, **kwargs) -> ContainerCluster:
    for k, v in kwargs.items():
        setattr(host, k, v)
    db.commit()
    db.refresh(host)
    return host


def delete_docker_host(db: Session, host: ContainerCluster) -> None:
    db.delete(host)
    db.commit()


def count_docker_hosts(db: Session) -> int:
    return db.scalar(
        select(func.count(ContainerCluster.id)).where(ContainerCluster.provider == "docker")
    ) or 0


def is_host_online(host: ContainerCluster) -> bool:
    """判断主机是否在线（基于最后成功拉取时间）。"""
    if not host.last_heartbeat:
        return False
    return (datetime.now(timezone.utc) - host.last_heartbeat).total_seconds() < OFFLINE_TIMEOUT


# ─── 从 Agent 拉取数据 ────────────────────────────────────

def pull_from_agent(host: ContainerCluster) -> dict[str, Any] | None:
    """
    从 Agent 拉取快照数据。

    返回 {"host_info": {...}, "containers": [...], "collected_at": float} 或 None。
    """
    agent_url = host.endpoint
    if not agent_url:
        return None

    # 自动补协议
    if not agent_url.startswith("http"):
        agent_url = f"http://{agent_url}"

    try:
        resp = requests.get(f"{agent_url}/snapshot", timeout=PULL_TIMEOUT)
        if resp.status_code == 200:
            return resp.json()
    except requests.RequestException as e:
        logger.debug("拉取 Agent %s 失败: %s", host.name, e)

    return None


def sync_host_from_agent(db: Session, host: ContainerCluster) -> bool:
    """
    从 Agent 拉取数据并同步到数据库。

    返回是否成功。
    """
    data = pull_from_agent(host)
    if not data:
        return False

    now = datetime.now(timezone.utc)
    host_info = data.get("host_info", {})
    containers_data = data.get("containers", [])

    # 更新主机信息
    host.last_heartbeat = now
    host.status = "running"
    host.status_message = ""
    if host_info.get("os"):
        host.host_os = host_info["os"]
    if host_info.get("ip"):
        host.host_ip = host_info["ip"]
    if host_info.get("docker_version"):
        host.docker_version = host_info["docker_version"]

    # 保存主机指标到 agent_key 字段（复用存储，JSON 格式）
    host_metrics = {
        "cpu_count": host_info.get("cpu_count"),
        "memory_total": host_info.get("memory_total"),
        "cpu_percent": host_info.get("cpu_percent"),
        "memory_percent": host_info.get("memory_percent"),
        "disk_usage": host_info.get("disk_usage"),
    }
    host.agent_key = json.dumps(host_metrics)

    # 同步容器数据
    _sync_containers(db, host.id, containers_data)

    db.commit()
    return True


def _sync_containers(db: Session, host_id: int, containers_data: list[dict]) -> None:
    """同步容器列表到数据库。"""
    now = datetime.now(timezone.utc)
    reported_ids = {c["id"][:12] for c in containers_data if c.get("id")}

    # 删除已不存在的容器
    existing = db.scalars(
        select(DockerContainer).where(DockerContainer.host_id == host_id)
    ).all()
    for old in existing:
        if old.container_id not in reported_ids:
            db.delete(old)

    # 更新或创建容器
    for c in containers_data:
        cid = c["id"][:12]
        container = db.scalar(
            select(DockerContainer).where(
                DockerContainer.host_id == host_id,
                DockerContainer.container_id == cid,
            )
        )

        ports_raw = c.get("ports", {})
        ports_str = json.dumps(ports_raw) if isinstance(ports_raw, dict) else str(ports_raw)

        fields = dict(
            name=c.get("name", ""),
            image=c.get("image", ""),
            status=c.get("status", "unknown"),
            state=c.get("state", ""),
            ports=ports_str,
            cpu_percent=c.get("cpu_percent", 0),
            memory_usage=c.get("memory_usage", 0),
            memory_limit=c.get("memory_limit", 0),
            memory_percent=c.get("memory_percent", 0),
            net_rx_bytes=c.get("net_rx_bytes", 0),
            net_tx_bytes=c.get("net_tx_bytes", 0),
            block_read=c.get("block_read", 0),
            block_write=c.get("block_write", 0),
            restart_count=c.get("restart_count", 0),
            started_at=c.get("started_at", ""),
        )

        if container:
            for k, v in fields.items():
                setattr(container, k, v)
            container.updated_at = now
        else:
            db.add(DockerContainer(host_id=host_id, container_id=cid, **fields))


def sync_all_hosts(db: Session) -> None:
    """同步所有 Docker 主机（供后台定时任务调用）。"""
    hosts = list_docker_hosts(db)
    for host in hosts:
        try:
            ok = sync_host_from_agent(db, host)
            if not ok:
                # 拉取失败，标记离线
                if host.last_heartbeat and (datetime.now(timezone.utc) - host.last_heartbeat).total_seconds() > OFFLINE_TIMEOUT:
                    if host.status != "stopped":
                        host.status = "stopped"
                        host.status_message = "Agent 连接失败"
                        db.commit()
        except Exception as e:
            logger.error("同步主机 %s 失败: %s", host.name, e)


# ─── 容器查询 ──────────────────────────────────────────────

def list_docker_containers(
    db: Session,
    *,
    host_id: int | None = None,
    keyword: str = "",
    status: str = "",
) -> list[DockerContainer]:
    stmt = select(DockerContainer)
    if host_id:
        stmt = stmt.where(DockerContainer.host_id == host_id)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(
            or_(DockerContainer.name.ilike(like), DockerContainer.image.ilike(like))
        )
    if status:
        stmt = stmt.where(DockerContainer.status == status)
    stmt = stmt.order_by(DockerContainer.updated_at.desc())
    return list(db.scalars(stmt).all())


def count_docker_containers(db: Session) -> int:
    return db.scalar(select(func.count(DockerContainer.id))) or 0


def count_docker_containers_by_status(db: Session) -> list[tuple[str, int]]:
    rows = db.execute(
        select(DockerContainer.status, func.count(DockerContainer.id))
        .group_by(DockerContainer.status)
    ).all()
    return [(r[0], r[1]) for r in rows]


# ─── 概览统计 ──────────────────────────────────────────────

def docker_overview(db: Session) -> dict[str, Any]:
    hosts = list_docker_hosts(db)
    online = sum(1 for h in hosts if is_host_online(h))
    total_containers = count_docker_containers(db)
    status_counts = dict(count_docker_containers_by_status(db))

    total_cpu = 0
    total_memory_percent = 0.0
    host_count = len(hosts)
    for h in hosts:
        if h.agent_key:
            try:
                metrics = json.loads(h.agent_key)
                total_cpu += metrics.get("cpu_count", 0)
                total_memory_percent += metrics.get("memory_percent", 0)
            except (json.JSONDecodeError, TypeError):
                pass

    return {
        "host_total": host_count,
        "host_online": online,
        "container_total": total_containers,
        "container_running": status_counts.get("running", 0),
        "container_exited": status_counts.get("exited", 0),
        "container_paused": status_counts.get("paused", 0),
        "total_cpu_cores": total_cpu,
        "avg_memory_percent": round(total_memory_percent / host_count, 1) if host_count else 0,
    }
