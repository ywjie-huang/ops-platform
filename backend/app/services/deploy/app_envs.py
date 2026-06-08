"""Application-Environment association service — deploy module."""
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import CHINA_TZ
from app.models.deploy import DeployAppEnv, DeployApplication


def list_app_envs(db: Session, app_id: int) -> list[DeployAppEnv]:
    """获取应用的所有环境配置。"""
    stmt = (
        select(DeployAppEnv)
        .options(
            selectinload(DeployAppEnv.environment),
            selectinload(DeployAppEnv.ssh_asset),
            selectinload(DeployAppEnv.docker_host),
            selectinload(DeployAppEnv.k8s_cluster),
        )
        .where(DeployAppEnv.app_id == app_id)
        .order_by(DeployAppEnv.id)
    )
    return list(db.scalars(stmt).unique().all())


def get_app_env(db: Session, app_env_id: int) -> DeployAppEnv | None:
    """获取单个应用环境配置。"""
    stmt = (
        select(DeployAppEnv)
        .options(
            selectinload(DeployAppEnv.environment),
            selectinload(DeployAppEnv.ssh_asset),
            selectinload(DeployAppEnv.docker_host),
            selectinload(DeployAppEnv.k8s_cluster),
        )
        .where(DeployAppEnv.id == app_env_id)
    )
    return db.scalar(stmt)


def get_app_env_by_pair(db: Session, app_id: int, env_id: int) -> DeployAppEnv | None:
    """按 app_id + env_id 获取配置。"""
    stmt = (
        select(DeployAppEnv)
        .options(
            selectinload(DeployAppEnv.environment),
            selectinload(DeployAppEnv.ssh_asset),
            selectinload(DeployAppEnv.docker_host),
            selectinload(DeployAppEnv.k8s_cluster),
        )
        .where(DeployAppEnv.app_id == app_id, DeployAppEnv.env_id == env_id)
    )
    return db.scalar(stmt)


def upsert_app_env(
    db: Session,
    *,
    app_id: int,
    env_id: int,
    enabled: bool = True,
    ssh_asset_id: int | None = None,
    deploy_path: str = "",
    deploy_script: str = "",
    health_check_port: int = 0,
    docker_host_id: int | None = None,
    docker_image: str = "",
    docker_container_name: str = "",
    docker_ports: str = "",
    docker_env_vars: str = "",
    docker_network: str = "",
    docker_extra_args: str = "",
    k8s_cluster_id: int | None = None,
    k8s_namespace: str = "default",
    k8s_deployment: str = "",
    k8s_container_name: str = "",
) -> DeployAppEnv:
    """创建或更新应用环境配置（按 app_id + env_id 唯一）。"""
    app_env = get_app_env_by_pair(db, app_id, env_id)
    if app_env is None:
        app_env = DeployAppEnv(app_id=app_id, env_id=env_id)
        db.add(app_env)

    app_env.enabled = enabled
    app_env.ssh_asset_id = ssh_asset_id
    app_env.deploy_path = deploy_path
    app_env.deploy_script = deploy_script
    app_env.health_check_port = health_check_port
    app_env.docker_host_id = docker_host_id
    app_env.docker_image = docker_image
    app_env.docker_container_name = docker_container_name
    app_env.docker_ports = docker_ports
    app_env.docker_env_vars = docker_env_vars
    app_env.docker_network = docker_network
    app_env.docker_extra_args = docker_extra_args
    app_env.k8s_cluster_id = k8s_cluster_id
    app_env.k8s_namespace = k8s_namespace
    app_env.k8s_deployment = k8s_deployment
    app_env.k8s_container_name = k8s_container_name
    app_env.updated_at = datetime.now(CHINA_TZ)

    db.commit()
    return get_app_env(db, app_env.id) or app_env


def delete_app_env(db: Session, app_env: DeployAppEnv) -> None:
    """移除应用环境关联。"""
    db.delete(app_env)
    db.commit()
