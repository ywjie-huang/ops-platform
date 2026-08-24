"""应用发布 API — 模式 B（Jenkins 治理触发）：平台治理，Jenkins 执行。"""
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, noload, selectinload

from app.api.deps import api_permission_required, get_client_ip
from app.db.database import get_db
from app.models.deploy import DeployAppEnv, DeployApplication, DeployApproval
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
from app.services.deploy.overview import (
    current_version_for,
    get_feed,
    get_kpi,
    get_matrix,
    latest_records_by_app,
    latest_records_by_pair,
    record_brief,
)
from app.services.deploy.records import (
    append_log,
    create_record,
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

router = APIRouter(prefix="/deploy", tags=["应用发布"])


class AppCreate(BaseModel):
    name: str
    display_name: str = ""
    description: str = ""
    app_type: str = "web"
    git_url: str = ""
    git_branch: str = "main"
    jenkins_job_name: str = ""


class AppUpdate(BaseModel):
    name: str
    display_name: str = ""
    description: str = ""
    app_type: str = "web"
    status: str = "active"
    git_url: str = ""
    git_branch: str = "main"
    jenkins_job_name: str = ""


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
        "status": app.status,
        "git_url": app.git_url,
        "git_branch": app.git_branch,
        "jenkins_job_name": app.jenkins_job_name,
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
        "env_display_name": ae.environment.display_name if ae.environment else None,
        "env_sort_order": ae.environment.sort_order if ae.environment else 0,
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
    page_apps = items[start:start + page_size]
    page_items = [_app_dict(a) for a in page_apps]
    _attach_list_extras(db, page_apps, page_items)
    return {
        "code": 0,
        "data": {
            "items": page_items,
            "total": total,
            "page": page,
            "page_size": page_size,
        },
    }


def _attach_list_extras(db: Session, apps: list, items: list[dict]) -> None:
    """为应用列表行附加：各环境最新部署状态 chips + 最近一条部署记录。"""
    if not apps:
        return
    latest_app = latest_records_by_app(db)
    latest_pair = latest_records_by_pair(db)
    app_ids = [a.id for a in apps]
    app_envs = db.scalars(
        select(DeployAppEnv)
        .where(DeployAppEnv.app_id.in_(app_ids))
        .options(
            noload(DeployAppEnv.ssh_asset),
            noload(DeployAppEnv.docker_host),
            noload(DeployAppEnv.k8s_cluster),
            selectinload(DeployAppEnv.environment),
        )
    ).all()
    envs_by_app: dict[int, list] = {}
    for ae in app_envs:
        envs_by_app.setdefault(ae.app_id, []).append(ae)
    for app, item in zip(apps, items):
        env_status = []
        for ae in sorted(envs_by_app.get(app.id, []), key=lambda x: x.env_id):
            rec = latest_pair.get((app.id, ae.env_id))
            env_status.append({
                "env_id": ae.env_id,
                "env_name": ae.environment.name if ae.environment else None,
                "enabled": ae.enabled,
                "status": rec.status if rec else None,
                "record_id": rec.id if rec else None,
            })
        item["env_status"] = env_status
        item["last_record"] = record_brief(latest_app.get(app.id))


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
        git_url=body.git_url.strip(),
        git_branch=body.git_branch.strip() or "main",
        jenkins_job_name=body.jenkins_job_name.strip(),
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
        status=body.status.strip() or "active",
        git_url=body.git_url.strip(),
        git_branch=body.git_branch.strip() or "main",
        jenkins_job_name=body.jenkins_job_name.strip(),
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


# ──────────────────────── 发布总览 ────────────────────────


@router.get("/overview")
def api_overview(
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("deploy.view")),
):
    """发布总览聚合：KPI + 状态矩阵（应用×环境）+ 最近动态 + 待审批。"""
    pending = list_approvals(db, status="pending")[:5]
    return {
        "code": 0,
        "data": {
            "kpi": get_kpi(db),
            **get_matrix(db),
            "feed": [_record_dict(r) for r in get_feed(db, 10)],
            "approvals": [_approval_dict(a, db) for a in pending],
        },
    }


# ──────────────────────── 构建产物管理 ────────────────────────


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
    # 附每个环境的最新部署记录（环境管道卡片用），一次 max-id 子查询避免 N+1
    latest_map = latest_records_by_pair(db)
    items = []
    for e in envs:
        d = _app_env_dict(e)
        d["latest_record"] = record_brief(latest_map.get((app.id, e.env_id)))
        items.append(d)
    return {"code": 0, "data": items}


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
    result = {
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
    # 模式 B 字段：快照里的 Jenkins 构建信息（供前端跳转构建日志）
    if r.deploy_config:
        try:
            snap = json.loads(r.deploy_config)
            result["jenkins_build_url"] = snap.get("jenkins_build_url") or ""
            result["jenkins_build_number"] = snap.get("jenkins_build_number")
            result["release_mode"] = snap.get("release_mode") or "platform"
        except (ValueError, TypeError):
            pass
    return result


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
    """触发部署（模式 B）：平台治理，Jenkins 执行，回调更新状态。"""
    app = _resolve_app(db, body.app_name)
    if not (app.jenkins_job_name or "").strip():
        raise HTTPException(status_code=400, detail="应用未配置 Jenkins Job 名称，请先在应用编辑中填写")

    app_env = get_app_env_by_pair(db, app.id, body.env_id)
    if app_env is None:
        raise HTTPException(status_code=400, detail="该应用未配置此环境，请先配置")
    if not app_env.enabled:
        raise HTTPException(status_code=400, detail="该环境已禁用")

    env = app_env.environment
    config_snapshot = json.dumps({
        "app_id": app.id,
        "app_name": app.name,
        "release_mode": "jenkins",
        "env_id": body.env_id,
        "app_env_id": app_env.id,
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

    if env and env.approval_required:
        approval = create_approval(db, record_id=record.id)
        append_log(db, record, f"该环境需要审批，已创建审批记录 #{approval.id}，等待审批")
        db.commit()
        return {"code": 0, "msg": "已提交审批，等待审批通过后自动执行", "data": _record_dict(record), "approval_id": approval.id}

    db.commit()

    from app.services.deploy.modeb import spawn_jenkins_release
    spawn_jenkins_release(
        record_id=record.id,
        app_id=app.id,
        env_name=(env.name if env else str(body.env_id)),
        version=body.version or "",
        operator=current_user.username,
    )
    print(f"[deploy] 模式B触发: record_id={record.id}, app={app.name}, job={app.jenkins_job_name}")
    return {"code": 0, "msg": "已触发 Jenkins 执行部署，等待回调更新状态", "data": _record_dict(record)}


@router.post("/records/{record_id}/cancel")
def api_cancel_deploy(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("deploy.execute")),
):
    record = get_record(db, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="记录不存在")
    if record.status not in ("pending", "building", "deploying", "triggering"):
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
    """回滚到上一次成功部署：触发同一 Jenkins Job（RELEASE_MODE=rollback，跳过构建）。"""
    original = get_record(db, record_id)
    if original is None:
        raise HTTPException(status_code=404, detail="记录不存在")
    if original.status not in ("success", "failed", "cancelled"):
        raise HTTPException(status_code=400, detail="只能回滚已完成的部署记录")
    app = original.application
    if app is None:
        raise HTTPException(status_code=400, detail="应用不存在")
    if not (app.jenkins_job_name or "").strip():
        raise HTTPException(status_code=400, detail="应用未配置 Jenkins Job 名称，无法回滚")

    from sqlalchemy import select
    from app.models.deploy import DeployRecord as DR
    # 支持指定回滚目标（历史成功版本），缺省回滚到最近一次成功
    target_id = (body or {}).get("target_record_id")
    if target_id:
        prev_success = db.get(DR, int(target_id))
        if (
            prev_success is None
            or prev_success.app_id != original.app_id
            or prev_success.env_id != original.env_id
            or prev_success.status != "success"
        ):
            raise HTTPException(status_code=400, detail="目标记录不可用于回滚（需为同应用同环境的成功记录）")
    else:
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
    write_log(db, user=current_user, action="rollback", target_type="deploy_record", target_id=new_record.id, target_name=f"#{record_id} -> #{new_record.id}", ip_address=get_client_ip(request))
    db.commit()

    from app.services.deploy.modeb import spawn_jenkins_release
    spawn_jenkins_release(
        record_id=new_record.id,
        app_id=app.id,
        env_name=(new_record.environment.name if new_record.environment else ""),
        version=new_record.version or "",
        operator=current_user.username,
        release_mode="rollback",
        rollback_from=record_id,
    )
    return {"code": 0, "msg": "回滚已触发（Jenkins 执行）", "data": _record_dict(new_record)}


@router.get("/records/{record_id}/rollback-targets")
def api_rollback_targets(
    record_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("deploy.view")),
):
    """获取可回滚的历史成功部署记录（模式 B：构建在 Jenkins 侧，无平台构建版本）。"""
    record = get_record(db, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="记录不存在")

    from sqlalchemy import select
    from app.models.deploy import DeployRecord as DR
    prev_records = db.scalars(
        select(DR)
        .where(DR.app_id == record.app_id, DR.env_id == record.env_id, DR.status == "success", DR.id < record_id)
        .order_by(DR.id.desc())
        .limit(10)
    ).all()

    return {
        "code": 0,
        "data": {"records": [_record_dict(r) for r in prev_records], "builds": []},
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
    # 关联审批信息（详情页步骤条/侧栏展示）
    approval = db.scalar(
        select(DeployApproval)
        .where(DeployApproval.record_id == record_id)
        .order_by(DeployApproval.id.desc())
        .limit(1)
    )
    data["approval"] = _approval_dict(approval) if approval else None
    return {"code": 0, "data": data}



def _approval_dict(a, db: Session | None = None) -> dict:
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
        "jenkins_job_name": rec.application.jenkins_job_name if rec and rec.application else "",
        "record_status": rec.status if rec else None,
    }
    # 版本对比：该环境此记录之前的最近一次成功版本（当前线上版本）
    if db is not None and rec is not None:
        result["current_version"] = current_version_for(db, rec.app_id, rec.env_id, rec.id)
    else:
        result["current_version"] = ""
    return result


@router.get("/approvals")
def api_list_approvals(
    status: str = "pending",
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("deploy.view")),
):
    items = list_approvals(db, status=status)
    return {"code": 0, "data": [_approval_dict(a, db) for a in items]}


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

    # 审批通过 → 触发 Jenkins 执行部署（模式 B）
    record = a.record
    if record and record.status in ("pending", "cancelled"):
        from app.services.deploy.records import update_status
        update_status(db, record, "pending")
        append_log(db, record, f"审批通过 (审批人: {current_user.username})，触发 Jenkins 执行部署…")
        db.commit()
        app = record.application
        if app:
            from app.services.deploy.modeb import spawn_jenkins_release
            spawn_jenkins_release(
                record_id=record.id,
                app_id=app.id,
                env_name=(record.environment.name if record.environment else ""),
                version=record.version or "",
                operator=current_user.username,
            )

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


