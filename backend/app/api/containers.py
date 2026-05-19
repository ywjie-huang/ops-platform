"""容器管理 API — 对接 K8s API 自动发现资源。"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import api_permission_required, get_client_ip
from app.db.database import get_db
from app.models.user import User
from app.services.audit import write_log
from app.services.containers import (
    delete_cluster,
    get_cluster,
    list_clusters,
)
from app.services.k8s import (
    delete_pod,
    get_cluster_info,
    get_deployments,
    get_nodes,
    get_pod_events,
    get_pod_logs,
    get_pods,
    get_services,
    restart_deployment,
    test_connection,
)

router = APIRouter(prefix="/containers", tags=["容器管理"])


# ─── Schemas ────────────────────────────────────────────────


class ClusterCreate(BaseModel):
    name: str
    endpoint: str
    token: str = ""
    description: str = ""


class ClusterUpdate(BaseModel):
    name: str
    endpoint: str
    token: str = ""
    description: str = ""


class ConnectionTest(BaseModel):
    endpoint: str
    token: str = ""


# ─── Helpers ────────────────────────────────────────────────


def _cluster_dict(c, *, include_token: bool = False) -> dict:
    d = {
        "id": c.id, "name": c.name, "provider": c.provider,
        "version": c.version, "endpoint": c.endpoint,
        "status": c.status, "status_message": c.status_message or "",
        "node_count": c.node_count,
        "description": c.description,
        "created_at": c.created_at.isoformat(),
        "updated_at": c.updated_at.isoformat(),
    }
    if include_token:
        d["token"] = c.token or ""
    return d


def _sync_cluster_meta(cluster, info: dict) -> None:
    """用 K8s 返回的集群信息更新 cluster 元数据。"""
    cluster.version = info.get("version", cluster.version)
    cluster.node_count = info.get("node_count", cluster.node_count)
    if info.get("connected"):
        cluster.status = "running"
        cluster.status_message = ""
    else:
        cluster.status = "stopped"
        cluster.status_message = info.get("error", "连接失败")


# ─── 连接测试 ───────────────────────────────────────────────


@router.post("/test-connection")
def api_test_connection(
    body: ConnectionTest,
    _: User = Depends(api_permission_required("containers.view")),
):
    """测试 K8s API 连通性。"""
    result = test_connection(body.endpoint.strip(), body.token.strip())
    return {"code": 0, "data": result}


# ─── 集群管理 ───────────────────────────────────────────────


@router.get("/clusters")
def api_list_clusters(
    keyword: str = "",
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("containers.view")),
):
    items = list_clusters(db, keyword=keyword)
    return {"code": 0, "data": [_cluster_dict(c) for c in items]}


@router.get("/clusters/{cluster_id}")
def api_get_cluster(
    cluster_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("containers.view")),
):
    c = get_cluster(db, cluster_id)
    if c is None:
        raise HTTPException(status_code=404, detail="集群不存在")
    return {"code": 0, "data": _cluster_dict(c)}


@router.post("/clusters")
def api_create_cluster(
    body: ClusterCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("containers.create")),
):
    """创建集群，自动测试连接并获取集群信息。"""
    from app.services.containers import create_cluster, update_cluster

    endpoint = body.endpoint.strip()
    token = body.token.strip()

    # 先测试连接
    info = test_connection(endpoint, token)
    if not info.get("ok"):
        raise HTTPException(status_code=400, detail=f"连接失败: {info.get('error', '未知错误')}")

    # 获取完整集群信息
    cluster_info = get_cluster_info(endpoint, token)

    c = create_cluster(
        db,
        name=body.name.strip(),
        provider="kubernetes",
        endpoint=endpoint,
        token=token,
        description=body.description.strip(),
    )

    # 同步集群元数据
    _sync_cluster_meta(c, cluster_info)
    db.commit()
    db.refresh(c)

    write_log(db, user=current_user, action="create", target_type="container",
              target_id=c.id, target_name=c.name, detail=f"接入 K8s 集群 {endpoint}",
              ip_address=get_client_ip(request))
    db.commit()

    return {"code": 0, "msg": "创建成功", "data": _cluster_dict(c)}


@router.put("/clusters/{cluster_id}")
def api_update_cluster(
    cluster_id: int, body: ClusterUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("containers.update")),
):
    from app.services.containers import update_cluster

    c = get_cluster(db, cluster_id)
    if c is None:
        raise HTTPException(status_code=404, detail="集群不存在")

    endpoint = body.endpoint.strip()
    token = body.token.strip() or c.token  # 不填 token 则保留旧值

    # 测试新连接
    info = test_connection(endpoint, token)
    if not info.get("ok"):
        raise HTTPException(status_code=400, detail=f"连接失败: {info.get('error', '未知错误')}")

    cluster_info = get_cluster_info(endpoint, token)

    update_cluster(db, c, name=body.name.strip(), endpoint=endpoint,
                   token=token, description=body.description.strip())
    _sync_cluster_meta(c, cluster_info)
    db.commit()
    db.refresh(c)

    write_log(db, user=current_user, action="update", target_type="container",
              target_id=c.id, target_name=c.name, ip_address=get_client_ip(request))
    db.commit()

    return {"code": 0, "msg": "更新成功", "data": _cluster_dict(c)}


@router.delete("/clusters/{cluster_id}")
def api_delete_cluster(
    cluster_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("containers.delete")),
):
    c = get_cluster(db, cluster_id)
    if c is None:
        raise HTTPException(status_code=404, detail="集群不存在")

    write_log(db, user=current_user, action="delete", target_type="container",
              target_id=c.id, target_name=c.name, ip_address=get_client_ip(request))
    delete_cluster(db, c)
    db.commit()
    return {"code": 0, "msg": "删除成功"}


# ─── 集群资源（实时从 K8s API 拉取）────────────────────────


@router.get("/clusters/{cluster_id}/resources")
def api_cluster_resources(
    cluster_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("containers.view")),
):
    """实时从 K8s API 获取集群全部资源。"""
    c = get_cluster(db, cluster_id)
    if c is None:
        raise HTTPException(status_code=404, detail="集群不存在")
    if not c.token:
        raise HTTPException(status_code=400, detail="集群未配置 Token，无法连接 K8s API")

    info = get_cluster_info(c.endpoint, c.token)

    # 更新集群状态
    if info.get("connected"):
        c.status = "running"
        c.status_message = ""
    else:
        c.status = "stopped"
        c.status_message = info.get("error", "连接失败")
    if info.get("version"):
        c.version = info["version"]
    if info.get("node_count") is not None:
        c.node_count = info["node_count"]
    db.commit()

    return {"code": 0, "data": info}


@router.get("/clusters/{cluster_id}/nodes")
def api_cluster_nodes(
    cluster_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("containers.view")),
):
    """获取集群节点列表。"""
    c = get_cluster(db, cluster_id)
    if c is None:
        raise HTTPException(status_code=404, detail="集群不存在")
    nodes = get_nodes(c.endpoint, c.token) if c.token else []
    return {"code": 0, "data": nodes}


@router.get("/clusters/{cluster_id}/pods")
def api_cluster_pods(
    cluster_id: int,
    namespace: str = "",
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("containers.view")),
):
    """获取集群 Pod 列表。"""
    c = get_cluster(db, cluster_id)
    if c is None:
        raise HTTPException(status_code=404, detail="集群不存在")
    pods = get_pods(c.endpoint, c.token) if c.token else []
    if namespace:
        pods = [p for p in pods if p["namespace"] == namespace]
    return {"code": 0, "data": pods}


@router.get("/clusters/{cluster_id}/pods/{namespace}/{pod_name}/logs")
def api_pod_logs(
    cluster_id: int,
    namespace: str,
    pod_name: str,
    tail_lines: int = 200,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("containers.view")),
):
    """获取 Pod 日志。"""
    c = get_cluster(db, cluster_id)
    if c is None:
        raise HTTPException(status_code=404, detail="集群不存在")
    if not c.token:
        raise HTTPException(status_code=400, detail="集群未配置 Token，无法连接 K8s API")
    result = get_pod_logs(c.endpoint, c.token, namespace, pod_name, tail_lines)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "获取 Pod 日志失败"))
    return {"code": 0, "data": {"logs": result.get("logs", "")}}


@router.get("/clusters/{cluster_id}/pods/{namespace}/{pod_name}/events")
def api_pod_events(
    cluster_id: int,
    namespace: str,
    pod_name: str,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("containers.view")),
):
    """获取 Pod 事件。"""
    c = get_cluster(db, cluster_id)
    if c is None:
        raise HTTPException(status_code=404, detail="集群不存在")
    if not c.token:
        raise HTTPException(status_code=400, detail="集群未配置 Token，无法连接 K8s API")
    return {"code": 0, "data": get_pod_events(c.endpoint, c.token, namespace, pod_name)}


@router.delete("/clusters/{cluster_id}/pods/{namespace}/{pod_name}")
def api_delete_pod(
    cluster_id: int,
    namespace: str,
    pod_name: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("containers.delete")),
):
    """删除 Pod。"""
    c = get_cluster(db, cluster_id)
    if c is None:
        raise HTTPException(status_code=404, detail="集群不存在")
    if not c.token:
        raise HTTPException(status_code=400, detail="集群未配置 Token，无法连接 K8s API")
    result = delete_pod(c.endpoint, c.token, namespace, pod_name)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "删除 Pod 失败"))
    write_log(db, user=current_user, action="delete", target_type="pod",
              target_name=f"{namespace}/{pod_name}", detail=f"删除 Pod: {namespace}/{pod_name}",
              ip_address=get_client_ip(request))
    db.commit()
    return {"code": 0, "msg": "删除成功"}


@router.post("/clusters/{cluster_id}/deployments/{namespace}/{deployment_name}/restart")
def api_restart_deployment(
    cluster_id: int,
    namespace: str,
    deployment_name: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("containers.update")),
):
    """滚动重启 Deployment。"""
    c = get_cluster(db, cluster_id)
    if c is None:
        raise HTTPException(status_code=404, detail="集群不存在")
    if not c.token:
        raise HTTPException(status_code=400, detail="集群未配置 Token，无法连接 K8s API")
    result = restart_deployment(c.endpoint, c.token, namespace, deployment_name)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "重启 Deployment 失败"))
    write_log(db, user=current_user, action="restart", target_type="deployment",
              target_name=f"{namespace}/{deployment_name}", detail=f"滚动重启 Deployment: {namespace}/{deployment_name}",
              ip_address=get_client_ip(request))
    db.commit()
    return {"code": 0, "msg": "重启已触发", "data": {"restarted_at": result.get("restarted_at")}}


@router.get("/clusters/{cluster_id}/services")
def api_cluster_services(
    cluster_id: int,
    namespace: str = "",
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("containers.view")),
):
    """获取集群 Service 列表。"""
    c = get_cluster(db, cluster_id)
    if c is None:
        raise HTTPException(status_code=404, detail="集群不存在")
    svcs = get_services(c.endpoint, c.token) if c.token else []
    if namespace:
        svcs = [s for s in svcs if s["namespace"] == namespace]
    return {"code": 0, "data": svcs}


@router.get("/clusters/{cluster_id}/deployments")
def api_cluster_deployments(
    cluster_id: int,
    namespace: str = "",
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("containers.view")),
):
    """获取集群 Deployment 列表。"""
    c = get_cluster(db, cluster_id)
    if c is None:
        raise HTTPException(status_code=404, detail="集群不存在")
    deps = get_deployments(c.endpoint, c.token) if c.token else []
    if namespace:
        deps = [d for d in deps if d["namespace"] == namespace]
    return {"code": 0, "data": deps}
