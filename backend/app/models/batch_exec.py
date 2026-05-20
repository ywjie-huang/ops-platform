"""批量执行模型 — 执行历史 + 命令预设。"""
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class BatchExecution(Base):
    __tablename__ = "batch_executions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    command: Mapped[str] = mapped_column(Text, nullable=False)
    asset_ids: Mapped[str] = mapped_column(String(500), default="")  # 逗号分隔的资产 ID
    asset_names: Mapped[str] = mapped_column(String(500), default="")  # 逗号分隔的资产名称
    total_hosts: Mapped[int] = mapped_column(Integer, default=0)
    success_hosts: Mapped[int] = mapped_column(Integer, default=0)
    failed_hosts: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="running")  # running / completed / failed
    operator: Mapped[str] = mapped_column(String(100), default="")  # 操作人
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    finished_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)


class CommandPreset(Base):
    __tablename__ = "command_presets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    command: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(String(200), default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
