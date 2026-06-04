"""K8s deploy strategy — update Deployment image via K8s API, poll rollout, health check."""
from __future__ import annotations

import json
import logging
import time

import httpx
from sqlalchemy.orm import Session

from app.models.deploy import DeployAppEnv, DeployApplication, DeployRecord
from app.services.deploy.records import (
    append_log,
    is_cancelled,
    set_error,
    update_status,
)
from app.services.deploy.strategies.base import poll_health

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(connect=5, read=15, write=15, pool=5)


def _k8s_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Accept": "application/json"}


def execute_k8s_deploy(
    db: Session,
    record: DeployRecord,
    app: DeployApplication,
    app_env: DeployAppEnv,
) -> None:
    """执行 K8s 部署：PATCH Deployment 镜像 → 轮询 rollout → 健康检查。"""
    cluster = app_env.k8s_cluster
    if cluster is None:
        update_status(db, record, "failed")
        set_error(db, record, "未配置 K8s 集群")
        return

    endpoint = cluster.endpoint
    token = cluster.token
    if not endpoint or not token:
        update_status(db, record, "failed")
        set_error(db, record, "K8s 集群未配置 endpoint 或 token")
        return

    namespace = app_env.k8s_namespace or "default"
    deployment_name = app_env.k8s_deployment
    container_name = app_env.k8s_container_name or ""
    image = app_env.docker_image  # 复用 docker_image 字段存储镜像

    if not deployment_name:
        update_status(db, record, "failed")
        set_error(db, record, "未配置 Deployment 名称")
        return

    if not image:
        update_status(db, record, "failed")
        set_error(db, record, "未配置镜像")
        return

    health_url = app.health_check_url or ""
    health_timeout = app.health_check_timeout or 30
    base = endpoint.rstrip("/")

    try:
        update_status(db, record, "deploying")
        append_log(db, record, f"K8s 集群: {cluster.name} ({endpoint})")
        append_log(db, record, f"目标: {namespace}/{deployment_name}")
        append_log(db, record, f"镜像: {image}")

        # ── 1. 获取当前 Deployment ──
        if is_cancelled(record.id):
            update_status(db, record, "cancelled")
            return

        deploy_url = f"{base}/apis/apps/v1/namespaces/{namespace}/deployments/{deployment_name}"
        with httpx.Client(timeout=_TIMEOUT, verify=False) as client:
            resp = client.get(deploy_url, headers=_k8s_headers(token))
            if resp.status_code == 404:
                update_status(db, record, "failed")
                set_error(db, record, f"Deployment {deployment_name} 不存在")
                append_log(db, record, f"Deployment 不存在: {namespace}/{deployment_name}")
                return
            resp.raise_for_status()
            current_deploy = resp.json()

        # ── 2. PATCH 镜像 ──
        if is_cancelled(record.id):
            update_status(db, record, "cancelled")
            return

        # 构建 patch：找到目标容器并更新 image
        containers = current_deploy.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [])
        target_container = container_name
        if not target_container and containers:
            target_container = containers[0].get("name", "")

        if not target_container:
            update_status(db, record, "failed")
            set_error(db, record, "无法确定容器名，请配置 k8s_container_name")
            return

        patch_body = {
            "spec": {
                "template": {
                    "spec": {
                        "containers": [
                            {
                                "name": target_container,
                                "image": image,
                            }
                        ]
                    }
                }
            }
        }

        append_log(db, record, f"更新容器 {target_container} 镜像 → {image}")
        with httpx.Client(timeout=_TIMEOUT, verify=False) as client:
            resp = client.patch(
                deploy_url,
                headers={**_k8s_headers(token), "Content-Type": "application/strategic-merge-patch+json"},
                content=json.dumps(patch_body),
            )
            resp.raise_for_status()

        append_log(db, record, "Deployment 已更新，等待 rollout 完成…")

        # ── 3. 轮询 rollout status ──
        if is_cancelled(record.id):
            update_status(db, record, "cancelled")
            return

        rollout_ok = _poll_rollout(base, token, namespace, deployment_name, record, db, timeout=180)
        if not rollout_ok:
            update_status(db, record, "failed")
            set_error(db, record, "Rollout 超时或失败")
            return

        append_log(db, record, "Rollout 完成")

        # ── 4. 健康检查 ──
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

    except httpx.HTTPStatusError as e:
        msg = f"K8s API 错误: HTTP {e.response.status_code}"
        logger.exception("K8s deploy HTTP error for record %s", record.id)
        update_status(db, record, "failed")
        set_error(db, record, msg)
        append_log(db, record, msg)

    except Exception as e:
        logger.exception("K8s deploy error for record %s", record.id)
        update_status(db, record, "failed")
        set_error(db, record, str(e))
        append_log(db, record, f"部署异常: {e}")


def _poll_rollout(
    base: str,
    token: str,
    namespace: str,
    deployment_name: str,
    record: DeployRecord,
    db,
    timeout: int = 180,
    interval: int = 5,
) -> bool:
    """轮询 Deployment rollout 状态，直到成功或超时。"""
    deploy_url = f"{base}/apis/apps/v1/namespaces/{namespace}/deployments/{deployment_name}"
    deadline = time.time() + timeout

    while time.time() < deadline:
        if is_cancelled(record.id):
            return False

        try:
            with httpx.Client(timeout=_TIMEOUT, verify=False) as client:
                resp = client.get(deploy_url, headers=_k8s_headers(token))
                resp.raise_for_status()
                deploy = resp.json()

            status = deploy.get("status", {})
            conditions = status.get("conditions", []) or []
            replicas = status.get("replicas", 0)
            ready = status.get("readyReplicas", 0) or 0
            updated = status.get("updatedReplicas", 0) or 0

            # 检查 Progressing=True 且 Available=True
            progressing = next((c for c in conditions if c.get("type") == "Progressing"), None)
            available = next((c for c in conditions if c.get("type") == "Available"), None)

            if progressing and progressing.get("status") == "True" and progressing.get("reason") == "NewReplicaSetAvailable":
                if available and available.get("status") == "True":
                    append_log(db, record, f"  就绪: {ready}/{replicas} pods")
                    return True

            append_log(db, record, f"  进度: {updated} updated / {ready} ready / {replicas} total")

        except Exception as e:
            logger.debug("Rollout poll error: %s", e)

        time.sleep(interval)

    return False
