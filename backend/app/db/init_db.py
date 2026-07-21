import logging
from pathlib import Path

import pymysql
from passlib.context import CryptContext
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import DEMO_PASSWORD, DEMO_USERNAME, MYSQL_DATABASE, MYSQL_HOST, MYSQL_PASSWORD, MYSQL_PORT, MYSQL_USER
from app.db.database import Base, engine
from app.models.asset import Asset, generate_asset_public_id
from app.models.deploy import DeployAppEnv, DeployApproval, DeployApplication, DeployBuild, DeployConfig, DeployEnvironment, DeployRecord
from app.models.rbac import Permission, Role
from app.models.ticket import Ticket
from app.models.conversation import Conversation, Message
from app.models.user import User

logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

USER_DELETE_SET_NULL_FOREIGN_KEYS = (
    ("audit_logs", "user_id", "users", "id"),
    ("conversations", "user_id", "users", "id"),
    ("deploy_applications", "creator_id", "users", "id"),
    ("deploy_records", "trigger_user_id", "users", "id"),
    ("deploy_approvals", "approver_id", "users", "id"),
    ("tickets", "creator_id", "users", "id"),
)

USER_DELETE_CASCADE_FOREIGN_KEYS = (
    ("user_roles", "user_id", "users", "id"),
)


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


def _ensure_asset_public_ids() -> None:
    """Backfill stable public identifiers for assets created by older versions."""
    conn = pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
    )
    try:
        with conn.cursor() as cur:
            cur.execute("SHOW COLUMNS FROM assets LIKE 'public_id'")
            if cur.fetchone() is None:
                cur.execute("ALTER TABLE assets ADD COLUMN public_id VARCHAR(36) NULL")

            cur.execute("SELECT id FROM assets WHERE public_id IS NULL OR public_id = ''")
            for (asset_id,) in cur.fetchall():
                cur.execute(
                    "UPDATE assets SET public_id = %s WHERE id = %s",
                    (generate_asset_public_id(), asset_id),
                )

            cur.execute("ALTER TABLE assets MODIFY COLUMN public_id VARCHAR(36) NOT NULL")
            cur.execute("SHOW INDEX FROM assets WHERE Column_name = 'public_id'")
            if cur.fetchone() is None:
                cur.execute(
                    "CREATE UNIQUE INDEX ux_assets_public_id ON assets (public_id)"
                )
        conn.commit()
    finally:
        conn.close()


def _ensure_user_delete_foreign_keys() -> None:
    """Keep historical records when users are deleted."""
    conn = None
    try:
        conn = pymysql.connect(
            host=MYSQL_HOST, port=MYSQL_PORT, user=MYSQL_USER, password=MYSQL_PASSWORD, database=MYSQL_DATABASE,
        )
        with conn.cursor() as cur:
            for table_name, column_name, ref_table, ref_column in USER_DELETE_SET_NULL_FOREIGN_KEYS:
                _ensure_foreign_key_delete_rule(cur, table_name, column_name, ref_table, ref_column, "SET NULL")
            for table_name, column_name, ref_table, ref_column in USER_DELETE_CASCADE_FOREIGN_KEYS:
                _ensure_foreign_key_delete_rule(cur, table_name, column_name, ref_table, ref_column, "CASCADE")
            conn.commit()
    except Exception as e:
        logger.warning("[init_db] _ensure_user_delete_foreign_keys skipped: %s", e)
    finally:
        if conn is not None:
            conn.close()


def _ensure_foreign_key_delete_rule(
    cur,
    table_name: str,
    column_name: str,
    ref_table: str,
    ref_column: str,
    delete_rule: str,
) -> None:
    cur.execute("SHOW TABLES LIKE %s", (table_name,))
    if cur.fetchone() is None:
        return

    cur.execute(f"SHOW COLUMNS FROM `{table_name}` LIKE %s", (column_name,))
    if cur.fetchone() is None:
        return

    cur.execute(
        """
        SELECT rc.CONSTRAINT_NAME, rc.DELETE_RULE
        FROM information_schema.KEY_COLUMN_USAGE kcu
        JOIN information_schema.REFERENTIAL_CONSTRAINTS rc
          ON rc.CONSTRAINT_SCHEMA = kcu.CONSTRAINT_SCHEMA
         AND rc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
        WHERE kcu.CONSTRAINT_SCHEMA = %s
          AND kcu.TABLE_NAME = %s
          AND kcu.COLUMN_NAME = %s
          AND kcu.REFERENCED_TABLE_NAME = %s
          AND kcu.REFERENCED_COLUMN_NAME = %s
        LIMIT 1
        """,
        (MYSQL_DATABASE, table_name, column_name, ref_table, ref_column),
    )
    row = cur.fetchone()
    constraint_name = row[0] if row else f"fk_{table_name}_{column_name}_{ref_table}_{ref_column}"
    if row and row[1] == delete_rule:
        return

    if row:
        cur.execute(f"ALTER TABLE `{table_name}` DROP FOREIGN KEY `{constraint_name}`")
    cur.execute(
        f"ALTER TABLE `{table_name}` "
        f"ADD CONSTRAINT `{constraint_name}` FOREIGN KEY (`{column_name}`) "
        f"REFERENCES `{ref_table}`(`{ref_column}`) ON DELETE {delete_rule}"
    )
    print(f"[init_db] Updated {table_name}.{column_name} FK ON DELETE {delete_rule}")


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


def _ensure_deploy_artifact_columns() -> None:
    """为 deploy_applications / deploy_app_envs 表补充产物字段，并将旧 local 模式迁移为 upload。"""
    try:
        conn = pymysql.connect(
            host=MYSQL_HOST, port=MYSQL_PORT, user=MYSQL_USER, password=MYSQL_PASSWORD, database=MYSQL_DATABASE,
        )
        with conn.cursor() as cur:
            # deploy_applications: 产物元数据
            cur.execute("SHOW TABLES LIKE 'deploy_applications'")
            if cur.fetchone() is not None:
                for col, col_def in [
                    ('artifact_filename', "VARCHAR(255) NOT NULL DEFAULT ''"),
                    ('artifact_size', "INT NOT NULL DEFAULT 0"),
                    ('artifact_uploaded_at', 'DATETIME NULL'),
                ]:
                    cur.execute(f"SHOW COLUMNS FROM deploy_applications LIKE '{col}'")
                    if cur.fetchone() is None:
                        cur.execute(f"ALTER TABLE deploy_applications ADD COLUMN {col} {col_def}")
                        print(f'[init_db] Added {col} to deploy_applications')

                cur.execute("UPDATE deploy_applications SET build_mode='upload' WHERE build_mode='local'")

            # deploy_app_envs: 环境级产物字段 + 健康检查
            cur.execute("SHOW TABLES LIKE 'deploy_app_envs'")
            if cur.fetchone() is not None:
                for col, col_def in [
                    ('health_check_url', "VARCHAR(500) NOT NULL DEFAULT ''"),
                    ('health_check_port', "INT NOT NULL DEFAULT 0"),
                    ('health_check_timeout', "INT NOT NULL DEFAULT 30"),
                    ('artifact_path', "VARCHAR(500) NOT NULL DEFAULT ''"),
                    ('artifact_filename', "VARCHAR(255) NOT NULL DEFAULT ''"),
                    ('artifact_size', "INT NOT NULL DEFAULT 0"),
                    ('artifact_uploaded_at', 'DATETIME NULL'),
                ]:
                    cur.execute(f"SHOW COLUMNS FROM deploy_app_envs LIKE '{col}'")
                    if cur.fetchone() is None:
                        cur.execute(f"ALTER TABLE deploy_app_envs ADD COLUMN {col} {col_def}")
                        print(f'[init_db] Added {col} to deploy_app_envs')

            # Migrate health check fields from app level to env level (one-time)
            cur.execute("SHOW TABLES LIKE 'deploy_applications'")
            if cur.fetchone() is not None:
                for old_col in ('health_check_port', 'health_check_url', 'health_check_timeout'):
                    cur.execute(f"SHOW COLUMNS FROM deploy_applications LIKE '{old_col}'")
                    if cur.fetchone() is not None:
                        if old_col == 'health_check_port':
                            cur.execute(
                                "UPDATE deploy_app_envs ae "
                                "JOIN deploy_applications a ON ae.app_id = a.id "
                                "SET ae.health_check_port = a.health_check_port "
                                "WHERE a.health_check_port > 0 AND ae.health_check_port = 0"
                            )
                        elif old_col == 'health_check_url':
                            cur.execute(
                                "UPDATE deploy_app_envs ae "
                                "JOIN deploy_applications a ON ae.app_id = a.id "
                                "SET ae.health_check_url = a.health_check_url "
                                "WHERE a.health_check_url != '' AND ae.health_check_url = ''"
                            )
                        elif old_col == 'health_check_timeout':
                            cur.execute(
                                "UPDATE deploy_app_envs ae "
                                "JOIN deploy_applications a ON ae.app_id = a.id "
                                "SET ae.health_check_timeout = a.health_check_timeout "
                                "WHERE a.health_check_timeout != 30 AND ae.health_check_timeout = 30"
                            )
                        cur.execute(f"ALTER TABLE deploy_applications DROP COLUMN {old_col}")
                        print(f'[init_db] Migrated {old_col} from deploy_applications to deploy_app_envs')

            conn.commit()
    except Exception as e:
        print(f'[init_db] _ensure_deploy_artifact_columns error: {e}')
    finally:
        conn.close()


def _ensure_deploy_tables() -> None:
    """确保应用发布相关表存在（模型定义即真相，create_all 只建缺失的表）。"""
    try:
        from app.models.deploy import (
            DeployApplication, DeployEnvironment, DeployAppEnv,
            DeployRecord, DeployApproval, DeployConfig, DeployBuild,
        )
        Base.metadata.create_all(bind=engine, tables=[
            DeployEnvironment.__table__,
            DeployApplication.__table__,
            DeployAppEnv.__table__,
            DeployRecord.__table__,
            DeployApproval.__table__,
            DeployConfig.__table__,
            DeployBuild.__table__,
        ])
        print('[init_db] Verified deploy tables exist')
    except Exception as e:
        print(f'[init_db] _ensure_deploy_tables error: {e}')


def _ensure_webhook_columns() -> None:
    """为 deploy_applications 表补充 webhook_secret 字段，为 deploy_builds 表补充新字段（兼容旧库）。"""
    try:
        conn = pymysql.connect(
            host=MYSQL_HOST, port=MYSQL_PORT, user=MYSQL_USER, password=MYSQL_PASSWORD, database=MYSQL_DATABASE,
        )
        with conn.cursor() as cur:
            # deploy_applications: webhook_secret 字段
            cur.execute("SHOW TABLES LIKE 'deploy_applications'")
            if cur.fetchone() is not None:
                cur.execute("SHOW COLUMNS FROM deploy_applications LIKE 'webhook_secret'")
                if cur.fetchone() is None:
                    cur.execute("ALTER TABLE deploy_applications ADD COLUMN webhook_secret VARCHAR(64) NOT NULL DEFAULT ''")
                    print('[init_db] Added webhook_secret to deploy_applications')

            # deploy_builds: 新字段
            cur.execute("SHOW TABLES LIKE 'deploy_builds'")
            if cur.fetchone() is not None:
                for col, col_def in [
                    ('tag', "VARCHAR(100) NOT NULL DEFAULT ''"),
                    ('is_pinned', 'TINYINT(1) NOT NULL DEFAULT 0'),
                    ('deployed_at', 'DATETIME NULL'),
                    ('deploy_count', 'INT NOT NULL DEFAULT 0'),
                ]:
                    cur.execute(f"SHOW COLUMNS FROM deploy_builds LIKE '{col}'")
                    if cur.fetchone() is None:
                        cur.execute(f"ALTER TABLE deploy_builds ADD COLUMN {col} {col_def}")
                        print(f'[init_db] Added {col} to deploy_builds')

            conn.commit()
    except Exception as e:
        print(f'[init_db] _ensure_webhook_columns error: {e}')
    finally:
        conn.close()


def _seed_deploy_environments(db: Session) -> None:
    """种子数据：3 个默认环境（dev / staging / prod）。"""
    env_specs = [
        ("dev", "开发环境", "开发", False, 1),
        ("staging", "预发布环境", "预发布", False, 2),
        ("prod", "生产环境", "生产", True, 3),
    ]
    for name, desc, display, approval, sort in env_specs:
        existing = db.scalar(select(DeployEnvironment).where(DeployEnvironment.name == name))
        if existing is None:
            db.add(DeployEnvironment(
                name=name,
                display_name=display,
                description=desc,
                approval_required=approval,
                sort_order=sort,
            ))
    db.flush()


def init_db() -> None:
    _ensure_database()
    Base.metadata.create_all(bind=engine)
    _ensure_asset_public_ids()
    _ensure_asset_ssh_columns()
    _ensure_container_token_column()
    _ensure_docker_columns()
    _ensure_deploy_tables()
    _ensure_user_delete_foreign_keys()
    _ensure_deploy_artifact_columns()
    _ensure_webhook_columns()

    with Session(engine) as db:
        _seed_permissions(db)
        _seed_users(db)
        _seed_admin_permissions(db)
        _seed_assets(db)
        _seed_tickets(db)
        _seed_deploy_environments(db)
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
        ("查看主机密钥", "ssh_keys.view", "ssh_keys", "查看主机密钥列表"),
        ("新增主机密钥", "ssh_keys.create", "ssh_keys", "新增主机密钥"),
        ("编辑主机密钥", "ssh_keys.update", "ssh_keys", "编辑主机密钥"),
        ("删除主机密钥", "ssh_keys.delete", "ssh_keys", "删除主机密钥"),
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
        # 应用发布模块
        ("查看应用发布", "deploy.view", "deploy", "查看应用列表和部署记录"),
        ("创建应用", "deploy.create", "deploy", "创建和导入应用"),
        ("编辑应用", "deploy.update", "deploy", "编辑应用配置和环境"),
        ("删除应用", "deploy.delete", "deploy", "删除应用及关联数据"),
        ("执行部署", "deploy.execute", "deploy", "触发部署执行"),
        ("审批部署", "deploy.approve", "deploy", "审批待审批的部署"),
        ("回滚部署", "deploy.rollback", "deploy", "回滚到历史部署版本"),
        ("管理配置", "deploy.config", "deploy", "管理应用环境变量和配置项"),
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
