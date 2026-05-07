from pathlib import Path

import pymysql
from passlib.context import CryptContext
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import DEMO_PASSWORD, DEMO_USERNAME, MYSQL_DATABASE, MYSQL_HOST, MYSQL_PASSWORD, MYSQL_PORT, MYSQL_USER
from app.db.database import Base, engine
from app.models.alert import Alert
from app.models.asset import Asset
from app.models.rbac import Permission, Role
from app.models.ticket import Ticket
from app.models.user import User

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)


def _ensure_database() -> None:
    """确保 MySQL 数据库存在，不存在则自动创建。"""
    conn = pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
    )
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DATABASE}` "
                f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    _ensure_database()
    Base.metadata.create_all(bind=engine)

    with Session(engine) as db:
        _seed_permissions(db)
        _seed_users(db)
        _seed_admin_permissions(db)
        _seed_assets(db)
        _seed_tickets(db)
        _seed_alerts(db)
        from app.services.roles import sync_default_roles

        sync_default_roles(db)
        db.commit()


def _seed_users(db: Session) -> None:
    admin_role = db.scalar(select(Role).where(Role.code == "super_admin"))
    if admin_role is None:
        admin_role = Role(
            name="超级管理员",
            code="super_admin",
            description="拥有系统全部权限",
            is_system=True,
        )
        db.add(admin_role)
        db.flush()

    existing_user = db.scalar(select(User).where(User.username == DEMO_USERNAME))
    if existing_user:
        if not existing_user.password_hash.startswith("$pbkdf2-sha256$"):
            existing_user.password_hash = hash_password(DEMO_PASSWORD)
        if admin_role not in existing_user.roles:
            existing_user.roles.append(admin_role)
        return

    db.add(
        User(
            username=DEMO_USERNAME,
            password_hash=hash_password(DEMO_PASSWORD),
            full_name="系统管理员",
            roles=[admin_role],
        )
    )


def _seed_admin_permissions(db: Session) -> None:
    """确保 super_admin 角色拥有全部权限。必须在 _seed_users 之后调用。"""
    admin_role = db.scalar(select(Role).where(Role.code == "super_admin"))
    if admin_role is None:
        return
    all_permissions = list(db.scalars(select(Permission).order_by(Permission.id)).all())
    if not all_permissions:
        return
    admin_role.permissions = all_permissions
    db.flush()


def _seed_permissions(db: Session) -> None:
    permission_specs = [
        ("查看仪表盘", "dashboard.view", "dashboard", "查看首页仪表盘"),
        ("查看资产", "assets.view", "assets", "查看资产列表"),
        ("新增资产", "assets.create", "assets", "新增资产"),
        ("编辑资产", "assets.update", "assets", "编辑资产"),
        ("删除资产", "assets.delete", "assets", "删除资产"),
        ("查看用户", "users.view", "users", "查看用户列表"),
        ("新增用户", "users.create", "users", "新增用户"),
        ("编辑用户", "users.update", "users", "编辑用户"),
        ("删除用户", "users.delete", "users", "删除用户"),
        ("查看角色", "roles.view", "roles", "查看角色列表"),
        ("新增角色", "roles.create", "roles", "新增角色"),
        ("编辑角色", "roles.update", "roles", "编辑角色及授权"),
        ("删除角色", "roles.delete", "roles", "删除角色"),
        ("查看工单", "tickets.view", "tickets", "查看工单列表"),
        ("新增工单", "tickets.create", "tickets", "新增工单"),
        ("编辑工单", "tickets.update", "tickets", "编辑工单"),
        ("删除工单", "tickets.delete", "tickets", "删除工单"),
        ("查看告警", "alerts.view", "alerts", "查看告警列表"),
        ("新增告警", "alerts.create", "alerts", "新增告警"),
        ("编辑告警", "alerts.update", "alerts", "编辑告警"),
        ("删除告警", "alerts.delete", "alerts", "删除告警"),
        ("查看审计日志", "audit.view", "audit", "查看审计日志"),
        ("查看报表", "reports.view", "reports", "查看报表中心"),
        ("创建报表", "reports.create", "reports", "创建自定义报表"),
        ("编辑报表", "reports.update", "reports", "编辑报表配置"),
        ("删除报表", "reports.delete", "reports", "删除报表"),
        ("查看容器", "containers.view", "containers", "查看容器管理"),
        ("创建容器", "containers.create", "containers", "创建容器/集群"),
        ("编辑容器", "containers.update", "containers", "编辑容器配置"),
        ("删除容器", "containers.delete", "containers", "删除容器/集群"),
        ("查看监控", "monitoring.view", "monitoring", "查看监控指标和主机监控"),
        ("创建监控指标", "monitoring.create", "monitoring", "创建自定义监控指标"),
        ("编辑监控指标", "monitoring.update", "monitoring", "编辑监控指标配置"),
        ("删除监控指标", "monitoring.delete", "monitoring", "删除自定义监控指标"),
    ]

    for name, code, module, description in permission_specs:
        existing = db.scalar(select(Permission).where(Permission.code == code))
        if existing is None:
            db.add(
                Permission(
                    name=name,
                    code=code,
                    module=module,
                    description=description,
                )
            )

    db.flush()


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


def _seed_tickets(db: Session) -> None:
    existing = db.scalar(select(Ticket).limit(1))
    if existing:
        return

    assets = list(db.scalars(select(Asset)).all())
    admin = db.scalar(select(User).where(User.username == DEMO_USERNAME))

    db.add_all(
        [
            Ticket(
                title="新增监控项配置",
                description="需要为 web-prod-01 添加 CPU、内存、磁盘监控告警规则",
                priority="normal",
                status="in_progress",
                assignee="张三",
                asset_id=assets[0].id if assets else None,
                creator_id=admin.id if admin else None,
            ),
            Ticket(
                title="数据库慢查询排查",
                description="近期 db-prod-01 出现多条慢查询，需要排查优化",
                priority="high",
                status="open",
                assignee="李四",
                asset_id=assets[1].id if len(assets) > 1 else None,
                creator_id=admin.id if admin else None,
            ),
            Ticket(
                title="SSL 证书续期",
               description="api.example.com 证书将在 7 天后到期，需要续期并部署",
                priority="critical",
                status="open",
                assignee="王五",
                asset_id=None,
                creator_id=admin.id if admin else None,
            ),
        ]
    )


def _seed_alerts(db: Session) -> None:
    existing = db.scalar(select(Alert).limit(1))
    if existing:
        return

    assets = list(db.scalars(select(Asset)).all())

    db.add_all(
        [
            Alert(
                title="CPU 使用率过高",
                description="web-prod-01 CPU 使用率持续超过 90%，已持续 15 分钟",
                level="high",
                status="confirmed",
                source="监控系统",
                asset_id=assets[0].id if assets else None,
            ),
            Alert(
                title="磁盘空间不足",
                description="db-prod-01 /data 分区使用率已达 92%",
                level="medium",
                status="pending",
                source="监控系统",
                asset_id=assets[1].id if len(assets) > 1 else None,
            ),
            Alert(
                title="SSL 证书即将到期",
                description="api.example.com 的 SSL 证书将在 7 天后到期",
                level="low",
                status="pending",
                source="证书巡检",
                asset_id=None,
            ),
        ]
    )
