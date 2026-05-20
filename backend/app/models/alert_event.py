"""告警事件模型 — 记录 Alertmanager 推送的每一次告警。"""
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class AlertEvent(Base):
    """Alertmanager webhook 推送的告警事件。"""

    __tablename__ = "alert_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fingerprint: Mapped[str] = mapped_column(String(64), index=True, default="")
    alert_name: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    severity: Mapped[str] = mapped_column(String(20), default="warning")
    status: Mapped[str] = mapped_column(String(20), default="firing")        # firing / resolved
    alert_value: Mapped[str] = mapped_column(String(100), default="")        # 告警值
    summary: Mapped[str] = mapped_column(Text, default="")
    description: Mapped[str] = mapped_column(Text, default="")
    instance: Mapped[str] = mapped_column(String(200), default="")
    job: Mapped[str] = mapped_column(String(100), default="")
    firing_count: Mapped[int] = mapped_column(Integer, default=1)            # 连续触发次数
    generator_url: Mapped[str] = mapped_column(String(500), default="")
    raw_labels: Mapped[str] = mapped_column(Text, default="{}")              # JSON
    raw_annotations: Mapped[str] = mapped_column(Text, default="{}")         # JSON
    starts_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
