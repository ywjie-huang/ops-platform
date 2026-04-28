from pathlib import Path

from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import DEMO_PASSWORD, DEMO_USERNAME
from app.db.database import Base, engine
from app.models.asset import Asset
from app.models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)

    with Session(engine) as db:
        _seed_users(db)
        _seed_assets(db)
        db.commit()


def _seed_users(db: Session) -> None:
    existing_user = db.scalar(select(User).where(User.username == DEMO_USERNAME))
    if existing_user:
        return

    db.add(
        User(
            username=DEMO_USERNAME,
            password_hash=hash_password(DEMO_PASSWORD),
            full_name="系统管理员",
        )
    )


def _seed_assets(db: Session) -> None:
    existing_asset = db.scalar(select(Asset).limit(1))
    if existing_asset:
        return

    db.add_all(
        [
            Asset(
                name="web-prod-01",
                asset_type="云主机",
                ip_address="10.10.1.12",
                status="在线",
                owner="平台组",
                description="核心业务 Web 节点",
            ),
            Asset(
                name="db-prod-01",
                asset_type="数据库",
                ip_address="10.10.1.21",
                status="在线",
                owner="DBA",
                description="主数据库实例",
            ),
            Asset(
                name="waf-gateway",
                asset_type="网络设备",
                ip_address="10.10.1.2",
                status="维护中",
                owner="安全组",
                description="统一入口网关",
            ),
        ]
    )
