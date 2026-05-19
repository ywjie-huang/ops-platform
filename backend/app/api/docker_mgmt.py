"""Docker 管理 API — 平台端 Docker 主机管理 / 容器查询 / 主动拉取。"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import api_permission_required, get_client_ip
from app.db.database import get_db
from app.models.container import ContainerCluster
from app.models.user import User
from app.services.audit import write_log
from app.services.docker_agent import (
    create_docker_host,
    delete_docker_host,
    docker_overview,
    get_docker_host,
    is_host_online,
    list_docker_containers,
    list_docker_hosts,
    sync_host_from_agent,
    update_docker_host,
)

router = APIRouter(prefix="/containers/docker", tags=["Docker 管理"])


# ─── Schemas ───────────────────────────────────────────────

class DockerHostCreate(BaseModel):
    name: str
    endpoint: str  # IP:端口，如 192.168.1.200:9001
    description: str = ""


class DockerHostUpdate(BaseModel):
    name: str
    endpoint: str = ""
    description: str = ""


# ─── Helpers ───────────────────────────────────────────────

def _host_dict(h: ContainerCluster) -> dict:
    # agent_key 字段复用存储主机指标 JSON
    metrics = {}
    if h.agent_key:
        try:
            import json
            metrics = json.loads(h.agent_key)
        except (json.JSONDecodeError, TypeError):
            pass

    return {
        "id": h.id,
        "name": h.name,
        "provider": h.provider,
        "status": h.status,
        "endpoint": h.endpoint or "",
        "host_os": h.host_os or "",
        "host_ip": h.host_ip or "",
        "docker_version": h.docker_version or "",
        "last_heartbeat": h.last_heartbeat.isoformat() if h.last_heartbeat else None,
        "online": is_host_online(h),
        "description": h.description or "",
        "metrics": metrics,
        "created_at": h.created_at.isoformat(),
        "updated_at": h.updated_at.isoformat(),
    }


def _container_dict(c) -> dict:
    return {
        "id": c.id,
        "host_id": c.host_id,
        "container_id": c.container_id,
        "name": c.name,
        "image": c.image,
        "status": c.status,
        "state": c.state,
        "ports": c.ports,
        "cpu_percent": c.cpu_percent,
        "memory_usage": c.memory_usage,
        "memory_limit": c.memory_limit,
        "memory_percent": c.memory_percent,
        "net_rx_bytes": c.net_rx_bytes,
        "net_tx_bytes": c.net_tx_bytes,
        "block_read": c.block_read,
        "block_write": c.block_write,
        "restart_count": c.restart_count,
        "started_at": c.started_at or "",
        "updated_at": c.updated_at.isoformat(),
    }


# ─── 概览 ─────────────────────────────────────────────────

@router.get("/overview")
def api_docker_overview(
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("containers.view")),
):
    return {"code": 0, "data": docker_overview(db)}


# ─── Docker 主机管理 ──────────────────────────────────────

@router.get("/hosts")
def api_list_docker_hosts(
    keyword: str = "",
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("containers.view")),
):
    hosts = list_docker_hosts(db, keyword=keyword)
    return {"code": 0, "data": [_host_dict(h) for h in hosts]}


@router.get("/hosts/{host_id}")
def api_get_docker_host(
    host_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("containers.view")),
):
    h = get_docker_host(db, host_id)
    if not h:
        raise HTTPException(status_code=404, detail="主机不存在")
    return {"code": 0, "data": _host_dict(h)}


@router.post("/hosts")
def api_create_docker_host(
    body: DockerHostCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("containers.create")),
):
    """注册 Docker 主机，填写名称和 Agent 地址（IP:端口）。"""
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="主机名称不能为空")
    if not body.endpoint.strip():
        raise HTTPException(status_code=400, detail="Agent 地址不能为空")

    h = create_docker_host(
        db,
        name=body.name.strip(),
        endpoint=body.endpoint.strip(),
        description=body.description.strip(),
    )

    # 立即尝试拉取一次数据
    ok = sync_host_from_agent(db, h)

    write_log(
        db, user=current_user, action="create", target_type="docker_host",
        target_id=h.id, target_name=h.name,
        detail=f"注册 Docker 主机，地址: {h.endpoint}，首次拉取: {'成功' if ok else '失败'}",
        ip_address=get_client_ip(request),
    )
    db.commit()

    return {"code": 0, "msg": "注册成功" + ("，已连接 Agent" if ok else "，Agent 暂时不可达，请确认 Agent 已启动"), "data": _host_dict(h)}


@router.put("/hosts/{host_id}")
def api_update_docker_host(
    host_id: int,
    body: DockerHostUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("containers.update")),
):
    h = get_docker_host(db, host_id)
    if not h:
        raise HTTPException(status_code=404, detail="主机不存在")

    kwargs = {}
    if body.name.strip():
        kwargs["name"] = body.name.strip()
    if body.endpoint.strip():
        kwargs["endpoint"] = body.endpoint.strip()
    if body.description:
        kwargs["description"] = body.description

    update_docker_host(db, h, **kwargs)

    write_log(
        db, user=current_user, action="update", target_type="docker_host",
        target_id=h.id, target_name=h.name,
        ip_address=get_client_ip(request),
    )
    db.commit()

    return {"code": 0, "msg": "更新成功", "data": _host_dict(h)}


@router.delete("/hosts/{host_id}")
def api_delete_docker_host(
    host_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("containers.delete")),
):
    h = get_docker_host(db, host_id)
    if not h:
        raise HTTPException(status_code=404, detail="主机不存在")

    write_log(
        db, user=current_user, action="delete", target_type="docker_host",
        target_id=h.id, target_name=h.name,
        ip_address=get_client_ip(request),
    )
    delete_docker_host(db, h)
    db.commit()

    return {"code": 0, "msg": "删除成功"}


# ─── 手动刷新（从 Agent 拉取）─────────────────────────────

@router.post("/hosts/{host_id}/refresh")
def api_refresh_host(
    host_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("containers.view")),
):
    """手动触发从 Agent 拉取最新数据。"""
    h = get_docker_host(db, host_id)
    if not h:
        raise HTTPException(status_code=404, detail="主机不存在")

    ok = sync_host_from_agent(db, h)
    if not ok:
        raise HTTPException(status_code=502, detail="Agent 连接失败，请确认 Agent 已启动且地址正确")

    return {"code": 0, "msg": "刷新成功", "data": _host_dict(h)}


# ─── 容器查询 ──────────────────────────────────────────────

@router.get("/containers")
def api_list_docker_containers(
    host_id: int | None = None,
    keyword: str = "",
    status: str = "",
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("containers.view")),
):
    containers = list_docker_containers(db, host_id=host_id, keyword=keyword, status=status)
    return {"code": 0, "data": [_container_dict(c) for c in containers]}


@router.get("/hosts/{host_id}/containers")
def api_host_containers(
    host_id: int,
    keyword: str = "",
    status: str = "",
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("containers.view")),
):
    h = get_docker_host(db, host_id)
    if not h:
        raise HTTPException(status_code=404, detail="主机不存在")
    containers = list_docker_containers(db, host_id=host_id, keyword=keyword, status=status)
    return {"code": 0, "data": [_container_dict(c) for c in containers]}
