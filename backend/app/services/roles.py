from collections import defaultdict

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.rbac import Permission, Role
from app.models.user import User


DEFAULT_ROLE_PERMISSION_CODES = {
    "viewer": ["dashboard.view", "reports.view", "assets.view", "containers.view", "monitoring.view", "users.view", "roles.view", "tickets.view", "alerts.view", "audit.view"],
    "asset_admin": [
        "dashboard.view",
        "reports.view",
        "assets.view",
        "containers.view",
        "monitoring.view",
        "assets.create",
        "assets.update",
        "users.view",
        "roles.view",
        "tickets.view",
        "alerts.view",
        "audit.view",
    ],
}


def list_roles(
    db: Session,
    *,
    keyword: str = "",
    system_only: bool = False,
) -> list[Role]:
    stmt = select(Role).options(selectinload(Role.permissions), selectinload(Role.users))
    keyword = keyword.strip()

    if keyword:
        like_value = f"%{keyword}%"
        stmt = stmt.where(
            or_(Role.name.ilike(like_value), Role.code.ilike(like_value), Role.description.ilike(like_value))
        )
    if system_only:
        stmt = stmt.where(Role.is_system.is_(True))

    stmt = stmt.order_by(Role.id.desc())
    return list(db.scalars(stmt).unique().all())


def count_users_by_role(db: Session) -> list[tuple[Role, int]]:
    stmt = (
        select(Role, func.count(User.id))
        .outerjoin(Role.users)
        .options(selectinload(Role.permissions), selectinload(Role.users))
        .group_by(Role.id)
        .order_by(func.count(User.id).desc(), Role.id.asc())
    )
    return list(db.execute(stmt).all())


def list_permissions(db: Session) -> list[Permission]:
    stmt = select(Permission).order_by(Permission.module.asc(), Permission.id.asc())
    return list(db.scalars(stmt).all())


def get_role(db: Session, role_id: int) -> Role | None:
    stmt = select(Role).options(selectinload(Role.permissions), selectinload(Role.users)).where(Role.id == role_id)
    return db.scalar(stmt)


def get_role_by_code(db: Session, code: str) -> Role | None:
    stmt = select(Role).options(selectinload(Role.permissions), selectinload(Role.users)).where(Role.code == code)
    return db.scalar(stmt)


def get_role_by_name(db: Session, name: str) -> Role | None:
    stmt = select(Role).options(selectinload(Role.permissions), selectinload(Role.users)).where(Role.name == name)
    return db.scalar(stmt)


def group_permissions_by_module(permissions: list[Permission]) -> list[tuple[str, list[Permission]]]:
    groups: dict[str, list[Permission]] = defaultdict(list)
    for permission in permissions:
        groups[permission.module].append(permission)
    return [(module, groups[module]) for module in sorted(groups.keys())]


def create_role(
    db: Session,
    *,
    name: str,
    code: str,
    description: str,
    permission_ids: list[int],
) -> Role:
    permissions = _get_permissions_by_ids(db, permission_ids)
    role = Role(name=name, code=code, description=description, permissions=permissions)
    db.add(role)
    db.commit()
    db.refresh(role)
    return get_role(db, role.id) or role


def update_role(
    db: Session,
    role: Role,
    *,
    name: str,
    code: str,
    description: str,
    permission_ids: list[int],
) -> Role:
    role.name = name
    role.code = code
    role.description = description
    role.permissions = _get_permissions_by_ids(db, permission_ids)
    db.commit()
    db.refresh(role)
    return get_role(db, role.id) or role


def delete_role(db: Session, role: Role) -> None:
    db.delete(role)
    db.commit()


def sync_default_roles(db: Session) -> None:
    permissions_by_code = {item.code: item for item in list_permissions(db)}
    specs = [
        ("只读人员", "viewer", "只允许查看主要页面和数据"),
        ("资产管理员", "asset_admin", "负责资产日常维护"),
    ]
    for name, code, description in specs:
        role = get_role_by_code(db, code)
        if role is None:
            role = Role(name=name, code=code, description=description, is_system=True)
            db.add(role)
            db.flush()
        role.permissions = [
            permissions_by_code[item_code]
            for item_code in DEFAULT_ROLE_PERMISSION_CODES.get(code, [])
            if item_code in permissions_by_code
        ]


def _get_permissions_by_ids(db: Session, permission_ids: list[int]) -> list[Permission]:
    if not permission_ids:
        return []
    stmt = select(Permission).where(Permission.id.in_(permission_ids)).order_by(Permission.id.asc())
    return list(db.scalars(stmt).all())


# ── 权限树构建 ──

PERMISSION_LABELS = {
    "dashboard": "仪表盘",
    "reports": "报表中心",
    "assets": "主机管理",
    "containers": "容器管理",
    "tickets": "工单协作",
    "alerts": "告警中心",
    "monitoring": "监控指标",
    "monitoring_host": "主机监控",
    "users": "用户管理",
    "roles": "角色权限",
    "audit": "审计日志",
    "settings": "配置中心",
    "batch_exec": "批量执行",
    "patrol": "巡检中心",
}


def build_permission_tree(permissions):
    """构建三级权限树：父页面 -> 子页面 -> 功能。"""
    MODULE_PARENT = {
        "dashboard": ("报表大屏", 1),
        "reports": ("报表大屏", 1),
        "assets": ("资产管理", 2),
        "containers": ("资产管理", 2),
        "monitoring": ("监控告警", 3),
        "tickets": ("工单协作", 4),
        "alerts": ("告警中心", 5),
        "users": ("用户管理", 6),
        "roles": ("用户管理", 6),
        "audit": ("系统管理", 7),
        "settings": ("系统管理", 7),
        "batch_exec": ("批量执行", 8),
        "patrol": ("巡检中心", 9),
    }
    PARENT_ORDER = {"报表大屏": 1, "资产管理": 2, "监控告警": 3, "工单协作": 4, "告警中心": 5, "用户管理": 6, "系统管理": 7, "批量执行": 8, "巡检中心": 9}

    children: dict[str, dict[str, list]] = {}
    child_order: dict[str, list[str]] = {}
    for perm in permissions:
        parent, _ = MODULE_PARENT.get(perm.module, (perm.module, 99))
        if parent not in children:
            children[parent] = {}
            child_order[parent] = []
        if perm.module not in children[parent]:
            children[parent][perm.module] = []
            child_order[parent].append(perm.module)
        children[parent][perm.module].append(perm)

    tree = []
    for parent_name in sorted(children.keys(), key=lambda x: PARENT_ORDER.get(x, 99)):
        child_modules = []
        for mod in child_order[parent_name]:
            child_modules.append({
                "module": mod,
                "label": PERMISSION_LABELS.get(mod, mod),
                "permissions": children[parent_name][mod],
            })
        tree.append({"parent": parent_name, "children": child_modules})
    return tree
