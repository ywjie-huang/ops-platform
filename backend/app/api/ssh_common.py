"""SSH 共享工具函数 — 终端和 SFTP 共用。"""
from __future__ import annotations

import logging
from typing import Any

import paramiko

from app.db.database import SessionLocal
from app.models.asset import Asset
from app.models.ssh_key import SSHKey

logger = logging.getLogger(__name__)


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
