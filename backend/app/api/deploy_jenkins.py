"""模式 B（Jenkins 治理触发）链路验证端点 — demo 性质 + 正式回调端点。

用途：不动现有 Jenkins job，用一个 demo job 验证
「平台触发 → Jenkins 执行 → 回调 → 平台状态更新」整条链路。

端点：
- GET  /deploy/jenkins/demo/config   拿 callback 地址（配到 Jenkinsfile）
- POST /deploy/jenkins/demo/trigger  触发 demo job，建 triggering 记录
- POST /deploy/jenkins/callback      Jenkins post 阶段回调（无 JWT，一次性 token 认证 + 幂等）

认证机制（一次性 token）：平台每次触发时生成只绑定本次记录的随机 token，
随构建参数 CALLBACK_TOKEN 下发给 Jenkins，post 回调时带回。Jenkins 侧
无需配置任何凭据；token 用后即焚（记录终态后永久失效），泄露无影响。

正式落地模式 B 时，callback 端点直接复用；demo 两端点可下线。
完整设计见 docs/design/deploy-reliability-hardening.md §7 与
docs/superpowers/specs/2026-07-13-jenkins-release-integration-design.md。
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


def _ensure_demo_app(db: Session) -> DeployApplication:
    """确保 demo 应用存在（archived，不干扰正常应用列表）。"""
    app = db.scalar(select(DeployApplication).where(DeployApplication.name == DEMO_APP_NAME))
    if app is None:
        app = DeployApplication(
            name=DEMO_APP_NAME,
            display_name="模式B链路测试",
            description="Jenkins 模式 B 链路验证专用，可随时删除",
            app_type="other",
            deploy_strategy="ssh",
            status="archived",
            build_mode="jenkins",
        )
        db.add(app)
        db.flush()
    return app


def _resolve_env(db: Session, env_name: str) -> DeployEnvironment | None:
    env = db.scalar(select(DeployEnvironment).where(DeployEnvironment.name == env_name))
    if env is None:
        env = db.scalar(select(DeployEnvironment).limit(1))
    return env


@router.get("/demo/config")
def demo_config(
    request: Request,
    _: User = Depends(api_permission_required("deploy.execute")),
):
    """拿 callback 地址（Jenkinsfile 里配置用）。一次性 token 模式无需配 Jenkins 凭据。"""
    base = str(request.base_url).rstrip("/")
    return {
        "code": 0,
        "data": {
            "callback_url": f"{base}/api/v1/deploy/jenkins/callback",
            "demo_job_default": DEMO_JOB_DEFAULT,
            "note": (
                "一次性 token 模式：无需在 Jenkins 配置任何凭据。callback_url 按"
                "当前请求推断，Jenkins 侧请按网络拓扑改写（如 "
                "http://backend.ops-platform.svc:8000/api/v1/deploy/jenkins/callback）。"
            ),
        },
    }


@router.post("/demo/trigger")
def demo_trigger(
    body: dict = Body(default={}),
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("deploy.execute")),
):
    """触发 demo job：建 triggering 记录 → buildWithParameters → 回填构建号。

    body 可选：job_name / env / version / simulate(success|failure) / release_mode(deploy|rollback)
    """
    from app.services.deploy.builder import _get_jenkins_config

    jenkins_cfg = _get_jenkins_config()
    if not jenkins_cfg or not jenkins_cfg.get("url"):
        return {"code": 1, "msg": "Jenkins 未配置，请先在系统设置中配置 Jenkins"}

    job_name = (body.get("job_name") or DEMO_JOB_DEFAULT).strip()
    env_name = (body.get("env") or "dev").strip()
    version = (body.get("version") or f"demo-{datetime.now(CHINA_TZ).strftime('%H%M%S')}").strip()
    simulate = body.get("simulate") or "success"
    release_mode = body.get("release_mode") or "deploy"
    if simulate not in ("success", "failure"):
        return {"code": 1, "msg": "simulate 只能是 success / failure"}
    if release_mode not in ("deploy", "rollback"):
        return {"code": 1, "msg": "release_mode 只能是 deploy / rollback"}

    base_url = jenkins_cfg["url"].rstrip("/")
    username = jenkins_cfg.get("username", "")
    token = jenkins_cfg.get("token", "")
    auth = (username, token) if username else None

    app = _ensure_demo_app(db)
    env = _resolve_env(db, env_name)

    # 一次性回调 token：只绑定本记录，随构建参数下发，用后即焚
    callback_token = secrets.token_urlsafe(24)
    snapshot = {
        "mode": "jenkins-modeb-demo",
        "jenkins_job": job_name,
        "jenkins_build_number": None,
        "jenkins_build_url": "",
        "operator": current_user.username,
        "simulate": simulate,
        "release_mode": release_mode,
        "callback_token": callback_token,
    }
    record = DeployRecord(
        app_id=app.id,
        env_id=env.id if env else None,
        version=version,
        status="triggering",
        trigger_type="rollback" if release_mode == "rollback" else "manual",
        trigger_user_id=current_user.id,
        deploy_config=json.dumps(snapshot, ensure_ascii=False),
        log=(
            f"[模式B demo] 触发 Jenkins job={job_name} env={env_name} version={version} "
            f"simulate={simulate} release_mode={release_mode}\n"
            f"操作人: {current_user.username}，等待 Jenkins 执行并回调…"
        ),
        started_at=datetime.now(CHINA_TZ),
    )
    db.add(record)
    db.commit()

    # ── 触发 buildWithParameters（带模式 B 参数契约）──
    params = {
        "APP_NAME": app.name,
        "ENV": env_name,
        "VERSION": version,
        "OPERATOR": current_user.username,
        "RECORD_ID": str(record.id),
        "RELEASE_MODE": release_mode,
        "ROLLBACK_FROM": "",
        "SIMULATE_RESULT": simulate,
        "CALLBACK_TOKEN": callback_token,
    }
    queue_url = ""
    try:
        with httpx.Client(timeout=_JENKINS_TIMEOUT, verify=False) as client:
            resp = client.post(
                f"{base_url}/job/{job_name}/buildWithParameters",
                auth=auth,
                data=params,
            )
            if resp.status_code not in (200, 201, 202):
                record.status = "failed"
                record.error_message = f"Jenkins 触发失败: HTTP {resp.status_code} {resp.text[:200]}"
                record.log += f"\n[错误] Jenkins 触发失败: HTTP {resp.status_code}"
                record.finished_at = datetime.now(CHINA_TZ)
                db.commit()
                return {"code": 1, "msg": record.error_message, "data": {"record_id": record.id}}
            queue_url = resp.headers.get("Location", "")
    except Exception as e:  # noqa: BLE001
        record.status = "failed"
        record.error_message = f"Jenkins 连接失败: {e}"
        record.finished_at = datetime.now(CHINA_TZ)
        db.commit()
        return {"code": 1, "msg": record.error_message, "data": {"record_id": record.id}}

    # ── 从 queue 拿构建号（简化轮询，拿不到不阻塞，demo 宽容）──
    # 10 次 × 2s = 20s：Jenkins executor 忙时分配合并队列可能较慢
    build_number: int | None = None
    if queue_url:
        for _ in range(10):
            try:
                with httpx.Client(timeout=_JENKINS_TIMEOUT, verify=False) as client:
                    q = client.get(f"{queue_url.rstrip('/')}/api/json", auth=auth).json()
                    exe = q.get("executable") or {}
                    build_number = exe.get("number")
                    if build_number:
                        break
            except Exception:  # noqa: BLE001
                pass
            import time
            time.sleep(2)

    build_url = f"{base_url}/job/{job_name}/{build_number}" if build_number else ""
    if build_number:
        snapshot["jenkins_build_number"] = build_number
        snapshot["jenkins_build_url"] = build_url
        record.deploy_config = json.dumps(snapshot, ensure_ascii=False)
        record.log += f"\nJenkins 构建 #{build_number} 已开始：{build_url}"
    else:
        record.log += "\n[提示] 未能从队列取到构建号（不影响 demo，回调按 RECORD_ID 对账）"
    db.commit()

    write_log(
        db, user=current_user, action="deploy_jenkins_demo_trigger",
        target_type="deploy_record", target_name=f"{app.name}/{env_name}",
        detail=f"模式B demo 触发 job={job_name} version={version} simulate={simulate}",
    )
    db.commit()

    return {
        "code": 0,
        "msg": "已触发，等待 Jenkins 执行并回调",
        "data": {
            "record_id": record.id,
            "jenkins_build_url": build_url,
            "提示": "到「应用发布 → 部署记录」观察 jenkins-modeb-demo 应用的状态流转（triggering → success/failed）",
        },
    }


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
