"""审批逻辑。"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.deploy import DeployApproval, DeployRecord


def list_approvals(db: Session, deployment_id: int) -> list[DeployApproval]:
    """获取某次发布的所有审批记录。"""
    stmt = (
        select(DeployApproval)
        .where(DeployApproval.deployment_id == deployment_id)
        .order_by(DeployApproval.id.desc())
    )
    return list(db.scalars(stmt).all())


def create_approval(
    db: Session,
    *,
    deployment_id: int,
    action: str,
    comment: str = "",
    approver_id: int | None = None,
) -> DeployApproval:
    """创建审批记录（通过或驳回）。"""
    approval = DeployApproval(
        deployment_id=deployment_id,
        action=action,
        comment=comment,
        approver_id=approver_id,
    )
    db.add(approval)
    db.flush()
    return approval


def get_pending_deployments(db: Session) -> list[DeployRecord]:
    """获取所有待审批的发布记录。"""
    stmt = (
        select(DeployRecord)
        .where(DeployRecord.status == "pending")
        .order_by(DeployRecord.id.desc())
    )
    return list(db.scalars(stmt).all())
