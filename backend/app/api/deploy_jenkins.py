"""模式 B（Jenkins 治理触发）回调端点。

POST /deploy/jenkins/callback：Jenkins pipeline post 阶段调用，
一次性 token 认证（触发时生成、随构建参数 CALLBACK_TOKEN 下发、用后即焚）
+ 幂等（仅 triggering 状态接受变更）。触发逻辑见 services/deploy/modeb.py。
"""
from __future__ import annotations

import json
import secrets
from datetime import datetime

import httpx
from fastapi import APIRouter, Body, Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import api_permission_required
from app.core.config import CHINA_TZ
from app.db.database import get_db
from app.models.deploy import DeployApplication, DeployEnvironment, DeployRecord
from app.models.user import User
from app.services.audit import write_log

router = APIRouter(prefix="/deploy/jenkins", tags=["应用发布-Jenkins模式B"])

DEMO_APP_NAME = "jenkins-modeb-demo"
DEMO_JOB_DEFAULT = "ops-modeb-demo"
_JENKINS_TIMEOUT = 15



@router.post("/callback")
def jenkins_callback(
    body: dict = Body(...),
    x_deploy_token: str = Header(default="", alias="X-Deploy-Token"),
    db: Session = Depends(get_db),
):
    """Jenkins post 阶段回调。一次性 token 认证 + 幂等（仅 triggering 状态接受变更）。

    认证：token 是触发时生成、绑定该记录的一次性值（存 deploy_config 快照），
    随构建参数 CALLBACK_TOKEN 下发。记录进入终态后即失效。
    body: {"record_id": int, "status": "success"|"failed", "build_url": str, "message": str}
    """
    record_id = body.get("record_id")
    status = body.get("status")
    if not isinstance(record_id, int) or status not in ("success", "failed"):
        return {"code": 1, "msg": "body 需要 record_id(int) 与 status(success|failed)"}

    record = db.get(DeployRecord, record_id)
    if record is None:
        return {"code": 1, "msg": f"记录 {record_id} 不存在"}

    # 一次性 token 校验：与该记录快照里的 token 严格比对
    try:
        snapshot = json.loads(record.deploy_config or "{}")
    except (ValueError, TypeError):
        snapshot = {}
    expected_token = str(snapshot.get("callback_token") or "")
    if not expected_token or not secrets.compare_digest(x_deploy_token, expected_token):
        return {"code": 1, "msg": "回调 token 无效"}

    # 幂等：只有 triggering 状态接受回调；重复/迟到回调直接 no-op
    if record.status != "triggering":
        return {"code": 0, "msg": f"no-op：记录当前状态 {record.status}，忽略回调"}

    build_url = str(body.get("build_url") or "")
    message = str(body.get("message") or "")
    now = datetime.now(CHINA_TZ)
    record.status = status
    record.finished_at = now
    if record.started_at:
        # MySQL 读回的 datetime 是 naive（时区被剥离），补上中国时区再相减，
        # 否则 aware - naive 抛 TypeError → 500
        started = record.started_at
        if started.tzinfo is None:
            started = started.replace(tzinfo=CHINA_TZ)
        record.duration = (now - started).total_seconds()
    if status == "failed":
        record.error_message = message or "Jenkins 构建失败（详见构建日志）"
    record.log += f"\n[Jenkins 回调] status={status} build_url={build_url}"
    if message:
        record.log += f" message={message}"

    # 合并 build_url 进快照；一次性 token 用后即焚（从快照清除）
    if build_url:
        snapshot["jenkins_build_url"] = build_url
    snapshot.pop("callback_token", None)
    record.deploy_config = json.dumps(snapshot, ensure_ascii=False)
    db.commit()

    return {"code": 0, "msg": f"记录 {record_id} 已更新为 {status}"}
