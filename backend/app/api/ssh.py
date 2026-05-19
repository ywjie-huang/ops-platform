"""SSH 终端 + SFTP 文件管理 WebSocket 代理。"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import stat
import time
from datetime import datetime
from typing import Any

import paramiko
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.database import SessionLocal, get_db
from app.models.asset import Asset
from app.models.ssh_key import SSHKey
from app.services.audit import write_log

logger = logging.getLogger(__name__)

router = APIRouter(tags=["SSH 终端"])


# ── 工具函数 ──

def _get_asset_sync(asset_id: int) -> Asset | None:
    db = SessionLocal()
    try:
        return db.query(Asset).filter(Asset.id == asset_id).first()
    finally:
        db.close()


def _get_ssh_key_sync(key_id: int) -> SSHKey | None:
    db = SessionLocal()
    try:
        return db.query(SSHKey).filter(SSHKey.id == key_id).first()
    finally:
        db.close()


def _get_default_ssh_key_sync() -> SSHKey | None:
    db = SessionLocal()
    try:
        return db.query(SSHKey).filter(SSHKey.is_default == True).first()
    finally:
        db.close()


def _build_ssh_client(asset: Asset, auth: dict[str, Any]) -> tuple[paramiko.SSHClient, str, str]:
    """建立 SSH 连接，返回 (client, username, host)。"""
    host = asset.ip_address

    key_id = auth.get("key_id")
    ssh_key = None
    if key_id:
        ssh_key = _get_ssh_key_sync(key_id)
    elif "key_id" not in auth:
        ssh_key = _get_default_ssh_key_sync()

    if ssh_key:
        port = ssh_key.port or int(asset.ssh_port or 22)
        username = ssh_key.username or asset.ssh_username or "root"
        if ssh_key.auth_type == "key" and ssh_key.private_key:
            from io import StringIO
            pkey = None
            for KeyClass in [paramiko.RSAKey, paramiko.Ed25519Key, paramiko.ECDSAKey]:
                try:
                    key_file = StringIO(ssh_key.private_key)
                    pkey = KeyClass.from_private_key(
                        key_file, password=ssh_key.passphrase or None
                    )
                    break
                except paramiko.SSHException:
                    continue
            if not pkey:
                raise ValueError("私钥解析失败，请检查私钥格式")
            password = None
        else:
            pkey = None
            password = ssh_key.password or ""
    else:
        port = int(auth.get("port", asset.ssh_port or 22))
        username = auth.get("username", asset.ssh_username or "root")
        password = auth.get("password", asset.ssh_password or "")
        pkey = None

    if not password and not pkey:
        raise ValueError("未配置 SSH 密码或密钥")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

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
    return ssh, username, host


def _sftp_list(sftp: paramiko.SFTPClient, path: str) -> list[dict]:
    """列出目录内容。"""
    result = []
    for entry in sftp.listdir_attr(path):
        full_path = f"{path.rstrip('/')}/{entry.filename}"
        is_dir = stat.S_ISDIR(entry.st_mode)
        result.append({
            "name": entry.filename,
            "path": full_path,
            "is_dir": is_dir,
            "size": entry.st_size if not is_dir else 0,
            "permissions": stat.filemode(entry.st_mode),
            "modified": datetime.fromtimestamp(entry.st_mtime).strftime("%Y-%m-%d %H:%M:%S") if entry.st_mtime else "",
            "owner": str(entry.st_uid),
            "group": str(entry.st_gid),
        })
    # 目录在前，文件在后，同类型按名称排序
    result.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
    return result


def _sftp_read_file(sftp: paramiko.SFTPClient, path: str, max_size: int = 2 * 1024 * 1024) -> dict:
    """读取文件内容（文本），限制 2MB。"""
    stat_info = sftp.stat(path)
    if stat_info.st_size > max_size:
        raise ValueError(f"文件过大 ({stat_info.st_size / 1024 / 1024:.1f}MB)，最大支持 {max_size / 1024 / 1024:.0f}MB")
    with sftp.open(path, "r") as f:
        content = f.read()
    return {"path": path, "content": content, "size": stat_info.st_size}


def _sftp_write_file(sftp: paramiko.SFTPClient, path: str, content: str) -> None:
    """写入文件内容。"""
    with sftp.open(path, "w") as f:
        f.write(content)


# ── WebSocket SSH 终端 ──

@router.websocket("/ws/ssh/{asset_id}")
async def ws_ssh(websocket: WebSocket, asset_id: int):
    """WebSocket → SSH 桥接。"""
    await websocket.accept()

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
        write_log(db, user=None, action="ssh_connect", target_type="asset",
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
            except Exception:
                break
        try:
            await websocket.send_text("\r\n\x1b[33mSSH 连接已断开\x1b[0m\r\n")
            await websocket.close()
        except Exception:
            pass

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
            except Exception:
                break

    try:
        await asyncio.gather(ssh_to_ws(), ws_to_ssh())
    finally:
        channel.close()
        ssh.close()


def _read_channel(channel: paramiko.Channel) -> str | None:
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


# ── SFTP 文件管理 HTTP API ──

@router.get("/ssh/{asset_id}/sftp/list", summary="列出目录内容")
def sftp_list(
    asset_id: int,
    path: str = Query("/", description="目录路径"),
    key_id: int = Query(None, description="SSH 密钥 ID"),
    db: Session = Depends(get_db),
):
    asset = db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(404, "资产不存在")

    auth = {"key_id": key_id} if key_id else {}
    try:
        ssh, _, _ = _build_ssh_client(asset, auth)
    except Exception as e:
        raise HTTPException(400, str(e))

    try:
        sftp = ssh.open_sftp()
        try:
            items = _sftp_list(sftp, path)
        finally:
            sftp.close()
    finally:
        ssh.close()

    return {"data": {"path": path, "items": items}}


@router.get("/ssh/{asset_id}/sftp/read", summary="读取文件内容")
def sftp_read(
    asset_id: int,
    path: str = Query(..., description="文件路径"),
    key_id: int = Query(None),
    db: Session = Depends(get_db),
):
    asset = db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(404, "资产不存在")

    auth = {"key_id": key_id} if key_id else {}
    try:
        ssh, _, _ = _build_ssh_client(asset, auth)
    except Exception as e:
        raise HTTPException(400, str(e))

    try:
        sftp = ssh.open_sftp()
        try:
            result = _sftp_read_file(sftp, path)
        finally:
            sftp.close()
    finally:
        ssh.close()

    return {"data": result}


@router.post("/ssh/{asset_id}/sftp/write", summary="写入文件内容")
def sftp_write(
    asset_id: int,
    path: str = Query(..., description="文件路径"),
    content: str = Form(...),
    key_id: int = Form(None),
    db: Session = Depends(get_db),
):
    asset = db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(404, "资产不存在")

    auth = {"key_id": key_id} if key_id else {}
    try:
        ssh, _, _ = _build_ssh_client(asset, auth)
    except Exception as e:
        raise HTTPException(400, str(e))

    try:
        sftp = ssh.open_sftp()
        try:
            _sftp_write_file(sftp, path, content)
        finally:
            sftp.close()
    finally:
        ssh.close()

    return {"message": "保存成功"}


@router.post("/ssh/{asset_id}/sftp/upload", summary="上传文件")
async def sftp_upload(
    asset_id: int,
    path: str = Form(..., description="目标目录"),
    file: UploadFile = File(...),
    key_id: int = Form(None),
    db: Session = Depends(get_db),
):
    asset = db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(404, "资产不存在")

    auth = {"key_id": key_id} if key_id else {}
    try:
        ssh, _, _ = _build_ssh_client(asset, auth)
    except Exception as e:
        raise HTTPException(400, str(e))

    try:
        sftp = ssh.open_sftp()
        try:
            remote_path = f"{path.rstrip('/')}/{file.filename}"
            content = await file.read()
            with sftp.open(remote_path, "wb") as f:
                f.write(content)
            # 审计
            write_log(db, user=None, action="sftp_upload", target_type="asset",
                      target_id=asset.id, target_name=asset.name,
                      detail=f"上传文件: {remote_path} ({len(content)} bytes)")
            db.commit()
        finally:
            sftp.close()
    finally:
        ssh.close()

    return {"message": "上传成功", "data": {"path": remote_path, "size": len(content)}}


@router.get("/ssh/{asset_id}/sftp/download", summary="下载文件")
def sftp_download(
    asset_id: int,
    path: str = Query(..., description="文件路径"),
    key_id: int = Query(None),
    db: Session = Depends(get_db),
):
    asset = db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(404, "资产不存在")

    auth = {"key_id": key_id} if key_id else {}
    try:
        ssh, _, _ = _build_ssh_client(asset, auth)
    except Exception as e:
        raise HTTPException(400, str(e))

    try:
        sftp = ssh.open_sftp()
        try:
            filename = os.path.basename(path)
            stat_info = sftp.stat(path)

            def file_iter():
                with sftp.open(path, "rb") as f:
                    while True:
                        chunk = f.read(65536)
                        if not chunk:
                            break
                        yield chunk
                sftp.close()
                ssh.close()

            # 审计
            write_log(db, user=None, action="sftp_download", target_type="asset",
                      target_id=asset.id, target_name=asset.name,
                      detail=f"下载文件: {path} ({stat_info.st_size} bytes)")
            db.commit()

            return StreamingResponse(
                file_iter(),
                media_type="application/octet-stream",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"',
                    "Content-Length": str(stat_info.st_size),
                },
            )
        except Exception:
            sftp.close()
            raise
    except HTTPException:
        raise
    except Exception as e:
        ssh.close()
        raise HTTPException(400, str(e))


@router.post("/ssh/{asset_id}/sftp/mkdir", summary="创建目录")
def sftp_mkdir(
    asset_id: int,
    path: str = Query(..., description="目录路径"),
    key_id: int = Query(None),
    db: Session = Depends(get_db),
):
    asset = db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(404, "资产不存在")

    auth = {"key_id": key_id} if key_id else {}
    try:
        ssh, _, _ = _build_ssh_client(asset, auth)
    except Exception as e:
        raise HTTPException(400, str(e))

    try:
        sftp = ssh.open_sftp()
        try:
            sftp.mkdir(path)
        finally:
            sftp.close()
    finally:
        ssh.close()

    return {"message": "创建成功"}


@router.post("/ssh/{asset_id}/sftp/remove", summary="删除文件/目录")
def sftp_remove(
    asset_id: int,
    path: str = Query(..., description="路径"),
    is_dir: bool = Query(False),
    key_id: int = Query(None),
    db: Session = Depends(get_db),
):
    asset = db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(404, "资产不存在")

    auth = {"key_id": key_id} if key_id else {}
    try:
        ssh, _, _ = _build_ssh_client(asset, auth)
    except Exception as e:
        raise HTTPException(400, str(e))

    try:
        sftp = ssh.open_sftp()
        try:
            if is_dir:
                sftp.rmdir(path)
            else:
                sftp.remove(path)
            write_log(db, user=None, action="sftp_delete", target_type="asset",
                      target_id=asset.id, target_name=asset.name,
                      detail=f"删除{'目录' if is_dir else '文件'}: {path}")
            db.commit()
        finally:
            sftp.close()
    finally:
        ssh.close()

    return {"message": "删除成功"}


@router.post("/ssh/{asset_id}/sftp/rename", summary="重命名")
def sftp_rename(
    asset_id: int,
    old_path: str = Query(...),
    new_path: str = Query(...),
    key_id: int = Query(None),
    db: Session = Depends(get_db),
):
    asset = db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(404, "资产不存在")

    auth = {"key_id": key_id} if key_id else {}
    try:
        ssh, _, _ = _build_ssh_client(asset, auth)
    except Exception as e:
        raise HTTPException(400, str(e))

    try:
        sftp = ssh.open_sftp()
        try:
            sftp.rename(old_path, new_path)
        finally:
            sftp.close()
    finally:
        ssh.close()

    return {"message": "重命名成功"}


@router.get("/ssh/{asset_id}/sftp/stat", summary="获取文件/目录信息")
def sftp_stat(
    asset_id: int,
    path: str = Query(...),
    key_id: int = Query(None),
    db: Session = Depends(get_db),
):
    asset = db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(404, "资产不存在")

    auth = {"key_id": key_id} if key_id else {}
    try:
        ssh, _, _ = _build_ssh_client(asset, auth)
    except Exception as e:
        raise HTTPException(400, str(e))

    try:
        sftp = ssh.open_sftp()
        try:
            st = sftp.stat(path)
            return {"data": {
                "path": path,
                "size": st.st_size,
                "is_dir": stat.S_ISDIR(st.st_mode),
                "permissions": stat.filemode(st.st_mode),
                "modified": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S") if st.st_mtime else "",
                "owner": str(st.st_uid),
                "group": str(st.st_gid),
            }}
        finally:
            sftp.close()
    finally:
        ssh.close()
