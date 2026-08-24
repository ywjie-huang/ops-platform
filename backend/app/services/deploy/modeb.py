"""模式 B（Jenkins 治理触发）：平台治理、Jenkins 执行。

平台职责：权限/审批/版本台账/审计 + 触发 Job（带参数契约）+ 等回调更新状态。
Jenkins 职责：构建 + 部署。平台不下载产物、不碰目标服务器。

回调：POST /deploy/jenkins/callback（api/deploy_jenkins.py），一次性 token
认证 + 幂等，本模块触发时生成 token 存入 deploy_config 快照并随参数下发。
"""
from __future__ import annotations

import json
import logging
import secrets
import threading
import time
from datetime import datetime
from typing import Any

import httpx

from app.core.config import CHINA_TZ
from app.db.database import SessionLocal
from app.models.deploy import DeployApplication, DeployRecord

logger = logging.getLogger(__name__)

_JENKINS_TIMEOUT = 15
_QUEUE_POLL_TIMES = 10      # 10 × 2s = 20s：等 Jenkins 队列分配合并构建号
_QUEUE_POLL_INTERVAL = 2

RELEASE_MODES = ("platform", "jenkins")


def build_jenkins_params(
    *,
    app_name: str,
    env_name: str,
    version: str,
    operator: str,
    record_id: int,
    release_mode: str = "deploy",
    rollback_from: int | None = None,
    callback_token: str,
) -> dict[str, str]:
    """构造模式 B 的 Job 参数契约（纯函数，便于测试）。"""
    return {
        "APP_NAME": app_name,
        "ENV": env_name,
        "VERSION": version,
        "OPERATOR": operator,
        "RECORD_ID": str(record_id),
        "RELEASE_MODE": release_mode,
        "ROLLBACK_FROM": str(rollback_from) if rollback_from else "",
        "CALLBACK_TOKEN": callback_token,
    }


def _append_snapshot(record: DeployRecord, **kv: Any) -> None:
    """向 deploy_config 快照合并键值（触发线程与回调端点共用）。"""
    try:
        snapshot = json.loads(record.deploy_config or "{}")
    except (ValueError, TypeError):
        snapshot = {}
    snapshot.update(kv)
    record.deploy_config = json.dumps(snapshot, ensure_ascii=False)


def _fail(db, record: DeployRecord, message: str) -> None:
    """置 failed 并记录错误信息（update_status 无 error 参数，先赋值再更新）。"""
    from app.services.deploy.records import append_log, update_status

    record.error_message = message
    append_log(db, record, f"[错误] {message}")
    update_status(db, record, "failed")


def spawn_jenkins_release(
    *,
    record_id: int,
    app_id: int,
    env_name: str,
    version: str,
    operator: str,
    release_mode: str = "deploy",
    rollback_from: int | None = None,
) -> None:
    """起后台线程执行模式 B 触发；API 立即返回，记录状态为 triggering 等回调。"""
    thread = threading.Thread(
        target=_trigger_and_track,
        args=(record_id, app_id, env_name, version, operator, release_mode, rollback_from),
        daemon=True,
    )
    thread.start()


def _trigger_and_track(
    record_id: int,
    app_id: int,
    env_name: str,
    version: str,
    operator: str,
    release_mode: str,
    rollback_from: int | None,
) -> None:
    """触发 Jenkins Job → 轮询队列拿构建号 → 回填快照。失败置 failed。

    在独立线程与 Session 中运行（与 execute_deploy 的线程模式一致）。
    """
    from app.services.deploy.builder import _get_jenkins_config
    from app.services.deploy.records import append_log, update_status

    db = SessionLocal()
    try:
        record = db.get(DeployRecord, record_id)
        app = db.get(DeployApplication, app_id)
        if record is None or app is None:
            logger.error("[modeB] 记录或应用不存在: record=%s app=%s", record_id, app_id)
            return

        jenkins_cfg = _get_jenkins_config()
        if not jenkins_cfg or not jenkins_cfg.get("url"):
            _fail(db, record, "Jenkins 未配置，请在系统设置中配置")
            return
        job_name = (app.jenkins_job_name or "").strip()
        if not job_name:
            _fail(db, record, "应用未配置 Jenkins Job 名称")
            return

        base_url = jenkins_cfg["url"].rstrip("/")
        username = jenkins_cfg.get("username", "")
        token = jenkins_cfg.get("token", "")
        auth = (username, token) if username else None

        # 版本兜底：未填时用分支名+时间戳，保证 Jenkins 侧可追溯
        final_version = version or f"{app.git_branch or 'main'}-{datetime.now(CHINA_TZ).strftime('%Y%m%d%H%M%S')}"

        callback_token = secrets.token_urlsafe(24)
        _append_snapshot(
            record,
            release_mode="jenkins",
            callback_token=callback_token,
            jenkins_job=job_name,
            jenkins_build_number=None,
            jenkins_build_url="",
        )
        record.started_at = record.started_at or datetime.now(CHINA_TZ)
        record.status = "triggering"  # 回调幂等只认 triggering
        append_log(db, record, f"[模式B] 触发 Jenkins job={job_name} env={env_name} version={final_version} 操作人={operator}")
        db.commit()

        params = build_jenkins_params(
            app_name=app.name,
            env_name=env_name,
            version=final_version,
            operator=operator,
            record_id=record.id,
            release_mode=release_mode,
            rollback_from=rollback_from,
            callback_token=callback_token,
        )

        # ── 触发 ──
        queue_url = ""
        try:
            with httpx.Client(timeout=_JENKINS_TIMEOUT, verify=False) as client:
                resp = client.post(
                    f"{base_url}/job/{job_name}/buildWithParameters",
                    auth=auth,
                    data=params,
                )
                if resp.status_code not in (200, 201, 202):
                    _fail(db, record, f"Jenkins 触发失败: HTTP {resp.status_code} {resp.text[:200]}")
                    return
                queue_url = resp.headers.get("Location", "")
        except Exception as e:  # noqa: BLE001
            _fail(db, record, f"Jenkins 连接失败: {e}")
            return

        # ── 轮询队列拿构建号（拿不到不阻塞，回调按 RECORD_ID 对账）──
        build_number: int | None = None
        if queue_url:
            for _ in range(_QUEUE_POLL_TIMES):
                try:
                    with httpx.Client(timeout=_JENKINS_TIMEOUT, verify=False) as client:
                        q = client.get(f"{queue_url.rstrip('/')}/api/json", auth=auth).json()
                        build_number = (q.get("executable") or {}).get("number")
                        if build_number:
                            break
                except Exception:  # noqa: BLE001
                    pass
                time.sleep(_QUEUE_POLL_INTERVAL)

        if build_number:
            build_url = f"{base_url}/job/{job_name}/{build_number}"
            _append_snapshot(record, jenkins_build_number=build_number, jenkins_build_url=build_url)
            append_log(db, record, f"Jenkins 构建 #{build_number} 已开始：{build_url}")
        else:
            append_log(db, record, "[提示] 未能从队列取到构建号，回调将按 RECORD_ID 对账")
        append_log(db, record, "等待 Jenkins 执行并回调…")
        db.commit()
        # 记录保持 triggering，等 /deploy/jenkins/callback 更新终态

    except Exception as e:  # noqa: BLE001
        logger.exception("[modeB] 触发线程异常: record=%s", record_id)
        try:
            record = db.get(DeployRecord, record_id)
            if record and record.status == "triggering":
                _fail(db, record, f"触发异常: {e}")
        except Exception:  # noqa: BLE001
            pass
    finally:
        db.close()
