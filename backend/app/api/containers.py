"""容器管理 API — 对接 K8s API 自动发现资源。"""
import asyncio
import time

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import api_permission_required, get_client_ip
from app.api.sse_auth import validate_stream_token
from app.api.sse_utils import log_line_ts_to_unix, sse_event
from app.db.database import get_db
from app.models.user import User
from app.services.audit import write_log
from app.services.containers import (
    cluster_name_exists,
    cluster_runtime_summary,
    delete_cluster,
    find_clusters_by_name,
    list_clusters,
    refresh_cluster_connection_status,
)
from app.services.k8s import (
    build_kubeconfig,
    delete_pod,
    drain_node,
    get_cluster_info,
    get_deployments,
    get_events,
    get_node_maintenance_preview,
    get_nodes,
    get_pod_events,
    get_pod_detail,
    get_pod_logs,
    get_pods,
    get_services,
    restart_deployment,
    scale_deployment,
    set_node_schedulable,
    test_connection,
)
from app.services.prometheus import get_pod_trends

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


class NodeCordonRequest(BaseModel):
    confirm_node: str
    unschedulable: bool = True


class NodeDrainRequest(BaseModel):
    confirm_node: str
    grace_period_seconds: int = 30


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


def _mark_cluster_token_missing(cluster) -> None:
    cluster.status = "stopped"
    cluster.status_message = "Token is not configured"


def _require_cluster_by_name(db: Session, cluster_name: str):
    if cluster_name.isdigit():
        raise HTTPException(status_code=404, detail="集群不存在")
    matches = find_clusters_by_name(db, cluster_name)
    if not matches:
        raise HTTPException(status_code=404, detail="集群不存在")
    if len(matches) > 1:
        raise HTTPException(status_code=409, detail="存在同名集群，请先修改集群名称")
    return matches[0]


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
    payload = []
    for cluster in items:
        refresh_cluster_connection_status(db, cluster)
        row = _cluster_dict(cluster)
        row.update(cluster_runtime_summary(db, cluster.id))
        row["ready_nodes"] = cluster.node_count
        payload.append(row)
    db.commit()
    return {"code": 0, "data": payload}


@router.get("/clusters/{cluster_name}")
def api_get_cluster(
    cluster_name: str,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("containers.view")),
):
    c = _require_cluster_by_name(db, cluster_name)
    return {"code": 0, "data": _cluster_dict(c)}


@router.get("/clusters/{cluster_name}/kubeconfig")
def api_download_cluster_kubeconfig(
    cluster_name: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("containers.update")),
):
    """Download a kubeconfig generated from the saved cluster credential."""
    c = _require_cluster_by_name(db, cluster_name)
    if not c.token:
        raise HTTPException(status_code=400, detail="集群未配置 Token，无法生成 kubeconfig")

    write_log(
        db,
        user=current_user,
        action="download",
        target_type="container",
        target_id=c.id,
        target_name=c.name,
        detail="下载 K8s kubeconfig",
        ip_address=get_client_ip(request),
    )
    db.commit()

    filename = f"{c.name}-kubeconfig.yaml"
    return PlainTextResponse(
        build_kubeconfig(c.name, c.endpoint, c.token),
        media_type="application/x-yaml; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.post("/clusters/{cluster_name}/test-connection")
def api_test_saved_cluster_connection(
    cluster_name: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("containers.update")),
):
    """Test the current saved credential without ever returning its value."""
    c = _require_cluster_by_name(db, cluster_name)
    if not c.token:
        raise HTTPException(status_code=400, detail="集群未配置 Token，无法测试连接")

    result = test_connection(c.endpoint, c.token)
    if result.get("ok"):
        c.status = "running"
        c.status_message = ""
        c.version = result.get("version") or c.version
    else:
        c.status = "stopped"
        c.status_message = result.get("error", "连接失败")

    write_log(
        db,
        user=current_user,
        action="test_connection",
        target_type="container",
        target_id=c.id,
        target_name=c.name,
        detail="测试 K8s 集群连接",
        ip_address=get_client_ip(request),
    )
    db.commit()
    return {
        "code": 0,
        "msg": "连接正常" if result.get("ok") else "连接失败",
        "data": result,
    }


@router.post("/clusters")
def api_create_cluster(
    body: ClusterCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("containers.create")),
):
    """创建集群，自动测试连接并获取集群信息。"""
    from app.services.containers import create_cluster, update_cluster

    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="集群名称不能为空")
    if name.isdigit() or "/" in name or "\\" in name:
        raise HTTPException(status_code=400, detail="集群名称必须包含文字，且不能包含斜杠")
    if cluster_name_exists(db, name):
        raise HTTPException(status_code=409, detail="集群名称已存在")

    endpoint = body.endpoint.strip()
    token = body.token.strip()
    if not endpoint:
        raise HTTPException(status_code=400, detail="API Server 地址不能为空")

    cluster_info = None
    if token:
        # 先测试连接
        info = test_connection(endpoint, token)
        if not info.get("ok"):
            raise HTTPException(status_code=400, detail=f"连接失败: {info.get('error', '未知错误')}")

        # 获取完整集群信息
        cluster_info = get_cluster_info(endpoint, token)

    c = create_cluster(
        db,
        name=name,
        provider="kubernetes",
        endpoint=endpoint,
        token=token,
        description=body.description.strip(),
    )

    # 未配置 Token 时仅保存，等待后续补充凭据。
    if cluster_info:
        _sync_cluster_meta(c, cluster_info)
    else:
        _mark_cluster_token_missing(c)
    db.commit()
    db.refresh(c)

    write_log(db, user=current_user, action="create", target_type="container",
              target_id=c.id, target_name=c.name, detail=f"接入 K8s 集群 {endpoint}",
              ip_address=get_client_ip(request))
    db.commit()

    return {"code": 0, "msg": "创建成功", "data": _cluster_dict(c)}


@router.put("/clusters/{cluster_name}")
def api_update_cluster(
    cluster_name: str, body: ClusterUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("containers.update")),
):
    from app.services.containers import update_cluster

    c = _require_cluster_by_name(db, cluster_name)

    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="集群名称不能为空")
    if name.isdigit() or "/" in name or "\\" in name:
        raise HTTPException(status_code=400, detail="集群名称必须包含文字，且不能包含斜杠")
    if cluster_name_exists(db, name, exclude_id=c.id):
        raise HTTPException(status_code=409, detail="集群名称已存在")

    endpoint = body.endpoint.strip()
    token = body.token.strip() or c.token  # 不填 token 则保留旧值
    if not endpoint:
        raise HTTPException(status_code=400, detail="API Server 地址不能为空")

    cluster_info = None
    if token:
        # 测试新连接
        info = test_connection(endpoint, token)
        if not info.get("ok"):
            raise HTTPException(status_code=400, detail=f"连接失败: {info.get('error', '未知错误')}")

        cluster_info = get_cluster_info(endpoint, token)

    update_cluster(db, c, name=name, endpoint=endpoint,
                   token=token, description=body.description.strip())
    if cluster_info:
        _sync_cluster_meta(c, cluster_info)
    else:
        _mark_cluster_token_missing(c)
    db.commit()
    db.refresh(c)

    write_log(db, user=current_user, action="update", target_type="container",
              target_id=c.id, target_name=c.name, ip_address=get_client_ip(request))
    db.commit()

    return {"code": 0, "msg": "更新成功", "data": _cluster_dict(c)}


@router.delete("/clusters/{cluster_name}")
def api_delete_cluster(
    cluster_name: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("containers.delete")),
):
    c = _require_cluster_by_name(db, cluster_name)

    write_log(db, user=current_user, action="delete", target_type="container",
              target_id=c.id, target_name=c.name, ip_address=get_client_ip(request))
    delete_cluster(db, c)
    db.commit()
    return {"code": 0, "msg": "删除成功"}


# ─── 集群资源（实时从 K8s API 拉取）────────────────────────


@router.get("/clusters/{cluster_name}/resources")
def api_cluster_resources(
    cluster_name: str,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("containers.view")),
):
    """实时从 K8s API 获取集群全部资源。"""
    c = _require_cluster_by_name(db, cluster_name)
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


@router.get("/clusters/{cluster_name}/nodes")
def api_cluster_nodes(
    cluster_name: str,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("containers.view")),
):
    """获取集群节点列表。"""
    c = _require_cluster_by_name(db, cluster_name)
    nodes = get_nodes(c.endpoint, c.token) if c.token else []
    return {"code": 0, "data": nodes}


@router.get("/clusters/{cluster_name}/nodes/{node_name}/maintenance-preview")
def api_node_maintenance_preview(
    cluster_name: str,
    node_name: str,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("containers.view")),
):
    """Show the exact drain impact before a maintenance command can be submitted."""
    c = _require_cluster_by_name(db, cluster_name)
    if not c.token:
        raise HTTPException(status_code=400, detail="集群未配置 Token，无法执行节点预检")
    result = get_node_maintenance_preview(c.endpoint, c.token, node_name)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "节点维护预检失败"))
    return {"code": 0, "data": result}


@router.post("/clusters/{cluster_name}/nodes/{node_name}/cordon")
def api_cordon_cluster_node(
    cluster_name: str,
    node_name: str,
    body: NodeCordonRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("containers.update")),
):
    """Cordon or restore scheduling for a node after an explicit name confirmation."""
    if body.confirm_node.strip() != node_name:
        raise HTTPException(status_code=400, detail="确认节点名称不匹配")
    c = _require_cluster_by_name(db, cluster_name)
    if not c.token:
        raise HTTPException(status_code=400, detail="集群未配置 Token，无法修改节点状态")

    result = set_node_schedulable(
        c.endpoint,
        c.token,
        node_name,
        unschedulable=body.unschedulable,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "节点调度状态更新失败"))

    action_label = "Cordon" if body.unschedulable else "恢复调度"
    write_log(
        db,
        user=current_user,
        action="cordon" if body.unschedulable else "uncordon",
        target_type="k8s_node",
        target_name=f"{c.name}/{node_name}",
        detail=f"{action_label} K8s 节点",
        ip_address=get_client_ip(request),
    )
    db.commit()
    return {"code": 0, "msg": f"{action_label} 已执行", "data": result}


@router.post("/clusters/{cluster_name}/nodes/{node_name}/drain")
def api_drain_cluster_node(
    cluster_name: str,
    node_name: str,
    body: NodeDrainRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("containers.update")),
):
    """Cordon a node and evict only Pods that pass the server-side preflight."""
    if body.confirm_node.strip() != node_name:
        raise HTTPException(status_code=400, detail="确认节点名称不匹配")
    c = _require_cluster_by_name(db, cluster_name)
    if not c.token:
        raise HTTPException(status_code=400, detail="集群未配置 Token，无法执行节点维护")

    result = drain_node(
        c.endpoint,
        c.token,
        node_name,
        grace_period_seconds=body.grace_period_seconds,
    )
    if "preview" in result:
        raise HTTPException(status_code=409, detail=result.get("error", "节点维护预检未通过"))
    if not result.get("cordoned"):
        raise HTTPException(status_code=400, detail=result.get("error", "节点驱逐失败"))

    evicted = len(result.get("evicted", []))
    failed = len(result.get("failed", []))
    write_log(
        db,
        user=current_user,
        action="drain",
        target_type="k8s_node",
        target_name=f"{c.name}/{node_name}",
        detail=f"Drain K8s 节点，已提交 {evicted} 个 Pod 驱逐，失败 {failed} 个",
        ip_address=get_client_ip(request),
    )
    db.commit()
    return {
        "code": 0,
        "msg": "驱逐请求已提交" if not failed else "部分 Pod 未能提交驱逐",
        "data": result,
    }


@router.get("/clusters/{cluster_name}/pods")
def api_cluster_pods(
    cluster_name: str,
    namespace: str = "",
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("containers.view")),
):
    """获取集群 Pod 列表。"""
    c = _require_cluster_by_name(db, cluster_name)
    pods = get_pods(c.endpoint, c.token) if c.token else []
    if namespace:
        pods = [p for p in pods if p["namespace"] == namespace]
    return {"code": 0, "data": pods}


@router.get("/clusters/{cluster_name}/pods/{namespace}/{pod_name}/logs")
def api_pod_logs(
    cluster_name: str,
    namespace: str,
    pod_name: str,
    tail_lines: int = 200,
    since: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("containers.view")),
):
    """获取 Pod 日志：按行数（tail_lines）或按时间段（since，unix 秒）。"""
    c = _require_cluster_by_name(db, cluster_name)
    if not c.token:
        raise HTTPException(status_code=400, detail="集群未配置 Token，无法连接 K8s API")

    # since=0 表示"全部"：不加时间过滤，仅用大行数上限；否则换算成相对秒
    if since is not None and since > 0:
        since_seconds = max(1, int(time.time()) - int(since))
    else:
        since_seconds = None
    result = get_pod_logs(c.endpoint, c.token, namespace, pod_name, tail_lines=tail_lines, since_seconds=since_seconds)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "获取 Pod 日志失败"))
    return {"code": 0, "data": {"logs": result.get("logs", ""), "since": since}}


@router.get("/clusters/{cluster_name}/pods/{namespace}/{pod_name}/logs/stream")
async def api_pod_logs_stream(
    cluster_name: str,
    namespace: str,
    pod_name: str,
    request: Request,
    token: str | None = None,
    since: int | None = None,
    interval: int = 2,
    db: Session = Depends(get_db),
):
    """SSE 近实时 Pod 日志流：每 interval 秒拉取 since 之后的日志并推送新行。

    EventSource 无法自定义请求头，鉴权用 ``?token=<JWT>``，复用 containers.view 权限。
    鉴权失败直接 401（EventSource 规范：首次非 200 → CLOSED 且不自动重连）。
    """
    user, err = validate_stream_token(token, "containers.view")
    if err is not None or user is None:
        raise HTTPException(status_code=401, detail=err or "Authentication required")

    c = _require_cluster_by_name(db, cluster_name)
    if not c.token:
        raise HTTPException(status_code=400, detail="集群未配置 Token，无法连接 K8s API")
    interval = max(1, min(int(interval), 30))

    return StreamingResponse(
        _pod_log_event_stream(c.endpoint, c.token, namespace, pod_name, since, interval, request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _pod_log_event_stream(
    endpoint: str,
    token: str,
    namespace: str,
    pod_name: str,
    since_arg: int | None,
    interval: int,
    request: Request,
):
    """轮询 K8s /log（sinceSeconds），对相邻批次做秒级去重后以 SSE 推送新行。"""
    last_ts = int(since_arg) if since_arg is not None else int(time.time())
    prev_batch: set[str] = set()
    yield sse_event({"type": "ready", "since": last_ts})

    tick = 0
    while True:
        if await request.is_disconnected():
            break
        try:
            # get_pod_logs 为同步 httpx 调用，丢到线程池避免阻塞事件循环
            result = await asyncio.to_thread(
                get_pod_logs,
                endpoint, token, namespace, pod_name,
                tail_lines=1000,
                since_seconds=max(1, int(time.time()) - last_ts),
            )
            if not result.get("ok"):
                yield sse_event({"type": "error", "message": result.get("error", "拉取失败")})
                await asyncio.sleep(interval)
                continue
            raw = result.get("logs", "") or ""
        except Exception as e:
            yield sse_event({"type": "error", "message": f"K8s 拉取失败: {e}"})
            await asyncio.sleep(interval)
            continue

        batch_lines = raw.splitlines() if raw else []
        new_lines = [ln for ln in batch_lines if ln not in prev_batch]
        prev_batch = set(batch_lines)

        if new_lines:
            timestamps = [ts for ts in (log_line_ts_to_unix(ln) for ln in batch_lines) if ts is not None]
            if timestamps:
                last_ts = max(timestamps)
            yield sse_event({
                "type": "append",
                "lines": "\n".join(new_lines),
                "count": len(new_lines),
            })

        tick += 1
        if tick % 15 == 0:
            yield sse_event({"type": "heartbeat"})

        await asyncio.sleep(interval)

    yield sse_event({"type": "done"})


@router.get("/clusters/{cluster_name}/pods/{namespace}/{pod_name}/events")
def api_pod_events(
    cluster_name: str,
    namespace: str,
    pod_name: str,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("containers.view")),
):
    """获取 Pod 事件。"""
    c = _require_cluster_by_name(db, cluster_name)
    if not c.token:
        raise HTTPException(status_code=400, detail="集群未配置 Token，无法连接 K8s API")
    return {"code": 0, "data": get_pod_events(c.endpoint, c.token, namespace, pod_name)}


@router.get("/clusters/{cluster_name}/pods/{namespace}/{pod_name}")
def api_pod_detail(
    cluster_name: str,
    namespace: str,
    pod_name: str,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("containers.view")),
):
    """获取 Pod 详情：完整 manifest + 关联事件，前端分区渲染（对标 Docker inspect）。"""
    c = _require_cluster_by_name(db, cluster_name)
    if not c.token:
        raise HTTPException(status_code=400, detail="集群未配置 Token，无法连接 K8s API")
    result = get_pod_detail(c.endpoint, c.token, namespace, pod_name)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "获取 Pod 详情失败"))
    return {"code": 0, "data": {"pod": result.get("pod", {}), "events": result.get("events", [])}}


@router.get("/clusters/{cluster_name}/events")
def api_cluster_events(
    cluster_name: str,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("containers.view")),
):
    """获取集群级事件（全命名空间，按最后发生时间倒序）。"""
    c = _require_cluster_by_name(db, cluster_name)
    if not c.token:
        raise HTTPException(status_code=400, detail="集群未配置 Token，无法连接 K8s API")
    return {"code": 0, "data": get_events(c.endpoint, c.token)}


@router.delete("/clusters/{cluster_name}/pods/{namespace}/{pod_name}")
def api_delete_pod(
    cluster_name: str,
    namespace: str,
    pod_name: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("containers.delete")),
):
    """删除 Pod。"""
    c = _require_cluster_by_name(db, cluster_name)
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


@router.post("/clusters/{cluster_name}/deployments/{namespace}/{deployment_name}/restart")
def api_restart_deployment(
    cluster_name: str,
    namespace: str,
    deployment_name: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("containers.update")),
):
    """滚动重启 Deployment。"""
    c = _require_cluster_by_name(db, cluster_name)
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


class ScaleDeploymentRequest(BaseModel):
    replicas: int


@router.post("/clusters/{cluster_name}/deployments/{namespace}/{deployment_name}/scale")
def api_scale_deployment(
    cluster_name: str,
    namespace: str,
    deployment_name: str,
    body: ScaleDeploymentRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("containers.update")),
):
    """调整 Deployment 副本数（扩缩容）。"""
    c = _require_cluster_by_name(db, cluster_name)
    if not c.token:
        raise HTTPException(status_code=400, detail="集群未配置 Token，无法连接 K8s API")
    result = scale_deployment(c.endpoint, c.token, namespace, deployment_name, body.replicas)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "调整副本数失败"))
    write_log(db, user=current_user, action="scale", target_type="deployment",
              target_name=f"{namespace}/{deployment_name}",
              detail=f"扩缩容 Deployment: {namespace}/{deployment_name} -> {result.get('replicas')}",
              ip_address=get_client_ip(request))
    db.commit()
    return {"code": 0, "msg": "副本数已更新", "data": {"replicas": result.get("replicas")}}


@router.get("/clusters/{cluster_name}/pods/{namespace}/{pod_name}/trends")
async def api_pod_trends(
    cluster_name: str,
    namespace: str,
    pod_name: str,
    minutes: int = 60,
    step_seconds: int = 60,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("containers.view")),
):
    """Pod 容器资源趋势（Prometheus / cAdvisor）。"""
    _require_cluster_by_name(db, cluster_name)
    safe_minutes = min(max(minutes, 15), 360)
    safe_step = min(max(step_seconds, 30), 300)
    data = await get_pod_trends(namespace, pod_name, db, minutes=safe_minutes, step_seconds=safe_step)
    return {"code": 0, "data": data}


@router.get("/clusters/{cluster_name}/services")
def api_cluster_services(
    cluster_name: str,
    namespace: str = "",
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("containers.view")),
):
    """获取集群 Service 列表。"""
    c = _require_cluster_by_name(db, cluster_name)
    svcs = get_services(c.endpoint, c.token) if c.token else []
    if namespace:
        svcs = [s for s in svcs if s["namespace"] == namespace]
    return {"code": 0, "data": svcs}


@router.get("/clusters/{cluster_name}/deployments")
def api_cluster_deployments(
    cluster_name: str,
    namespace: str = "",
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("containers.view")),
):
    """获取集群 Deployment 列表。"""
    c = _require_cluster_by_name(db, cluster_name)
    deps = get_deployments(c.endpoint, c.token) if c.token else []
    if namespace:
        deps = [d for d in deps if d["namespace"] == namespace]
    return {"code": 0, "data": deps}
