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
AGENT_READY_TIMEOUT_SECONDS = 15
router = APIRouter(tags=["容器终端"])


class AgentExecHandshakeError(RuntimeError):
    pass


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


def _agent_message_text(message) -> str:
    if isinstance(message, (bytes, bytearray)):
        return message.decode("utf-8", errors="replace")
    return str(message)


def _agent_control_frame(message) -> dict | None:
    text = _agent_message_text(message)
    if not text.startswith("{"):
        return None
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict) or payload.get("type") not in {"ready", "error"}:
        return None
    return payload


async def _wait_for_agent_ready(agent_ws):
    try:
        first_message = await asyncio.wait_for(
            agent_ws.recv(), timeout=AGENT_READY_TIMEOUT_SECONDS
        )
    except asyncio.TimeoutError as e:
        raise AgentExecHandshakeError(
            "Agent 启动容器终端超时，请确认 Agent 已升级并支持 exec 就绪握手"
        ) from e
    except Exception as e:
        reason = (
            getattr(e, "reason", None)
            or getattr(agent_ws, "close_reason", None)
            or str(e)
            or "连接已关闭"
        )
        raise AgentExecHandshakeError(f"Agent 在容器终端就绪前断开：{reason}") from e

    control = _agent_control_frame(first_message)
    if control is None:
        # 旧版 Agent 没有 ready 控制帧；收到实际输出也能证明 exec 已建立。
        return first_message
    if control["type"] == "error":
        message = str(control.get("message") or "Agent 无法启动容器终端")
        raise AgentExecHandshakeError(message)
    return None


async def _run_bridge_until_closed(*coroutines) -> None:
    tasks = [asyncio.create_task(coroutine) for coroutine in coroutines]
    try:
        _, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
        results = await asyncio.gather(*tasks, return_exceptions=True)
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, BaseException) and not isinstance(result, asyncio.CancelledError):
            raise result


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

    logger.info(
        "exec[docker] Agent 已连接 %s command=%s [%s]",
        agent_url, command_argv, f"{host_name}/{container_id}",
    )

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
        try:
            await agent_ws.send(json.dumps({"command": command_argv}))
            buffered_output = await _wait_for_agent_ready(agent_ws)
        except AgentExecHandshakeError as e:
            logger.warning(
                "exec[docker] Agent 就绪失败: %s [%s]", e, f"{host_name}/{container_id}"
            )
            await _send_error_and_close(websocket, str(e))
            return
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "exec[docker] 命令发送失败: %s [%s]", e, f"{host_name}/{container_id}"
            )
            await _send_error_and_close(websocket, f"无法启动 Agent 容器终端：{e}")
            return

        await _send_ready(websocket)
        if buffered_output is not None:
            await websocket.send_text(_agent_message_text(buffered_output))
        logger.info("exec[docker] Agent 已就绪，进入双向桥接 [%s]", f"{host_name}/{container_id}")

        async def agent_to_browser():
            try:
                async for msg in agent_ws:
                    if isinstance(msg, (bytes, bytearray)):
                        msg = msg.decode("utf-8", errors="replace")
                    await websocket.send_text(msg)
            except Exception as e:  # noqa: BLE001
                logger.info("exec[docker] Agent→浏览器 异常: %s [%s]", e, f"{host_name}/{container_id}")
            # Agent exec WS 关闭后记录关闭码；异常关闭时把原因透传给前端，避免静默断开。
            code = getattr(agent_ws, "close_code", None)
            reason = (getattr(agent_ws, "close_reason", None) or "").strip()
            logger.info(
                "exec[docker] Agent 侧关闭 code=%s reason=%s [%s]",
                code, reason or "(空)", f"{host_name}/{container_id}",
            )
            if code not in (None, 1000, 1001) and reason:
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
                    logger.info("exec[docker] 浏览器侧断开 [%s]", f"{host_name}/{container_id}")
                    break
                try:
                    await agent_ws.send(msg)
                except Exception as e:  # noqa: BLE001
                    logger.debug("浏览器→Agent 写入失败: %s", e)
                    break

        await _run_bridge_until_closed(agent_to_browser(), browser_to_agent())
    finally:
        try:
            await agent_ws.close()
        except Exception:  # noqa: BLE001
            pass
        try:
            await websocket.close()
        except Exception:  # noqa: BLE001
            pass
