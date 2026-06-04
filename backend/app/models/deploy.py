"""应用发布数据模型。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import CHINA_TZ
from app.db.database import Base


class DeployApplication(Base):
    """应用注册表。"""

    __tablename__ = "deploy_applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)  # 应用标识，如 user-service
    display_name: Mapped[str] = mapped_column(String(256), default="")  # 中文显示名
    app_type: Mapped[str] = mapped_column(String(32), default="backend")  # backend / frontend / service / other
    deploy_method: Mapped[str] = mapped_column(String(32), default="jenkins")  # jenkins / docker / kubernetes
    repo_url: Mapped[str] = mapped_column(String(512), default="")  # Git 仓库地址
    repo_branch: Mapped[str] = mapped_column(String(128), default="main")  # 默认分支
    build_script: Mapped[str] = mapped_column(Text, default="")  # 非 Jenkins 场景的构建脚本
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="active")  # active / archived
    creator_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(CHINA_TZ))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(CHINA_TZ), onupdate=lambda: datetime.now(CHINA_TZ))

    creator: Mapped["User"] = relationship("User", lazy="joined")
    environments: Mapped[list["DeployAppEnv"]] = relationship(back_populates="application", cascade="all, delete-orphan")
    deployments: Mapped[list["DeployRecord"]] = relationship(back_populates="application", cascade="all, delete-orphan")


class DeployEnvironment(Base):
    """环境定义表。"""

    __tablename__ = "deploy_environments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)  # dev / staging / prod
    display_name: Mapped[str] = mapped_column(String(128), default="")  # 开发环境 / 测试环境 / 生产环境
    description: Mapped[str] = mapped_column(Text, default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(CHINA_TZ))

    app_envs: Mapped[list["DeployAppEnv"]] = relationship(back_populates="environment", cascade="all, delete-orphan")


class DeployAppEnv(Base):
    """应用×环境配置表（M:N 中间表）。"""

    __tablename__ = "deploy_app_envs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(Integer, ForeignKey("deploy_applications.id", ondelete="CASCADE"), nullable=False)
    environment_id: Mapped[int] = mapped_column(Integer, ForeignKey("deploy_environments.id", ondelete="CASCADE"), nullable=False)
    # Jenkins 配置
    jenkins_job_name: Mapped[str] = mapped_column(String(256), default="")
    jenkins_params_json: Mapped[str] = mapped_column(Text, default="{}")  # JSON 构建参数
    # Docker 配置
    docker_image: Mapped[str] = mapped_column(String(512), default="")  # 镜像地址
    docker_host_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("container_clusters.id", ondelete="SET NULL"), nullable=True)
    # K8s 配置
    k8s_cluster_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("container_clusters.id", ondelete="SET NULL"), nullable=True)
    k8s_namespace: Mapped[str] = mapped_column(String(64), default="default")
    k8s_deployment_name: Mapped[str] = mapped_column(String(128), default="")
    # SSH 部署配置
    ssh_asset_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("assets.id", ondelete="SET NULL"), nullable=True)
    ssh_deploy_path: Mapped[str] = mapped_column(String(512), default="")  # 部署目标目录，如 /opt/apps/user-service/
    ssh_deploy_script: Mapped[str] = mapped_column(Text, default="")  # 部署后执行的脚本
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(CHINA_TZ))

    application: Mapped["DeployApplication"] = relationship(back_populates="environments", lazy="joined")
    environment: Mapped["DeployEnvironment"] = relationship(back_populates="app_envs", lazy="joined")


class DeployRecord(Base):
    """发布记录表。"""

    __tablename__ = "deploy_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(Integer, ForeignKey("deploy_applications.id", ondelete="CASCADE"), nullable=False)
    environment_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("deploy_environments.id", ondelete="SET NULL"), nullable=True)
    deploy_method: Mapped[str] = mapped_column(String(32), default="jenkins")  # jenkins / docker / kubernetes
    version: Mapped[str] = mapped_column(String(256), default="")  # 版本号 / tag / commit SHA
    image: Mapped[str] = mapped_column(String(512), default="")  # Docker 镜像
    status: Mapped[str] = mapped_column(String(32), default="pending")
    # pending / approved / rejected / building / deploying / success / failed / rolled_back
    trigger_type: Mapped[str] = mapped_column(String(32), default="manual")  # manual / scheduled / webhook
    # Jenkins 追踪
    jenkins_build_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    jenkins_build_url: Mapped[str] = mapped_column(String(512), default="")
    # 结果
    logs: Mapped[str] = mapped_column(Text, default="")  # 部署日志
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rollback_from: Mapped[int | None] = mapped_column(Integer, ForeignKey("deploy_records.id", ondelete="SET NULL"), nullable=True)
    # 审计
    creator_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(CHINA_TZ))

    application: Mapped["DeployApplication"] = relationship(back_populates="deployments", lazy="joined")
    environment: Mapped["DeployEnvironment"] = relationship("DeployEnvironment", lazy="joined")
    creator: Mapped["User"] = relationship("User", lazy="joined")
