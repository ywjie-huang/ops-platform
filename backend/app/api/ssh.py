"""SSH Web Terminal — WebSocket 代理。"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import paramiko
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.models.asset import Asset
from app.models.ssh_key import SSHKey
from app.services.audit import write_log

logger = logging.getLogger(__name__)

router = APIRouter(tags=["SSH 终端"])


def _get_asset_sync(asset_id: int) -> Asset | None:
    """同步获取资产（WebSocket 不能用 Depends 注入）。"""
    db = SessionLocal()
    try:
        return db.query(Asset).filter(Asset.id == asset_id).first()
    finally:
        db.close()


def _get_ssh_key_sync(key_id: int) -> SSHKey | None:
    """同步获取 SSH 密钥。"""
    db = SessionLocal()
    try:
        return db.query(SSHKey).filter(SSHKey.id == key_id).first()
    finally:
        db.close()


def _get_default_ssh_key_sync() -> SSHKey | None:
    """获取默认 SSH 密钥。"""
    db = SessionLocal()
    try:
        return db.query(SSHKey).filter(SSHKey.is_default == True).first()
    finally:
        db.close()


@router.websocket("/ws/ssh/{asset_id}")
async def ws_ssh(websocket: WebSocket, asset_id: int):
    """WebSocket → SSH 桥接。"""
    await websocket.accept()

    # 等待客户端发送认证信息（用户名/密码/key_id），或使用资产自带凭据
    auth_msg = await websocket.receive_text()
    try:
        auth = json.loads(auth_msg)
    except json.JSONDecodeError:
        auth = {}

    asset = _get_asset_sync(asset_id)
    if asset is None:
        await websocket.send_text("\r\n\x1b[31m错误：资产不存在\x1b[0m\r\n")
        await websocket.close()
        return

    host = asset.ip_address

    # 解析认证方式：优先使用客户端指定的 key_id，其次用默认密钥，最后用资产自带密码
    key_id = auth.get("key_id")
    ssh_key = None

    if key_id:
        ssh_key = _get_ssh_key_sync(key_id)
    elif "key_id" not in auth:
        # 客户端没有传 key_id 字段时，尝试使用默认密钥
        ssh_key = _get_default_ssh_key_sync()

    if ssh_key:
        # 使用密钥认证
        port = ssh_key.port or int(asset.ssh_port or 22)
        username = ssh_key.username or asset.ssh_username or "root"

        if ssh_key.auth_type == "key" and ssh_key.private_key:
            # 私钥认证
            try:
                from io import StringIO
                key_file = StringIO(ssh_key.private_key)
                if ssh_key.passphrase:
                    pkey = paramiko.RSAKey.from_private_key(key_file, password=ssh_key.passphrase)
                else:
                    pkey = paramiko.RSAKey.from_private_key(key_file)
            except paramiko.SSHException:
                # 尝试 Ed25519
                try:
                    key_file = StringIO(ssh_key.private_key)
                    if ssh_key.passphrase:
                        pkey = paramiko.Ed25519Key.from_private_key(key_file, password=ssh_key.passphrase)
                    else:
                        pkey = paramiko.Ed25519Key.from_private_key(key_file)
                except Exception as e:
                    await websocket.send_text(f"\r\n\x1b[31m私钥解析失败：{e}\x1b[0m\r\n")
                    await websocket.close()
                    return

            password = None
        else:
            # 密码认证
            pkey = None
            password = ssh_key.password or ""
    else:
        # 使用资产自带凭据
        port = int(auth.get("port", asset.ssh_port or 22))
        username = auth.get("username", asset.ssh_username or "root")
        password = auth.get("password", asset.ssh_password or "")
        pkey = None

    if not password and not pkey:
        await websocket.send_text("\r\n\x1b[31m错误：未配置 SSH 密码或密钥\x1b[0m\r\n")
        await websocket.close()
        return

    # 建立 SSH 连接
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        connect_kwargs: dict[str, Any] = {
            "hostname": host,
            "port": port,
            "username": username,
            "timeout": 10,
            "allow_agent": False,
            "look_for_keys": False,
        }
        if pkey:
            connect_kwargs["pkey"] = pkey
        else:
            connect_kwargs["password"] = password

        ssh.connect(**connect_kwargs)
    except Exception as e:
        await websocket.send_text(f"\r\n\x1b[31mSSH 连接失败：{e}\x1b[0m\r\n")
        await websocket.close()
        return

    # 提取客户端真实 IP
    client_ip = ""
    forwarded = websocket.headers.get("x-forwarded-for")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    elif websocket.headers.get("x-real-ip"):
        client_ip = websocket.headers["x-real-ip"].strip()
    elif websocket.client:
        client_ip = websocket.client.host or ""

    # 记录审计日志
    db = SessionLocal()
    try:
        auth_method = f"密钥[{ssh_key.name}]" if ssh_key else "密码"
        write_log(db, user=None, action="ssh_connect", target_type="asset",
                  target_id=asset.id, target_name=asset.name,
                  ip_address=client_ip, detail=f"SSH 连接到 {host} (认证方式: {auth_method})")
        db.commit()
    finally:
        db.close()

    await websocket.send_text(f"\r\n\x1b[32m已连接到 {host} ({username})\x1b[0m\r\n")

    # 打开交互式 Shell
    transport = ssh.get_transport()
    channel = transport.open_session()
    channel.get_pty(term="xterm-256color", width=120, height=40)
    channel.invoke_shell()

    # 设置非阻塞
    async def ssh_to_ws():
        """SSH 输出 → WebSocket。"""
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
            except Exception:
                break
        try:
            await websocket.send_text("\r\n\x1b[33mSSH 连接已断开\x1b[0m\r\n")
            await websocket.close()
        except Exception:
            pass

    async def ws_to_ssh():
        """WebSocket 输入 → SSH。"""
        while True:
            try:
                msg = await websocket.receive_text()
                # 支持 JSON 消息（resize）和纯文本（输入）
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
            except Exception:
                break

    try:
        await asyncio.gather(ssh_to_ws(), ws_to_ssh())
    finally:
        channel.close()
        ssh.close()


def _read_channel(channel: paramiko.Channel) -> str | None:
    """从 SSH channel 读取数据。
    返回 None 表示连接已关闭，返回空字符串表示暂无数据。
    """
    import time
    data = b""
    # 等待数据到达（最多 0.5 秒）
    for _ in range(5):
        if channel.recv_ready():
            break
        time.sleep(0.1)
    while channel.recv_ready():
        chunk = channel.recv(4096)
        if not chunk:
            # channel 已关闭
            return None if not data else data.decode("utf-8", errors="replace")
        data += chunk
        time.sleep(0.01)
    if data:
        return data.decode("utf-8", errors="replace")
    # 没有数据但连接还活着
    return ""
