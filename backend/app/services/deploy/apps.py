"""应用管理 CRUD。"""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.deploy import DeployApplication, DeployAppEnv


# ─── 应用 CRUD ──────────────────────────────────────────────


def list_apps(
    db: Session,
    *,
    keyword: str = "",
    deploy_method: str = "",
    status: str = "",
) -> list[DeployApplication]:
    stmt = select(DeployApplication)
    keyword = keyword.strip()
    deploy_method = deploy_method.strip()
    status = status.strip()

    if keyword:
        like_val = f"%{keyword}%"
        stmt = stmt.where(
            or_(
                DeployApplication.name.ilike(like_val),
                DeployApplication.display_name.ilike(like_val),
                DeployApplication.description.ilike(like_val),
            )
        )
    if deploy_method:
        stmt = stmt.where(DeployApplication.deploy_method == deploy_method)
    if status:
        stmt = stmt.where(DeployApplication.status == status)

    stmt = stmt.order_by(DeployApplication.id.desc())
    return list(db.scalars(stmt).all())


def get_app(db: Session, app_id: int) -> DeployApplication | None:
    return db.get(DeployApplication, app_id)


def create_app(
    db: Session,
    *,
    name: str,
    display_name: str = "",
    app_type: str = "backend",
    deploy_method: str = "jenkins",
    repo_url: str = "",
    repo_branch: str = "main",
    build_script: str = "",
    description: str = "",
    creator_id: int | None = None,
) -> DeployApplication:
    app = DeployApplication(
        name=name,
        display_name=display_name,
        app_type=app_type,
        deploy_method=deploy_method,
        repo_url=repo_url,
        repo_branch=repo_branch,
        build_script=build_script,
        description=description,
        creator_id=creator_id,
    )
    db.add(app)
    db.flush()
    return app


def update_app(db: Session, app: DeployApplication, **kwargs) -> DeployApplication:
    for key, value in kwargs.items():
        if hasattr(app, key) and value is not None:
            setattr(app, key, value)
    db.flush()
    return app


def delete_app(db: Session, app: DeployApplication) -> None:
    db.delete(app)
    db.flush()


# ─── 应用-环境配置 CRUD ──────────────────────────────────────


def list_app_envs(db: Session, app_id: int) -> list[DeployAppEnv]:
    stmt = select(DeployAppEnv).where(DeployAppEnv.application_id == app_id)
    return list(db.scalars(stmt).all())


def get_app_env(db: Session, app_env_id: int) -> DeployAppEnv | None:
    return db.get(DeployAppEnv, app_env_id)


def get_app_env_by_pair(db: Session, app_id: int, env_id: int) -> DeployAppEnv | None:
    stmt = select(DeployAppEnv).where(
        DeployAppEnv.application_id == app_id,
        DeployAppEnv.environment_id == env_id,
    )
    return db.scalar(stmt)


def save_app_env(
    db: Session,
    *,
    application_id: int,
    environment_id: int,
    jenkins_job_name: str = "",
    jenkins_params_json: str = "{}",
    docker_image: str = "",
    docker_host_id: int | None = None,
    k8s_cluster_id: int | None = None,
    k8s_namespace: str = "default",
    k8s_deployment_name: str = "",
) -> DeployAppEnv:
    """创建或更新应用-环境配置。"""
    existing = get_app_env_by_pair(db, application_id, environment_id)
    if existing:
        existing.jenkins_job_name = jenkins_job_name
        existing.jenkins_params_json = jenkins_params_json
        existing.docker_image = docker_image
        existing.docker_host_id = docker_host_id
        existing.k8s_cluster_id = k8s_cluster_id
        existing.k8s_namespace = k8s_namespace
        existing.k8s_deployment_name = k8s_deployment_name
        db.flush()
        return existing

    app_env = DeployAppEnv(
        application_id=application_id,
        environment_id=environment_id,
        jenkins_job_name=jenkins_job_name,
        jenkins_params_json=jenkins_params_json,
        docker_image=docker_image,
        docker_host_id=docker_host_id,
        k8s_cluster_id=k8s_cluster_id,
        k8s_namespace=k8s_namespace,
        k8s_deployment_name=k8s_deployment_name,
    )
    db.add(app_env)
    db.flush()
    return app_env


def delete_app_env(db: Session, app_env: DeployAppEnv) -> None:
    db.delete(app_env)
    db.flush()
