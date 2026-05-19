"""Ticket data model — SQLAlchemy ORM."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    priority: Mapped[str] = mapped_column(String(20), default="normal")   # low / normal / high / critical
    status: Mapped[str] = mapped_column(String(20), default="open")       # open / in_progress / resolved / closed
    assignee: Mapped[str] = mapped_column(String(100), default="")
    asset_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("assets.id", ondelete="SET NULL"), nullable=True)
    creator_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    asset = relationship("Asset", lazy="joined")
    creator = relationship("User", foreign_keys=[creator_id], lazy="joined")
