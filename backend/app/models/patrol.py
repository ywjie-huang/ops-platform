"""巡检中心模型。"""
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import CHINA_TZ
from app.db.database import Base


class PatrolReport(Base):
    """巡检报告 — 一次巡检的总记录。"""
    __tablename__ = "patrol_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), default="")
    status: Mapped[str] = mapped_column(String(20), default="normal")  # normal / warning / critical
    total_checks: Mapped[int] = mapped_column(Integer, default=0)
    normal_count: Mapped[int] = mapped_column(Integer, default=0)
    warning_count: Mapped[int] = mapped_column(Integer, default=0)
    critical_count: Mapped[int] = mapped_column(Integer, default=0)
    summary: Mapped[str] = mapped_column(Text, default="")  # 文字摘要
    operator: Mapped[str] = mapped_column(String(100), default="")  # 操作人（手动触发时记录）
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(CHINA_TZ))


class PatrolItem(Base):
    """巡检项 — 每个检查点的结果。"""
    __tablename__ = "patrol_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    report_id: Mapped[int] = mapped_column(Integer, index=True)
    category: Mapped[str] = mapped_column(String(50), default="")  # host / k8s / asset
    target_name: Mapped[str] = mapped_column(String(200), default="")  # 主机名 / 集群名
    target_ip: Mapped[str] = mapped_column(String(100), default="")
    check_name: Mapped[str] = mapped_column(String(100), default="")  # CPU / 内存 / 磁盘 / 节点状态…
    status: Mapped[str] = mapped_column(String(20), default="normal")  # normal / warning / critical
    value: Mapped[str] = mapped_column(String(200), default="")  # 当前值
    threshold: Mapped[str] = mapped_column(String(200), default="")  # 阈值
    detail: Mapped[str] = mapped_column(Text, default="")  # 详细说明
