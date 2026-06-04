"""Build service — local (SSH) and Jenkins build modes."""
from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime

import httpx

from app.core.config import CHINA_TZ
from app.models.deploy import DeployAppEnv, DeployApplication, DeployRecord

logger = logging.getLogger(__name__)

_JENKINS_TIMEOUT = httpx.Timeout(connect=10, read=30, write=10, pool=10)


def _get_jenkins_config() -> dict | None:
    """从 system_config 表读取 Jenkins 配置。"""
    from app.db.database import SessionLocal
    from app.models.system_config import SystemConfig
    from sqlalchemy import select

    db = SessionLocal()
    try:
        cfg = db.scalar(select(SystemConfig).where(SystemConfig.key == "jenkins_config"))
        if cfg and cfg.value:
            try:
                return json.loads(cfg.value)
            except json.JSONDecodeError:
                logger.error("jenkins_config JSON 解析失败")
        return None
    finally:
        db.close()


def execute_build(
    db,
    record: DeployRecord,
    app: DeployApplication,
    app_env: DeployAppEnv,
) -> str | None:
    """执行构建，返回产物路径。None 表示无产物或构建失败。"""
    from app.services.deploy.records import append_log, is_cancelled, update_status

    build_mode = app.build_mode or "local"
    append_log(db, record, f"构建模式: {build_mode}")

    if build_mode == "jenkins":
        return _build_jenkins(db, record, app)
    else:
        return _build_local(db, record, app, app_env)


def _build_local(
    db,
    record: DeployRecord,
    app: DeployApplication,
    app_env: DeployAppEnv,
) -> str | None:
    """本地构建：SSH 到目标主机执行构建命令。"""
    from app.api.ssh_common import _build_ssh_client
    from app.models.asset import Asset
    from app.services.deploy.records import append_log, is_cancelled, update_status
    from sqlalchemy import select

    build_command = app.build_command
    if not build_command:
        append_log(db, record, "未配置构建命令，跳过构建")
        return app.artifact_path or None

    # 构建主机：优先用 SSH 目标主机，否则用 Docker 主机的 IP
    asset = app_env.ssh_asset
    if asset is None and app_env.docker_host:
        host_ip = app_env.docker_host.host_ip or app_env.docker_host.endpoint.split(":")[0]
        if host_ip:
            asset = db.scalar(select(Asset).where(Asset.ip_address == host_ip))

    if asset is None:
        append_log(db, record, "未找到构建主机，跳过本地构建")
        return app.artifact_path or None

    if is_cancelled(record.id):
        return None

    try:
        ssh, username, host = _build_ssh_client(asset, {})
        append_log(db, record, f"构建主机: {host} ({username})")
    except Exception as e:
        append_log(db, record, f"构建主机连接失败: {e}")
        return None

    try:
        append_log(db, record, f"执行构建命令: {build_command}")
        stdin, stdout, stderr = ssh.exec_command(build_command, timeout=600)
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        exit_code = stdout.channel.recv_exit_status()

        # 输出最后 20 行
        if out:
            for line in out.strip().split("\n")[-20:]:
                append_log(db, record, f"  {line}")
        if err:
            for line in err.strip().split("\n")[-10:]:
                append_log(db, record, f"  [stderr] {line}")

        if exit_code != 0:
            append_log(db, record, f"构建失败 (exit_code={exit_code})")
            return None

        append_log(db, record, "构建成功 ✓")
        return app.artifact_path or None

    except Exception as e:
        append_log(db, record, f"构建异常: {e}")
        return None

    finally:
        ssh.close()


def _build_jenkins(
    db,
    record: DeployRecord,
    app: DeployApplication,
) -> str | None:
    """Jenkins 构建：触发 Job → 轮询状态 → 获取产物路径。"""
    from app.services.deploy.records import append_log, is_cancelled

    jenkins_cfg = _get_jenkins_config()
    if not jenkins_cfg:
        append_log(db, record, "Jenkins 未配置，请在系统设置中配置 Jenkins")
        return None

    base_url = jenkins_cfg.get("url", "").rstrip("/")
    username = jenkins_cfg.get("username", "")
    token = jenkins_cfg.get("token", "")
    if not base_url:
        append_log(db, record, "Jenkins URL 未配置")
        return None

    job_name = app.jenkins_job_name
    if not job_name:
        append_log(db, record, "未配置 Jenkins Job 名称")
        return None

    auth = (username, token) if username else None
    append_log(db, record, f"Jenkins: {base_url}")
    append_log(db, record, f"Job: {job_name}")

    # ── 1. 触发构建 ──
    if is_cancelled(record.id):
        return None

    trigger_url = f"{base_url}/job/{job_name}/build"
    if app.jenkins_token:
        trigger_url = f"{base_url}/job/{job_name}/build?token={app.jenkins_token}"

    try:
        with httpx.Client(timeout=_JENKINS_TIMEOUT, verify=False) as client:
            resp = client.post(trigger_url, auth=auth)
            if resp.status_code not in (200, 201, 202):
                # 尝试用 parameters 格式
                resp = client.post(
                    f"{base_url}/job/{job_name}/buildWithParameters",
                    auth=auth,
                )
            if resp.status_code not in (200, 201, 202):
                append_log(db, record, f"Jenkins 触发失败: HTTP {resp.status_code}")
                return None

            # 从 queue URL 获取 build number
            queue_url = resp.headers.get("Location", "")
            append_log(db, record, "构建已触发，等待队列分配…")

    except Exception as e:
        append_log(db, record, f"Jenkins 触发异常: {e}")
        return None

    # ── 2. 等待构建开始 ──
    if is_cancelled(record.id):
        return None

    build_number = _wait_for_build_start(base_url, auth, job_name, queue_url, db, record, timeout=120)
    if build_number is None:
        append_log(db, record, "Jenkins 构建未在超时时间内开始")
        return None

    append_log(db, record, f"构建 #{build_number} 开始执行…")

    # ── 3. 轮询构建状态 ──
    if is_cancelled(record.id):
        return None

    result = _poll_build_status(base_url, auth, job_name, build_number, db, record, timeout=600)
    if result != "SUCCESS":
        append_log(db, record, f"Jenkins 构建结果: {result}")
        return None

    append_log(db, record, f"Jenkins 构建 #{build_number} 成功 ✓")

    # 返回产物路径（Jenkins 构建产物通常在 workspace 中）
    return app.artifact_path or None


def _wait_for_build_start(
    base_url: str,
    auth: tuple | None,
    job_name: str,
    queue_url: str,
    db,
    record,
    timeout: int = 120,
) -> int | None:
    """等待 Jenkins 队列分配，返回 build number。"""
    from app.services.deploy.records import append_log, is_cancelled

    deadline = time.time() + timeout
    queue_path = queue_url.lstrip("/") if queue_url else ""

    while time.time() < deadline:
        if is_cancelled(record.id):
            return None

        try:
            if queue_path:
                with httpx.Client(timeout=_JENKINS_TIMEOUT, verify=False) as client:
                    resp = client.get(f"{base_url}/{queue_path}api/json", auth=auth)
                    if resp.status_code == 200:
                        data = resp.json()
                        if data.get("cancelled"):
                            return None
                        executable = data.get("executable")
                        if executable:
                            return executable.get("number")
        except Exception:
            pass

        time.sleep(3)

    return None


def _poll_build_status(
    base_url: str,
    auth: tuple | None,
    job_name: str,
    build_number: int,
    db,
    record,
    timeout: int = 600,
) -> str:
    """轮询 Jenkins 构建状态，返回 result（SUCCESS/FAILURE/ABORTED）。"""
    from app.services.deploy.records import append_log, is_cancelled

    deadline = time.time() + timeout
    last_progress = 0

    while time.time() < deadline:
        if is_cancelled(record.id):
            return "ABORTED"

        try:
            with httpx.Client(timeout=_JENKINS_TIMEOUT, verify=False) as client:
                resp = client.get(
                    f"{base_url}/job/{job_name}/{build_number}/api/json",
                    auth=auth,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    building = data.get("building", False)
                    result = data.get("result")

                    # 进度提示
                    progress = data.get("executor", {})
                    if progress and progress.get("progress") is not None:
                        pct = progress["progress"]
                        if pct != last_progress:
                            append_log(db, record, f"  构建进度: {pct}%")
                            last_progress = pct

                    if not building:
                        return result or "UNKNOWN"

        except Exception as e:
            logger.debug("Jenkins poll error: %s", e)

        time.sleep(5)

    return "TIMEOUT"
