from datetime import datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.db.init_db import hash_password, verify_password
from app.models.rbac import Role
from app.models.user import User


def list_users(
    db: Session,
    *,
    keyword: str = "",
    role_id: int | None = None,
) -> list[User]:
    stmt = select(User).options(selectinload(User.roles))
    keyword = keyword.strip()

    if keyword:
        like_value = f"%{keyword}%"
        stmt = stmt.where(or_(User.username.ilike(like_value), User.full_name.ilike(like_value)))
    if role_id:
        stmt = stmt.join(User.roles).where(Role.id == role_id)

    stmt = stmt.order_by(User.id.desc())
    return list(db.scalars(stmt).unique().all())


def list_recent_users(db: Session, limit: int = 5) -> list[User]:
    stmt = select(User).options(selectinload(User.roles)).order_by(User.created_at.desc(), User.id.desc()).limit(limit)
    return list(db.scalars(stmt).unique().all())


def count_new_users_since(db: Session, days: int = 7) -> int:
    since = datetime.utcnow() - timedelta(days=days)
    stmt = select(User).where(User.created_at >= since)
    return len(db.scalars(stmt).all())


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
    password: str,
    role_ids: list[int] | None = None,
) -> User:
    user.username = username
    user.full_name = full_name
    user.roles = _get_roles_by_ids(db, role_ids or [])
    if password.strip():
        user.password_hash = hash_password(password)
    db.commit()
    db.refresh(user)
    return get_user(db, user.id) or user


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
