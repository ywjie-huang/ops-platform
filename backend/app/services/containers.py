"""
容器管理服务层
K8s 集群 CRUD + 集群列表运行态摘要（实时资源读取走 services/k8s.py）。

注：早期「用 MySQL 模拟 K8s 资源」的 Deployment/Pod/Service CRUD 已移除——
K8s API 端点现在全部实时读取，这些表不再写入。cluster_runtime_summary 仍查询
ContainerPod/ContainerDeployment 做轻量摘要（当前通常为空）。
"""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.container import (
    ContainerCluster,
    ContainerDeployment,
    ContainerPod,
)
from app.services.k8s import test_connection


# ─── Clusters ───────────────────────────────────────────────


def list_clusters(db: Session, *, keyword: str = "") -> list[ContainerCluster]:
    stmt = select(ContainerCluster).where(ContainerCluster.provider == "kubernetes")
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(
            or_(ContainerCluster.name.ilike(like), ContainerCluster.endpoint.ilike(like))
        )
    stmt = stmt.order_by(ContainerCluster.id.desc())
    return list(db.scalars(stmt).all())


def refresh_cluster_connection_status(db: Session, cluster: ContainerCluster) -> None:
    if not cluster.token:
        cluster.status = "stopped"
        cluster.status_message = "Token is not configured"
        return

    info = test_connection(cluster.endpoint, cluster.token)
    if info.get("ok"):
        cluster.status = "running"
        cluster.status_message = ""
        if info.get("version"):
            cluster.version = info["version"]
    else:
        cluster.status = "stopped"
        cluster.status_message = info.get("error", "Connection failed")


def cluster_runtime_summary(db: Session, cluster_id: int) -> dict[str, int]:
    pod_rows = db.execute(
        select(ContainerPod.status, func.count(ContainerPod.id))
        .where(ContainerPod.cluster_id == cluster_id)
        .group_by(ContainerPod.status)
    ).all()
    abnormal_pod_count = sum(count for status, count in pod_rows if status not in {"Running", "Succeeded"})

    deployment_rows = db.execute(
        select(ContainerDeployment.replicas, ContainerDeployment.ready_replicas)
        .where(ContainerDeployment.cluster_id == cluster_id)
    ).all()
    deployment_gap_count = sum(1 for replicas, ready_replicas in deployment_rows if (ready_replicas or 0) < (replicas or 0))

    return {
        "abnormal_pod_count": abnormal_pod_count,
        "deployment_gap_count": deployment_gap_count,
    }


def find_clusters_by_name(db: Session, name: str) -> list[ContainerCluster]:
    return list(db.scalars(
        select(ContainerCluster).where(
            ContainerCluster.name == name,
            ContainerCluster.provider == "kubernetes",
        )
    ).all())


def cluster_name_exists(db: Session, name: str, *, exclude_id: int | None = None) -> bool:
    stmt = select(ContainerCluster.id).where(
        ContainerCluster.name == name,
        ContainerCluster.provider == "kubernetes",
    )
    if exclude_id is not None:
        stmt = stmt.where(ContainerCluster.id != exclude_id)
    return db.scalar(stmt.limit(1)) is not None


def create_cluster(db: Session, **kwargs) -> ContainerCluster:
    obj = ContainerCluster(**kwargs)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_cluster(db: Session, obj: ContainerCluster, **kwargs) -> ContainerCluster:
    for k, v in kwargs.items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


def delete_cluster(db: Session, obj: ContainerCluster) -> None:
    db.delete(obj)
    db.commit()


def count_pods_by_status(db: Session) -> list[tuple[str, int]]:
    rows = db.execute(
        select(ContainerPod.status, func.count(ContainerPod.id)).group_by(ContainerPod.status)
    ).all()
    return [(r[0], r[1]) for r in rows]
