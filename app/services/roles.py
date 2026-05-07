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
