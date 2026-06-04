"""Application deployment models — SQLAlchemy ORM."""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import CHINA_TZ
from app.db.database import Base


class DeployApplication(Base):
    """应用表 — 一个可部署的应用单元。"""
    __tablename__ = "deploy_applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    app_type: Mapped[str] = mapped_column(String(30), default="web")          # web / api / worker / frontend / other
    deploy_strategy: Mapped[str] = mapped_column(String(20), default="ssh")   # ssh / docker / k8s
    status: Mapped[str] = mapped_column(String(20), default="active")         # active / archived

    # Git 信息
    git_url: Mapped[str] = mapped_column(String(500), default="")
    git_branch: Mapped[str] = mapped_column(String(100), default="main")

    # 构建配置
    build_mode: Mapped[str] = mapped_column(String(20), default="local")      # local / jenkins
    build_command: Mapped[str] = mapped_column(Text, default="")
    artifact_path: Mapped[str] = mapped_column(String(500), default="")       # 构建产物路径

    # Jenkins 配置（build_mode=jenkins 时使用）
    jenkins_job_name: Mapped[str] = mapped_column(String(200), default="")
    jenkins_token: Mapped[str] = mapped_column(String(200), default="")

    # 健康检查
    health_check_url: Mapped[str] = mapped_column(String(500, collation="utf8mb4_unicode_ci"), default="")
    health_check_timeout: Mapped[int] = mapped_column(Integer, default=30)    # 秒

    creator_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(CHINA_TZ))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(CHINA_TZ), onupdate=lambda: datetime.now(CHINA_TZ))

    creator = relationship("User", foreign_keys=[creator_id], lazy="joined")
    envs: Mapped[list["DeployAppEnv"]] = relationship(back_populates="application", cascade="all, delete-orphan")
    records: Mapped[list["DeployRecord"]] = relationship(back_populates="application", cascade="all, delete-orphan")
    configs: Mapped[list["DeployConfig"]] = relationship(back_populates="application", cascade="all, delete-orphan")


class DeployEnvironment(Base):
    """环境表 — 部署目标环境（dev / staging / prod 等）。"""
    __tablename__ = "deploy_environments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    approval_required: Mapped[bool] = mapped_column(Boolean, default=False)    # 该环境是否需要审批
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(CHINA_TZ))

    app_envs: Mapped[list["DeployAppEnv"]] = relationship(back_populates="environment", cascade="all, delete-orphan")


class DeployAppEnv(Base):
    """应用×环境关联表 — 每个应用在每个环境下的部署目标配置。"""
    __tablename__ = "deploy_app_envs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    app_id: Mapped[int] = mapped_column(Integer, ForeignKey("deploy_applications.id", ondelete="CASCADE"), nullable=False)
    env_id: Mapped[int] = mapped_column(Integer, ForeignKey("deploy_environments.id", ondelete="CASCADE"), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # SSH 策略配置
    ssh_asset_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("assets.id", ondelete="SET NULL"), nullable=True)
    deploy_path: Mapped[str] = mapped_column(String(500), default="")
    deploy_script: Mapped[str] = mapped_column(Text, default="")              # 部署后执行的脚本

    # Docker 策略配置
    docker_host_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("container_clusters.id", ondelete="SET NULL"), nullable=True)
    docker_image: Mapped[str] = mapped_column(String(500, collation="utf8mb4_unicode_ci"), default="")
    docker_container_name: Mapped[str] = mapped_column(String(200), default="")
    docker_ports: Mapped[str] = mapped_column(String(500), default="")        # "8080:80,443:443"
    docker_env_vars: Mapped[str] = mapped_column(Text, default="")            # JSON: {"KEY":"value"}
    docker_network: Mapped[str] = mapped_column(String(100, collation="utf8mb4_unicode_ci"), default="")
    docker_extra_args: Mapped[str] = mapped_column(Text, default="")           # 额外 docker run 参数

    # K8s 策略配置
    k8s_cluster_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("container_clusters.id", ondelete="SET NULL"), nullable=True)
    k8s_namespace: Mapped[str] = mapped_column(String(100), default="default")
    k8s_deployment: Mapped[str] = mapped_column(String(200), default="")
    k8s_container_name: Mapped[str] = mapped_column(String(200, collation="utf8mb4_unicode_ci"), default="")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(CHINA_TZ))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(CHINA_TZ), onupdate=lambda: datetime.now(CHINA_TZ))

    application = relationship("DeployApplication", back_populates="envs")
    environment = relationship("DeployEnvironment", back_populates="app_envs")
    ssh_asset = relationship("Asset", foreign_keys=[ssh_asset_id], lazy="joined")
    docker_host = relationship("ContainerCluster", foreign_keys=[docker_host_id], lazy="joined")
    k8s_cluster = relationship("ContainerCluster", foreign_keys=[k8s_cluster_id], lazy="joined")


class DeployRecord(Base):
    """部署记录表 — 每次部署执行的完整记录。"""
    __tablename__ = "deploy_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    app_id: Mapped[int] = mapped_column(Integer, ForeignKey("deploy_applications.id", ondelete="CASCADE"), nullable=False)
    env_id: Mapped[int] = mapped_column(Integer, ForeignKey("deploy_environments.id", ondelete="SET NULL"), nullable=True)
    app_env_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("deploy_app_envs.id", ondelete="SET NULL"), nullable=True)

    version: Mapped[str] = mapped_column(String(100), default="")             # 部署版本号/commit/tag
    status: Mapped[str] = mapped_column(String(20), default="pending")        # pending / building / deploying / success / failed / cancelled
    trigger_type: Mapped[str] = mapped_column(String(20), default="manual")   # manual / rollback / webhook
    trigger_user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)

    # 部署配置快照（部署时冻结，保证回滚时配置不变）
    deploy_config: Mapped[str] = mapped_column(Text, default="")              # JSON 快照

    # 日志与结果
    log: Mapped[str] = mapped_column(Text, default="")
    error_message: Mapped[str] = mapped_column(Text, default="")
    duration: Mapped[float | None] = mapped_column(Float, nullable=True)      # 耗时（秒）

    # 回滚关联
    rollback_from: Mapped[int | None] = mapped_column(Integer, nullable=True) # 原记录 ID

    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(CHINA_TZ))

    application = relationship("DeployApplication", back_populates="records")
    environment = relationship("DeployEnvironment", lazy="joined")
    trigger_user = relationship("User", foreign_keys=[trigger_user_id], lazy="joined")


class DeployApproval(Base):
    """审批表 — 部署审批记录。"""
    __tablename__ = "deploy_approvals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    record_id: Mapped[int] = mapped_column(Integer, ForeignKey("deploy_records.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")         # pending / approved / rejected
    approver_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(CHINA_TZ))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    record = relationship("DeployRecord", lazy="joined")
    approver = relationship("User", foreign_keys=[approver_id], lazy="joined")


class DeployConfig(Base):
    """配置表 — 应用的环境变量/配置项，支持加密存储。"""
    __tablename__ = "deploy_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    app_id: Mapped[int] = mapped_column(Integer, ForeignKey("deploy_applications.id", ondelete="CASCADE"), nullable=False)
    env_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("deploy_environments.id", ondelete="CASCADE"), nullable=True)

    key: Mapped[str] = mapped_column(String(200), nullable=False)
    value: Mapped[str] = mapped_column(Text, default="")
    is_encrypted: Mapped[bool] = mapped_column(Boolean, default=False)         # 加密字段不回显明文
    description: Mapped[str] = mapped_column(Text, default="")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(CHINA_TZ))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(CHINA_TZ), onupdate=lambda: datetime.now(CHINA_TZ))

    application = relationship("DeployApplication", back_populates="configs")
    environment = relationship("DeployEnvironment", lazy="joined")
