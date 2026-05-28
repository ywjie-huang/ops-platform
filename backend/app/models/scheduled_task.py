"""定时任务模型。"""
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import CHINA_TZ
from app.db.database import Base


class ScheduledTask(Base):
    """定时任务定义。"""
    __tablename__ = "scheduled_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    task_type: Mapped[str] = mapped_column(String(50))  # patrol / report / backup
    cron_expr: Mapped[str] = mapped_column(String(100))  # 5-field cron: "min hour day month weekday"
    params: Mapped[dict | None] = mapped_column(JSON, default=None)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    description: Mapped[str] = mapped_column(String(500), default="")
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    last_status: Mapped[str] = mapped_column(String(20), default="")  # success / failed / running
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(CHINA_TZ))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(CHINA_TZ), onupdate=lambda: datetime.now(CHINA_TZ))


class TaskExecutionLog(Base):
    """定时任务执行日志。"""
    __tablename__ = "task_execution_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_id: Mapped[int] = mapped_column(Integer, ForeignKey("scheduled_tasks.id", ondelete="CASCADE"), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(CHINA_TZ))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    status: Mapped[str] = mapped_column(String(20), default="running")  # running / success / failed
    result: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str] = mapped_column(Text, default="")
