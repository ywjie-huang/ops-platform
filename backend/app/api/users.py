"""用户管理 API。"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import api_permission_required, get_client_ip, get_current_api_user
from app.db.database import get_db
from app.models.user import User
from app.services.audit import write_log
from app.services.roles import list_roles
from app.services.users import (
    change_password,
    create_user,
    delete_user,
    get_user,
    get_user_by_username,
    list_users,
    update_user,
)

router = APIRouter(prefix="/users", tags=["用户管理"])


class UserCreate(BaseModel):
    username: str
    full_name: str
    password: str
    role_ids: list[int] = []


class UserUpdate(BaseModel):
    username: str
    full_name: str
    password: str = ""
    role_ids: list[int] = []


def _user_dict(u: User) -> dict:
    return {
        "id": u.id,
        "username": u.username,
        "full_name": u.full_name,
        "roles": [{"id": r.id, "name": r.name} for r in u.roles],
        "created_at": u.created_at.isoformat(),
    }


@router.get("/")
def api_list_users(
    keyword: str = "",
    role_id: int | None = None,
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("users.view")),
):
    items = list_users(db, keyword=keyword, role_id=role_id)
    total = len(items)
    start = (max(page, 1) - 1) * page_size
    return {
        "code": 0,
        "data": {
            "items": [_user_dict(u) for u in items[start:start + page_size]],
            "total": total,
            "page": page,
            "page_size": page_size,
        },
    }


@router.post("/")
def api_create_user(
    body: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("users.create")),
):
    username = body.username.strip()
    full_name = body.full_name.strip()
    if get_user_by_username(db, username):
        raise HTTPException(status_code=400, detail="用户名已存在")

    user = create_user(db, username=username, full_name=full_name, password=body.password, role_ids=body.role_ids)
    write_log(db, user=_, action="create", target_type="user", target_id=user.id, target_name=user.username, ip_address=get_client_ip(request))
    db.commit()
    return {"code": 0, "msg": "创建成功", "data": _user_dict(user)}


@router.get("/{user_id}")
def api_get_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("users.view")),
):
    user = get_user(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {"code": 0, "data": _user_dict(user)}


@router.put("/{user_id}")
def api_update_user(
    user_id: int,
    body: UserUpdate,
    request: Request,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("users.update")),
):
    user = get_user(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")

    username = body.username.strip()
    full_name = body.full_name.strip()
    duplicate = get_user_by_username(db, username)
    if duplicate and duplicate.id != user.id:
        raise HTTPException(status_code=400, detail="用户名已存在")

    update_user(db, user, username=username, full_name=full_name, password=body.password, role_ids=body.role_ids)
    write_log(db, user=_, action="update", target_type="user", target_id=user.id, target_name=user.username, ip_address=get_client_ip(request))
    db.commit()
    return {"code": 0, "msg": "更新成功", "data": _user_dict(user)}


@router.delete("/{user_id}")
def api_delete_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("users.delete")),
):
    user = get_user(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="不能删除自己")

    write_log(db, user=current_user, action="delete", target_type="user", target_id=user.id, target_name=user.username, ip_address=get_client_ip(request))
    delete_user(db, user)
    db.commit()
    return {"code": 0, "msg": "删除成功"}


@router.get("/meta/roles")
def api_user_roles(
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("users.view")),
):
    """获取角色列表（给用户表单用）。"""
    roles = list_roles(db)
    return {
        "code": 0,
        "data": [{"id": r.id, "name": r.name, "code": r.code, "description": r.description} for r in roles],
    }
