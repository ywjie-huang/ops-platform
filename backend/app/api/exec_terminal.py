"""容器交互式终端（exec）WebSocket 桥接。

高风险能力：默认不挂载，需通过 ENABLE_EXEC_TERMINAL 开启（见 app/api/__init__.py），
并要求 containers.exec 权限。鉴权复用 SSH 终端的首帧 token 模式。
"""
from __future__ import annotations

import asyncio
import json
import logging
from urllib.parse import urlparse

import websockets
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.api.ssh_terminal import (
    AUTH_TIMEOUT_SECONDS,
    _authenticate_websocket_user,
    _close_websocket,
)
from app.db.database import SessionLocal
from app.models.container import ContainerCluster
from app.services.audit import write_log
from sqlalchemy import select

logger = logging.getLogger(__name__)

EXEC_PERMISSION = "containers.exec"
DEFAULT_COMMAND = "/bin/sh"
router = APIRouter(tags=["容器终端"])


# ─── 公共辅助 ──────────────────────────────────────────────

def _client_ip(websocket: WebSocket) -> str:
    forwarded = websocket.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if websocket.headers.get("x-real-ip"):
        return websocket.headers["x-real-ip"].strip()
    if websocket.client:
        return websocket.client.host or ""
    return ""


def _resolve_cluster(db, name: str) -> ContainerCluster | None:
    return db.scalar(
        select(ContainerCluster).where(
            ContainerCluster.name == name,
            ContainerCluster.provider == "kubernetes",
        )
    )


def _resolve_docker_host(db, name: str) -> ContainerCluster | None:
    return db.scalar(
        select(ContainerCluster).where(
            ContainerCluster.name == name,
            ContainerCluster.provider == "docker",
        )
    )


async def _send_ready(websocket: WebSocket) -> None:
    await websocket.send_text(json.dumps({"type": "ready"}))


async def _send_error_and_close(websocket: WebSocket, message: str) -> None:
    try:
        await websocket.send_text(json.dumps({"type": "error", "message": message}))
    finally:
        await _close_websocket(websocket, 1011, message)


# ─── K8s exec ─────────────────────────────────────────────

def _build_core_v1(endpoint: str, token: str):
    """构造 K8s CoreV1Api 客户端（TLS 不校验，与 k8s.py 行为一致）。"""
    from kubernetes import client

    host = endpoint if endpoint.startswith("http") else f"https://{endpoint}"
    configuration = client.Configuration()
    configuration.host = host.rstrip("/")
    configuration.api_key = {"authorization": f"Bearer {token}"}
    configuration.verify_ssl = False
    configuration.assert_hostname = False
    configuration.ssl_ca_cert = None
    api_client = client.ApiClient(configuration)
    return client.CoreV1Api(api_client)


def _open_exec_stream(core_v1, namespace: str, pod_name: str, container: str, command: list[str]):
    """打开交互式 exec 流，返回 kubernetes WSClient。"""
    from kubernetes.stream import stream as kube_stream

    return kube_stream(
        core_v1.connect_get_namespaced_pod_exec,
        name=pod_name,
        namespace=namespace,
        container=container or None,
        command=command,
        stderr=True,
        stdin=True,
        stdout=True,
        tty=True,
        _preload_content=False,
    )


def _poll_exec(ws_client) -> tuple[str, str, bool]:
    """处理一帧 K8s exec 输出（阻塞最长约 1s），返回 (stdout, stderr, closed)。"""
    if not ws_client.is_open():
        return "", "", True
    ws_client.update(timeout=1)
    out = ws_client.read_stdout() if ws_client.peek_stdout() else ""
    err = ws_client.read_stderr() if ws_client.peek_stderr() else ""
    return out, err, False


@router.websocket("/ws/exec/k8s/{cluster_name}/pods/{namespace}/{pod_name}")
async def ws_k8s_exec(
    websocket: WebSocket,
    cluster_name: str,
    namespace: str,
    pod_name: str,
    command: str = Query(default=DEFAULT_COMMAND),
    container: str = Query(default=""),
):
    """浏览器 ↔ K8s API server exec 桥接。"""
    await websocket.accept()

    try:
        auth_msg = await asyncio.wait_for(websocket.receive_text(), timeout=AUTH_TIMEOUT_SECONDS)
        auth = json.loads(auth_msg)
    except (asyncio.TimeoutError, json.JSONDecodeError):
        await _close_websocket(websocket, 1008, "鉴权超时或无效")
        return
    except WebSocketDisconnect:
        return

    if not isinstance(auth, dict):
        await _close_websocket(websocket, 1008, "无效的鉴权消息")
        return

    token = auth.pop("token", None)
    current_user, auth_error = _authenticate_websocket_user(
        token, permission=EXEC_PERMISSION, permission_error="无容器终端权限"
    )
    if auth_error:
        await _close_websocket(websocket, 1008, auth_error)
        return

    db = SessionLocal()
    try:
        cluster = _resolve_cluster(db, cluster_name)
        if cluster is None:
            await _send_error_and_close(websocket, "集群不存在")
            return
        if not cluster.token:
            await _send_error_and_close(websocket, "集群未配置 Token，无法 exec")
            return
    finally:
        db.close()

    command_argv = [c for c in (command or DEFAULT_COMMAND).split() if c] or [DEFAULT_COMMAND]

    try:
        core_v1 = _build_core_v1(cluster.endpoint, cluster.token)
        ws_client = _open_exec_stream(core_v1, namespace, pod_name, container, command_argv)
    except Exception as e:
        logger.warning("K8s exec 建立失败 [%s/%s]: %s", namespace, pod_name, e)
        await _send_error_and_close(websocket, f"无法进入容器：{e}")
        return

    # 审计
    db = SessionLocal()
    try:
        write_log(
            db, user=current_user, action="k8s_exec", target_type="pod",
            target_name=f"{cluster_name}/{namespace}/{pod_name}",
            ip_address=_client_ip(websocket),
            detail=f"进入 Pod 终端：{cluster_name}/{namespace}/{pod_name} (cmd={command_argv[0]})",
        )
        db.commit()
    finally:
        db.close()

    await _send_ready(websocket)

    async def k8s_to_ws():
        try:
            while True:
                out, err, closed = await asyncio.to_thread(_poll_exec, ws_client)
                if closed:
                    break
                if out:
                    await websocket.send_text(out)
                if err:
                    await websocket.send_text(err)
        except Exception as e:  # noqa: BLE001
            logger.debug("K8s exec 读取循环结束: %s", e)
        try:
            await websocket.send_text("\r\n\x1b[33m容器终端已断开\x1b[0m\r\n")
            await websocket.close()
        except Exception:  # noqa: BLE001
            pass

    async def ws_to_k8s():
        while True:
            try:
                msg = await websocket.receive_text()
            except WebSocketDisconnect:
                break
            if msg.startswith("{"):
                try:
                    data = json.loads(msg)
                    if "cols" in data and "rows" in data:
                        ws_client.write_channel(
                            4, json.dumps({"Width": int(data["cols"]), "Height": int(data["rows"])})
                        )
                        continue
                except (json.JSONDecodeError, ValueError, TypeError):
                    pass
            try:
                ws_client.write_stdin(msg)
            except Exception as e:  # noqa: BLE001
                logger.debug("K8s exec stdin 写入失败: %s", e)
                break

    try:
        await asyncio.gather(k8s_to_ws(), ws_to_k8s())
    finally:
        try:
            ws_client.write_channel(3, json.dumps({"status": "exit"}))
        except Exception:  # noqa: BLE001
            pass


# ─── Docker exec（backend ↔ agent WebSocket 三跳桥接）─────

def _agent_exec_url(endpoint: str, container_id: str) -> str:
    """Agent exec WS 地址：约定 exec WS 端口 = HTTP 端口 + 1（agent 默认 9002）。"""
    raw = endpoint if endpoint.startswith("http") else f"http://{endpoint}"
    parsed = urlparse(raw)
    host = parsed.hostname or ""
    port = (parsed.port or 9001) + 1
    return f"ws://{host}:{port}/containers/{container_id}/exec"


@router.websocket("/ws/exec/docker/{host_name}/containers/{container_id}")
async def ws_docker_exec(
    websocket: WebSocket,
    host_name: str,
    container_id: str,
    command: str = Query(default=DEFAULT_COMMAND),
):
    """浏览器 ↔ Docker agent exec 桥接。"""
    await websocket.accept()

    try:
        auth_msg = await asyncio.wait_for(websocket.receive_text(), timeout=AUTH_TIMEOUT_SECONDS)
        auth = json.loads(auth_msg)
    except (asyncio.TimeoutError, json.JSONDecodeError):
        await _close_websocket(websocket, 1008, "鉴权超时或无效")
        return
    except WebSocketDisconnect:
        return

    if not isinstance(auth, dict):
        await _close_websocket(websocket, 1008, "无效的鉴权消息")
        return

    token = auth.pop("token", None)
    current_user, auth_error = _authenticate_websocket_user(
        token, permission=EXEC_PERMISSION, permission_error="无容器终端权限"
    )
    if auth_error:
        await _close_websocket(websocket, 1008, auth_error)
        return

    db = SessionLocal()
    try:
        host = _resolve_docker_host(db, host_name)
        if host is None:
            await _send_error_and_close(websocket, "主机不存在")
            return
        if not host.endpoint:
            await _send_error_and_close(websocket, "主机未配置 Agent 地址")
            return
    finally:
        db.close()

    command_argv = [c for c in (command or DEFAULT_COMMAND).split() if c] or [DEFAULT_COMMAND]
    agent_url = _agent_exec_url(host.endpoint, container_id)

    try:
        agent_ws = await websockets.connect(agent_url, open_timeout=10, max_size=None)
    except Exception as e:  # noqa: BLE001
        logger.warning("连接 Docker agent exec 失败 %s: %s", agent_url, e)
        await _send_error_and_close(websocket, f"无法连接 Agent：{e}")
        return

    # 审计
    db = SessionLocal()
    try:
        write_log(
            db, user=current_user, action="docker_exec", target_type="container",
            target_name=f"{host_name}/{container_id}",
            ip_address=_client_ip(websocket),
            detail=f"进入容器终端：{host_name}/{container_id} (cmd={command_argv[0]})",
        )
        db.commit()
    finally:
        db.close()

    try:
        await agent_ws.send(json.dumps({"command": command_argv}))
        await _send_ready(websocket)

        async def agent_to_browser():
            try:
                async for msg in agent_ws:
                    if isinstance(msg, (bytes, bytearray)):
                        msg = msg.decode("utf-8", errors="replace")
                    await websocket.send_text(msg)
            except Exception as e:  # noqa: BLE001
                logger.debug("Agent→浏览器 读取结束: %s", e)
            # Agent exec WS 关闭后透出异常关闭原因，避免 exec 失败时前端只看到连接静默断开。
            code = getattr(agent_ws, "close_code", None)
            reason = (getattr(agent_ws, "close_reason", None) or "").strip()
            if code not in (None, 1000, 1001):
                logger.warning(
                    "Docker agent exec WS 异常关闭 code=%s reason=%s [%s]",
                    code, reason or "(空)", f"{host_name}/{container_id}",
                )
                if reason:
                    try:
                        await websocket.send_text(
                            json.dumps({"type": "error", "message": f"Agent: {reason}"})
                        )
                    except Exception:  # noqa: BLE001
                        pass

        async def browser_to_agent():
            while True:
                try:
                    msg = await websocket.receive_text()
                except WebSocketDisconnect:
                    break
                try:
                    await agent_ws.send(msg)
                except Exception as e:  # noqa: BLE001
                    logger.debug("浏览器→Agent 写入失败: %s", e)
                    break

        await asyncio.gather(agent_to_browser(), browser_to_agent())
    finally:
        try:
            await agent_ws.close()
        except Exception:  # noqa: BLE001
            pass
        try:
            await websocket.close()
        except Exception:  # noqa: BLE001
            pass
