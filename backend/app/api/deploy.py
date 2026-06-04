"""应用发布 API。"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import api_permission_required, get_client_ip
from app.db.database import get_db
from app.models.user import User
from app.services.audit import write_log
from app.services.deploy.applications import (
    create_application,
    delete_application,
    get_application,
    list_applications,
    list_environments,
    update_application,
)

router = APIRouter(prefix="/deploy", tags=["应用发布"])


# ──────────────────────── Pydantic 模型 ────────────────────────


class AppCreate(BaseModel):
    name: str
    description: str = ""
    app_type: str = "web"
    deploy_strategy: str = "ssh"
    git_url: str = ""
    git_branch: str = "main"
    build_mode: str = "local"
    build_command: str = ""
    artifact_path: str = ""
    jenkins_job_name: str = ""
    jenkins_token: str = ""
    health_check_url: str = ""
    health_check_timeout: int = 30


class AppUpdate(BaseModel):
    name: str
    description: str = ""
    app_type: str = "web"
    deploy_strategy: str = "ssh"
    status: str = "active"
    git_url: str = ""
    git_branch: str = "main"
    build_mode: str = "local"
    build_command: str = ""
    artifact_path: str = ""
    jenkins_job_name: str = ""
    jenkins_token: str = ""
    health_check_url: str = ""
    health_check_timeout: int = 30


# ──────────────────────── 序列化辅助 ────────────────────────


def _app_dict(app) -> dict:
    return {
        "id": app.id,
        "name": app.name,
        "description": app.description,
        "app_type": app.app_type,
        "deploy_strategy": app.deploy_strategy,
        "status": app.status,
        "git_url": app.git_url,
        "git_branch": app.git_branch,
        "build_mode": app.build_mode,
        "build_command": app.build_command,
        "artifact_path": app.artifact_path,
        "jenkins_job_name": app.jenkins_job_name,
        "jenkins_token": app.jenkins_token,
        "health_check_url": app.health_check_url,
        "health_check_timeout": app.health_check_timeout,
        "creator_id": app.creator_id,
        "creator_name": app.creator.username if app.creator else None,
        "created_at": app.created_at.isoformat(),
        "updated_at": app.updated_at.isoformat(),
    }


def _env_dict(env) -> dict:
    return {
        "id": env.id,
        "name": env.name,
        "description": env.description,
        "approval_required": env.approval_required,
        "sort_order": env.sort_order,
    }


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


@router.get("/apps/{app_id}")
def api_get_app(
    app_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("deploy.view")),
):
    app = get_application(db, app_id)
    if app is None:
        raise HTTPException(status_code=404, detail="应用不存在")
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
        description=body.description.strip(),
        app_type=body.app_type.strip() or "web",
        deploy_strategy=body.deploy_strategy.strip() or "ssh",
        git_url=body.git_url.strip(),
        git_branch=body.git_branch.strip() or "main",
        build_mode=body.build_mode.strip() or "local",
        build_command=body.build_command.strip(),
        artifact_path=body.artifact_path.strip(),
        jenkins_job_name=body.jenkins_job_name.strip(),
        jenkins_token=body.jenkins_token.strip(),
        health_check_url=body.health_check_url.strip(),
        health_check_timeout=body.health_check_timeout,
        creator_id=current_user.id,
    )
    write_log(db, user=current_user, action="create", target_type="deploy_app", target_id=app.id, target_name=app.name, ip_address=get_client_ip(request))
    db.commit()
    return {"code": 0, "msg": "创建成功", "data": _app_dict(app)}


@router.put("/apps/{app_id}")
def api_update_app(
    app_id: int,
    body: AppUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("deploy.update")),
):
    app = get_application(db, app_id)
    if app is None:
        raise HTTPException(status_code=404, detail="应用不存在")

    # 检查名称唯一性（排除自身）
    if body.name != app.name:
        existing = list_applications(db, keyword=body.name)
        if any(a.name == body.name and a.id != app_id for a in existing):
            raise HTTPException(status_code=400, detail="应用名称已存在")

    update_application(
        db, app,
        name=body.name.strip(),
        description=body.description.strip(),
        app_type=body.app_type.strip() or "web",
        deploy_strategy=body.deploy_strategy.strip() or "ssh",
        status=body.status.strip() or "active",
        git_url=body.git_url.strip(),
        git_branch=body.git_branch.strip() or "main",
        build_mode=body.build_mode.strip() or "local",
        build_command=body.build_command.strip(),
        artifact_path=body.artifact_path.strip(),
        jenkins_job_name=body.jenkins_job_name.strip(),
        jenkins_token=body.jenkins_token.strip(),
        health_check_url=body.health_check_url.strip(),
        health_check_timeout=body.health_check_timeout,
    )
    write_log(db, user=current_user, action="update", target_type="deploy_app", target_id=app.id, target_name=app.name, ip_address=get_client_ip(request))
    db.commit()
    return {"code": 0, "msg": "更新成功", "data": _app_dict(app)}


@router.delete("/apps/{app_id}")
def api_delete_app(
    app_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("deploy.delete")),
):
    app = get_application(db, app_id)
    if app is None:
        raise HTTPException(status_code=404, detail="应用不存在")

    write_log(db, user=current_user, action="delete", target_type="deploy_app", target_id=app.id, target_name=app.name, ip_address=get_client_ip(request))
    delete_application(db, app)
    db.commit()
    return {"code": 0, "msg": "删除成功"}


# ──────────────────────── 环境列表 ────────────────────────


@router.get("/envs")
def api_list_envs(
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("deploy.view")),
):
    envs = list_environments(db)
    return {"code": 0, "data": [_env_dict(e) for e in envs]}
