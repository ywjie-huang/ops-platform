"""容器管理 API。"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import api_permission_required
from app.db.database import get_db
from app.models.user import User
from app.services.containers import (
    container_overview,
    create_cluster,
    create_deployment,
    delete_cluster,
    delete_deployment,
    delete_pod,
    delete_service,
    get_cluster,
    get_deployment,
    get_pod,
    get_service,
    list_clusters,
    list_deployments,
    list_pods,
    list_services,
    update_cluster,
    update_deployment,
)

router = APIRouter(prefix="/containers", tags=["容器管理"])


class ClusterCreate(BaseModel):
    name: str
    cluster_type: str
    api_server: str = ""
    description: str = ""


@router.get("/overview")
def api_container_overview(
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("containers.view")),
):
    data = container_overview(db)
    return {"code": 0, "data": data}


@router.get("/clusters")
def api_list_clusters(db: Session = Depends(get_db), _: User = Depends(api_permission_required("containers.view"))):
    items = list_clusters(db)
    return {
        "code": 0,
        "data": [
            {"id": c.id, "name": c.name, "cluster_type": c.cluster_type, "api_server": c.api_server, "description": c.description, "status": c.status, "created_at": c.created_at.isoformat()}
            for c in items
        ],
    }


@router.post("/clusters")
def api_create_cluster(body: ClusterCreate, db: Session = Depends(get_db), _: User = Depends(api_permission_required("containers.create"))):
    c = create_cluster(db, name=body.name.strip(), cluster_type=body.cluster_type.strip(), api_server=body.api_server.strip(), description=body.description.strip())
    return {"code": 0, "msg": "创建成功", "data": {"id": c.id, "name": c.name}}


@router.put("/clusters/{cluster_id}")
def api_update_cluster(cluster_id: int, body: ClusterCreate, db: Session = Depends(get_db), _: User = Depends(api_permission_required("containers.update"))):
    c = get_cluster(db, cluster_id)
    if c is None:
        raise HTTPException(status_code=404, detail="集群不存在")
    update_cluster(db, c, name=body.name.strip(), cluster_type=body.cluster_type.strip(), api_server=body.api_server.strip(), description=body.description.strip())
    return {"code": 0, "msg": "更新成功"}


@router.delete("/clusters/{cluster_id}")
def api_delete_cluster(cluster_id: int, db: Session = Depends(get_db), _: User = Depends(api_permission_required("containers.delete"))):
    c = get_cluster(db, cluster_id)
    if c is None:
        raise HTTPException(status_code=404, detail="集群不存在")
    delete_cluster(db, c)
    return {"code": 0, "msg": "删除成功"}


@router.get("/pods")
def api_list_pods(cluster_id: int | None = None, status: str = "", db: Session = Depends(get_db), _: User = Depends(api_permission_required("containers.view"))):
    items = list_pods(db, cluster_id=cluster_id, status=status)
    return {
        "code": 0,
        "data": [
            {"id": p.id, "name": p.name, "namespace": p.namespace, "status": p.status, "node": p.node_name, "pod_ip": p.pod_ip, "restarts": p.restarts, "cluster_id": p.cluster_id, "created_at": p.created_at.isoformat()}
            for p in items
        ],
    }


@router.delete("/pods/{pod_id}")
def api_delete_pod(pod_id: int, db: Session = Depends(get_db), _: User = Depends(api_permission_required("containers.delete"))):
    p = get_pod(db, pod_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Pod 不存在")
    delete_pod(db, p)
    return {"code": 0, "msg": "删除成功"}


@router.get("/services")
def api_list_services(cluster_id: int | None = None, db: Session = Depends(get_db), _: User = Depends(api_permission_required("containers.view"))):
    items = list_services(db, cluster_id=cluster_id)
    return {
        "code": 0,
        "data": [
            {"id": s.id, "name": s.name, "namespace": s.namespace, "service_type": s.service_type, "cluster_ip": s.cluster_ip, "ports": s.ports, "selector": s.selector, "cluster_id": s.cluster_id, "created_at": s.created_at.isoformat()}
            for s in items
        ],
    }


@router.delete("/services/{service_id}")
def api_delete_service(service_id: int, db: Session = Depends(get_db), _: User = Depends(api_permission_required("containers.delete"))):
    s = get_service(db, service_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Service 不存在")
    delete_service(db, s)
    return {"code": 0, "msg": "删除成功"}


@router.get("/deployments")
def api_list_deployments(cluster_id: int | None = None, db: Session = Depends(get_db), _: User = Depends(api_permission_required("containers.view"))):
    items = list_deployments(db, cluster_id=cluster_id)
    return {
        "code": 0,
        "data": [
            {"id": d.id, "name": d.name, "namespace": d.namespace, "replicas": d.replicas, "available_replicas": d.available_replicas, "cluster_id": d.cluster_id, "created_at": d.created_at.isoformat()}
            for d in items
        ],
    }
