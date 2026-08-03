"""Docker 管理 API — 平台端 Docker 主机管理 / 容器查询 / 容器操作 / 主动拉取。"""

import re
from html import unescape

import httpx
import requests as http_requests
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import api_permission_required, get_client_ip
from app.api.sse_auth import validate_stream_token
from app.api.sse_utils import polling_log_stream
from app.core.config import CHINA_TZ
from app.db.database import get_db
from app.models.container import ContainerCluster
from app.models.user import User
from app.services.audit import write_log
from app.services.docker_agent import (
    create_docker_host,
    delete_docker_host,
    docker_host_name_exists,
    docker_overview,
    find_docker_hosts_by_name,
    get_container_trends,
    is_host_online,
    list_docker_containers,
    list_docker_hosts,
    sync_host_from_agent,
    update_docker_host,
)

router = APIRouter(prefix="/containers/docker", tags=["Docker 管理"])
MAX_DOCKER_LOG_TAIL = 1000
DOCKER_LOG_VIEW_PERMISSION = "containers.view"


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


def _normalize_log_tail_lines(value: int) -> int:
    return max(1, min(int(value or 300), MAX_DOCKER_LOG_TAIL))


def _require_docker_host_by_name(db: Session, host_name: str) -> ContainerCluster:
    if host_name.isdigit():
        raise HTTPException(status_code=404, detail="主机不存在")
    matches = find_docker_hosts_by_name(db, host_name)
    if not matches:
        raise HTTPException(status_code=404, detail="主机不存在")
    if len(matches) > 1:
        raise HTTPException(status_code=409, detail="存在同名主机，请先修改主机名称")
    return matches[0]


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


@router.get("/hosts/{host_name}")
def api_get_docker_host(
    host_name: str,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("containers.view")),
):
    h = _require_docker_host_by_name(db, host_name)
    return {"code": 0, "data": _host_dict(h)}


@router.post("/hosts")
def api_create_docker_host(
    body: DockerHostCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("containers.create")),
):
    """注册 Docker 主机，填写名称和 Agent 地址（IP:端口）。"""
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="主机名称不能为空")
    if name.isdigit() or "/" in name or "\\" in name:
        raise HTTPException(status_code=400, detail="主机名称必须包含文字，且不能包含斜杠")
    if docker_host_name_exists(db, name):
        raise HTTPException(status_code=409, detail="主机名称已存在")
    if not body.endpoint.strip():
        raise HTTPException(status_code=400, detail="Agent 地址不能为空")

    h = create_docker_host(
        db,
        name=name,
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


@router.put("/hosts/{host_name}")
def api_update_docker_host(
    host_name: str,
    body: DockerHostUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("containers.update")),
):
    h = _require_docker_host_by_name(db, host_name)

    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="主机名称不能为空")
    if name.isdigit() or "/" in name or "\\" in name:
        raise HTTPException(status_code=400, detail="主机名称必须包含文字，且不能包含斜杠")
    if docker_host_name_exists(db, name, exclude_id=h.id):
        raise HTTPException(status_code=409, detail="主机名称已存在")

    kwargs = {"name": name}
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


@router.delete("/hosts/{host_name}")
def api_delete_docker_host(
    host_name: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("containers.delete")),
):
    h = _require_docker_host_by_name(db, host_name)

    write_log(
        db, user=current_user, action="delete", target_type="docker_host",
        target_id=h.id, target_name=h.name,
        ip_address=get_client_ip(request),
    )
    delete_docker_host(db, h)
    db.commit()

    return {"code": 0, "msg": "删除成功"}


# ─── 手动刷新（从 Agent 拉取）─────────────────────────────

@router.post("/hosts/{host_name}/refresh")
def api_refresh_host(
    host_name: str,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("containers.view")),
):
    """手动触发从 Agent 拉取最新数据。"""
    h = _require_docker_host_by_name(db, host_name)

    ok = sync_host_from_agent(db, h)
    if not ok:
        raise HTTPException(status_code=502, detail="Agent 连接失败，请确认 Agent 已启动且地址正确")

    return {"code": 0, "msg": "刷新成功", "data": _host_dict(h)}


# ─── 容器查询 ──────────────────────────────────────────────

@router.get("/containers")
def api_list_docker_containers(
    keyword: str = "",
    status: str = "",
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("containers.view")),
):
    containers = list_docker_containers(db, keyword=keyword, status=status)
    return {"code": 0, "data": [_container_dict(c) for c in containers]}


@router.get("/hosts/{host_name}/containers")
def api_host_containers(
    host_name: str,
    keyword: str = "",
    status: str = "",
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("containers.view")),
):
    h = _require_docker_host_by_name(db, host_name)
    containers = list_docker_containers(db, host_id=h.id, keyword=keyword, status=status)
    return {"code": 0, "data": [_container_dict(c) for c in containers]}


@router.get("/hosts/{host_name}/containers/{container_id}/logs")
def api_container_logs(
    host_name: str,
    container_id: str,
    tail_lines: int = 300,
    since: int | None = None,
    until: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required(DOCKER_LOG_VIEW_PERMISSION)),
):
    """拉取容器日志：按行数（tail_lines）或按时间段（since/until，unix 秒）。"""
    h = _require_docker_host_by_name(db, host_name)

    params = []
    if since is not None:
        params.append(f"since={int(since)}")
        if until is not None:
            params.append(f"until={int(until)}")
        # since 模式不传 tail，由 Agent 用 5000 行大默认（时间窗做主过滤）
        tail_echo: int | None = None
    else:
        tail = _normalize_log_tail_lines(tail_lines)
        params.append(f"tail={tail}")
        tail_echo = tail

    qs = "&".join(params)
    result = _proxy_to_agent(h, "GET", f"/containers/{container_id}/logs?{qs}")
    return {
        "code": 0,
        "data": {
            "logs": result.get("logs", ""),
            "tail": result.get("tail", tail_echo),
            "since": since,
            "until": until,
        },
    }


@router.get("/hosts/{host_name}/containers/{container_id}/inspect")
def api_container_inspect(
    host_name: str,
    container_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required(DOCKER_LOG_VIEW_PERMISSION)),
):
    """获取容器 inspect 详情：透传 Agent 返回的完整 attrs，字段裁剪交给前端。"""
    h = _require_docker_host_by_name(db, host_name)
    result = _proxy_to_agent(h, "GET", f"/containers/{container_id}/inspect")
    return {"code": 0, "data": {"inspect": result.get("inspect", {})}}


@router.get("/hosts/{host_name}/containers/{container_id}/trends")
def api_container_trends(
    host_name: str,
    container_id: str,
    minutes: int = 60,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required(DOCKER_LOG_VIEW_PERMISSION)),
):
    """容器指标历史趋势（自建历史表，由后台轮询采样）。"""
    h = _require_docker_host_by_name(db, host_name)
    data = get_container_trends(db, h.id, container_id, minutes=minutes)
    if data is None:
        raise HTTPException(status_code=404, detail="容器不存在")
    return {"code": 0, "data": data}


# ─── SSE：近实时日志流 ─────────────────────────────────────


@router.get("/hosts/{host_name}/containers/{container_id}/logs/stream")
async def api_container_logs_stream(
    host_name: str,
    container_id: str,
    request: Request,
    token: str | None = None,
    since: int | None = None,
    interval: int = 2,
    db: Session = Depends(get_db),
):
    """SSE 近实时日志流：每 interval 秒向 Agent 轮询 since 之后的日志并推送新行。

    EventSource 无法自定义请求头，因此鉴权用 ``?token=<JWT>``。
    鉴权失败直接 401（EventSource 规范：首次响应非 200 → CLOSED 且不自动重连，
    不会造成无限重连）。
    """
    user, err = validate_stream_token(token, DOCKER_LOG_VIEW_PERMISSION)
    if err is not None or user is None:
        raise HTTPException(status_code=401, detail=err or "Authentication required")

    h = _require_docker_host_by_name(db, host_name)
    interval = max(1, min(int(interval), 30))

    return StreamingResponse(
        _log_event_stream(h.endpoint, container_id, since, interval, request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _log_event_stream(
    endpoint: str,
    container_id: str,
    since_arg: int | None,
    interval: int,
    request: Request,
):
    """轮询 Agent 的 /logs?since= 端点，对相邻批次做秒级去重后以 SSE 推送新行。"""
    # endpoint 以字符串传入：生成器生命周期长于 DB 会话，避免访问已 detach 的模型对象
    base = endpoint if endpoint.startswith("http") else f"http://{endpoint}"
    url = f"{base}/containers/{container_id}/logs"
    timeout = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)

    async def fetch(last_ts: int) -> str:
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(url, params={"since": last_ts, "tail": 1000})
                data = resp.json()
                return data.get("logs", "") or ""
        except (httpx.HTTPError, ValueError) as e:
            # 单次拉取失败不致命：交给通用流发 error 事件后继续
            raise RuntimeError(f"Agent 拉取失败: {e}") from e

    async for event in polling_log_stream(request, interval, since_arg, fetch):
        yield event


# ─── 容器操作（代理到 Agent）─────────────────────────────────

def _proxy_to_agent(host: ContainerCluster, method: str, path: str) -> dict:
    """代理请求到 Docker Agent。"""
    endpoint = host.endpoint
    if not endpoint.startswith("http"):
        endpoint = f"http://{endpoint}"

    try:
        resp = http_requests.request(method, f"{endpoint}{path}", timeout=15)
        if resp.status_code < 400 and not (getattr(resp, "text", "") or "").strip():
            return {}
        try:
            data = resp.json()
        except ValueError:
            if resp.status_code >= 400:
                detail = _agent_error_detail(resp.status_code, getattr(resp, "text", ""), method)
                raise HTTPException(status_code=502, detail=detail)
            return {"message": (getattr(resp, "text", "") or "").strip()}
        if resp.status_code >= 400:
            raise HTTPException(status_code=resp.status_code, detail=data.get("error", "Agent 请求失败"))
        return data
    except http_requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Agent 连接失败: {e}")


def _agent_error_detail(status_code: int, body: str, method: str) -> str:
    text = (body or "").strip()
    if status_code == 501 and f"Unsupported method ('{method}')" in text:
        return "当前 Docker Agent 版本不支持容器操作，请在目标主机拉取最新镜像并重建 ops-agent 后重试。"
    if text.startswith("<"):
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", unescape(text)).strip()
    return (text or "Agent 请求失败")[:500]


@router.post("/hosts/{host_name}/containers/{container_id}/{action}")
def api_container_action(
    host_name: str,
    container_id: str,
    action: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("containers.update")),
):
    """对容器执行操作：start / stop / restart / delete。"""
    if action not in ("start", "stop", "restart", "delete"):
        raise HTTPException(status_code=400, detail="不支持的操作")

    h = _require_docker_host_by_name(db, host_name)

    result = _proxy_to_agent(h, "POST", f"/containers/{container_id}/{action}")

    action_labels = {"start": "启动", "stop": "停止", "restart": "重启", "delete": "删除"}
    write_log(
        db, user=current_user, action=action, target_type="docker_container",
        target_id=0, target_name=container_id,
        detail=f"{action_labels[action]}容器 {container_id}（主机 {h.name}）",
        ip_address=get_client_ip(request),
    )
    db.commit()

    return {"code": 0, "msg": result.get("message", "操作成功")}
