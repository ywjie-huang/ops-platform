"""
SSH 部署服务 — 上传文件 + 执行部署脚本。
复用现有的 paramiko SSH/SFTP 模式。
"""

from __future__ import annotations

import logging
import os
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.config import CHINA_TZ

logger = logging.getLogger(__name__)


def deploy_via_ssh(
    db: Session,
    *,
    asset_id: int,
    deploy_path: str,
    deploy_script: str,
    file_content: bytes,
    file_name: str,
) -> dict:
    """
    SSH 部署流程：
    1. 连接目标服务器
    2. 通过 SFTP 上传文件到 deploy_path
    3. 执行 deploy_script
    4. 返回执行结果

    返回 {"ok": True, "logs": str} 或 {"ok": False, "error": str}
    """
    from app.api.ssh_common import _build_ssh_client
    from app.models.asset import Asset

    asset = db.get(Asset, asset_id)
    if not asset:
        return {"ok": False, "error": f"主机 ID={asset_id} 不存在"}

    ssh = None
    sftp = None
    logs = []

    try:
        # 1. 建立 SSH 连接
        ssh, username, host = _build_ssh_client(asset, {})
        logs.append(f"[连接] 已连接 {username}@{host}")

        # 2. 确保目标目录存在
        sftp = ssh.open_sftp()
        remote_file = f"{deploy_path.rstrip('/')}/{file_name}"
        logs.append(f"[上传] 目标路径: {remote_file}")

        # 创建远程目录（递归）
        _ensure_remote_dir(sftp, deploy_path)
        logs.append(f"[上传] 目录已就绪: {deploy_path}")

        # 3. 上传文件
        with sftp.open(remote_file, "wb") as f:
            f.write(file_content)
        file_size_mb = len(file_content) / (1024 * 1024)
        logs.append(f"[上传] 完成: {file_name} ({file_size_mb:.2f} MB)")

        sftp.close()
        sftp = None

        # 4. 执行部署脚本
        if deploy_script:
            logs.append(f"[执行] {deploy_script}")
            # 如果脚本不包含路径，则在 deploy_path 下执行
            if not deploy_script.startswith("cd ") and "/" not in deploy_script.split(" ")[0]:
                cmd = f"cd {deploy_path} && {deploy_script}"
            else:
                cmd = deploy_script

            stdin, stdout, stderr = ssh.exec_command(cmd, timeout=300)
            exit_code = stdout.channel.recv_exit_status()
            stdout_text = stdout.read().decode("utf-8", errors="replace")
            stderr_text = stderr.read().decode("utf-8", errors="replace")

            if stdout_text.strip():
                logs.append(f"[输出] {stdout_text.strip()}")
            if stderr_text.strip():
                logs.append(f"[错误] {stderr_text.strip()}")

            if exit_code != 0:
                logs.append(f"[结果] 脚本执行失败，退出码: {exit_code}")
                return {"ok": False, "error": f"部署脚本执行失败 (exit code: {exit_code})", "logs": "\n".join(logs)}

            logs.append("[结果] 脚本执行成功")
        else:
            logs.append("[跳过] 未配置部署脚本，仅上传文件")

        return {"ok": True, "logs": "\n".join(logs)}

    except Exception as e:
        logs.append(f"[错误] {str(e)}")
        return {"ok": False, "error": str(e), "logs": "\n".join(logs)}
    finally:
        if sftp:
            try:
                sftp.close()
            except Exception:
                pass
        if ssh:
            try:
                ssh.close()
            except Exception:
                pass


def _ensure_remote_dir(sftp, path: str) -> None:
    """递归创建远程目录。"""
    parts = path.strip("/").split("/")
    current = ""
    for part in parts:
        current = f"{current}/{part}"
        try:
            sftp.stat(current)
        except FileNotFoundError:
            try:
                sftp.mkdir(current)
            except OSError:
                pass  # 目录可能已被并发创建
