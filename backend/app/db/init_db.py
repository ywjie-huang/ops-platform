import logging
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

logger = logging.getLogger(__name__)
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


def _ensure_asset_ssh_columns() -> None:
    """为 assets 表补充 SSH 相关字段（兼容旧库）。"""
    conn = pymysql.connect(
        host=MYSQL_HOST, port=MYSQL_PORT, user=MYSQL_USER, password=MYSQL_PASSWORD, database=MYSQL_DATABASE,
    )
    try:
        with conn.cursor() as cur:
            cur.execute("SHOW COLUMNS FROM assets LIKE 'ssh_port'")
            if cur.fetchone() is None:
                cur.execute("ALTER TABLE assets ADD COLUMN ssh_port INT NOT NULL DEFAULT 22")
                cur.execute("ALTER TABLE assets ADD COLUMN ssh_username VARCHAR(100) NOT NULL DEFAULT 'root'")
                cur.execute("ALTER TABLE assets ADD COLUMN ssh_password VARCHAR(200) NOT NULL DEFAULT ''")
            cur.execute("SHOW COLUMNS FROM assets LIKE 'spec'")
            if cur.fetchone() is None:
                cur.execute("ALTER TABLE assets ADD COLUMN spec VARCHAR(100) NOT NULL DEFAULT ''")
                cur.execute("ALTER TABLE assets ADD COLUMN os VARCHAR(100) NOT NULL DEFAULT ''")
            cur.execute("SHOW COLUMNS FROM assets LIKE 'ssh_key_id'")
            if cur.fetchone() is None:
                cur.execute("ALTER TABLE assets ADD COLUMN ssh_key_id INT NULL DEFAULT NULL")
            # 修复外键约束：删除资产时自动置空关联的告警/工单
            for tbl, fk_name in [('alerts', 'alerts_ibfk_1'), ('tickets', 'tickets_ibfk_1')]:
                try:
                    cur.execute(f"SHOW CREATE TABLE {tbl}")
                    create_sql = cur.fetchone()[1]
                    if 'ON DELETE SET NULL' not in create_sql and fk_name in create_sql:
                        cur.execute(f"ALTER TABLE {tbl} DROP FOREIGN KEY {fk_name}")
                        cur.execute(f"ALTER TABLE {tbl} ADD CONSTRAINT {fk_name} FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE SET NULL")
                except Exception as e:
                    logger.debug('FK alter skipped: %s', e)
            conn.commit()
    finally:
        conn.close()


def _ensure_container_token_column() -> None:
    """为 container_clusters 表补充 token / status_message 字段（兼容旧库）。"""
    try:
        conn = pymysql.connect(
            host=MYSQL_HOST, port=MYSQL_PORT, user=MYSQL_USER, password=MYSQL_PASSWORD, database=MYSQL_DATABASE,
        )
        with conn.cursor() as cur:
            cur.execute("SHOW TABLES LIKE 'container_clusters'")
            if cur.fetchone() is None:
                conn.commit()
                return  # 表还不存在，create_all 会按新模型创建
            cur.execute("SHOW COLUMNS FROM container_clusters LIKE 'token'")
            if cur.fetchone() is None:
                cur.execute("ALTER TABLE container_clusters ADD COLUMN token VARCHAR(4000) NOT NULL DEFAULT ''")
                print('[init_db] Added token column to container_clusters')
            cur.execute("SHOW COLUMNS FROM container_clusters LIKE 'status_message'")
            if cur.fetchone() is None:
                cur.execute("ALTER TABLE container_clusters ADD COLUMN status_message VARCHAR(512) NOT NULL DEFAULT ''")
                print('[init_db] Added status_message column to container_clusters')
            conn.commit()
    except Exception as e:
        print(f'[init_db] _ensure_container_token_column error: {e}')
    finally:
        conn.close()


def _ensure_docker_columns() -> None:
    """为 container_clusters 表补充 Docker Agent 字段 + 创建 docker_containers 表（兼容旧库）。"""
    try:
        conn = pymysql.connect(
            host=MYSQL_HOST, port=MYSQL_PORT, user=MYSQL_USER, password=MYSQL_PASSWORD, database=MYSQL_DATABASE,
        )
        with conn.cursor() as cur:
            # container_clusters 新增字段
            cur.execute("SHOW TABLES LIKE 'container_clusters'")
            if cur.fetchone() is not None:
                for col, col_def in [
                    ('agent_key', "VARCHAR(1024) NOT NULL DEFAULT ''"),
                    ('last_heartbeat', 'DATETIME NULL'),
                    ('host_os', "VARCHAR(128) NOT NULL DEFAULT ''"),
                    ('host_ip', "VARCHAR(64) NOT NULL DEFAULT ''"),
                    ('docker_version', "VARCHAR(32) NOT NULL DEFAULT ''"),
                ]:
                    cur.execute(f"SHOW COLUMNS FROM container_clusters LIKE '{col}'")
                    if cur.fetchone() is None:
                        cur.execute(f"ALTER TABLE container_clusters ADD COLUMN {col} {col_def}")
                        print(f'[init_db] Added {col} column to container_clusters')

                # 兼容旧库：agent_key 列可能被早期版本创建为较小的 VARCHAR，扩容到 1024
                cur.execute("SHOW COLUMNS FROM container_clusters LIKE 'agent_key'")
                row = cur.fetchone()
                if row and 'varchar' in (row[1] or '').lower():
                    cur.execute("SELECT CHARACTER_MAXIMUM_LENGTH FROM information_schema.COLUMNS "
                                "WHERE TABLE_SCHEMA=%s AND TABLE_NAME='container_clusters' AND COLUMN_NAME='agent_key'",
                                (MYSQL_DATABASE,))
                    size_row = cur.fetchone()
                    if size_row and (size_row[0] or 0) < 1024:
                        cur.execute("ALTER TABLE container_clusters MODIFY COLUMN agent_key VARCHAR(1024) NOT NULL DEFAULT ''")
                        print(f'[init_db] Expanded agent_key column from {size_row[0]} to VARCHAR(1024)')

            # 创建 docker_containers 表
            cur.execute("SHOW TABLES LIKE 'docker_containers'")
            if cur.fetchone() is None:
                cur.execute("""
                    CREATE TABLE docker_containers (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        host_id INT NOT NULL,
                        container_id VARCHAR(64) NOT NULL,
                        name VARCHAR(256) NOT NULL DEFAULT '',
                        image VARCHAR(512) NOT NULL DEFAULT '',
                        status VARCHAR(32) NOT NULL DEFAULT 'running',
                        state VARCHAR(32) NOT NULL DEFAULT '',
                        ports VARCHAR(512) NOT NULL DEFAULT '',
                        cpu_percent FLOAT NOT NULL DEFAULT 0,
                        memory_usage BIGINT NOT NULL DEFAULT 0,
                        memory_limit BIGINT NOT NULL DEFAULT 0,
                        memory_percent FLOAT NOT NULL DEFAULT 0,
                        net_rx_bytes BIGINT NOT NULL DEFAULT 0,
                        net_tx_bytes BIGINT NOT NULL DEFAULT 0,
                        block_read BIGINT NOT NULL DEFAULT 0,
                        block_write BIGINT NOT NULL DEFAULT 0,
                        restart_count INT NOT NULL DEFAULT 0,
                        started_at VARCHAR(64) NOT NULL DEFAULT '',
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        FOREIGN KEY (host_id) REFERENCES container_clusters(id) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)
                print('[init_db] Created docker_containers table')

            # 兼容旧库：INT 字段扩容为 BIGINT（容器内存/网络/磁盘字节可能超过 INT 上限）
            cur.execute("SHOW TABLES LIKE 'docker_containers'")
            if cur.fetchone() is not None:
                for col in ['memory_usage', 'memory_limit', 'net_rx_bytes', 'net_tx_bytes', 'block_read', 'block_write']:
                    cur.execute("SELECT DATA_TYPE FROM information_schema.COLUMNS "
                                "WHERE TABLE_SCHEMA=%s AND TABLE_NAME='docker_containers' AND COLUMN_NAME=%s",
                                (MYSQL_DATABASE, col))
                    row = cur.fetchone()
                    if row and row[0] == 'int':
                        cur.execute(f"ALTER TABLE docker_containers MODIFY COLUMN {col} BIGINT NOT NULL DEFAULT 0")
                        print(f'[init_db] Expanded {col} from INT to BIGINT')

            conn.commit()
    except Exception as e:
        print(f'[init_db] _ensure_docker_columns error: {e}')
    finally:
        conn.close()


def init_db() -> None:
    _ensure_database()
    Base.metadata.create_all(bind=engine)
    _ensure_asset_ssh_columns()
    _ensure_container_token_column()
    _ensure_docker_columns()

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
        ("查看监控", "monitoring.view", "monitoring", "查看主机监控和告警规则"),
        ("查看配置", "settings.view", "settings", "查看系统配置"),
        ("编辑配置", "settings.update", "settings", "修改系统配置"),
        ("查看批量执行", "batch_exec.view", "batch_exec", "查看批量执行和历史"),
        ("执行批量命令", "batch_exec.execute", "batch_exec", "执行批量命令"),
        ("删除执行记录", "batch_exec.delete", "batch_exec", "删除批量执行记录"),
        ("查看巡检", "patrol.view", "patrol", "查看巡检报告"),
        ("执行巡检", "patrol.execute", "patrol", "手动触发巡检"),
        ("删除巡检报告", "patrol.delete", "patrol", "删除巡检报告"),
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
                status="使用中",
                owner="平台组",
                spec="4C8G",
                os="Ubuntu 22.04",
                description="核心业务 Web 节点",
            ),
            Asset(
                name="db-prod-01",
                asset_type="数据库",
                ip_address="10.10.1.21",
                status="使用中",
                owner="DBA",
                spec="8C16G",
                os="CentOS 7.9",
                description="主数据库实例",
            ),
            Asset(
                name="waf-gateway",
                asset_type="网络设备",
                ip_address="10.10.1.2",
                status="已关机",
                owner="安全组",
                spec="2C4G",
                os="Debian 11",
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
