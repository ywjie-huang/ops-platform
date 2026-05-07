"""监控告警数据模型。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text, DateTime, Float, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class MonitoringMetric(Base):
    """监控指标定义（可自定义）。"""

    __tablename__ = "monitoring_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    unit: Mapped[str] = mapped_column(String(16), default="%")
    category: Mapped[str] = mapped_column(String(64), default="系统")
    description: Mapped[str] = mapped_column(Text, default="")
    threshold_warning: Mapped[float] = mapped_column(Float, default=80.0)
    threshold_critical: Mapped[float] = mapped_column(Float, default=95.0)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    data_points: Mapped[list["MonitoringData"]] = relationship(back_populates="metric", cascade="all, delete-orphan")


class MonitoringData(Base):
    """监控数据点。"""

    __tablename__ = "monitoring_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    metric_id: Mapped[int] = mapped_column(Integer, ForeignKey("monitoring_metrics.id"), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String(128), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    metric: Mapped["MonitoringMetric"] = relationship(back_populates="data_points")
