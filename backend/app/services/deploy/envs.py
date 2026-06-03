"""环境管理 CRUD。"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.deploy import DeployEnvironment


def list_envs(db: Session) -> list[DeployEnvironment]:
    """获取所有环境，按 sort_order 排序。"""
    stmt = select(DeployEnvironment).order_by(DeployEnvironment.sort_order, DeployEnvironment.id)
    return list(db.scalars(stmt).all())


def get_env(db: Session, env_id: int) -> DeployEnvironment | None:
    return db.get(DeployEnvironment, env_id)


def create_env(db: Session, *, name: str, display_name: str = "", approval_required: bool = False, description: str = "", sort_order: int = 0) -> DeployEnvironment:
    env = DeployEnvironment(
        name=name,
        display_name=display_name,
        approval_required=approval_required,
        description=description,
        sort_order=sort_order,
    )
    db.add(env)
    db.flush()
    return env


def update_env(db: Session, env: DeployEnvironment, **kwargs) -> DeployEnvironment:
    for key, value in kwargs.items():
        if hasattr(env, key) and value is not None:
            setattr(env, key, value)
    db.flush()
    return env


def delete_env(db: Session, env: DeployEnvironment) -> None:
    db.delete(env)
    db.flush()
