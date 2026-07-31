"""Docker deploy strategy — SSH to Docker host, pull → stop → rm → run → health check."""
from __future__ import annotations

import json
import logging
import shlex

from sqlalchemy import select
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


def execute_docker_deploy(
    db: Session,
    record: DeployRecord,
    app: DeployApplication,
    app_env: DeployAppEnv,
) -> None:
    """执行 Docker 部署：SSH 到目标主机 → docker pull → stop → rm → run → 健康检查。"""
    docker_host = app_env.docker_host
    if docker_host is None:
        update_status(db, record, "failed")
        set_error(db, record, "未配置 Docker 主机")
        return

    image = app_env.docker_image
    if not image:
        update_status(db, record, "failed")
        set_error(db, record, "未配置 Docker 镜像")
        return

    container_name = app_env.docker_container_name or app.name
    ports = app_env.docker_ports or ""
    env_vars = app_env.docker_env_vars or ""
    network = app_env.docker_network or ""
    extra_args = app_env.docker_extra_args or ""
    health_url = app.health_check_url or ""
    health_timeout = app.health_check_timeout or 30

    # 从 Docker 主机的 endpoint 解析 IP（格式: IP:端口）
    host_ip = docker_host.host_ip or docker_host.endpoint.split(":")[0]
    if not host_ip:
        update_status(db, record, "failed")
        set_error(db, record, "Docker 主机 IP 无法解析")
        return

    # 查找对应的资产以获取 SSH 凭据
    asset = db.scalar(select(Asset).where(Asset.ip_address == host_ip))
    if asset is None:
        update_status(db, record, "failed")
        set_error(db, record, f"未找到 IP 为 {host_ip} 的资产，请先添加主机")
        return

    ssh = None

    try:
        update_status(db, record, "deploying")
        append_log(db, record, f"连接 Docker 主机 {docker_host.name} ({host_ip})")

        if is_cancelled(record.id):
            update_status(db, record, "cancelled")
            return

        # SSH 连接
        try:
            ssh, username, host = _build_ssh_client(asset, {})
            append_log(db, record, f"SSH 连接成功 ({username}@{host})")
        except Exception as e:
            update_status(db, record, "failed")
            set_error(db, record, f"SSH 连接失败: {e}")
            append_log(db, record, f"SSH 连接失败: {e}")
            return

        # ── 1. docker pull ──
        if is_cancelled(record.id):
            update_status(db, record, "cancelled")
            return

        append_log(db, record, f"拉取镜像 {image}")
        exit_code, out, err = ssh_exec(ssh, f"docker pull {shlex.quote(image)}", timeout=300)
        if exit_code != 0:
            update_status(db, record, "failed")
            set_error(db, record, f"docker pull 失败: {err}")
            append_log(db, record, f"拉取失败: {err}")
            return
        append_log(db, record, "镜像拉取成功")

        # ── 2. docker stop ──
        if is_cancelled(record.id):
            update_status(db, record, "cancelled")
            return

        append_log(db, record, f"停止旧容器 {container_name}")
        ssh_exec(ssh, f"docker stop {shlex.quote(container_name)}", timeout=30)
        # 忽略 stop 错误（容器可能不存在）

        # ── 3. docker rm ──
        append_log(db, record, f"删除旧容器 {container_name}")
        ssh_exec(ssh, f"docker rm {shlex.quote(container_name)}", timeout=15)

        # ── 4. docker run ──
        if is_cancelled(record.id):
            update_status(db, record, "cancelled")
            return

        # 构建 docker run 命令（以 argv 形式累积，最后用 shlex.join 安全拼接，
        # 确保所有用户可控字段都被正确转义，杜绝 shell 命令注入）
        argv = ["docker", "run", "-d", "--name", container_name, "--restart", "unless-stopped"]

        # 端口映射
        if ports:
            for p in ports.split(","):
                p = p.strip()
                if p:
                    argv += ["-p", p]

        # 环境变量
        if env_vars:
            try:
                env_dict = json.loads(env_vars)
                for k, v in env_dict.items():
                    argv += ["-e", f"{k}={v}"]
            except json.JSONDecodeError:
                # 非 JSON 格式，按行解析
                for line in env_vars.strip().split("\n"):
                    line = line.strip()
                    if "=" in line:
                        argv += ["-e", line]

        # 网络
        if network:
            argv += ["--network", network]

        # 额外参数：用 shlex.split 拆成字面 token，再交给 shlex.join 统一转义，
        # 这样原始字符串中的 shell 元字符会被当作字面参数而非命令分隔符。
        if extra_args:
            argv += shlex.split(extra_args)

        argv.append(image)

        run_cmd = shlex.join(argv)
        append_log(db, record, f"启动新容器 {container_name}")
        exit_code, out, err = ssh_exec(ssh, run_cmd, timeout=120)
        if exit_code != 0:
            update_status(db, record, "failed")
            set_error(db, record, f"docker run 失败: {err}")
            append_log(db, record, f"启动失败: {err}")
            return

        container_id = out.strip()[:12]
        append_log(db, record, f"容器启动成功 (ID: {container_id})")

        # ── 5. 健康检查 ──
        if is_cancelled(record.id):
            update_status(db, record, "cancelled")
            return

        if health_url:
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
        logger.exception("Docker deploy error for record %s", record.id)
        update_status(db, record, "failed")
        set_error(db, record, str(e))
        append_log(db, record, f"部署异常: {e}")

    finally:
        if ssh:
            try:
                ssh.close()
            except Exception:
                pass
