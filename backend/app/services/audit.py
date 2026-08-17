"""Audit log service — write + query."""
from datetime import datetime, timedelta

from app.core.config import CHINA_TZ

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

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
    username: str = "",
) -> AuditLog:
    log = AuditLog(
        user_id=user.id if user else None,
        # 登录失败等场景没有 User 对象，用调用方传入的用户名留痕
        username=user.username if user else username,
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


def _build_conditions(keyword: str, action: str, target_type: str, days: int):
    keyword = keyword.strip()
    action = action.strip()
    target_type = target_type.strip()
    conds = []
    if keyword:
        like_val = f"%{keyword}%"
        conds.append(
            or_(
                AuditLog.username.ilike(like_val),
                AuditLog.target_name.ilike(like_val),
                AuditLog.detail.ilike(like_val),
            )
        )
    if action:
        conds.append(AuditLog.action == action)
    if target_type:
        conds.append(AuditLog.target_type == target_type)
    if days > 0:
        since = datetime.now(CHINA_TZ) - timedelta(days=days)
        conds.append(AuditLog.created_at >= since)
    return conds


def list_logs(
    db: Session,
    *,
    keyword: str = "",
    action: str = "",
    target_type: str = "",
    days: int = 0,
    page: int = 1,
    page_size: int = 10,
) -> tuple[list[AuditLog], int]:
    """SQL 级分页查询，返回 (当前页数据, 总条数)。"""
    conds = _build_conditions(keyword, action, target_type, days)
    total = db.scalar(select(func.count(AuditLog.id)).where(*conds)) or 0
    page = max(page, 1)
    page_size = max(1, min(page_size, 200))
    stmt = (
        select(AuditLog)
        .where(*conds)
        .order_by(AuditLog.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(db.scalars(stmt).all()), total


def query_logs_for_export(
    db: Session,
    *,
    keyword: str = "",
    action: str = "",
    target_type: str = "",
    days: int = 0,
    limit: int = 10000,
) -> list[AuditLog]:
    """导出用查询，上限 limit 条防滥用。"""
    conds = _build_conditions(keyword, action, target_type, days)
    stmt = select(AuditLog).where(*conds).order_by(AuditLog.id.desc()).limit(limit)
    return list(db.scalars(stmt).all())


def get_stats(db: Session) -> dict:
    now = datetime.now(CHINA_TZ)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)
    week_start = now - timedelta(days=7)

    def count(*conds) -> int:
        return db.scalar(select(func.count(AuditLog.id)).where(*conds)) or 0

    active_users_7d = db.scalar(
        select(func.count(func.distinct(AuditLog.username))).where(AuditLog.created_at >= week_start)
    ) or 0
    return {
        "today_events": count(AuditLog.created_at >= today_start),
        "yesterday_events": count(AuditLog.created_at >= yesterday_start, AuditLog.created_at < today_start),
        "today_logins": count(AuditLog.created_at >= today_start, AuditLog.action == "login"),
        "today_login_failed": count(AuditLog.created_at >= today_start, AuditLog.action == "login_failed"),
        "deletes_7d": count(AuditLog.created_at >= week_start, AuditLog.action == "delete"),
        "active_users_7d": active_users_7d,
    }


def count_logs(db: Session) -> int:
    return db.scalar(select(func.count(AuditLog.id))) or 0


ACTION_LABELS = {
    "create": "新增",
    "update": "编辑",
    "delete": "删除",
    "login": "登录",
    "login_failed": "登录失败",
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
