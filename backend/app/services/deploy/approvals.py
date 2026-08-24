"""Deploy approval service — create, query, approve, reject."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import CHINA_TZ
from app.models.deploy import (
    DeployAppEnv,
    DeployApproval,
    DeployApplication,
    DeployEnvironment,
    DeployRecord,
)


def list_approvals(
    db: Session,
    *,
    status: str = "pending",
) -> list[DeployApproval]:
    """查询审批列表。"""
    stmt = select(DeployApproval).options(
        selectinload(DeployApproval.record).selectinload(DeployRecord.application),
        selectinload(DeployApproval.record).selectinload(DeployRecord.environment),
        selectinload(DeployApproval.record).selectinload(DeployRecord.trigger_user),
        selectinload(DeployApproval.approver),
    )
    if status == "resolved":
        stmt = stmt.where(DeployApproval.status.in_(["approved", "rejected"]))
    elif status:
        stmt = stmt.where(DeployApproval.status == status)
    stmt = stmt.order_by(DeployApproval.id.desc())
    return list(db.scalars(stmt).unique().all())


def get_approval(db: Session, approval_id: int) -> DeployApproval | None:
    """获取单条审批记录。"""
    stmt = select(DeployApproval).options(
        selectinload(DeployApproval.record).selectinload(DeployRecord.application),
        selectinload(DeployApproval.record).selectinload(DeployRecord.environment),
        selectinload(DeployApproval.record).selectinload(DeployRecord.trigger_user),
        selectinload(DeployApproval.approver),
    ).where(DeployApproval.id == approval_id)
    return db.scalar(stmt)


def create_approval(
    db: Session,
    *,
    record_id: int,
) -> DeployApproval:
    """创建审批记录（状态=pending）。"""
    approval = DeployApproval(
        record_id=record_id,
        status="pending",
    )
    db.add(approval)
    db.commit()
    db.refresh(approval)
    return get_approval(db, approval.id) or approval


def approve(
    db: Session,
    approval: DeployApproval,
    *,
    approver_id: int,
    comment: str = "",
) -> DeployApproval:
    """审批通过 → 更新审批记录，返回审批对象（调用方负责触发部署）。"""
    approval.status = "approved"
    approval.approver_id = approver_id
    approval.comment = comment
    approval.resolved_at = datetime.now(CHINA_TZ)
    db.commit()
    return get_approval(db, approval.id) or approval


def reject(
    db: Session,
    approval: DeployApproval,
    *,
    approver_id: int,
    comment: str = "",
) -> DeployApproval:
    """审批拒绝 → 更新审批记录 + 取消关联的部署记录。"""
    approval.status = "rejected"
    approval.approver_id = approver_id
    approval.comment = comment
    approval.resolved_at = datetime.now(CHINA_TZ)

    # 取消关联的部署记录
    record = approval.record
    if record and record.status in ("pending",):
        from app.services.deploy.records import update_status, append_log
        update_status(db, record, "cancelled")
        append_log(db, record, f"审批被拒绝 (审批人: {approver_id})")

    db.commit()
    return get_approval(db, approval.id) or approval
