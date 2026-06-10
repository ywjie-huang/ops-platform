"""Webhook 服务 — 处理 CI/CD 推送的构建产物。"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time
from datetime import datetime

import httpx

from app.core.config import CHINA_TZ

logger = logging.getLogger(__name__)

# 产物存储根目录
_ARTIFACTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "artifacts")


def verify_webhook_signature(
    payload: bytes,
    signature: str,
    secret: str,
) -> bool:
    """验证 Webhook 签名（HMAC-SHA256）。

    Args:
        payload: 原始请求体
        signature: 请求头中的签名，格式为 "sha256=xxx"
        secret: Webhook 密钥

    Returns:
        签名是否有效
    """
    if not secret:
        # 未配置密钥，跳过验证
        return True

    if not signature:
        return False

    # 计算期望的签名
    expected = hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()

    # 比较签名（防止时序攻击）
    expected_full = f"sha256={expected}"
    return hmac.compare_digest(expected_full, signature)


def generate_webhook_secret() -> str:
    """生成随机的 Webhook 密钥。"""
    import secrets
    return secrets.token_hex(32)


def get_artifact_dir(app_id: int, build_number: str) -> str:
    """获取构建产物的存储目录。

    目录结构: artifacts/{app_id}/{build_number}/
    """
    return os.path.join(_ARTIFACTS_DIR, str(app_id), f"build_{build_number}")


def save_artifact_file(
    file_content: bytes,
    filename: str,
    app_id: int,
    build_number: str,
) -> tuple[str, int]:
    """保存构建产物文件。

    Args:
        file_content: 文件内容
        filename: 原始文件名
        app_id: 应用 ID
        build_number: 构建号

    Returns:
        (产物路径, 文件大小)
    """
    artifact_dir = get_artifact_dir(app_id, build_number)
    os.makedirs(artifact_dir, exist_ok=True)

    # 保存文件
    artifact_path = os.path.join(artifact_dir, filename)
    with open(artifact_path, "wb") as f:
        f.write(file_content)

    file_size = len(file_content)
    logger.info("Saved artifact: %s (%d bytes)", artifact_path, file_size)

    return artifact_path, file_size


def download_artifact_from_url(
    url: str,
    app_id: int,
    build_number: str,
    filename: str = None,
    auth: tuple[str, str] = None,
    headers: dict[str, str] = None,
    timeout: int = 300,
) -> tuple[str, int]:
    """从 URL 下载构建产物。

    Args:
        url: 产物下载 URL
        app_id: 应用 ID
        build_number: 构建号
        filename: 保存的文件名（可选，从 URL 或 Content-Disposition 解析）
        auth: 认证信息 (username, password)
        headers: 额外的请求头
        timeout: 下载超时时间（秒）

    Returns:
        (产物路径, 文件大小)
    """
    artifact_dir = get_artifact_dir(app_id, build_number)
    os.makedirs(artifact_dir, exist_ok=True)

    # 确定文件名
    if not filename:
        filename = url.split("/")[-1].split("?")[0]
        if not filename or "." not in filename:
            filename = "artifact.zip"

    artifact_path = os.path.join(artifact_dir, filename)

    # 下载文件
    with httpx.Client(timeout=timeout, verify=False) as client:
        with client.stream("GET", url, auth=auth, headers=headers) as resp:
            resp.raise_for_status()

            # 尝试从 Content-Disposition 获取文件名
            content_disposition = resp.headers.get("Content-Disposition", "")
            if "filename=" in content_disposition:
                import re
                match = re.search(r'filename="?([^"]+)"?', content_disposition)
                if match:
                    extracted_name = match.group(1)
                    artifact_path = os.path.join(artifact_dir, extracted_name)

            # 写入文件
            total_size = 0
            with open(artifact_path, "wb") as f:
                for chunk in resp.iter_bytes(chunk_size=8192):
                    f.write(chunk)
                    total_size += len(chunk)

    logger.info("Downloaded artifact: %s (%d bytes)", artifact_path, total_size)
    return artifact_path, total_size


def download_from_jenkins(
    jenkins_url: str,
    job_name: str,
    build_number: int,
    username: str,
    token: str,
    app_id: int,
) -> tuple[str, int]:
    """从 Jenkins 下载构建产物。

    Args:
        jenkins_url: Jenkins URL
        job_name: Job 名称
        build_number: 构建号
        username: Jenkins 用户名
        token: Jenkins API Token
        app_id: 应用 ID

    Returns:
        (产物路径, 文件大小)
    """
    base_url = jenkins_url.rstrip("/")
    auth = (username, token) if username else None

    # 1. 获取构建信息，检查是否有产物
    build_info_url = f"{base_url}/job/{job_name}/{build_number}/api/json"
    with httpx.Client(timeout=30, verify=False) as client:
        resp = client.get(build_info_url, auth=auth)
        resp.raise_for_status()
        build_info = resp.json()

    if build_info.get("result") != "SUCCESS":
        raise ValueError(f"Jenkins 构建 #{build_number} 未成功: {build_info.get('result')}")

    # 2. 下载产物（zip 格式）
    artifact_url = f"{base_url}/job/{job_name}/{build_number}/artifact/*zip*/archive.zip"
    return download_artifact_from_url(
        url=artifact_url,
        app_id=app_id,
        build_number=str(build_number),
        filename=f"jenkins_{build_number}.zip",
        auth=auth,
    )


def create_build_record(
    db,
    app_id: int,
    build_number: str,
    source: str,
    artifact_path: str,
    artifact_filename: str,
    artifact_size: int,
    commit: str = "",
    branch: str = "",
    status: str = "success",
    build_duration: int = 0,
    build_log: str = "",
    webhook_payload: str = "",
) -> "DeployBuild":
    """创建构建记录（幂等处理）。

    如果同一 app_id + build_number 已存在，则更新状态。
    """
    from app.models.deploy import DeployBuild

    # 检查是否已存在
    existing = db.query(DeployBuild).filter(
        DeployBuild.app_id == app_id,
        DeployBuild.build_number == build_number,
    ).first()

    if existing:
        if existing.status == "success" and status == "success":
            # 已成功，跳过
            logger.info("Build %s/%s already exists, skipping", app_id, build_number)
            return existing
        else:
            # 更新状态
            existing.status = status
            existing.artifact_path = artifact_path
            existing.artifact_filename = artifact_filename
            existing.artifact_size = artifact_size
            if commit:
                existing.commit = commit
            if branch:
                existing.branch = branch
            if build_duration:
                existing.build_duration = build_duration
            if build_log:
                existing.build_log = build_log
            if webhook_payload:
                existing.webhook_payload = webhook_payload
            db.commit()
            logger.info("Updated build record: %s/%s", app_id, build_number)
            return existing

    # 创建新记录
    build = DeployBuild(
        app_id=app_id,
        build_number=build_number,
        source=source,
        commit=commit,
        branch=branch,
        status=status,
        artifact_path=artifact_path,
        artifact_filename=artifact_filename,
        artifact_size=artifact_size,
        build_duration=build_duration,
        build_log=build_log,
        webhook_payload=webhook_payload,
    )
    db.add(build)
    db.commit()
    db.refresh(build)
    logger.info("Created build record: %s/%s", app_id, build_number)
    return build


def generate_build_number() -> str:
    """生成自增的构建号（基于时间戳 + 随机数）。"""
    timestamp = int(time.time() * 1000)
    import random
    rand = random.randint(100, 999)
    return f"{timestamp}_{rand}"


def cleanup_old_builds(
    db,
    app_id: int,
    keep_count: int = 10,
) -> int:
    """清理旧的构建记录和产物文件。

    Args:
        app_id: 应用 ID
        keep_count: 保留的构建数量

    Returns:
        删除的构建数量
    """
    from app.models.deploy import DeployBuild

    # 获取所有构建记录，按时间倒序
    builds = db.query(DeployBuild).filter(
        DeployBuild.app_id == app_id,
    ).order_by(DeployBuild.created_at.desc()).all()

    if len(builds) <= keep_count:
        return 0

    to_delete = builds[keep_count:]
    deleted_count = 0

    for build in to_delete:
        # 删除产物文件
        if build.artifact_path and os.path.exists(build.artifact_path):
            try:
                # 删除整个构建目录
                build_dir = os.path.dirname(build.artifact_path)
                if os.path.exists(build_dir):
                    import shutil
                    shutil.rmtree(build_dir)
                    logger.info("Deleted artifact directory: %s", build_dir)
            except Exception as e:
                logger.error("Failed to delete artifact: %s", e)

        # 删除记录
        db.delete(build)
        deleted_count += 1

    db.commit()
    logger.info("Cleaned up %d old builds for app %d", deleted_count, app_id)
    return deleted_count
