"""SSH deploy strategy — SFTP upload + SSH script execution + health check."""
from __future__ import annotations

import logging
import os
import shlex
import time

import paramiko
from sqlalchemy.orm import Session

from app.api.ssh_common import _build_ssh_client
from app.models.asset import Asset
from app.models.deploy import DeployAppEnv, DeployApplication, DeployRecord
from app.services.deploy.records import (
    append_log,
    is_cancelled,
    set_error,
    update_status,
)
from app.services.deploy.strategies.base import poll_health, ssh_exec

logger = logging.getLogger(__name__)


def execute_ssh_deploy(
    db: Session,
    record: DeployRecord,
    app: DeployApplication,
    app_env: DeployAppEnv,
) -> None:
    """执行 SSH 部署：上传产物 → 执行脚本 → 健康检查。"""
    asset = app_env.ssh_asset
    if asset is None:
        update_status(db, record, "failed")
        set_error(db, record, "未配置目标主机")
        return

    deploy_path = app_env.deploy_path or f"/opt/apps/{app.name}"
    deploy_script = app_env.deploy_script or ""
    health_url = app_env.health_check_url or ""
    health_port = app_env.health_check_port or 0
    health_timeout = app_env.health_check_timeout or 30

    # 构建 auth dict（使用资产自带的 SSH 凭据）
    auth: dict = {}

    ssh = None
    sftp = None

    try:
        # ── 1. 建立 SSH 连接 ──
        update_status(db, record, "deploying")
        append_log(db, record, f"连接目标主机 {asset.name} ({asset.ip_address})")

        if is_cancelled(record.id):
            update_status(db, record, "cancelled")
            return

        try:
            ssh, username, host = _build_ssh_client(asset, auth)
            append_log(db, record, f"SSH 连接成功 ({username}@{host})")
        except Exception as e:
            update_status(db, record, "failed")
            set_error(db, record, f"SSH 连接失败: {e}")
            append_log(db, record, f"SSH 连接失败: {e}")
            return

        # ── 2. 创建远程目录 ──
        if is_cancelled(record.id):
            update_status(db, record, "cancelled")
            return

        append_log(db, record, f"创建部署目录 {deploy_path}")
        ssh_exec(ssh, f"mkdir -p {shlex.quote(deploy_path)}")

        # ── 3. 上传产物（回滚时如果远程文件已存在则跳过） ──
        if is_cancelled(record.id):
            update_status(db, record, "cancelled")
            return

        artifact_path = app_env.artifact_path or ""
        is_rollback = record.trigger_type == "rollback"

        if artifact_path and os.path.isfile(artifact_path):
            remote_filename = os.path.basename(artifact_path)
            remote_path = f"{deploy_path}/{remote_filename}"

            need_upload = True
            if is_rollback:
                # 回滚：检查远程是否已有该文件
                check_exit, _, _ = ssh_exec(ssh, f"test -f {shlex.quote(remote_path)}")
                if check_exit == 0:
                    append_log(db, record, f"回滚: 远程文件已存在，跳过上传")
                    need_upload = False
                else:
                    append_log(db, record, f"回滚: 远程文件不存在，重新上传")

            if need_upload:
                _do_upload(ssh, sftp, db, record, artifact_path, remote_path)
                sftp = None  # _do_upload 内部关闭 sftp

            # 创建软链接：原始文件名 → 带时间戳的文件
            # 这样 restart.sh 引用原始文件名就能自动指向最新版本
            original_filename = app_env.artifact_filename or ""
            if original_filename and original_filename != remote_filename:
                symlink_path = f"{deploy_path}/{original_filename}"
                ssh_exec(ssh, f"ln -sf {shlex.quote(remote_filename)} {shlex.quote(symlink_path)}")
                append_log(db, record, f"软链接: {original_filename} → {remote_filename}")
        elif artifact_path:
            append_log(db, record, f"产物路径不存在，跳过上传: {artifact_path}")
        else:
            append_log(db, record, "未配置产物路径，跳过上传")

        # ── 4. 执行部署脚本 ──
        if is_cancelled(record.id):
            update_status(db, record, "cancelled")
            return

        if deploy_script:
            append_log(db, record, "执行部署脚本…")
            # deploy_path 是结构化字段，必须转义以防命令注入；
            # deploy_script 本身就是用户预期的部署脚本，保持原样。
            full_script = f"cd {shlex.quote(deploy_path)} && {deploy_script}"
            exit_code, stdout, stderr = ssh_exec(ssh, full_script, timeout=300)

            if stdout:
                for line in stdout.strip().split("\n")[-20:]:  # 最多保留最后 20 行
                    append_log(db, record, f"  {line}")
            if stderr:
                for line in stderr.strip().split("\n")[-10:]:
                    append_log(db, record, f"  [stderr] {line}")

            if exit_code != 0:
                update_status(db, record, "failed")
                set_error(db, record, f"部署脚本执行失败 (exit_code={exit_code})")
                append_log(db, record, f"部署脚本执行失败，退出码: {exit_code}")
                return

            append_log(db, record, "部署脚本执行成功")
        else:
            append_log(db, record, "未配置部署脚本，跳过执行")

        # ── 5. 健康检查 ──
        if is_cancelled(record.id):
            update_status(db, record, "cancelled")
            return

        # TCP 端口检测（优先）
        if health_port:
            host_ip = asset.ip_address
            append_log(db, record, f"健康检查: TCP {host_ip}:{health_port} (超时 {health_timeout}s)")
            healthy = _check_port_via_ssh(ssh, host_ip, health_port, timeout=health_timeout)
            if healthy:
                append_log(db, record, f"端口 {health_port} 检测通过 ✓")
            else:
                update_status(db, record, "failed")
                set_error(db, record, f"端口 {health_port} 检测超时 ({health_timeout}s)")
                append_log(db, record, "健康检查超时，部署失败")
                return
        elif health_url:
            # HTTP 健康检查（兼容旧配置）
            append_log(db, record, f"健康检查: {health_url} (超时 {health_timeout}s)")
            healthy = poll_health(health_url, timeout=health_timeout)
            if healthy:
                append_log(db, record, "健康检查通过 ✓")
            else:
                update_status(db, record, "failed")
                set_error(db, record, f"健康检查超时 ({health_timeout}s)")
                append_log(db, record, "健康检查超时，部署失败")
                return

        # ── 完成 ──
        update_status(db, record, "success")
        append_log(db, record, "部署成功 ✓")

    except Exception as e:
        logger.exception("SSH deploy error for record %s", record.id)
        update_status(db, record, "failed")
        set_error(db, record, str(e))
        append_log(db, record, f"部署异常: {e}")

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


def _do_upload(ssh, sftp, db: Session, record: DeployRecord, local_path: str, remote_path: str) -> None:
    """通过 SFTP 上传文件到远程主机。"""
    append_log(db, record, f"上传产物 {local_path} → {remote_path}")
    if sftp is None:
        sftp = ssh.open_sftp()
    progress_cb = _make_progress_cb(db, record)
    sftp.put(local_path, remote_path, callback=progress_cb)
    sftp.close()
    append_log(db, record, f"上传完成: {remote_path}")


def _check_port_via_ssh(ssh, host: str, port: int, timeout: int = 30) -> bool:
    """通过已有 SSH 连接检测目标端口是否可达（在远程主机上执行端口检测）。"""
    import time as _time

    deadline = _time.time() + timeout
    # 优先用 nc（netcat），回退到 bash /dev/tcp
    # host/port 来自配置字段，必须转义以防命令注入。
    check_cmd = (
        f"for i in $(seq 1 {int(timeout)}); do "
        f"  nc -z -w1 {shlex.quote(str(host))} {int(port)} 2>/dev/null && exit 0; "
        f"  sleep 1; "
        f"done; exit 1"
    )

    try:
        stdin, stdout, stderr = ssh.exec_command(check_cmd, timeout=timeout + 5)
        exit_code = stdout.channel.recv_exit_status()
        return exit_code == 0
    except Exception:
        return False


def _make_progress_cb(db: Session, record: DeployRecord):
    """创建 SFTP 上传进度回调（每 10% 输出一次，去重）。"""
    last_pct = [-1]

    def cb(sent: int, total: int) -> None:
        if total <= 0:
            return
        pct = int(sent * 100 / total)
        if pct % 10 == 0 and sent > 0 and pct != last_pct[0]:
            last_pct[0] = pct
            append_log(db, record, f"上传进度: {pct}%")

    return cb
