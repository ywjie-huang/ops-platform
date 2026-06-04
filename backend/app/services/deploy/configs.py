"""Deploy config service — CRUD for application environment variables."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import CHINA_TZ
from app.models.deploy import DeployConfig


def list_configs(
    db: Session,
    *,
    app_id: int,
    env_id: int | None = None,
) -> list[DeployConfig]:
    """获取应用的配置列表，可按环境筛选。"""
    stmt = (
        select(DeployConfig)
        .options(selectinload(DeployConfig.environment))
        .where(DeployConfig.app_id == app_id)
    )
    if env_id is not None:
        stmt = stmt.where(DeployConfig.env_id == env_id)
    stmt = stmt.order_by(DeployConfig.id)
    return list(db.scalars(stmt).unique().all())


def get_config(db: Session, config_id: int) -> DeployConfig | None:
    """获取单条配置。"""
    stmt = select(DeployConfig).options(
        selectinload(DeployConfig.environment),
    ).where(DeployConfig.id == config_id)
    return db.scalar(stmt)


def create_config(
    db: Session,
    *,
    app_id: int,
    env_id: int | None = None,
    key: str,
    value: str = "",
    is_encrypted: bool = False,
    description: str = "",
) -> DeployConfig:
    """新增配置项。"""
    cfg = DeployConfig(
        app_id=app_id,
        env_id=env_id,
        key=key,
        value=value,
        is_encrypted=is_encrypted,
        description=description,
    )
    db.add(cfg)
    db.commit()
    db.refresh(cfg)
    return get_config(db, cfg.id) or cfg


def update_config(
    db: Session,
    cfg: DeployConfig,
    *,
    key: str,
    value: str = "",
    is_encrypted: bool = False,
    description: str = "",
) -> DeployConfig:
    """更新配置项。"""
    cfg.key = key
    # 加密字段：如果传入的是掩码则不更新值
    if not (cfg.is_encrypted and value == "******"):
        cfg.value = value
    cfg.is_encrypted = is_encrypted
    cfg.description = description
    cfg.updated_at = datetime.now(CHINA_TZ)
    db.commit()
    return get_config(db, cfg.id) or cfg


def delete_config(db: Session, cfg: DeployConfig) -> None:
    """删除配置项。"""
    db.delete(cfg)
    db.commit()
