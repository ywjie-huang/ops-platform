from datetime import datetime, timedelta

from app.core.config import CHINA_TZ

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.db.init_db import hash_password, verify_password
from app.models.audit import AuditLog
from app.models.rbac import Role
from app.models.user import User


def count_users(db: Session) -> int:
    return db.scalar(select(func.count(User.id))) or 0


def _last_login_subquery():
    """按 username 聚合最近一次登录成功时间（源自审计日志）。"""
    return (
        select(
            AuditLog.username.label("login_username"),
            func.max(AuditLog.created_at).label("last_login"),
        )
        .where(AuditLog.action == "login")
        .group_by(AuditLog.username)
        .subquery()
    )


def list_users(
    db: Session,
    *,
    keyword: str = "",
    role_id: int | None = None,
    activity: str = "",
    page: int = 1,
    page_size: int = 10,
) -> tuple[list[tuple[User, datetime | None]], int]:
    """SQL 级分页查询，返回 ([(User, 最近登录时间)], 总数)。

    activity: active_7d（近 7 天活跃）/ dormant（超过 7 天未登录）/
              never（从未登录）/ no_role（未分配角色）。
    """
    sq = _last_login_subquery()
    conds = []

    keyword = keyword.strip()
    if keyword:
        like_value = f"%{keyword}%"
        conds.append(or_(User.username.ilike(like_value), User.full_name.ilike(like_value)))
    if role_id:
        conds.append(User.roles.any(Role.id == role_id))

    activity = activity.strip()
    if activity == "no_role":
        conds.append(~User.roles.any())
    elif activity in ("active_7d", "dormant", "never"):
        week_ago = datetime.now(CHINA_TZ) - timedelta(days=7)
        if activity == "active_7d":
            conds.append(sq.c.last_login >= week_ago)
        elif activity == "dormant":
            conds.append(sq.c.last_login.isnot(None))
            conds.append(sq.c.last_login < week_ago)
        else:
            conds.append(sq.c.last_login.is_(None))

    join_cond = User.username == sq.c.login_username
    total = db.scalar(
        select(func.count(User.id)).outerjoin(sq, join_cond).where(*conds)
    ) or 0

    page = max(page, 1)
    page_size = max(1, min(page_size, 100))
    stmt = (
        select(User, sq.c.last_login)
        .outerjoin(sq, join_cond)
        .where(*conds)
        .options(selectinload(User.roles))
        .order_by(User.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = db.execute(stmt).all()
    return [(row[0], row[1]) for row in rows], total


def list_recent_users(db: Session, limit: int = 5) -> list[User]:
    stmt = select(User).options(selectinload(User.roles)).order_by(User.created_at.desc(), User.id.desc()).limit(limit)
    return list(db.scalars(stmt).unique().all())


def count_new_users_since(db: Session, days: int = 7) -> int:
    since = datetime.now(CHINA_TZ) - timedelta(days=days)
    stmt = select(User).where(User.created_at >= since)
    return len(db.scalars(stmt).all())


def get_user_stats(db: Session) -> dict:
    """用户管理页概览：规模 + 登录活跃度（口径与审计页一致）。"""
    now = datetime.now(CHINA_TZ)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)

    total_users = count_users(db)
    new_users_7d = db.scalar(select(func.count(User.id)).where(User.created_at >= week_ago)) or 0
    no_role_count = db.scalar(select(func.count(User.id)).where(~User.roles.any())) or 0

    def distinct_users(*conds) -> int:
        return db.scalar(
            select(func.count(func.distinct(AuditLog.username))).where(*conds)
        ) or 0

    return {
        "total_users": total_users,
        "new_users_7d": new_users_7d,
        "today_logins": distinct_users(AuditLog.created_at >= today_start, AuditLog.action == "login"),
        "today_login_failed": db.scalar(
            select(func.count(AuditLog.id)).where(AuditLog.created_at >= today_start, AuditLog.action == "login_failed")
        ) or 0,
        "active_7d": distinct_users(AuditLog.created_at >= week_ago, AuditLog.action == "login"),
        "no_role_count": no_role_count,
    }


def get_user_activity(db: Session, user: User) -> dict:
    """单个用户活跃摘要（详情抽屉用）。"""
    now = datetime.now(CHINA_TZ)
    month_ago = now - timedelta(days=30)
    week_ago = now - timedelta(days=7)
    mine = AuditLog.username == user.username

    last_login = db.scalar(
        select(func.max(AuditLog.created_at)).where(mine, AuditLog.action == "login")
    )
    recent_logs = list(db.scalars(
        select(AuditLog).where(mine).order_by(AuditLog.id.desc()).limit(5)
    ).all())

    return {
        "login_count_30d": db.scalar(
            select(func.count(AuditLog.id)).where(mine, AuditLog.action == "login", AuditLog.created_at >= month_ago)
        ) or 0,
        "login_failed_7d": db.scalar(
            select(func.count(AuditLog.id)).where(mine, AuditLog.action == "login_failed", AuditLog.created_at >= week_ago)
        ) or 0,
        "last_login_at": last_login,
        "recent_logs": recent_logs,
    }


def get_user(db: Session, user_id: int) -> User | None:
    stmt = select(User).options(selectinload(User.roles)).where(User.id == user_id)
    return db.scalar(stmt)


def get_user_by_username(db: Session, username: str) -> User | None:
    stmt = select(User).options(selectinload(User.roles)).where(User.username == username)
    return db.scalar(stmt)


def create_user(
    db: Session,
    *,
    username: str,
    password: str,
    full_name: str,
    role_ids: list[int] | None = None,
) -> User:
    user = User(
        username=username,
        password_hash=hash_password(password),
        full_name=full_name,
        roles=_get_roles_by_ids(db, role_ids or []),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return get_user(db, user.id) or user


def update_user(
    db: Session,
    user: User,
    *,
    username: str,
    full_name: str,
    role_ids: list[int] | None = None,
) -> User:
    user.username = username
    user.full_name = full_name
    user.roles = _get_roles_by_ids(db, role_ids or [])
    db.commit()
    db.refresh(user)
    return get_user(db, user.id) or user


def reset_user_password(db: Session, user: User, password: str) -> tuple[bool, str]:
    """管理员重置密码，返回 (成功, 错误消息)。"""
    if len(password) < 6:
        return False, "密码至少 6 位"
    user.password_hash = hash_password(password)
    db.commit()
    return True, ""


def delete_user(db: Session, user: User) -> None:
    db.delete(user)
    db.commit()


def change_password(db: Session, user: User, old_password: str, new_password: str) -> tuple[bool, str]:
    """修改密码，返回 (成功, 错误消息)。"""
    if not verify_password(old_password, user.password_hash):
        return False, "原密码不正确"
    if len(new_password) < 6:
        return False, "新密码至少 6 位"
    user.password_hash = hash_password(new_password)
    db.commit()
    return True, ""


def _get_roles_by_ids(db: Session, role_ids: list[int]) -> list[Role]:
    if not role_ids:
        return []
    stmt = select(Role).where(Role.id.in_(role_ids)).order_by(Role.id.asc())
    return list(db.scalars(stmt).all())
