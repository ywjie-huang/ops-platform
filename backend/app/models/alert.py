"""Alert data model — SQLAlchemy ORM."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import CHINA_TZ
from app.db.database import Base


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    level: Mapped[str] = mapped_column(String(20), default="medium")      # low / medium / high / critical
    status: Mapped[str] = mapped_column(String(20), default="pending")    # pending / confirmed / resolved / ignored
    source: Mapped[str] = mapped_column(String(100), default="")
    asset_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("assets.id", ondelete="SET NULL"), nullable=True)
    handler_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(CHINA_TZ))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(CHINA_TZ), onupdate=lambda: datetime.now(CHINA_TZ))

    asset = relationship("Asset", lazy="joined")
    handler = relationship("User", foreign_keys=[handler_id], lazy="joined")
