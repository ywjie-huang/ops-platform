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


@router.websocket("/ws/ssh/{asset_id}")
async def ws_ssh(websocket: WebSocket, asset_id: int):
    """WebSocket → SSH 桥接。"""
    await websocket.accept()

    # 等待客户端发送认证信息（用户名/密码），或使用资产自带凭据
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
    port = int(auth.get("port", asset.ssh_port or 22))
    username = auth.get("username", asset.ssh_username or "root")
    password = auth.get("password", asset.ssh_password or "")

    if not password:
        await websocket.send_text("\r\n\x1b[31m错误：未配置 SSH 密码\x1b[0m\r\n")
        await websocket.close()
        return

    # 建立 SSH 连接
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(
            hostname=host,
            port=port,
            username=username,
            password=password,
            timeout=10,
            allow_agent=False,
            look_for_keys=False,
        )
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
        write_log(db, user=None, action="ssh_connect", target_type="asset",
                  target_id=asset.id, target_name=asset.name,
                  ip_address=client_ip, detail=f"SSH 连接到 {host}")
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
