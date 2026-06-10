"""应用发布 API。"""
import json
import os
import threading
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Header
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import api_permission_required, get_client_ip
from app.core.config import CHINA_TZ, DEPLOY_ARTIFACT_DIR
from app.db.database import get_db
from app.models.deploy import DeployApplication, DeployBuild
from app.models.user import User
from app.services.audit import write_log
from app.services.deploy.applications import (
    create_application,
    delete_application,
    get_application,
    get_application_by_name,
    list_applications,
    list_environments,
    update_application,
)
from app.services.deploy.app_envs import (
    delete_app_env,
    get_app_env,
    get_app_env_by_pair,
    list_app_envs,
    upsert_app_env,
)
from app.services.deploy.records import (
    append_log,
    create_record,
    execute_deploy,
    get_record,
    list_records,
    request_cancel,
    update_status,
)
from app.services.deploy.configs import (
    create_config,
    delete_config,
    get_config,
    list_configs,
    update_config,
)
from app.services.deploy.approvals import (
    approve,
    create_approval,
    get_approval,
    list_approvals,
    reject,
)
from app.services.deploy.webhook import (
    verify_webhook_signature,
    generate_webhook_secret,
    save_artifact_file,
    download_artifact_from_url,
    create_build_record,
    generate_build_number,
    cleanup_old_builds,
)

router = APIRouter(prefix="/deploy", tags=["应用发布"])


# ──────────────────────── Pydantic 模型 ────────────────────────


class AppCreate(BaseModel):
    name: str
    display_name: str = ""
    description: str = ""
    app_type: str = "web"
    deploy_strategy: str = "ssh"
    git_url: str = ""
    git_branch: str = "main"
    build_mode: str = "upload"
    build_command: str = ""
    artifact_path: str = ""
    jenkins_job_name: str = ""
    jenkins_token: str = ""


class AppUpdate(BaseModel):
    name: str
    display_name: str = ""
    description: str = ""
    app_type: str = "web"
    deploy_strategy: str = "ssh"
    status: str = "active"
    git_url: str = ""
    git_branch: str = "main"
    build_mode: str = "upload"
    build_command: str = ""
    artifact_path: str = ""
    jenkins_job_name: str = ""
    jenkins_token: str = ""


class AppEnvUpdate(BaseModel):
    enabled: bool = True
    # SSH
    ssh_asset_id: int | None = None
    deploy_path: str = ""
    deploy_script: str = ""
    health_check_url: str = ""
    health_check_port: int = 0
    health_check_timeout: int = 30
    # Docker
    docker_host_id: int | None = None
    docker_image: str = ""
    docker_container_name: str = ""
    docker_ports: str = ""
    docker_env_vars: str = ""
    docker_network: str = ""
    docker_extra_args: str = ""
    # K8s
    k8s_cluster_id: int | None = None
    k8s_namespace: str = "default"
    k8s_deployment: str = ""
    k8s_container_name: str = ""


# ──────────────────────── 序列化辅助 ────────────────────────


def _app_dict(app) -> dict:
    return {
        "id": app.id,
        "name": app.name,
        "display_name": app.display_name,
        "description": app.description,
        "app_type": app.app_type,
        "deploy_strategy": app.deploy_strategy,
        "status": app.status,
        "git_url": app.git_url,
        "git_branch": app.git_branch,
        "build_mode": app.build_mode,
        "build_command": app.build_command,
        "artifact_path": app.artifact_path,
        "artifact_filename": app.artifact_filename,
        "artifact_size": app.artifact_size,
        "artifact_uploaded_at": app.artifact_uploaded_at.isoformat() if app.artifact_uploaded_at else None,
        "jenkins_job_name": app.jenkins_job_name,
        "jenkins_token": app.jenkins_token,
        "webhook_secret_configured": bool(app.webhook_secret),  # 只显示是否已配置，不暴露密钥
        "creator_id": app.creator_id,
        "creator_name": app.creator.username if app.creator else None,
        "created_at": app.created_at.isoformat(),
        "updated_at": app.updated_at.isoformat(),
    }


def _env_dict(env) -> dict:
    return {
        "id": env.id,
        "name": env.name,
        "display_name": env.display_name,
        "description": env.description,
        "approval_required": env.approval_required,
        "sort_order": env.sort_order,
    }


def _app_env_dict(ae) -> dict:
    return {
        "id": ae.id,
        "app_id": ae.app_id,
        "env_id": ae.env_id,
        "env_name": ae.environment.name if ae.environment else None,
        "env_description": ae.environment.description if ae.environment else None,
        "approval_required": ae.environment.approval_required if ae.environment else False,
        "enabled": ae.enabled,
        # SSH
        "ssh_asset_id": ae.ssh_asset_id,
        "ssh_asset_name": ae.ssh_asset.name if ae.ssh_asset else None,
        "ssh_asset_ip": ae.ssh_asset.ip_address if ae.ssh_asset else None,
        "deploy_path": ae.deploy_path,
        "deploy_script": ae.deploy_script,
        "health_check_url": ae.health_check_url,
        "health_check_port": ae.health_check_port,
        "health_check_timeout": ae.health_check_timeout,
        # Docker
        "docker_host_id": ae.docker_host_id,
        "docker_host_name": ae.docker_host.name if ae.docker_host else None,
        "docker_image": ae.docker_image,
        "docker_container_name": ae.docker_container_name,
        "docker_ports": ae.docker_ports,
        "docker_env_vars": ae.docker_env_vars,
        "docker_network": ae.docker_network,
        "docker_extra_args": ae.docker_extra_args,
        # K8s
        "k8s_cluster_id": ae.k8s_cluster_id,
        "k8s_cluster_name": ae.k8s_cluster.name if ae.k8s_cluster else None,
        "k8s_namespace": ae.k8s_namespace,
        "k8s_deployment": ae.k8s_deployment,
        "k8s_container_name": ae.k8s_container_name,
        # 产物信息
        "artifact_path": ae.artifact_path,
        "artifact_filename": ae.artifact_filename,
        "artifact_size": ae.artifact_size,
        "artifact_uploaded_at": ae.artifact_uploaded_at.isoformat() if ae.artifact_uploaded_at else None,
        "created_at": ae.created_at.isoformat(),
        "updated_at": ae.updated_at.isoformat(),
    }


# ──────────────────────── 辅助函数 ────────────────────────


def _resolve_app(db: Session, app_name: str):
    """按名称解析应用，不存在则 404。"""
    app = get_application_by_name(db, app_name)
    if app is None:
        raise HTTPException(status_code=404, detail="应用不存在")
    return app


# ──────────────────────── 应用 CRUD ────────────────────────


@router.get("/apps")
def api_list_apps(
    keyword: str = "",
    app_type: str = "",
    deploy_strategy: str = "",
    status: str = "",
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("deploy.view")),
):
    items = list_applications(
        db,
        keyword=keyword,
        app_type=app_type,
        deploy_strategy=deploy_strategy,
        status=status,
    )
    total = len(items)
    start = (max(page, 1) - 1) * page_size
    return {
        "code": 0,
        "data": {
            "items": [_app_dict(a) for a in items[start:start + page_size]],
            "total": total,
            "page": page,
            "page_size": page_size,
        },
    }


@router.get("/apps/stats")
def api_app_stats(
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("deploy.view")),
):
    """返回应用统计概览：总数、各状态数量、各类型数量、各策略数量。"""
    from sqlalchemy import func

    total = db.query(func.count(DeployApplication.id)).scalar() or 0
    status_rows = (
        db.query(DeployApplication.status, func.count(DeployApplication.id))
        .group_by(DeployApplication.status)
        .all()
    )
    type_rows = (
        db.query(DeployApplication.app_type, func.count(DeployApplication.id))
        .group_by(DeployApplication.app_type)
        .all()
    )
    strategy_rows = (
        db.query(DeployApplication.deploy_strategy, func.count(DeployApplication.id))
        .group_by(DeployApplication.deploy_strategy)
        .all()
    )
    return {
        "code": 0,
        "data": {
            "total": total,
            "by_status": {row[0]: row[1] for row in status_rows},
            "by_type": {row[0]: row[1] for row in type_rows},
            "by_strategy": {row[0]: row[1] for row in strategy_rows},
        },
    }


@router.get("/apps/{app_name}")
def api_get_app(
    app_name: str,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("deploy.view")),
):
    app = _resolve_app(db, app_name)
    return {"code": 0, "data": _app_dict(app)}


@router.post("/apps")
def api_create_app(
    body: AppCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("deploy.create")),
):
    # 检查名称唯一性
    existing = list_applications(db, keyword=body.name)
    if any(a.name == body.name for a in existing):
        raise HTTPException(status_code=400, detail="应用名称已存在")

    app = create_application(
        db,
        name=body.name.strip(),
        display_name=body.display_name.strip(),
        description=body.description.strip(),
        app_type=body.app_type.strip() or "web",
        deploy_strategy=body.deploy_strategy.strip() or "ssh",
        git_url=body.git_url.strip(),
        git_branch=body.git_branch.strip() or "main",
        build_mode=body.build_mode.strip() or "upload",
        build_command=body.build_command.strip(),
        artifact_path=body.artifact_path.strip(),
        jenkins_job_name=body.jenkins_job_name.strip(),
        jenkins_token=body.jenkins_token.strip(),
        creator_id=current_user.id,
    )
    write_log(db, user=current_user, action="create", target_type="deploy_app", target_id=app.id, target_name=app.name, ip_address=get_client_ip(request))
    db.commit()
    return {"code": 0, "msg": "创建成功", "data": _app_dict(app)}


@router.put("/apps/{app_name}")
def api_update_app(
    app_name: str,
    body: AppUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("deploy.update")),
):
    app = _resolve_app(db, app_name)

    # 检查名称唯一性（排除自身）
    if body.name != app.name:
        existing = list_applications(db, keyword=body.name)
        if any(a.name == body.name and a.id != app.id for a in existing):
            raise HTTPException(status_code=400, detail="应用名称已存在")

    update_application(
        db, app,
        name=body.name.strip(),
        display_name=body.display_name.strip(),
        description=body.description.strip(),
        app_type=body.app_type.strip() or "web",
        deploy_strategy=body.deploy_strategy.strip() or "ssh",
        status=body.status.strip() or "active",
        git_url=body.git_url.strip(),
        git_branch=body.git_branch.strip() or "main",
        build_mode=body.build_mode.strip() or "upload",
        build_command=body.build_command.strip(),
        artifact_path=body.artifact_path.strip(),
        jenkins_job_name=body.jenkins_job_name.strip(),
        jenkins_token=body.jenkins_token.strip(),
    )
    write_log(db, user=current_user, action="update", target_type="deploy_app", target_id=app.id, target_name=app.name, ip_address=get_client_ip(request))
    db.commit()
    return {"code": 0, "msg": "更新成功", "data": _app_dict(app)}


@router.delete("/apps/{app_name}")
def api_delete_app(
    app_name: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("deploy.delete")),
):
    app = _resolve_app(db, app_name)
    write_log(db, user=current_user, action="delete", target_type="deploy_app", target_id=app.id, target_name=app.name, ip_address=get_client_ip(request))
    delete_application(db, app)
    db.commit()
    return {"code": 0, "msg": "删除成功"}


# ──────────────────────── 构建产物管理 ────────────────────────


def _cleanup_old_artifacts(artifact_dir: str, keep: int = 10) -> None:
    """清理旧产物，保留最近 keep 个文件。"""
    try:
        files = sorted(
            (os.path.join(artifact_dir, f) for f in os.listdir(artifact_dir) if os.path.isfile(os.path.join(artifact_dir, f))),
            key=os.path.getmtime,
            reverse=True,
        )
        for old_file in files[keep:]:
            try:
                os.remove(old_file)
            except OSError:
                pass
    except OSError:
        pass


@router.post("/apps/{app_name}/envs/{env_id}/artifact")
def api_upload_artifact(
    app_name: str,
    env_id: int,
    file: UploadFile = File(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("deploy.update")),
):
    """为指定环境上传构建产物（保留历史版本，每个环境最多 3 个）。"""
    app = _resolve_app(db, app_name)
    app_env = get_app_env_by_pair(db, app.id, env_id)
    if app_env is None:
        raise HTTPException(status_code=404, detail="未找到该环境配置")

    # 创建存储目录：{app_name}/{env_name}/
    env_name = app_env.environment.name if app_env.environment else str(env_id)
    safe_app = app.name.replace("/", "_").replace("\\", "_").replace(" ", "_")
    safe_env = env_name.replace("/", "_").replace("\\", "_").replace(" ", "_")
    artifact_dir = os.path.join(str(DEPLOY_ARTIFACT_DIR), safe_app, safe_env)
    os.makedirs(artifact_dir, exist_ok=True)

    # 保存新文件（时间戳前缀，避免覆盖旧版本）
    filename = file.filename or "artifact"
    safe_filename = filename.replace("/", "_").replace("\\", "_")
    ts = datetime.now(CHINA_TZ).strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(artifact_dir, f"{ts}_{safe_filename}")

    content = file.file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    # 更新环境产物元数据（指向最新产物）
    app_env.artifact_path = file_path
    app_env.artifact_filename = filename
    app_env.artifact_size = len(content)
    app_env.artifact_uploaded_at = datetime.now(CHINA_TZ)
    db.commit()
    db.refresh(app_env)

    # 清理旧产物，保留最近 3 个
    _cleanup_old_artifacts(artifact_dir, keep=3)

    write_log(db, user=current_user, action="upload_artifact", target_type="deploy_app_env",
              target_id=app_env.id, target_name=f"{app.name}:{env_name}:{filename}",
              ip_address=get_client_ip(request))
    db.commit()

    return {"code": 0, "msg": "上传成功", "data": _app_env_dict(app_env)}


@router.delete("/apps/{app_name}/envs/{env_id}/artifact")
def api_delete_artifact(
    app_name: str,
    env_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("deploy.update")),
):
    """删除指定环境的构建产物。"""
    app = _resolve_app(db, app_name)
    app_env = get_app_env_by_pair(db, app.id, env_id)
    if app_env is None:
        raise HTTPException(status_code=404, detail="未找到该环境配置")

    if app_env.artifact_path and os.path.isfile(app_env.artifact_path):
        try:
            os.remove(app_env.artifact_path)
        except OSError:
            pass

    app_env.artifact_path = ""
    app_env.artifact_filename = ""
    app_env.artifact_size = 0
    app_env.artifact_uploaded_at = None
    db.commit()

    env_name = app_env.environment.name if app_env.environment else str(env_id)
    write_log(db, user=current_user, action="delete_artifact", target_type="deploy_app_env",
              target_id=app_env.id, target_name=f"{app.name if app else ''}:{env_name}",
              ip_address=get_client_ip(request))
    db.commit()

    return {"code": 0, "msg": "已删除"}


@router.get("/apps/{app_name}/envs/{env_id}/artifact/download")
def api_download_artifact(
    app_name: str,
    env_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("deploy.view")),
):
    """下载指定环境的构建产物。"""
    app = _resolve_app(db, app_name)
    app_env = get_app_env_by_pair(db, app.id, env_id)
    if app_env is None:
        raise HTTPException(status_code=404, detail="未找到该环境配置")

    if not app_env.artifact_path or not os.path.isfile(app_env.artifact_path):
        raise HTTPException(status_code=404, detail="暂无构建产物")

    return FileResponse(
        path=app_env.artifact_path,
        filename=app_env.artifact_filename or os.path.basename(app_env.artifact_path),
        media_type="application/octet-stream",
    )


# ──────────────────────── 环境列表 ────────────────────────


@router.get("/envs")
def api_list_envs(
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("deploy.view")),
):
    envs = list_environments(db)
    return {"code": 0, "data": [_env_dict(e) for e in envs]}


# ──────────────────────── 应用环境配置 ────────────────────────


@router.get("/apps/{app_name}/envs")
def api_list_app_envs(
    app_name: str,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("deploy.view")),
):
    app = _resolve_app(db, app_name)
    envs = list_app_envs(db, app.id)
    return {"code": 0, "data": [_app_env_dict(e) for e in envs]}


@router.put("/apps/{app_name}/envs/{env_id}")
def api_update_app_env(
    app_name: str,
    env_id: int,
    body: AppEnvUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("deploy.update")),
):
    app = _resolve_app(db, app_name)
    app_env = upsert_app_env(
        db,
        app_id=app.id,
        env_id=env_id,
        enabled=body.enabled,
        ssh_asset_id=body.ssh_asset_id,
        deploy_path=body.deploy_path,
        deploy_script=body.deploy_script,
        health_check_url=body.health_check_url,
        health_check_port=body.health_check_port,
        health_check_timeout=body.health_check_timeout,
        docker_host_id=body.docker_host_id,
        docker_image=body.docker_image,
        docker_container_name=body.docker_container_name,
        docker_ports=body.docker_ports,
        docker_env_vars=body.docker_env_vars,
        docker_network=body.docker_network,
        docker_extra_args=body.docker_extra_args,
        k8s_cluster_id=body.k8s_cluster_id,
        k8s_namespace=body.k8s_namespace,
        k8s_deployment=body.k8s_deployment,
        k8s_container_name=body.k8s_container_name,
    )
    write_log(db, user=current_user, action="update", target_type="deploy_app_env", target_id=app_env.id, target_name=f"{app.name}:{env_id}", ip_address=get_client_ip(request))
    db.commit()
    return {"code": 0, "msg": "保存成功", "data": _app_env_dict(app_env)}


@router.delete("/apps/{app_name}/envs/{env_id}")
def api_delete_app_env(
    app_name: str,
    env_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("deploy.update")),
):
    app = _resolve_app(db, app_name)
    app_env = get_app_env_by_pair(db, app.id, env_id)
    if app_env is None:
        raise HTTPException(status_code=404, detail="环境配置不存在")
    write_log(db, user=current_user, action="delete", target_type="deploy_app_env", target_id=app_env.id, target_name=f"{app.name}:{env_id}", ip_address=get_client_ip(request))
    delete_app_env(db, app_env)
    db.commit()
    return {"code": 0, "msg": "已移除"}


# ──────────────────────── 部署执行 + 记录 ────────────────────────


def _record_dict(r) -> dict:
    return {
        "id": r.id,
        "app_id": r.app_id,
        "app_name": r.application.name if r.application else None,
        "env_id": r.env_id,
        "env_name": r.environment.name if r.environment else None,
        "version": r.version,
        "status": r.status,
        "trigger_type": r.trigger_type,
        "trigger_user_id": r.trigger_user_id,
        "trigger_user_name": r.trigger_user.username if r.trigger_user else None,
        "error_message": r.error_message,
        "duration": r.duration,
        "rollback_from": r.rollback_from,
        "started_at": r.started_at.isoformat() if r.started_at else None,
        "finished_at": r.finished_at.isoformat() if r.finished_at else None,
        "created_at": r.created_at.isoformat(),
    }


class DeployExecute(BaseModel):
    app_name: str
    env_id: int
    version: str = ""


@router.post("/execute")
def api_execute_deploy(
    body: DeployExecute,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("deploy.execute")),
):
    app = _resolve_app(db, body.app_name)

    # 查找 app_env
    app_env = get_app_env_by_pair(db, app.id, body.env_id)
    if app_env is None:
        raise HTTPException(status_code=400, detail="该应用未配置此环境，请先配置部署目标")
    if not app_env.enabled:
        raise HTTPException(status_code=400, detail="该环境已禁用")

    # 构建配置快照（包含产物信息，回滚时使用）
    config_snapshot = json.dumps({
        "app_id": app.id,
        "app_name": app.name,
        "deploy_strategy": app.deploy_strategy,
        "env_id": body.env_id,
        "app_env_id": app_env.id,
        "artifact_path": app_env.artifact_path,
        "artifact_filename": app_env.artifact_filename,
    }, ensure_ascii=False)

    record = create_record(
        db,
        app_id=app.id,
        env_id=body.env_id,
        app_env_id=app_env.id,
        version=body.version,
        trigger_type="manual",
        trigger_user_id=current_user.id,
        deploy_config=config_snapshot,
    )
    write_log(db, user=current_user, action="deploy", target_type="deploy_record", target_id=record.id, target_name=f"{app.name}:{body.env_id}", ip_address=get_client_ip(request))

    # 检查是否需要审批
    env = app_env.environment
    if env and env.approval_required:
        approval = create_approval(db, record_id=record.id)
        append_log(db, record, f"该环境需要审批，已创建审批记录 #{approval.id}，等待审批")
        db.commit()
        return {"code": 0, "msg": "已提交审批，等待审批通过后自动执行", "data": _record_dict(record), "approval_id": approval.id}

    db.commit()

    # 异步线程执行部署
    thread = threading.Thread(target=execute_deploy, args=(record.id,), daemon=True)
    thread.start()

    print(f"[deploy] 触发部署: record_id={record.id}, app={app.name}")
    return {"code": 0, "msg": "部署已触发", "data": _record_dict(record)}


@router.post("/records/{record_id}/cancel")
def api_cancel_deploy(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("deploy.execute")),
):
    record = get_record(db, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="记录不存在")
    if record.status not in ("pending", "building", "deploying"):
        raise HTTPException(status_code=400, detail="当前状态无法取消")

    request_cancel(record_id)
    update_status(db, record, "cancelled")
    append_log(db, record, "用户取消部署")
    return {"code": 0, "msg": "已取消"}


@router.post("/records/{record_id}/rollback")
def api_rollback(
    record_id: int,
    request: Request,
    body: dict | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("deploy.rollback")),
):
    """回滚：基于上一次成功部署或指定构建版本重新执行。

    Body (可选):
        build_number: 指定回滚到的构建版本号（不指定则回滚到上一次成功部署）
    """
    original = get_record(db, record_id)
    if original is None:
        raise HTTPException(status_code=404, detail="记录不存在")
    if original.status not in ("success", "failed", "cancelled"):
        raise HTTPException(status_code=400, detail="只能回滚已完成的部署记录")

    build_number = (body or {}).get("build_number")

    if build_number:
        # 回滚到指定构建版本
        build = db.query(DeployBuild).filter(
            DeployBuild.app_id == original.app_id,
            DeployBuild.build_number == build_number,
            DeployBuild.status == "success",
        ).first()
        if build is None:
            raise HTTPException(status_code=404, detail="指定的构建版本不存在或未成功")

        if not build.artifact_path or not os.path.isfile(build.artifact_path):
            raise HTTPException(status_code=400, detail="构建产物文件不存在")

        # 构建配置快照
        config_snapshot = json.dumps({
            "app_id": original.app_id,
            "app_name": original.application.name if original.application else "",
            "deploy_strategy": original.application.deploy_strategy if original.application else "ssh",
            "env_id": original.env_id,
            "app_env_id": original.app_env_id,
            "artifact_path": build.artifact_path,
            "artifact_filename": build.artifact_filename,
            "build_number": build.build_number,
        }, ensure_ascii=False)

        new_record = create_record(
            db,
            app_id=original.app_id,
            env_id=original.env_id,
            app_env_id=original.app_env_id,
            version=build_number,
            trigger_type="rollback",
            trigger_user_id=current_user.id,
            deploy_config=config_snapshot,
        )
        new_record.rollback_from = record_id
        db.commit()

        append_log(db, new_record, f"回滚到构建版本 #{build_number}（从 #{record_id} 触发）")
    else:
        # 回滚到上一次成功部署（原有逻辑）
        from sqlalchemy import select
        from app.models.deploy import DeployRecord as DR
        prev_success = db.scalar(
            select(DR)
            .where(DR.app_id == original.app_id, DR.env_id == original.env_id, DR.status == "success", DR.id < record_id)
            .order_by(DR.id.desc())
        )
        if prev_success is None:
            raise HTTPException(status_code=400, detail="未找到可回滚的成功部署记录")

        new_record = create_record(
            db,
            app_id=original.app_id,
            env_id=original.env_id,
            app_env_id=original.app_env_id,
            version=prev_success.version,
            trigger_type="rollback",
            trigger_user_id=current_user.id,
            deploy_config=prev_success.deploy_config,
        )
        new_record.rollback_from = prev_success.id
        db.commit()

        append_log(db, new_record, f"回滚到部署 #{prev_success.id}（从 #{record_id} 触发）")

    write_log(db, user=current_user, action="rollback", target_type="deploy_record", target_id=new_record.id, target_name=f"#{record_id} → #{new_record.id}", ip_address=get_client_ip(request))
    db.commit()

    # 异步线程执行部署
    thread = threading.Thread(target=execute_deploy, args=(new_record.id,), daemon=True)
    thread.start()

    return {"code": 0, "msg": "回滚已触发", "data": _record_dict(new_record)}


@router.get("/records/{record_id}/rollback-targets")
def api_rollback_targets(
    record_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("deploy.view")),
):
    """获取可用的回滚目标（成功部署记录 + 成功构建版本）。"""
    record = get_record(db, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="记录不存在")

    # 获取该应用+环境的成功部署记录（最近 10 条）
    from sqlalchemy import select
    from app.models.deploy import DeployRecord as DR
    prev_records = db.scalars(
        select(DR)
        .where(DR.app_id == record.app_id, DR.env_id == record.env_id, DR.status == "success", DR.id < record_id)
        .order_by(DR.id.desc())
        .limit(10)
    ).all()

    # 获取该应用的成功构建版本（最近 20 条）
    builds = db.scalars(
        select(DeployBuild)
        .where(DeployBuild.app_id == record.app_id, DeployBuild.status == "success")
        .order_by(DeployBuild.created_at.desc())
        .limit(20)
    ).all()

    return {
        "code": 0,
        "data": {
            "records": [_record_dict(r) for r in prev_records],
            "builds": [_build_dict(b) for b in builds],
        },
    }


@router.get("/records")
def api_list_records(
    app_name: str = "",
    env_id: int | None = None,
    status: str = "",
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("deploy.view")),
):
    resolved_app_id = None
    if app_name:
        app = get_application_by_name(db, app_name)
        if app:
            resolved_app_id = app.id
    items = list_records(db, app_id=resolved_app_id, env_id=env_id, status=status)
    total = len(items)
    start = (max(page, 1) - 1) * page_size
    return {
        "code": 0,
        "data": {
            "items": [_record_dict(r) for r in items[start:start + page_size]],
            "total": total,
            "page": page,
            "page_size": page_size,
        },
    }


@router.get("/records/{record_id}")
def api_get_record(
    record_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("deploy.view")),
):
    record = get_record(db, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="记录不存在")
    data = _record_dict(record)
    data["log"] = record.log or ""
    return {"code": 0, "data": data}


@router.get("/records/{record_id}/log")
def api_record_log_sse(
    record_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("deploy.view")),
):
    """SSE 日志流 — 前端轮询获取最新日志。"""
    record = get_record(db, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="记录不存在")

    def event_stream():
        last_len = 0
        while True:
            # 重新查询记录（获取最新日志）
            from app.db.database import SessionLocal
            sse_db = SessionLocal()
            try:
                r = sse_db.get(DeployRecord, record_id)
                if r is None:
                    break
                log_text = r.log or ""
                if len(log_text) > last_len:
                    new_content = log_text[last_len:]
                    last_len = len(log_text)
                    yield f"data: {json.dumps({'log': new_content, 'status': r.status}, ensure_ascii=False)}\n\n"
                if r.status in ("success", "failed", "cancelled"):
                    yield f"data: {json.dumps({'log': '', 'status': r.status, 'done': True}, ensure_ascii=False)}\n\n"
                    break
            finally:
                sse_db.close()

            import time
            time.sleep(1)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ──────────────────────── 审批 ────────────────────────


def _approval_dict(a) -> dict:
    rec = a.record
    result = {
        "id": a.id,
        "record_id": a.record_id,
        "status": a.status,
        "approver_id": a.approver_id,
        "approver_name": a.approver.username if a.approver else None,
        "comment": a.comment,
        "created_at": a.created_at.isoformat(),
        "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None,
        # 关联信息
        "app_id": rec.app_id if rec else None,
        "app_name": rec.application.name if rec and rec.application else None,
        "env_id": rec.env_id if rec else None,
        "env_name": rec.environment.name if rec and rec.environment else None,
        "version": rec.version if rec else None,
        "trigger_user_name": rec.trigger_user.username if rec and rec.trigger_user else None,
        "trigger_type": rec.trigger_type if rec else None,
    }

    # 从 deploy_config 快照中提取构建信息
    if rec and rec.deploy_config:
        try:
            config = json.loads(rec.deploy_config)
            result["build_number"] = config.get("build_number", "")
            result["artifact_filename"] = config.get("artifact_filename", "")
        except (json.JSONDecodeError, KeyError):
            pass

    # 如果有 build_number，尝试获取构建详情
    build_number = result.get("build_number")
    if build_number and rec:
        from sqlalchemy import select
        build = db.scalar(
            select(DeployBuild).where(
                DeployBuild.app_id == rec.app_id,
                DeployBuild.build_number == build_number,
            )
        )
        if build:
            result["build_commit"] = build.commit
            result["build_branch"] = build.branch
            result["build_tag"] = build.tag
            result["build_created_at"] = build.created_at.isoformat() if build.created_at else None

    return result


@router.get("/approvals")
def api_list_approvals(
    status: str = "pending",
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("deploy.view")),
):
    items = list_approvals(db, status=status)
    return {"code": 0, "data": [_approval_dict(a) for a in items]}


@router.post("/approvals/{approval_id}/approve")
def api_approve(
    approval_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("deploy.approve")),
):
    a = get_approval(db, approval_id)
    if a is None:
        raise HTTPException(status_code=404, detail="审批记录不存在")
    if a.status != "pending":
        raise HTTPException(status_code=400, detail="该审批已处理")

    approve(db, a, approver_id=current_user.id, comment="")

    # 审批通过 → 触发部署
    record = a.record
    if record and record.status in ("pending", "cancelled"):
        from app.services.deploy.records import update_status, append_log
        update_status(db, record, "pending")
        append_log(db, record, f"审批通过 (审批人: {current_user.username})，开始部署…")
        db.commit()
        thread = threading.Thread(target=execute_deploy, args=(record.id,), daemon=True)
        thread.start()

    write_log(db, user=current_user, action="approve", target_type="deploy_approval", target_id=a.id, target_name=f"#{a.id}", ip_address=get_client_ip(request))
    db.commit()
    return {"code": 0, "msg": "审批通过，部署已触发"}


@router.post("/approvals/{approval_id}/reject")
def api_reject(
    approval_id: int,
    request: Request,
    body: dict | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("deploy.approve")),
):
    a = get_approval(db, approval_id)
    if a is None:
        raise HTTPException(status_code=404, detail="审批记录不存在")
    if a.status != "pending":
        raise HTTPException(status_code=400, detail="该审批已处理")

    comment = (body or {}).get("comment", "")
    reject(db, a, approver_id=current_user.id, comment=comment)

    write_log(db, user=current_user, action="reject", target_type="deploy_approval", target_id=a.id, target_name=f"#{a.id}", ip_address=get_client_ip(request))
    db.commit()
    return {"code": 0, "msg": "已拒绝"}


# ──────────────────────── 配置管理 ────────────────────────


def _config_dict(c) -> dict:
    return {
        "id": c.id,
        "app_id": c.app_id,
        "env_id": c.env_id,
        "env_name": c.environment.name if c.environment else None,
        "key": c.key,
        "value": "******" if c.is_encrypted else c.value,
        "is_encrypted": c.is_encrypted,
        "description": c.description,
        "created_at": c.created_at.isoformat(),
        "updated_at": c.updated_at.isoformat(),
    }


class ConfigCreate(BaseModel):
    env_id: int | None = None
    key: str
    value: str = ""
    is_encrypted: bool = False
    description: str = ""


class ConfigUpdate(BaseModel):
    env_id: int | None = None
    key: str
    value: str = ""
    is_encrypted: bool = False
    description: str = ""


@router.get("/apps/{app_name}/configs")
def api_list_configs(
    app_name: str,
    env_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("deploy.view")),
):
    app = _resolve_app(db, app_name)
    items = list_configs(db, app_id=app.id, env_id=env_id)
    return {"code": 0, "data": [_config_dict(c) for c in items]}


@router.post("/apps/{app_name}/configs")
def api_create_config(
    app_name: str,
    body: ConfigCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("deploy.config")),
):
    app = _resolve_app(db, app_name)
    cfg = create_config(
        db,
        app_id=app.id,
        env_id=body.env_id,
        key=body.key.strip(),
        value=body.value,
        is_encrypted=body.is_encrypted,
        description=body.description.strip(),
    )
    write_log(db, user=current_user, action="create", target_type="deploy_config", target_id=cfg.id, target_name=f"{app.name}:{cfg.key}", ip_address=get_client_ip(request))
    db.commit()
    return {"code": 0, "msg": "创建成功", "data": _config_dict(cfg)}


@router.put("/configs/{config_id}")
def api_update_config(
    config_id: int,
    body: ConfigUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("deploy.config")),
):
    cfg = get_config(db, config_id)
    if cfg is None:
        raise HTTPException(status_code=404, detail="配置项不存在")
    update_config(
        db, cfg,
        key=body.key.strip(),
        value=body.value,
        is_encrypted=body.is_encrypted,
        description=body.description.strip(),
    )
    write_log(db, user=current_user, action="update", target_type="deploy_config", target_id=cfg.id, target_name=cfg.key, ip_address=get_client_ip(request))
    db.commit()
    return {"code": 0, "msg": "更新成功", "data": _config_dict(cfg)}


@router.delete("/configs/{config_id}")
def api_delete_config(
    config_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("deploy.config")),
):
    cfg = get_config(db, config_id)
    if cfg is None:
        raise HTTPException(status_code=404, detail="配置项不存在")
    write_log(db, user=current_user, action="delete", target_type="deploy_config", target_id=cfg.id, target_name=cfg.key, ip_address=get_client_ip(request))
    delete_config(db, cfg)
    db.commit()
    return {"code": 0, "msg": "删除成功"}


# ──────────────────────── Webhook + 构建记录 ────────────────────────


def _build_dict(b) -> dict:
    return {
        "id": b.id,
        "app_id": b.app_id,
        "build_number": b.build_number,
        "source": b.source,
        "commit": b.commit,
        "branch": b.branch,
        "status": b.status,
        "artifact_filename": b.artifact_filename,
        "artifact_size": b.artifact_size,
        "tag": b.tag,
        "is_pinned": b.is_pinned,
        "deploy_count": b.deploy_count,
        "deployed_at": b.deployed_at.isoformat() if b.deployed_at else None,
        "build_duration": b.build_duration,
        "created_at": b.created_at.isoformat(),
    }


@router.get("/apps/{app_name}/builds")
def api_list_builds(
    app_name: str,
    status: str = "",
    tag: str = "",
    keyword: str = "",
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("deploy.view")),
):
    """获取应用的构建历史列表。"""
    app = _resolve_app(db, app_name)

    query = db.query(DeployBuild).filter(DeployBuild.app_id == app.id)
    if status:
        query = query.filter(DeployBuild.status == status)
    if tag:
        query = query.filter(DeployBuild.tag == tag)
    if keyword:
        query = query.filter(
            (DeployBuild.build_number.contains(keyword))
            | (DeployBuild.commit.contains(keyword))
            | (DeployBuild.tag.contains(keyword))
        )

    total = query.count()
    builds = query.order_by(DeployBuild.created_at.desc()).offset(
        (max(page, 1) - 1) * page_size
    ).limit(page_size).all()

    return {
        "code": 0,
        "data": {
            "items": [_build_dict(b) for b in builds],
            "total": total,
            "page": page,
            "page_size": page_size,
        },
    }


@router.get("/apps/{app_name}/builds/{build_number}")
def api_get_build(
    app_name: str,
    build_number: str,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("deploy.view")),
):
    """获取单个构建详情。"""
    app = _resolve_app(db, app_name)
    build = db.query(DeployBuild).filter(
        DeployBuild.app_id == app.id,
        DeployBuild.build_number == build_number,
    ).first()

    if build is None:
        raise HTTPException(status_code=404, detail="构建记录不存在")

    data = _build_dict(build)
    data["build_log"] = build.build_log or ""
    data["webhook_payload"] = build.webhook_payload or ""
    return {"code": 0, "data": data}


@router.post("/apps/{app_name}/builds/{build_number}/deploy")
def api_deploy_build(
    app_name: str,
    build_number: str,
    body: DeployExecute,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("deploy.execute")),
):
    """部署指定构建版本。"""
    app = _resolve_app(db, app_name)

    # 查找构建记录
    build = db.query(DeployBuild).filter(
        DeployBuild.app_id == app.id,
        DeployBuild.build_number == build_number,
        DeployBuild.status == "success",
    ).first()

    if build is None:
        raise HTTPException(status_code=404, detail="构建记录不存在或构建未成功")

    if not build.artifact_path or not os.path.isfile(build.artifact_path):
        raise HTTPException(status_code=400, detail="构建产物文件不存在")

    # 查找 app_env
    app_env = get_app_env_by_pair(db, app.id, body.env_id)
    if app_env is None:
        raise HTTPException(status_code=400, detail="该应用未配置此环境")
    if not app_env.enabled:
        raise HTTPException(status_code=400, detail="该环境已禁用")

    # 构建配置快照
    config_snapshot = json.dumps({
        "app_id": app.id,
        "app_name": app.name,
        "deploy_strategy": app.deploy_strategy,
        "env_id": body.env_id,
        "app_env_id": app_env.id,
        "artifact_path": build.artifact_path,
        "artifact_filename": build.artifact_filename,
        "build_number": build.build_number,
    }, ensure_ascii=False)

    record = create_record(
        db,
        app_id=app.id,
        env_id=body.env_id,
        app_env_id=app_env.id,
        version=build_number,
        trigger_type="manual",
        trigger_user_id=current_user.id,
        deploy_config=config_snapshot,
    )
    write_log(db, user=current_user, action="deploy_build", target_type="deploy_record",
              target_id=record.id, target_name=f"{app.name}:{build_number}", ip_address=get_client_ip(request))

    # 检查审批
    env = app_env.environment
    if env and env.approval_required:
        approval = create_approval(db, record_id=record.id)
        append_log(db, record, f"该环境需要审批，已创建审批记录 #{approval.id}")
        db.commit()
        return {"code": 0, "msg": "已提交审批", "data": _record_dict(record), "approval_id": approval.id}

    db.commit()

    # 异步执行
    thread = threading.Thread(target=execute_deploy, args=(record.id,), daemon=True)
    thread.start()

    return {"code": 0, "msg": "部署已触发", "data": _record_dict(record)}


@router.post("/apps/{app_name}/webhook-secret/generate")
def api_generate_webhook_secret(
    app_name: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("deploy.update")),
):
    """为应用生成新的 Webhook 密钥。"""
    app = _resolve_app(db, app_name)

    if app.build_mode != "webhook":
        raise HTTPException(status_code=400, detail="应用未配置为 Webhook 模式")

    secret = generate_webhook_secret()

    # 更新 webhook_secret 字段
    from app.models.deploy import DeployApplication as DA
    db.query(DA).filter(DA.id == app.id).update({"webhook_secret": secret})
    db.commit()

    write_log(db, user=current_user, action="generate_webhook_secret", target_type="deploy_app",
              target_id=app.id, target_name=app.name, ip_address=get_client_ip(request))
    db.commit()

    return {"code": 0, "msg": "密钥已生成", "data": {"secret": secret}}


@router.get("/apps/{app_name}/webhook-url")
def api_get_webhook_url(
    app_name: str,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("deploy.view")),
):
    """获取应用的 Webhook URL。"""
    app = _resolve_app(db, app_name)

    if app.build_mode != "webhook":
        raise HTTPException(status_code=400, detail="应用未配置为 Webhook 模式")

    # 从配置读取域名
    from app.core.settings import get_setting
    base_url = get_setting("system.base_url", "").rstrip("/")
    if not base_url:
        base_url = "http://localhost:8000"

    webhook_url = f"{base_url}/api/v1/deploy/artifacts/webhook/{app.id}"
    callback_url = f"{base_url}/api/v1/deploy/artifacts/callback/{app.id}"

    return {
        "code": 0,
        "data": {
            "webhook_url": webhook_url,
            "callback_url": callback_url,
        },
    }


@router.post("/artifacts/webhook/{app_id}")
async def api_webhook_push(
    app_id: int,
    request: Request,
    file: UploadFile = File(None),
    x_webhook_signature: str = Header(None, alias="X-Webhook-Signature"),
    x_build_number: str = Header(None, alias="X-Build-Number"),
    x_build_status: str = Header(None, alias="X-Build-Status"),
    x_commit: str = Header(None, alias="X-Commit"),
    x_branch: str = Header(None, alias="X-Branch"),
    db: Session = Depends(get_db),
):
    """Webhook 端点 — 接收 CI/CD 推送的构建产物。

    Headers:
        X-Webhook-Signature: HMAC-SHA256 签名，格式 "sha256=xxx"
        X-Build-Number: 构建号（可选，自动生成）
        X-Build-Status: 构建状态（success/failed，默认 success）
        X-Commit: Git commit hash（可选）
        X-Branch: Git branch（可选）

    Body:
        multipart/form-data 包含 file 字段，或 JSON 包含 artifact_url 字段
    """
    # 获取应用
    app = db.query(DeployApplication).filter(DeployApplication.id == app_id).first()
    if app is None:
        raise HTTPException(status_code=404, detail="应用不存在")

    if app.build_mode != "webhook":
        raise HTTPException(status_code=400, detail="应用未配置为 Webhook 模式")

    # 读取请求体用于签名验证
    body = await request.body()

    # 验证签名（使用 webhook_secret 字段）
    secret = app.webhook_secret or ""
    if secret and not verify_webhook_signature(body, x_webhook_signature or "", secret):
        raise HTTPException(status_code=401, detail="签名验证失败")

    # 解析参数
    build_number = x_build_number or generate_build_number()
    build_status = x_build_status or "success"
    commit = x_commit or ""
    branch = x_branch or ""

    if build_status == "failed":
        # 构建失败，只记录状态
        build = create_build_record(
            db,
            app_id=app_id,
            build_number=build_number,
            source="webhook",
            artifact_path="",
            artifact_filename="",
            artifact_size=0,
            commit=commit,
            branch=branch,
            status="failed",
            webhook_payload=body.decode("utf-8", errors="replace"),
        )
        return {"code": 0, "msg": "构建失败已记录", "data": _build_dict(build)}

    # 处理产物
    artifact_path = ""
    artifact_filename = ""
    artifact_size = 0

    if file:
        # 从上传的文件保存
        content = await file.read()
        artifact_path, artifact_size = save_artifact_file(
            content, file.filename or "artifact", app_id, build_number
        )
        artifact_filename = file.filename or "artifact"
    else:
        # 尝试从 JSON body 获取 artifact_url
        try:
            json_body = json.loads(body)
            artifact_url = json_body.get("artifact_url")
            if artifact_url:
                artifact_path, artifact_size = download_artifact_from_url(
                    artifact_url, app_id, build_number
                )
                artifact_filename = artifact_url.split("/")[-1].split("?")[0]
        except (json.JSONDecodeError, Exception) as e:
            raise HTTPException(status_code=400, detail=f"缺少产物文件或 URL: {e}")

    if not artifact_path:
        raise HTTPException(status_code=400, detail="未能获取构建产物")

    # 创建构建记录
    build = create_build_record(
        db,
        app_id=app_id,
        build_number=build_number,
        source="webhook",
        artifact_path=artifact_path,
        artifact_filename=artifact_filename,
        artifact_size=artifact_size,
        commit=commit,
        branch=branch,
        status="success",
        webhook_payload=body.decode("utf-8", errors="replace"),
    )

    # 清理旧构建（保留最近 20 个）
    cleanup_old_builds(db, app_id, keep_count=20)

    return {"code": 0, "msg": "构建产物已接收", "data": _build_dict(build)}


@router.post("/artifacts/callback/{app_id}")
async def api_webhook_callback(
    app_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Webhook 回调端点 — 接收 CI/CD 的构建状态通知（不传文件）。

    Body (JSON):
        {
            "build_number": "123",
            "status": "success|failed",
            "commit": "abc123",
            "branch": "main",
            "duration": 120,
            "artifact_url": "https://...",  # 可选，产物下载地址
            "logs": "..."                   # 可选，构建日志
        }
    """
    # 获取应用
    app = db.query(DeployApplication).filter(DeployApplication.id == app_id).first()
    if app is None:
        raise HTTPException(status_code=404, detail="应用不存在")

    if app.build_mode != "webhook":
        raise HTTPException(status_code=400, detail="应用未配置为 Webhook 模式")

    # 读取请求体
    body = await request.body()

    # 验证签名（使用 webhook_secret 字段）
    x_webhook_signature = request.headers.get("X-Webhook-Signature", "")
    secret = app.webhook_secret or ""
    if secret and not verify_webhook_signature(body, x_webhook_signature, secret):
        raise HTTPException(status_code=401, detail="签名验证失败")

    # 解析 JSON
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="无效的 JSON")

    build_number = data.get("build_number")
    if not build_number:
        raise HTTPException(status_code=400, detail="缺少 build_number")

    build_status = data.get("status", "success")
    commit = data.get("commit", "")
    branch = data.get("branch", "")
    duration = data.get("duration", 0)
    artifact_url = data.get("artifact_url", "")
    logs = data.get("logs", "")

    # 处理产物
    artifact_path = ""
    artifact_filename = ""
    artifact_size = 0

    if artifact_url:
        try:
            artifact_path, artifact_size = download_artifact_from_url(
                artifact_url, app_id, build_number
            )
            artifact_filename = artifact_url.split("/")[-1].split("?")[0]
        except Exception as e:
            logger.error("Failed to download artifact: %s", e)

    # 创建构建记录
    build = create_build_record(
        db,
        app_id=app_id,
        build_number=build_number,
        source="webhook",
        artifact_path=artifact_path,
        artifact_filename=artifact_filename,
        artifact_size=artifact_size,
        commit=commit,
        branch=branch,
        status=build_status,
        build_duration=duration,
        build_log=logs,
        webhook_payload=body.decode("utf-8", errors="replace"),
    )

    # 清理旧构建
    cleanup_old_builds(db, app_id, keep_count=20)

    return {"code": 0, "msg": "回调已处理", "data": _build_dict(build)}


@router.delete("/apps/{app_name}/builds/{build_number}")
def api_delete_build(
    app_name: str,
    build_number: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("deploy.update")),
):
    """删除指定构建记录及其产物。"""
    app = _resolve_app(db, app_name)
    build = db.query(DeployBuild).filter(
        DeployBuild.app_id == app.id,
        DeployBuild.build_number == build_number,
    ).first()

    if build is None:
        raise HTTPException(status_code=404, detail="构建记录不存在")

    # 删除产物文件
    if build.artifact_path and os.path.exists(build.artifact_path):
        try:
            build_dir = os.path.dirname(build.artifact_path)
            if os.path.exists(build_dir):
                import shutil
                shutil.rmtree(build_dir)
        except Exception as e:
            logger.error("Failed to delete artifact: %s", e)

    # 删除记录
    db.delete(build)
    db.commit()

    write_log(db, user=current_user, action="delete_build", target_type="deploy_build",
              target_id=build.id, target_name=f"{app.name}:{build_number}", ip_address=get_client_ip(request))
    db.commit()

    return {"code": 0, "msg": "已删除"}


class BuildTagUpdate(BaseModel):
    tag: str


@router.post("/apps/{app_name}/builds/{build_number}/tag")
def api_update_build_tag(
    app_name: str,
    build_number: str,
    body: BuildTagUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("deploy.update")),
):
    """为构建设置版本标签。"""
    app = _resolve_app(db, app_name)
    build = db.query(DeployBuild).filter(
        DeployBuild.app_id == app.id,
        DeployBuild.build_number == build_number,
    ).first()

    if build is None:
        raise HTTPException(status_code=404, detail="构建记录不存在")

    old_tag = build.tag
    build.tag = body.tag.strip()
    db.commit()

    write_log(db, user=current_user, action="update_build_tag", target_type="deploy_build",
              target_id=build.id, target_name=f"{app.name}:{build_number}:{old_tag}->{build.tag}",
              ip_address=get_client_ip(request))
    db.commit()

    return {"code": 0, "msg": "标签已更新", "data": _build_dict(build)}


@router.post("/apps/{app_name}/builds/{build_number}/pin")
def api_pin_build(
    app_name: str,
    build_number: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("deploy.update")),
):
    """固定构建（永久保留，不参与自动清理）。"""
    app = _resolve_app(db, app_name)
    build = db.query(DeployBuild).filter(
        DeployBuild.app_id == app.id,
        DeployBuild.build_number == build_number,
    ).first()

    if build is None:
        raise HTTPException(status_code=404, detail="构建记录不存在")

    build.is_pinned = True
    db.commit()

    write_log(db, user=current_user, action="pin_build", target_type="deploy_build",
              target_id=build.id, target_name=f"{app.name}:{build_number}", ip_address=get_client_ip(request))
    db.commit()

    return {"code": 0, "msg": "已固定", "data": _build_dict(build)}


@router.delete("/apps/{app_name}/builds/{build_number}/pin")
def api_unpin_build(
    app_name: str,
    build_number: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("deploy.update")),
):
    """取消固定构建。"""
    app = _resolve_app(db, app_name)
    build = db.query(DeployBuild).filter(
        DeployBuild.app_id == app.id,
        DeployBuild.build_number == build_number,
    ).first()

    if build is None:
        raise HTTPException(status_code=404, detail="构建记录不存在")

    build.is_pinned = False
    db.commit()

    write_log(db, user=current_user, action="unpin_build", target_type="deploy_build",
              target_id=build.id, target_name=f"{app.name}:{build_number}", ip_address=get_client_ip(request))
    db.commit()

    return {"code": 0, "msg": "已取消固定", "data": _build_dict(build)}


# ──────────────────────── 构建清理策略 ────────────────────────


@router.get("/apps/{app_name}/cleanup-config")
def api_get_cleanup_config(
    app_name: str,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("deploy.view")),
):
    """获取应用的构建清理策略配置。"""
    app = _resolve_app(db, app_name)

    # 从 system_config 读取全局配置
    from app.models.system_config import SystemConfig
    from sqlalchemy import select

    keep_count = 20  # 默认值
    keep_days = 30   # 默认值

    cfg_count = db.scalar(select(SystemConfig).where(SystemConfig.key == "deploy.keep_build_count"))
    if cfg_count and cfg_count.value:
        try:
            keep_count = int(cfg_count.value)
        except ValueError:
            pass

    cfg_days = db.scalar(select(SystemConfig).where(SystemConfig.key == "deploy.keep_build_days"))
    if cfg_days and cfg_days.value:
        try:
            keep_days = int(cfg_days.value)
        except ValueError:
            pass

    return {
        "code": 0,
        "data": {
            "keep_count": keep_count,
            "keep_days": keep_days,
        },
    }


class CleanupConfigUpdate(BaseModel):
    keep_count: int = 20
    keep_days: int = 30


@router.put("/apps/{app_name}/cleanup-config")
def api_update_cleanup_config(
    app_name: str,
    body: CleanupConfigUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("deploy.update")),
):
    """更新构建清理策略配置（全局配置）。"""
    app = _resolve_app(db, app_name)

    from app.models.system_config import SystemConfig
    from sqlalchemy import select

    # 更新或创建配置
    for key, value in [
        ("deploy.keep_build_count", str(body.keep_count)),
        ("deploy.keep_build_days", str(body.keep_days)),
    ]:
        cfg = db.scalar(select(SystemConfig).where(SystemConfig.key == key))
        if cfg:
            cfg.value = value
        else:
            db.add(SystemConfig(key=key, value=value, description="构建清理策略配置"))

    db.commit()

    write_log(db, user=current_user, action="update_cleanup_config", target_type="deploy_app",
              target_id=app.id, target_name=app.name, ip_address=get_client_ip(request))
    db.commit()

    return {"code": 0, "msg": "配置已更新"}


@router.post("/apps/{app_name}/builds/cleanup")
def api_cleanup_builds(
    app_name: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("deploy.update")),
):
    """手动触发构建清理。"""
    app = _resolve_app(db, app_name)

    # 读取配置
    from app.models.system_config import SystemConfig
    from sqlalchemy import select

    keep_count = 20
    cfg = db.scalar(select(SystemConfig).where(SystemConfig.key == "deploy.keep_build_count"))
    if cfg and cfg.value:
        try:
            keep_count = int(cfg.value)
        except ValueError:
            pass

    # 执行清理
    deleted = cleanup_old_builds(db, app.id, keep_count=keep_count)

    write_log(db, user=current_user, action="cleanup_builds", target_type="deploy_app",
              target_id=app.id, target_name=f"{app.name}:deleted={deleted}", ip_address=get_client_ip(request))
    db.commit()

    return {"code": 0, "msg": f"已清理 {deleted} 个构建记录"}


# ──────────────────────── 构建比较 ────────────────────────


@router.get("/apps/{app_name}/builds/compare")
def api_compare_builds(
    app_name: str,
    build_a: str,
    build_b: str,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("deploy.view")),
):
    """比较两个构建版本的差异。

    返回两个构建的详细信息，包括 commit、branch、tag、产物大小等。
    """
    app = _resolve_app(db, app_name)

    # 获取两个构建记录
    build1 = db.query(DeployBuild).filter(
        DeployBuild.app_id == app.id,
        DeployBuild.build_number == build_a,
    ).first()

    build2 = db.query(DeployBuild).filter(
        DeployBuild.app_id == app.id,
        DeployBuild.build_number == build_b,
    ).first()

    if build1 is None:
        raise HTTPException(status_code=404, detail=f"构建版本 {build_a} 不存在")
    if build2 is None:
        raise HTTPException(status_code=404, detail=f"构建版本 {build_b} 不存在")

    # 计算差异
    size_diff = (build2.artifact_size or 0) - (build1.artifact_size or 0)
    duration_diff = (build2.build_duration or 0) - (build1.build_duration or 0)

    return {
        "code": 0,
        "data": {
            "build_a": _build_dict(build1),
            "build_b": _build_dict(build2),
            "diff": {
                "size_diff": size_diff,
                "size_diff_formatted": format_size_diff(size_diff),
                "duration_diff": duration_diff,
                "duration_diff_formatted": format_duration_diff(duration_diff),
                "same_commit": build1.commit == build2.commit and bool(build1.commit),
                "same_branch": build1.branch == build2.branch and bool(build1.branch),
                "time_diff": _calculate_time_diff(build1.created_at, build2.created_at),
            },
        },
    }


def format_size_diff(diff: int) -> str:
    """格式化文件大小差异。"""
    if diff == 0:
        return "无变化"
    prefix = "+" if diff > 0 else ""
    abs_diff = abs(diff)
    if abs_diff < 1024:
        return f"{prefix}{diff} B"
    elif abs_diff < 1024 * 1024:
        return f"{prefix}{diff / 1024:.1f} KB"
    elif abs_diff < 1024 * 1024 * 1024:
        return f"{prefix}{diff / (1024 * 1024):.1f} MB"
    else:
        return f"{prefix}{diff / (1024 * 1024 * 1024):.1f} GB"


def format_duration_diff(diff: int) -> str:
    """格式化耗时差异。"""
    if diff == 0:
        return "无变化"
    prefix = "+" if diff > 0 else ""
    abs_diff = abs(diff)
    if abs_diff < 60:
        return f"{prefix}{diff}s"
    else:
        m = abs_diff // 60
        s = abs_diff % 60
        return f"{prefix}{m}m {s}s"


def _calculate_time_diff(time1: datetime | None, time2: datetime | None) -> str:
    """计算两个时间的差异。"""
    if not time1 or not time2:
        return ""

    # 确保两个时间都是 naive 的
    t1 = time1.replace(tzinfo=None) if time1.tzinfo else time1
    t2 = time2.replace(tzinfo=None) if time2.tzinfo else time2

    diff = abs((t2 - t1).total_seconds())
    if diff < 60:
        return f"{int(diff)} 秒"
    elif diff < 3600:
        return f"{int(diff // 60)} 分钟"
    elif diff < 86400:
        return f"{int(diff // 3600)} 小时"
    else:
        return f"{int(diff // 86400)} 天"
