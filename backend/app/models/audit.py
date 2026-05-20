"""Audit log data model — SQLAlchemy ORM."""
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    username: Mapped[str] = mapped_column(String(100), default="")
    action: Mapped[str] = mapped_column(String(50), nullable=False)       # create / update / delete / login / logout
    target_type: Mapped[str] = mapped_column(String(50), nullable=False)  # asset / user / role / ticket / alert / auth
    target_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_name: Mapped[str] = mapped_column(String(200), default="")
    detail: Mapped[str] = mapped_column(Text, default="")
    ip_address: Mapped[str] = mapped_column(String(50), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", foreign_keys=[user_id], lazy="joined")
