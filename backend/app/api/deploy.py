"""应用发布 API。"""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import api_permission_required, get_client_ip, get_current_api_user
from app.db.database import get_db
from app.models.user import User
from app.services.audit import write_log
from app.services.deploy import apps as app_service
from app.services.deploy import envs as env_service
from app.services.deploy import records as record_service
from app.services.deploy import approvals as approval_service

router = APIRouter(prefix="/deploy", tags=["应用发布"])


# ─── Pydantic 模型 ───────────────────────────────────────────


class AppCreate(BaseModel):
    name: str
    display_name: str = ""
    app_type: str = "backend"
    deploy_method: str = "jenkins"
    repo_url: str = ""
    repo_branch: str = "main"
    build_script: str = ""
    description: str = ""


class AppUpdate(BaseModel):
    name: str = ""
    display_name: str = ""
    app_type: str = ""
    deploy_method: str = ""
    repo_url: str = ""
    repo_branch: str = ""
    build_script: str = ""
    description: str = ""
    status: str = ""


class EnvCreate(BaseModel):
    name: str
    display_name: str = ""
    approval_required: bool = False
    description: str = ""
    sort_order: int = 0


class EnvUpdate(BaseModel):
    name: str = ""
    display_name: str = ""
    approval_required: bool | None = None
    description: str = ""
    sort_order: int | None = None


class AppEnvConfig(BaseModel):
    environment_id: int
    jenkins_job_name: str = ""
    jenkins_params_json: str = "{}"
    docker_image: str = ""
    docker_host_id: int | None = None
    k8s_cluster_id: int | None = None
    k8s_namespace: str = "default"
    k8s_deployment_name: str = ""
    ssh_asset_id: int | None = None
    ssh_deploy_path: str = ""
    ssh_deploy_script: str = ""


class DeployCreate(BaseModel):
    application_id: int
    environment_id: int
    version: str = ""
    image: str = ""


class ApprovalAction(BaseModel):
    action: str  # approved / rejected
    comment: str = ""


# ─── 序列化 ──────────────────────────────────────────────────


def _app_dict(app) -> dict:
    return {
        "id": app.id,
        "name": app.name,
        "display_name": app.display_name,
        "app_type": app.app_type,
        "deploy_method": app.deploy_method,
        "repo_url": app.repo_url,
        "repo_branch": app.repo_branch,
        "build_script": app.build_script,
        "description": app.description,
        "status": app.status,
        "creator_id": app.creator_id,
        "creator_name": app.creator.username if app.creator else "",
        "created_at": app.created_at.isoformat() if app.created_at else None,
        "updated_at": app.updated_at.isoformat() if app.updated_at else None,
    }


def _env_dict(env) -> dict:
    return {
        "id": env.id,
        "name": env.name,
        "display_name": env.display_name,
        "approval_required": env.approval_required,
        "description": env.description,
        "sort_order": env.sort_order,
        "created_at": env.created_at.isoformat() if env.created_at else None,
    }


def _app_env_dict(ae) -> dict:
    return {
        "id": ae.id,
        "application_id": ae.application_id,
        "environment_id": ae.environment_id,
        "environment_name": ae.environment.name if ae.environment else "",
        "environment_display_name": ae.environment.display_name if ae.environment else "",
        "jenkins_job_name": ae.jenkins_job_name,
        "jenkins_params_json": ae.jenkins_params_json,
        "docker_image": ae.docker_image,
        "docker_host_id": ae.docker_host_id,
        "k8s_cluster_id": ae.k8s_cluster_id,
        "k8s_namespace": ae.k8s_namespace,
        "k8s_deployment_name": ae.k8s_deployment_name,
        "ssh_asset_id": ae.ssh_asset_id,
        "ssh_deploy_path": ae.ssh_deploy_path,
        "ssh_deploy_script": ae.ssh_deploy_script,
        "created_at": ae.created_at.isoformat() if ae.created_at else None,
    }


def _record_dict(r) -> dict:
    return {
        "id": r.id,
        "application_id": r.application_id,
        "application_name": r.application.name if r.application else "",
        "environment_id": r.environment_id,
        "environment_name": r.environment.name if r.environment else "",
        "environment_display_name": r.environment.display_name if r.environment else "",
        "deploy_method": r.deploy_method,
        "version": r.version,
        "image": r.image,
        "status": r.status,
        "trigger_type": r.trigger_type,
        "jenkins_build_number": r.jenkins_build_number,
        "jenkins_build_url": r.jenkins_build_url,
        "duration_seconds": r.duration_seconds,
        "rollback_from": r.rollback_from,
        "creator_id": r.creator_id,
        "creator_name": r.creator.username if r.creator else "",
        "started_at": r.started_at.isoformat() if r.started_at else None,
        "finished_at": r.finished_at.isoformat() if r.finished_at else None,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


def _record_detail_dict(r) -> dict:
    d = _record_dict(r)
    d["logs"] = r.logs or ""
    d["approvals"] = [
        {
            "id": a.id,
            "action": a.action,
            "comment": a.comment,
            "approver_id": a.approver_id,
            "approver_name": a.approver.username if a.approver else "",
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in (r.approvals or [])
    ]
    return d


def _approval_dict(a) -> dict:
    return {
        "id": a.id,
        "deployment_id": a.deployment_id,
        "action": a.action,
        "comment": a.comment,
        "approver_id": a.approver_id,
        "approver_name": a.approver.username if a.approver else "",
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


# ─── 应用 CRUD ───────────────────────────────────────────────


@router.get("/apps")
def list_apps(
    keyword: str = "",
    deploy_method: str = "",
    status: str = "",
    page: int = 1,
    page_size: int = 20,
    _current_user: User = Depends(api_permission_required("deploy.view")),
    db: Session = Depends(get_db),
):
    items = app_service.list_apps(db, keyword=keyword, deploy_method=deploy_method, status=status)
    total = len(items)
    start = (max(page, 1) - 1) * page_size
    return {"code": 0, "data": {"items": [_app_dict(a) for a in items[start:start + page_size]], "total": total, "page": page, "page_size": page_size}}


@router.get("/apps/{app_id}")
def get_app(
    app_id: int,
    _current_user: User = Depends(api_permission_required("deploy.view")),
    db: Session = Depends(get_db),
):
    app = app_service.get_app(db, app_id)
    if not app:
        raise HTTPException(status_code=404, detail="应用不存在")
    data = _app_dict(app)
    data["environments"] = [_app_env_dict(ae) for ae in app_service.list_app_envs(db, app_id)]
    return {"code": 0, "data": data}


@router.post("/apps")
def create_app(
    body: AppCreate,
    request: Request,
    current_user: User = Depends(api_permission_required("deploy.create")),
    db: Session = Depends(get_db),
):
    app = app_service.create_app(db, name=body.name, display_name=body.display_name, app_type=body.app_type, deploy_method=body.deploy_method, repo_url=body.repo_url, repo_branch=body.repo_branch, build_script=body.build_script, description=body.description, creator_id=current_user.id)
    write_log(db, user=current_user, action="create", target_type="deploy_app", target_id=app.id, target_name=app.name, ip_address=get_client_ip(request))
    db.commit()
    return {"code": 0, "msg": "创建成功", "data": _app_dict(app)}


@router.put("/apps/{app_id}")
def update_app(
    app_id: int,
    body: AppUpdate,
    request: Request,
    current_user: User = Depends(api_permission_required("deploy.update")),
    db: Session = Depends(get_db),
):
    app = app_service.get_app(db, app_id)
    if not app:
        raise HTTPException(status_code=404, detail="应用不存在")
    update_data = {k: v for k, v in body.model_dump().items() if v}
    if update_data:
        app_service.update_app(db, app, **update_data)
    write_log(db, user=current_user, action="update", target_type="deploy_app", target_id=app.id, target_name=app.name, ip_address=get_client_ip(request))
    db.commit()
    return {"code": 0, "msg": "更新成功", "data": _app_dict(app)}


@router.delete("/apps/{app_id}")
def delete_app(
    app_id: int,
    request: Request,
    current_user: User = Depends(api_permission_required("deploy.delete")),
    db: Session = Depends(get_db),
):
    app = app_service.get_app(db, app_id)
    if not app:
        raise HTTPException(status_code=404, detail="应用不存在")
    name = app.name
    app_service.delete_app(db, app)
    write_log(db, user=current_user, action="delete", target_type="deploy_app", target_id=app_id, target_name=name, ip_address=get_client_ip(request))
    db.commit()
    return {"code": 0, "msg": "删除成功"}


# ─── 应用-环境配置 ───────────────────────────────────────────


@router.get("/apps/{app_id}/envs")
def list_app_envs(
    app_id: int,
    _current_user: User = Depends(api_permission_required("deploy.view")),
    db: Session = Depends(get_db),
):
    items = app_service.list_app_envs(db, app_id)
    return {"code": 0, "data": [_app_env_dict(ae) for ae in items]}


@router.post("/apps/{app_id}/envs")
def save_app_env(
    app_id: int,
    body: AppEnvConfig,
    request: Request,
    current_user: User = Depends(api_permission_required("deploy.update")),
    db: Session = Depends(get_db),
):
    app = app_service.get_app(db, app_id)
    if not app:
        raise HTTPException(status_code=404, detail="应用不存在")
    ae = app_service.save_app_env(db, application_id=app_id, environment_id=body.environment_id, jenkins_job_name=body.jenkins_job_name, jenkins_params_json=body.jenkins_params_json, docker_image=body.docker_image, docker_host_id=body.docker_host_id, k8s_cluster_id=body.k8s_cluster_id, k8s_namespace=body.k8s_namespace, k8s_deployment_name=body.k8s_deployment_name, ssh_asset_id=body.ssh_asset_id, ssh_deploy_path=body.ssh_deploy_path, ssh_deploy_script=body.ssh_deploy_script)
    write_log(db, user=current_user, action="update", target_type="deploy_app", target_id=app.id, target_name=app.name, detail=f"更新环境配置 env_id={body.environment_id}", ip_address=get_client_ip(request))
    db.commit()
    return {"code": 0, "msg": "保存成功", "data": _app_env_dict(ae)}


@router.delete("/apps/{app_id}/envs/{env_id}")
def delete_app_env(
    app_id: int,
    env_id: int,
    request: Request,
    current_user: User = Depends(api_permission_required("deploy.update")),
    db: Session = Depends(get_db),
):
    ae = app_service.get_app_env_by_pair(db, app_id, env_id)
    if not ae:
        raise HTTPException(status_code=404, detail="配置不存在")
    app_service.delete_app_env(db, ae)
    write_log(db, user=current_user, action="update", target_type="deploy_app", target_id=app_id, detail=f"移除环境配置 env_id={env_id}", ip_address=get_client_ip(request))
    db.commit()
    return {"code": 0, "msg": "删除成功"}


# ─── 环境管理 ────────────────────────────────────────────────


@router.get("/envs")
def list_envs(
    _current_user: User = Depends(api_permission_required("deploy.view")),
    db: Session = Depends(get_db),
):
    items = env_service.list_envs(db)
    return {"code": 0, "data": [_env_dict(e) for e in items]}


@router.post("/envs")
def create_env(
    body: EnvCreate,
    request: Request,
    current_user: User = Depends(api_permission_required("deploy.create")),
    db: Session = Depends(get_db),
):
    env = env_service.create_env(db, name=body.name, display_name=body.display_name, approval_required=body.approval_required, description=body.description, sort_order=body.sort_order)
    write_log(db, user=current_user, action="create", target_type="deploy_env", target_id=env.id, target_name=env.name, ip_address=get_client_ip(request))
    db.commit()
    return {"code": 0, "msg": "创建成功", "data": _env_dict(env)}


@router.put("/envs/{env_id}")
def update_env(
    env_id: int,
    body: EnvUpdate,
    request: Request,
    current_user: User = Depends(api_permission_required("deploy.update")),
    db: Session = Depends(get_db),
):
    env = env_service.get_env(db, env_id)
    if not env:
        raise HTTPException(status_code=404, detail="环境不存在")
    update_data = {k: v for k, v in body.model_dump().items() if v is not None and v != ""}
    if update_data:
        env_service.update_env(db, env, **update_data)
    write_log(db, user=current_user, action="update", target_type="deploy_env", target_id=env.id, target_name=env.name, ip_address=get_client_ip(request))
    db.commit()
    return {"code": 0, "msg": "更新成功", "data": _env_dict(env)}


@router.delete("/envs/{env_id}")
def delete_env(
    env_id: int,
    request: Request,
    current_user: User = Depends(api_permission_required("deploy.delete")),
    db: Session = Depends(get_db),
):
    env = env_service.get_env(db, env_id)
    if not env:
        raise HTTPException(status_code=404, detail="环境不存在")
    name = env.name
    env_service.delete_env(db, env)
    write_log(db, user=current_user, action="delete", target_type="deploy_env", target_id=env_id, target_name=name, ip_address=get_client_ip(request))
    db.commit()
    return {"code": 0, "msg": "删除成功"}


# ─── 发布记录 ────────────────────────────────────────────────


@router.get("/records")
def list_records(
    application_id: int | None = None,
    environment_id: int | None = None,
    status: str = "",
    keyword: str = "",
    page: int = 1,
    page_size: int = 20,
    _current_user: User = Depends(api_permission_required("deploy.view")),
    db: Session = Depends(get_db),
):
    items = record_service.list_records(db, application_id=application_id, environment_id=environment_id, status=status, keyword=keyword)
    total = len(items)
    start = (max(page, 1) - 1) * page_size
    return {"code": 0, "data": {"items": [_record_dict(r) for r in items[start:start + page_size]], "total": total, "page": page, "page_size": page_size}}


@router.get("/records/{record_id}")
def get_record(
    record_id: int,
    _current_user: User = Depends(api_permission_required("deploy.view")),
    db: Session = Depends(get_db),
):
    r = record_service.get_record(db, record_id)
    if not r:
        raise HTTPException(status_code=404, detail="发布记录不存在")
    return {"code": 0, "data": _record_detail_dict(r)}


@router.post("/records")
def create_deployment(
    body: DeployCreate,
    request: Request,
    current_user: User = Depends(api_permission_required("deploy.execute")),
    db: Session = Depends(get_db),
):
    app = app_service.get_app(db, body.application_id)
    if not app:
        raise HTTPException(status_code=404, detail="应用不存在")

    # SSH 部署必须走文件上传接口，不创建记录
    from app.models.deploy import DeployAppEnv
    app_env = db.scalar(
        select(DeployAppEnv).where(
            DeployAppEnv.application_id == body.application_id,
            DeployAppEnv.environment_id == body.environment_id,
        )
    )
    if app.deploy_method == "ssh" or (app_env and app_env.ssh_asset_id):
        raise HTTPException(status_code=400, detail="SSH 部署请使用文件上传接口")

    from app.models.deploy import DeployRecord
    record = DeployRecord(
        application_id=body.application_id,
        environment_id=body.environment_id,
        deploy_method=app.deploy_method,
        version=body.version,
        image=body.image,
        status="pending",
        trigger_type="manual",
        creator_id=current_user.id,
    )
    db.add(record)
    db.flush()

    # 检查是否需要审批
    from app.models.deploy import DeployEnvironment
    env = db.get(DeployEnvironment, body.environment_id)
    if env and env.approval_required:
        db.commit()
        return {"code": 0, "msg": "已提交，等待审批", "data": _record_dict(record)}

    # 直接执行
    result = record_service.execute_deployment(db, record)
    if not result["ok"]:
        record.status = "failed"
        record.logs = result.get("error", "")
        db.commit()
        raise HTTPException(status_code=400, detail=result.get("error", "发布失败"))

    write_log(db, user=current_user, action="create", target_type="deploy_record", target_id=record.id, target_name=f"{app.name} -> {env.name if env else ''}", ip_address=get_client_ip(request))
    db.commit()
    return {"code": 0, "msg": "发布已触发", "data": _record_dict(record)}


@router.post("/records/upload")
async def upload_and_deploy(
    request: Request,
    background_tasks: BackgroundTasks,
    application_id: int = Form(...),
    environment_id: int = Form(...),
    version: str = Form(""),
    file: UploadFile = File(...),
    current_user: User = Depends(api_permission_required("deploy.execute")),
    db: Session = Depends(get_db),
):
    """SSH 部署：上传文件到服务器并执行部署脚本（后台执行，立即返回）。"""
    app = app_service.get_app(db, application_id)
    if not app:
        raise HTTPException(status_code=404, detail="应用不存在")

    # 读取文件内容
    file_content = await file.read()
    if not file_content:
        raise HTTPException(status_code=400, detail="上传文件为空")
    if len(file_content) > 500 * 1024 * 1024:  # 500MB 限制
        raise HTTPException(status_code=400, detail="文件大小不能超过 500MB")

    from app.models.deploy import DeployRecord
    record = DeployRecord(
        application_id=application_id,
        environment_id=environment_id,
        deploy_method="ssh",
        version=version or file.filename or "",
        status="pending",
        trigger_type="manual",
        creator_id=current_user.id,
    )
    db.add(record)
    db.flush()
    record_id = record.id

    # SSH 部署跳过审批流程（手动上传文件，无需审批）
    write_log(db, user=current_user, action="create", target_type="deploy_record", target_id=record_id, target_name=f"{app.name} SSH 部署", ip_address=get_client_ip(request))
    db.commit()

    # 后台执行 SSH 部署
    background_tasks.add_task(
        record_service.execute_ssh_deployment_background,
        record_id, file_content, file.filename or "upload",
    )
    return {"code": 0, "msg": "部署已启动", "data": {"record_id": record_id}}


@router.post("/records/{record_id}/retry")
def retry_deployment(
    record_id: int,
    request: Request,
    current_user: User = Depends(api_permission_required("deploy.execute")),
    db: Session = Depends(get_db),
):
    record = record_service.get_record(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="发布记录不存在")
    if record.status not in ("failed", "rejected"):
        raise HTTPException(status_code=400, detail="只能重试失败或被驳回的发布")

    record.status = "pending"
    record.jenkins_build_number = None
    record.jenkins_build_url = ""
    record.logs = ""
    record.started_at = None
    record.finished_at = None
    record.duration_seconds = None
    db.flush()

    result = record_service.execute_deployment(db, record)
    if not result["ok"]:
        record.status = "failed"
        record.logs = result.get("error", "")
        db.commit()
        raise HTTPException(status_code=400, detail=result.get("error", "重试失败"))

    write_log(db, user=current_user, action="update", target_type="deploy_record", target_id=record.id, target_name="重试发布", ip_address=get_client_ip(request))
    db.commit()
    return {"code": 0, "msg": "重试已触发", "data": _record_dict(record)}


@router.post("/records/{record_id}/rollback")
def rollback_deployment(
    record_id: int,
    request: Request,
    current_user: User = Depends(api_permission_required("deploy.execute")),
    db: Session = Depends(get_db),
):
    result = record_service.rollback_deployment(db, record_id, current_user.id)
    if not result["ok"]:
        raise HTTPException(status_code=400, detail=result.get("error", "回滚失败"))

    write_log(db, user=current_user, action="create", target_type="deploy_record", target_id=result["record_id"], target_name=f"回滚自 #{record_id}", ip_address=get_client_ip(request))
    db.commit()
    return {"code": 0, "msg": "回滚记录已创建", "data": {"record_id": result["record_id"]}}


@router.get("/records/{record_id}/logs")
def get_deploy_logs(
    record_id: int,
    start: int = 0,
    _current_user: User = Depends(api_permission_required("deploy.view")),
    db: Session = Depends(get_db),
):
    record = record_service.get_record(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="发布记录不存在")

    # 如果正在构建中，实时拉取 Jenkins 日志
    if record.status == "building" and record.jenkins_build_number:
        jenkins_config = record_service._get_jenkins_config(db)
        if jenkins_config:
            from app.services.deploy.jenkins import get_build_log
            from app.models.deploy import DeployAppEnv
            app_env = db.scalar(
                __import__("sqlalchemy", fromlist=["select"]).select(DeployAppEnv).where(
                    DeployAppEnv.application_id == record.application_id,
                    DeployAppEnv.environment_id == record.environment_id,
                )
            )
            if app_env:
                result = get_build_log(
                    jenkins_config["base_url"], app_env.jenkins_job_name,
                    record.jenkins_build_number,
                    jenkins_config["username"], jenkins_config["api_token"],
                    start=start,
                )
                if result["ok"]:
                    return {"code": 0, "data": {"text": result["text"], "offset": result["offset"], "more": result["more"], "building": True}}

    return {"code": 0, "data": {"text": record.logs or "", "offset": 0, "more": False, "building": record.status == "building"}}


# ─── 审批 ────────────────────────────────────────────────────


@router.get("/pending")
def list_pending(
    _current_user: User = Depends(api_permission_required("deploy.approve")),
    db: Session = Depends(get_db),
):
    items = approval_service.get_pending_deployments(db)
    return {"code": 0, "data": [_record_dict(r) for r in items]}


@router.post("/records/{record_id}/approve")
def approve_deployment(
    record_id: int,
    body: ApprovalAction,
    request: Request,
    current_user: User = Depends(api_permission_required("deploy.approve")),
    db: Session = Depends(get_db),
):
    record = record_service.get_record(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="发布记录不存在")
    if record.status != "pending":
        raise HTTPException(status_code=400, detail="该记录不在待审批状态")

    if body.action not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="action 必须为 approved 或 rejected")

    approval_service.create_approval(db, deployment_id=record_id, action=body.action, comment=body.comment, approver_id=current_user.id)

    if body.action == "approved":
        record.status = "approved"
        db.flush()
        # 审批通过后自动执行
        result = record_service.execute_deployment(db, record)
        if not result["ok"]:
            record.status = "failed"
            record.logs = result.get("error", "")
    else:
        record.status = "rejected"
        record.finished_at = __import__("datetime").datetime.now(CHINA_TZ)

    write_log(db, user=current_user, action="update", target_type="deploy_record", target_id=record.id, target_name=f"审批: {body.action}", ip_address=get_client_ip(request))
    db.commit()
    return {"code": 0, "msg": "审批完成", "data": _record_dict(record)}


# ─── 看板与统计 ──────────────────────────────────────────────


@router.get("/status")
def get_status_matrix(
    _current_user: User = Depends(api_permission_required("deploy.view")),
    db: Session = Depends(get_db),
):
    data = record_service.get_status_matrix(db)
    return {"code": 0, "data": data}


@router.get("/overview")
def get_overview(
    _current_user: User = Depends(api_permission_required("deploy.view")),
    db: Session = Depends(get_db),
):
    data = record_service.get_overview(db)
    return {"code": 0, "data": data}
