"""Audit log service — write + query."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.audit import AuditLog
from app.models.user import User


def write_log(
    db: Session,
    *,
    user: User | None,
    action: str,
    target_type: str,
    target_id: int | None = None,
    target_name: str = "",
    detail: str = "",
    ip_address: str = "",
) -> AuditLog:
    log = AuditLog(
        user_id=user.id if user else None,
        username=user.username if user else "",
        action=action,
        target_type=target_type,
        target_id=target_id,
        target_name=target_name,
        detail=detail,
        ip_address=ip_address,
    )
    db.add(log)
    db.flush()
    return log


def list_logs(
    db: Session,
    *,
    keyword: str = "",
    action: str = "",
    target_type: str = "",
    days: int = 0,
) -> list[AuditLog]:
    stmt = select(AuditLog).options(selectinload(AuditLog.user))
    keyword = keyword.strip()
    action = action.strip()
    target_type = target_type.strip()

    if keyword:
        like_val = f"%{keyword}%"
        stmt = stmt.where(
            or_(
                AuditLog.username.ilike(like_val),
                AuditLog.target_name.ilike(like_val),
                AuditLog.detail.ilike(like_val),
            )
        )
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if target_type:
        stmt = stmt.where(AuditLog.target_type == target_type)
    if days > 0:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        stmt = stmt.where(AuditLog.created_at >= since)

    stmt = stmt.order_by(AuditLog.id.desc())
    return list(db.scalars(stmt).unique().all())


def count_logs(db: Session) -> int:
    return db.scalar(select(func.count(AuditLog.id))) or 0


ACTION_LABELS = {
    "create": "新增",
    "update": "编辑",
    "delete": "删除",
    "login": "登录",
    "logout": "登出",
}

TARGET_LABELS = {
    "asset": "资产",
    "user": "用户",
    "role": "角色",
    "ticket": "工单",
    "alert": "告警",
    "auth": "认证",
    "settings": "配置",
}
