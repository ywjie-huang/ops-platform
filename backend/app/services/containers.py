"""
容器管理服务层
模拟 K8s / Docker 资源管理（数据存储在 MySQL）。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.container import (
    ContainerCluster,
    ContainerDeployment,
    ContainerPod,
    ContainerService,
)


# ─── Clusters ───────────────────────────────────────────────


def list_clusters(db: Session, *, keyword: str = "") -> list[ContainerCluster]:
    stmt = select(ContainerCluster)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(
            or_(ContainerCluster.name.ilike(like), ContainerCluster.provider.ilike(like))
        )
    stmt = stmt.order_by(ContainerCluster.id.desc())
    return list(db.scalars(stmt).all())


def get_cluster(db: Session, cluster_id: int) -> ContainerCluster | None:
    return db.scalar(select(ContainerCluster).where(ContainerCluster.id == cluster_id))


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


def count_clusters(db: Session) -> int:
    return db.scalar(select(func.count(ContainerCluster.id))) or 0


# ─── Deployments ────────────────────────────────────────────


def list_deployments(db: Session, *, keyword: str = "", cluster_id: int | None = None) -> list[ContainerDeployment]:
    stmt = select(ContainerDeployment)
    if keyword:
        stmt = stmt.where(ContainerDeployment.name.ilike(f"%{keyword}%"))
    if cluster_id:
        stmt = stmt.where(ContainerDeployment.cluster_id == cluster_id)
    stmt = stmt.order_by(ContainerDeployment.id.desc())
    return list(db.scalars(stmt).all())


def get_deployment(db: Session, dep_id: int) -> ContainerDeployment | None:
    return db.scalar(select(ContainerDeployment).where(ContainerDeployment.id == dep_id))


def create_deployment(db: Session, **kwargs) -> ContainerDeployment:
    obj = ContainerDeployment(**kwargs)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_deployment(db: Session, obj: ContainerDeployment, **kwargs) -> ContainerDeployment:
    for k, v in kwargs.items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


def delete_deployment(db: Session, obj: ContainerDeployment) -> None:
    db.delete(obj)
    db.commit()


# ─── Pods ───────────────────────────────────────────────────


def list_pods(db: Session, *, keyword: str = "", cluster_id: int | None = None, status: str = "") -> list[ContainerPod]:
    stmt = select(ContainerPod)
    if keyword:
        stmt = stmt.where(ContainerPod.name.ilike(f"%{keyword}%"))
    if cluster_id:
        stmt = stmt.where(ContainerPod.cluster_id == cluster_id)
    if status:
        stmt = stmt.where(ContainerPod.status == status)
    stmt = stmt.order_by(ContainerPod.id.desc())
    return list(db.scalars(stmt).all())


def get_pod(db: Session, pod_id: int) -> ContainerPod | None:
    return db.scalar(select(ContainerPod).where(ContainerPod.id == pod_id))


def create_pod(db: Session, **kwargs) -> ContainerPod:
    obj = ContainerPod(**kwargs)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def delete_pod(db: Session, obj: ContainerPod) -> None:
    db.delete(obj)
    db.commit()


def count_pods_by_status(db: Session) -> list[tuple[str, int]]:
    rows = db.execute(
        select(ContainerPod.status, func.count(ContainerPod.id)).group_by(ContainerPod.status)
    ).all()
    return [(r[0], r[1]) for r in rows]


# ─── Services ───────────────────────────────────────────────


def list_services(db: Session, *, keyword: str = "", cluster_id: int | None = None) -> list[ContainerService]:
    stmt = select(ContainerService)
    if keyword:
        stmt = stmt.where(ContainerService.name.ilike(f"%{keyword}%"))
    if cluster_id:
        stmt = stmt.where(ContainerService.cluster_id == cluster_id)
    stmt = stmt.order_by(ContainerService.id.desc())
    return list(db.scalars(stmt).all())


def get_service(db: Session, svc_id: int) -> ContainerService | None:
    return db.scalar(select(ContainerService).where(ContainerService.id == svc_id))


def create_service(db: Session, **kwargs) -> ContainerService:
    obj = ContainerService(**kwargs)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def delete_service(db: Session, obj: ContainerService) -> None:
    db.delete(obj)
    db.commit()


# ─── Stats ──────────────────────────────────────────────────


def container_overview(db: Session) -> dict[str, Any]:
    """容器管理仪表盘数据。"""
    return {
        "clusters": count_clusters(db),
        "deployments": db.scalar(select(func.count(ContainerDeployment.id))) or 0,
        "pods": db.scalar(select(func.count(ContainerPod.id))) or 0,
        "services": db.scalar(select(func.count(ContainerService.id))) or 0,
        "pod_status": count_pods_by_status(db),
    }
