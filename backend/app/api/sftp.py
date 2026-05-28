"""SFTP 文件管理 HTTP API。"""
from __future__ import annotations

import os
import stat
from datetime import datetime

from app.core.config import CHINA_TZ

import paramiko
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.asset import Asset
from app.services.audit import write_log
from app.api.ssh_common import _build_ssh_client

router = APIRouter(prefix="/ssh", tags=["SFTP 文件管理"])


# ── 工具函数 ──

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
            "modified": datetime.fromtimestamp(entry.st_mtime, tz=CHINA_TZ).strftime("%Y-%m-%d %H:%M:%S") if entry.st_mtime else "",
            "owner": str(entry.st_uid),
            "group": str(entry.st_gid),
        })
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


# ── 路由 ──

@router.get("/{asset_id}/sftp/list", summary="列出目录内容")
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


@router.get("/{asset_id}/sftp/read", summary="读取文件内容")
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


@router.post("/{asset_id}/sftp/write", summary="写入文件内容")
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


@router.post("/{asset_id}/sftp/upload", summary="上传文件")
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
            write_log(db, user=None, action="sftp_upload", target_type="asset",
                      target_id=asset.id, target_name=asset.name,
                      detail=f"上传文件: {remote_path} ({len(content)} bytes)")
            db.commit()
        finally:
            sftp.close()
    finally:
        ssh.close()

    return {"message": "上传成功", "data": {"path": remote_path, "size": len(content)}}


@router.get("/{asset_id}/sftp/download", summary="下载文件")
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


@router.post("/{asset_id}/sftp/mkdir", summary="创建目录")
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


@router.post("/{asset_id}/sftp/remove", summary="删除文件/目录")
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


@router.post("/{asset_id}/sftp/rename", summary="重命名")
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


@router.get("/{asset_id}/sftp/stat", summary="获取文件/目录信息")
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
                "modified": datetime.fromtimestamp(st.st_mtime, tz=CHINA_TZ).strftime("%Y-%m-%d %H:%M:%S") if st.st_mtime else "",
                "owner": str(st.st_uid),
                "group": str(st.st_gid),
            }}
        finally:
            sftp.close()
    finally:
        ssh.close()
