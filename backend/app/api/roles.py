"""角色权限 API。"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import api_permission_required
from app.db.database import get_db
from app.models.user import User
from app.services.audit import write_log
from app.services.roles import (
    PERMISSION_LABELS,
    _get_permissions_by_ids,
    build_permission_tree,
    create_role,
    delete_role,
    get_role,
    get_role_by_code,
    get_role_by_name,
    list_permissions,
    list_roles,
    update_role,
)

router = APIRouter(prefix="/roles", tags=["角色权限"])


class RoleCreate(BaseModel):
    name: str
    code: str
    description: str = ""


class RoleUpdate(BaseModel):
    name: str
    code: str
    description: str = ""


class PermissionAssign(BaseModel):
    permission_ids: list[int]


def _role_dict(r) -> dict:
    return {
        "id": r.id,
        "name": r.name,
        "code": r.code,
        "description": r.description,
        "is_system": r.is_system,
        "permissions": [{"id": p.id, "name": p.name, "code": p.code, "module": p.module} for p in r.permissions],
        "user_count": len(r.users),
        "created_at": r.created_at.isoformat(),
    }


@router.get("/")
def api_list_roles(
    keyword: str = "",
    system_only: bool = False,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("roles.view")),
):
    items = list_roles(db, keyword=keyword, system_only=system_only)
    return {
        "code": 0,
        "data": {
            "items": [_role_dict(r) for r in items],
            "total": len(items),
        },
    }


@router.post("/")
def api_create_role(
    body: RoleCreate,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("roles.create")),
):
    name = body.name.strip()
    code = body.code.strip()
    if get_role_by_name(db, name):
        raise HTTPException(status_code=400, detail="角色名称已存在")
    if get_role_by_code(db, code):
        raise HTTPException(status_code=400, detail="角色编码已存在")

    role = create_role(db, name=name, code=code, description=body.description.strip(), permission_ids=[])
    write_log(db, user=_, action="create", target_type="role", target_id=role.id, target_name=role.name, ip_address="")
    db.commit()
    return {"code": 0, "msg": "创建成功", "data": _role_dict(role)}


@router.get("/{role_id}")
def api_get_role(
    role_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("roles.view")),
):
    role = get_role(db, role_id)
    if role is None:
        raise HTTPException(status_code=404, detail="角色不存在")
    return {"code": 0, "data": _role_dict(role)}


@router.put("/{role_id}")
def api_update_role(
    role_id: int,
    body: RoleUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("roles.update")),
):
    role = get_role(db, role_id)
    if role is None:
        raise HTTPException(status_code=404, detail="角色不存在")

    name = body.name.strip()
    code = body.code.strip()
    dup_name = get_role_by_name(db, name)
    if dup_name and dup_name.id != role.id:
        raise HTTPException(status_code=400, detail="角色名称已存在")
    dup_code = get_role_by_code(db, code)
    if dup_code and dup_code.id != role.id:
        raise HTTPException(status_code=400, detail="角色编码已存在")
    if role.is_system and role.code != code:
        raise HTTPException(status_code=400, detail="系统内置角色不允许修改编码")

    update_role(db, role, name=name, code=code, description=body.description.strip(), permission_ids=[p.id for p in role.permissions])
    write_log(db, user=_, action="update", target_type="role", target_id=role.id, target_name=role.name, ip_address="")
    db.commit()
    return {"code": 0, "msg": "更新成功", "data": _role_dict(role)}


@router.delete("/{role_id}")
def api_delete_role(
    role_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("roles.delete")),
):
    role = get_role(db, role_id)
    if role is None:
        raise HTTPException(status_code=404, detail="角色不存在")
    if role.is_system:
        raise HTTPException(status_code=400, detail="系统内置角色不可删除")
    if role.users:
        raise HTTPException(status_code=400, detail="该角色下还有用户，无法删除")

    write_log(db, user=_, action="delete", target_type="role", target_id=role.id, target_name=role.name, ip_address="")
    delete_role(db, role)
    db.commit()
    return {"code": 0, "msg": "删除成功"}


@router.put("/{role_id}/permissions")
def api_assign_permissions(
    role_id: int,
    body: PermissionAssign,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("roles.update")),
):
    role = get_role(db, role_id)
    if role is None:
        raise HTTPException(status_code=404, detail="角色不存在")
    if role.code == "super_admin":
        raise HTTPException(status_code=400, detail="超级管理员不允许调整权限")

    role.permissions = _get_permissions_by_ids(db, body.permission_ids)
    write_log(db, user=_, action="update", target_type="role", target_id=role.id, target_name=role.name, detail="分配菜单权限", ip_address="")
    db.commit()
    return {"code": 0, "msg": "权限分配成功", "data": _role_dict(role)}


@router.get("/meta/permission-tree")
def api_permission_tree(
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("roles.view")),
):
    """获取权限树结构（给分配菜单弹窗用）。"""
    permissions = list_permissions(db)
    tree = build_permission_tree(permissions)
    return {"code": 0, "data": tree}
