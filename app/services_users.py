from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.init_db import hash_password
from app.models.user import User


def list_users(db: Session) -> list[User]:
    return list(db.scalars(select(User).order_by(User.id.desc())).all())


def get_user(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def get_user_by_username(db: Session, username: str) -> User | None:
    return db.scalar(select(User).where(User.username == username))


def create_user(
    db: Session,
    *,
    username: str,
    password: str,
    full_name: str,
) -> User:
    user = User(
        username=username,
        password_hash=hash_password(password),
        full_name=full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(
    db: Session,
    user: User,
    *,
    username: str,
    full_name: str,
    password: str,
) -> User:
    user.username = username
    user.full_name = full_name
    if password.strip():
        user.password_hash = hash_password(password)
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user: User) -> None:
    db.delete(user)
    db.commit()
