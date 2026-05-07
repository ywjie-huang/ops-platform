from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.init_db import verify_password
from app.models.rbac import Role
from app.models.user import User


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    stmt = select(User).options(
        selectinload(User.roles).selectinload(Role.permissions)
    ).where(User.username == username)
    user = db.scalar(stmt)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user
