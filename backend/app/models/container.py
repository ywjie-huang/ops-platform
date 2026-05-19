"""容器管理数据模型。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Float, ForeignKey, Integer, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class ContainerCluster(Base):
    """K8s 集群 / Docker 主机。"""

    __tablename__ = "container_clusters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), default="kubernetes")  # kubernetes / docker
    version: Mapped[str] = mapped_column(String(32), default="")
    endpoint: Mapped[str] = mapped_column(String(256), default="")  # API server 地址
    token: Mapped[str] = mapped_column(String(4000), default="")  # ServiceAccount Token
    status: Mapped[str] = mapped_column(String(32), default="running")  # running / stopped / unknown
    status_message: Mapped[str] = mapped_column(String(512), default="")  # 状态描述/错误信息（K8s 用）
    endpoint: Mapped[str] = mapped_column(String(256), default="")  # API server 地址（K8s 用）
    node_count: Mapped[int] = mapped_column(Integer, default=0)
    description: Mapped[str] = mapped_column(Text, default="")
    agent_key: Mapped[str] = mapped_column(String(1024), default="")  # 主机指标 JSON（复用字段）
    last_heartbeat: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # Agent 最后心跳
    host_os: Mapped[str] = mapped_column(String(128), default="")  # 主机系统信息
    host_ip: Mapped[str] = mapped_column(String(64), default="")  # 主机 IP
    docker_version: Mapped[str] = mapped_column(String(32), default="")  # Docker 版本
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    deployments: Mapped[list["ContainerDeployment"]] = relationship(back_populates="cluster", cascade="all, delete-orphan")
    pods: Mapped[list["ContainerPod"]] = relationship(back_populates="cluster", cascade="all, delete-orphan")
    services: Mapped[list["ContainerService"]] = relationship(back_populates="cluster", cascade="all, delete-orphan")
    docker_containers: Mapped[list["DockerContainer"]] = relationship(back_populates="host", cascade="all, delete-orphan")


class ContainerDeployment(Base):
    """Deployment / Compose 服务。"""

    __tablename__ = "container_deployments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    cluster_id: Mapped[int] = mapped_column(Integer, ForeignKey("container_clusters.id"), nullable=False)
    namespace: Mapped[str] = mapped_column(String(64), default="default")
    replicas: Mapped[int] = mapped_column(Integer, default=1)
    ready_replicas: Mapped[int] = mapped_column(Integer, default=0)
    image: Mapped[str] = mapped_column(String(256), default="")
    status: Mapped[str] = mapped_column(String(32), default="running")  # running / stopped / updating / error
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    cluster: Mapped["ContainerCluster"] = relationship(back_populates="deployments")


class ContainerPod(Base):
    """Pod / 容器实例。"""

    __tablename__ = "container_pods"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    cluster_id: Mapped[int] = mapped_column(Integer, ForeignKey("container_clusters.id"), nullable=False)
    namespace: Mapped[str] = mapped_column(String(64), default="default")
    status: Mapped[str] = mapped_column(String(32), default="Running")  # Running / Pending / Succeeded / Failed / Unknown
    node: Mapped[str] = mapped_column(String(128), default="")
    pod_ip: Mapped[str] = mapped_column(String(64), default="")
    restarts: Mapped[int] = mapped_column(Integer, default=0)
    image: Mapped[str] = mapped_column(String(256), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    cluster: Mapped["ContainerCluster"] = relationship(back_populates="pods")


class ContainerService(Base):
    """Service / 网络服务。"""

    __tablename__ = "container_services"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    cluster_id: Mapped[int] = mapped_column(Integer, ForeignKey("container_clusters.id"), nullable=False)
    namespace: Mapped[str] = mapped_column(String(64), default="default")
    service_type: Mapped[str] = mapped_column(String(32), default="ClusterIP")  # ClusterIP / NodePort / LoadBalancer
    cluster_ip: Mapped[str] = mapped_column(String(64), default="")
    ports: Mapped[str] = mapped_column(String(128), default="")  # 如 "80:30080/TCP,443:30443/TCP"
    selector: Mapped[str] = mapped_column(String(256), default="")  # label selector
    status: Mapped[str] = mapped_column(String(32), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    cluster: Mapped["ContainerCluster"] = relationship(back_populates="services")


class DockerContainer(Base):
    """Docker 容器实例（由 Agent 上报）。"""

    __tablename__ = "docker_containers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    host_id: Mapped[int] = mapped_column(Integer, ForeignKey("container_clusters.id"), nullable=False)
    container_id: Mapped[str] = mapped_column(String(64), nullable=False)  # Docker 容器短 ID
    name: Mapped[str] = mapped_column(String(256), default="")
    image: Mapped[str] = mapped_column(String(512), default="")
    status: Mapped[str] = mapped_column(String(32), default="running")  # running / exited / paused / restarting / created / removing
    state: Mapped[str] = mapped_column(String(32), default="")  # running / dead / exited 等原始状态
    ports: Mapped[str] = mapped_column(String(512), default="")  # 端口映射 JSON
    cpu_percent: Mapped[float] = mapped_column(Float, default=0.0)
    memory_usage: Mapped[int] = mapped_column(BigInteger, default=0)  # bytes
    memory_limit: Mapped[int] = mapped_column(BigInteger, default=0)  # bytes
    memory_percent: Mapped[float] = mapped_column(Float, default=0.0)
    net_rx_bytes: Mapped[int] = mapped_column(BigInteger, default=0)  # 网络接收字节
    net_tx_bytes: Mapped[int] = mapped_column(BigInteger, default=0)  # 网络发送字节
    block_read: Mapped[int] = mapped_column(BigInteger, default=0)  # 磁盘读字节
    block_write: Mapped[int] = mapped_column(BigInteger, default=0)  # 磁盘写字节
    restart_count: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    host: Mapped["ContainerCluster"] = relationship(back_populates="docker_containers")
