from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db import init_db
from app.models.container import ContainerCluster  # noqa: F401
from app.models.rbac import Role, user_roles
from app.models.user import User


def _sqlite_session() -> tuple[Session, object]:
    engine = create_engine("sqlite://")
    Role.__table__.create(engine)
    User.__table__.create(engine)
    user_roles.create(engine)
    return Session(engine), engine


def test_seed_users_creates_configured_initial_admin(monkeypatch):
    db, engine = _sqlite_session()
    monkeypatch.setattr(init_db, "INITIAL_ADMIN_USERNAME", "platform-admin")
    monkeypatch.setattr(init_db, "INITIAL_ADMIN_PASSWORD", "ChangeMe-2026")
    try:
        init_db._seed_users(db)
        db.commit()

        user = db.scalar(select(User).where(User.username == "platform-admin"))

        assert user is not None
        assert init_db.verify_password("ChangeMe-2026", user.password_hash)
        assert {role.code for role in user.roles} == {"super_admin"}
    finally:
        db.close()
        engine.dispose()


def test_seed_users_does_not_create_another_admin_after_initialization(monkeypatch):
    db, engine = _sqlite_session()
    monkeypatch.setattr(init_db, "INITIAL_ADMIN_USERNAME", "new-admin")
    monkeypatch.setattr(init_db, "INITIAL_ADMIN_PASSWORD", "ChangeMe-2026")
    try:
        db.add(User(username="existing-user", password_hash="existing-hash", full_name="Existing"))
        db.commit()

        init_db._seed_users(db)
        db.commit()

        assert [user.username for user in db.scalars(select(User)).all()] == ["existing-user"]
    finally:
        db.close()
        engine.dispose()
