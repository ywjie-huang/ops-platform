"""SSH WebSocket 终端。"""
from __future__ import annotations

import asyncio
import json
import logging
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.jwt import decode_access_token
from app.db.database import SessionLocal
from app.models.asset import Asset
from app.models.user import User
from app.services.audit import write_log
from app.services.permissions import has_permission
from app.services.token_blacklist import is_revoked
from app.services.users import get_user
from app.api.ssh_common import _build_ssh_client, _get_ssh_key_sync

logger = logging.getLogger(__name__)

SSH_TERMINAL_PERMISSION = "ssh_terminal.connect"
AUTH_TIMEOUT_SECONDS = 10


def _authenticate_websocket_user(
    token: object,
    permission: str = SSH_TERMINAL_PERMISSION,
    permission_error: str = "SSH terminal permission required",
) -> tuple[User | None, str | None]:
    """Validate the token sent in the first WebSocket message before SSH use.

    ``permission`` 为该 WS 端点要求的权限码；默认校验 SSH 终端连接权限。
    """
    if not isinstance(token, str) or not token.strip():
        return None, "Authentication required"

    payload = decode_access_token(token)
    if payload is None:
        return None, "Authentication failed"
    if is_revoked(payload.get("jti")):
        return None, "Session expired"

    subject = payload.get("sub")
    if isinstance(subject, bool):
        return None, "Authentication failed"
    try:
        user_id = int(subject)
    except (TypeError, ValueError):
        return None, "Authentication failed"

    db = SessionLocal()
    try:
        user = get_user(db, user_id)
        if user is None:
            return None, "Authentication failed"
        if not has_permission(user, permission):
            return None, permission_error
        return user, None
    finally:
        db.close()


async def _close_websocket(websocket: WebSocket, code: int, reason: str) -> None:
    # RFC 6455 limits close reasons to 123 UTF-8 bytes.
    safe_reason = reason.encode("utf-8")[:123].decode("utf-8", errors="ignore")
    try:
        await websocket.close(code=code, reason=safe_reason)
    except RuntimeError:
        pass

router = APIRouter(tags=["SSH 终端"])


def _get_asset_sync(asset_id: int) -> Asset | None:
    db = SessionLocal()
    try:
        return db.query(Asset).filter(Asset.id == asset_id).first()
    finally:
        db.close()


def _read_channel(channel) -> str | None:
    data = b""
    for _ in range(5):
        if channel.recv_ready():
            break
        time.sleep(0.1)
    while channel.recv_ready():
        chunk = channel.recv(4096)
        if not chunk:
            return None if not data else data.decode("utf-8", errors="replace")
        data += chunk
        time.sleep(0.01)
    if data:
        return data.decode("utf-8", errors="replace")
    return ""


@router.websocket("/ws/ssh/{asset_id}")
async def ws_ssh(websocket: WebSocket, asset_id: int):
    """WebSocket → SSH 桥接。"""
    await websocket.accept()

    try:
        auth_msg = await asyncio.wait_for(websocket.receive_text(), timeout=AUTH_TIMEOUT_SECONDS)
        auth = json.loads(auth_msg)
    except asyncio.TimeoutError:
        await _close_websocket(websocket, 1008, "Authentication timed out")
        return
    except WebSocketDisconnect:
        return
    except json.JSONDecodeError:
        await _close_websocket(websocket, 1008, "Invalid authentication payload")
        return

    if not isinstance(auth, dict):
        await _close_websocket(websocket, 1008, "Invalid authentication payload")
        return

    token = auth.pop("token", None)
    current_user, auth_error = _authenticate_websocket_user(token)
    if auth_error:
        await _close_websocket(websocket, 1008, auth_error)
        return

    asset = _get_asset_sync(asset_id)
    if asset is None:
        await websocket.send_text("\r\n\x1b[31m错误：资产不存在\x1b[0m\r\n")
        await websocket.close()
        return

    try:
        ssh, username, host = _build_ssh_client(asset, auth)
    except Exception as e:
        await websocket.send_text(f"\r\n\x1b[31m{e}\x1b[0m\r\n")
        await websocket.close()
        return

    # 审计日志
    client_ip = ""
    forwarded = websocket.headers.get("x-forwarded-for")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    elif websocket.headers.get("x-real-ip"):
        client_ip = websocket.headers["x-real-ip"].strip()
    elif websocket.client:
        client_ip = websocket.client.host or ""

    db = SessionLocal()
    try:
        key_id = auth.get("key_id")
        ssh_key = _get_ssh_key_sync(key_id) if key_id else None
        auth_method = f"密钥[{ssh_key.name}]" if ssh_key else "密码"
        write_log(db, user=current_user, action="ssh_connect", target_type="asset",
                  target_id=asset.id, target_name=asset.name,
                  ip_address=client_ip, detail=f"SSH 连接到 {asset.ip_address} ({auth_method})")
        db.commit()
    finally:
        db.close()

    await websocket.send_text(f"\r\n\x1b[32m已连接到 {asset.ip_address} ({username})\x1b[0m\r\n")

    transport = ssh.get_transport()
    channel = transport.open_session()
    channel.get_pty(term="xterm-256color", width=120, height=40)
    channel.invoke_shell()

    async def ssh_to_ws():
        loop = asyncio.get_event_loop()
        while True:
            try:
                if channel.closed:
                    break
                data = await loop.run_in_executor(None, _read_channel, channel)
                if data is None:
                    break
                if data:
                    await websocket.send_text(data)
                await asyncio.sleep(0.02)
            except Exception as e:
                logger.debug('SSH channel read failed: %s', e)
                break
        try:
            await websocket.send_text("\r\n\x1b[33mSSH 连接已断开\x1b[0m\r\n")
            await websocket.close()
        except Exception as e:
            logger.debug('WS close after SSH disconnect failed: %s', e)

    async def ws_to_ssh():
        while True:
            try:
                msg = await websocket.receive_text()
                if msg.startswith("{"):
                    try:
                        data = json.loads(msg)
                        if "cols" in data and "rows" in data:
                            channel.resize_pty(width=data["cols"], height=data["rows"])
                            continue
                    except json.JSONDecodeError:
                        pass
                channel.send(msg)
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.debug('WS-to-SSH channel failed: %s', e)
                break

    try:
        await asyncio.gather(ssh_to_ws(), ws_to_ssh())
    finally:
        channel.close()
        ssh.close()
