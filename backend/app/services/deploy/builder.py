"""Build service — upload (artifact distribution) and Jenkins build modes."""
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

    build_mode = app.build_mode or "upload"

    if build_mode == "upload":
        # 文件上传模式：产物已通过 API 上传到平台，从环境配置读取
        artifact = app_env.artifact_path or ""
        if artifact and os.path.isfile(artifact):
            append_log(db, record, f"构建模式: 文件上传")
            append_log(db, record, f"产物: {app_env.artifact_filename} ({_format_size(app_env.artifact_size)})")
            return artifact
        else:
            append_log(db, record, "构建模式: 文件上传")
            append_log(db, record, "未找到构建产物，请先在环境配置中上传构建产物")
            return None

    append_log(db, record, f"构建模式: {build_mode}")

    if build_mode == "jenkins":
        return _build_jenkins(db, record, app)
    else:
        # deprecated: 旧 local 模式兼容
        return _build_local(db, record, app, app_env)


def _format_size(size: int) -> str:
    """格式化文件大小。"""
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    elif size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    else:
        return f"{size / (1024 * 1024 * 1024):.1f} GB"


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
            # 使用 token 触发时用 GET，使用 BasicAuth 时用 POST
            if app.jenkins_token:
                resp = client.get(trigger_url, auth=auth)
            else:
                resp = client.post(trigger_url, auth=auth)
                if resp.status_code not in (200, 201, 202):
                    # 尝试用 parameters 格式
                    resp = client.post(
                        f"{base_url}/job/{job_name}/buildWithParameters",
                        auth=auth,
                    )

            logger.info("Jenkins trigger response: status=%s, headers=%s", resp.status_code, dict(resp.headers))

            if resp.status_code not in (200, 201, 202):
                append_log(db, record, f"Jenkins 触发失败: HTTP {resp.status_code}")
                return None

            # 从 queue URL 获取 build number
            queue_url = resp.headers.get("Location", "")

            # 如果没有 Location header，尝试从响应中获取
            if not queue_url:
                # 有些 Jenkins 版本返回 200 但没有 Location
                # 此时直接获取最新构建号
                append_log(db, record, "构建已触发")
                logger.info("Jenkins trigger: no Location header, will use fallback")
            else:
                append_log(db, record, f"构建已触发，等待队列分配…")

    except Exception as e:
        append_log(db, record, f"Jenkins 触发异常: {e}")
        return None

    # ── 2. 获取构建号 ──
    if is_cancelled(record.id):
        return None

    build_number = None

    # 有队列 URL 时等待构建开始
    if queue_url:
        append_log(db, record, "等待队列分配…")
        build_number = _wait_for_build_start(base_url, auth, job_name, queue_url, db, record, timeout=120)

    # 没有队列 URL 或等待超时，获取最新构建号
    if build_number is None:
        time.sleep(2)  # 等待 Jenkins 更新
        build_number = _get_latest_build_number(base_url, auth, job_name)
        if build_number:
            append_log(db, record, f"获取到构建 #{build_number}")
        else:
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

    # ── 4. 从 Jenkins 下载产物 ──
    if is_cancelled(record.id):
        return None

    append_log(db, record, "正在从 Jenkins 下载构建产物…")
    try:
        from app.services.deploy.webhook import download_from_jenkins
        artifact_path, artifact_size = download_from_jenkins(
            jenkins_url=base_url,
            job_name=job_name,
            build_number=build_number,
            username=username,
            token=token,
            app_id=app.id,
        )
        append_log(db, record, f"产物下载成功: {artifact_path} ({_format_size(artifact_size)})")
        return artifact_path
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg:
            append_log(db, record, "产物下载失败: Jenkins Job 未配置归档产物（Archive the artifacts）")
            append_log(db, record, "请在 Jenkins Job 配置中添加"构建后操作 → 归档产物"")
        else:
            append_log(db, record, f"产物下载失败: {error_msg}")
        logger.error("Jenkins artifact download failed: %s", e)
        return None


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
    # 处理相对路径的 queue_url
    if queue_url:
        if queue_url.startswith("http"):
            queue_api = f"{queue_url}api/json"
        else:
            queue_path = queue_url.lstrip("/")
            queue_api = f"{base_url}/{queue_path}api/json"
    else:
        queue_api = ""

    logger.info("Jenkins queue API: %s", queue_api)

    while time.time() < deadline:
        if is_cancelled(record.id):
            return None

        try:
            if queue_api:
                with httpx.Client(timeout=_JENKINS_TIMEOUT, verify=False) as client:
                    resp = client.get(queue_api, auth=auth)
                    if resp.status_code == 200:
                        data = resp.json()
                        if data.get("cancelled"):
                            return None
                        executable = data.get("executable")
                        if executable:
                            build_num = executable.get("number")
                            logger.info("Jenkins build started: #%s", build_num)
                            return build_num
                        # 显示队列状态
                        why = data.get("why")
                        if why:
                            logger.debug("Jenkins queue why: %s", why)
        except Exception as e:
            logger.debug("Jenkins queue poll error: %s", e)

        time.sleep(3)

    return None


def _get_latest_build_number(
    base_url: str,
    auth: tuple | None,
    job_name: str,
) -> int | None:
    """获取 Job 的最新构建号。"""
    try:
        with httpx.Client(timeout=_JENKINS_TIMEOUT, verify=False) as client:
            resp = client.get(f"{base_url}/job/{job_name}/api/json?tree=lastBuild[number]", auth=auth)
            if resp.status_code == 200:
                data = resp.json()
                last_build = data.get("lastBuild")
                if last_build:
                    return last_build.get("number")
    except Exception as e:
        logger.debug("Jenkins get latest build error: %s", e)
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
