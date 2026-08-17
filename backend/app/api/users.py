"""用户管理 API。"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import api_permission_required, get_client_ip
from app.db.database import get_db
from app.models.user import User
from app.services.audit import write_log
from app.services.roles import list_roles
from app.services.users import (
    create_user,
    delete_user,
    get_user,
    get_user_activity,
    get_user_by_username,
    get_user_stats,
    list_users,
    reset_user_password,
    update_user,
)

router = APIRouter(prefix="/users", tags=["用户管理"])


class UserCreate(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    full_name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=6, max_length=100)
    role_ids: list[int] = []


class UserUpdate(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    full_name: str = Field(min_length=1, max_length=100)
    role_ids: list[int] = []


class PasswordReset(BaseModel):
    password: str = Field(min_length=6, max_length=100)


def _user_dict(u: User, last_login_at: datetime | None = None) -> dict:
    return {
        "id": u.id,
        "username": u.username,
        "full_name": u.full_name,
        "roles": [{"id": r.id, "name": r.name} for r in u.roles],
        "created_at": u.created_at.isoformat() if u.created_at else None,
        "last_login_at": last_login_at.isoformat() if last_login_at else None,
    }


@router.get("/")
def api_list_users(
    keyword: str = "",
    role_id: int | None = None,
    activity: str = "",
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("users.view")),
):
    rows, total = list_users(
        db, keyword=keyword, role_id=role_id, activity=activity, page=page, page_size=page_size,
    )
    return {
        "code": 0,
        "data": {
            "items": [_user_dict(u, last_login) for u, last_login in rows],
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
    write_log(db, user=_, action="create", target_type="user", target_id=user.id, target_name=user.username,
              detail=f"创建用户，角色：{', '.join(r.name for r in user.roles) or '未分配'}",
              ip_address=get_client_ip(request))
    db.commit()
    return {"code": 0, "msg": "创建成功", "data": _user_dict(user)}


# 注意：/stats 必须注册在 /{user_id} 之前，否则 "stats" 会被当作 user_id 匹配
@router.get("/stats")
def api_user_stats(
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("users.view")),
):
    """用户管理页概览统计。"""
    return {"code": 0, "data": get_user_stats(db)}


@router.get("/meta/roles")
def api_user_roles(
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("users.view")),
):
    """获取角色列表（给用户表单用）。"""
    roles, _ = list_roles(db)
    return {
        "code": 0,
        "data": [{"id": r.id, "name": r.name, "code": r.code, "description": r.description} for r in roles],
    }


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

    update_user(db, user, username=username, full_name=full_name, role_ids=body.role_ids)
    write_log(db, user=_, action="update", target_type="user", target_id=user.id, target_name=user.username,
              detail=f"更新资料，角色：{', '.join(r.name for r in user.roles) or '未分配'}",
              ip_address=get_client_ip(request))
    db.commit()
    return {"code": 0, "msg": "更新成功", "data": _user_dict(user)}


@router.put("/{user_id}/password")
def api_reset_password(
    user_id: int,
    body: PasswordReset,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("users.update")),
):
    """管理员重置用户密码。"""
    user = get_user(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")

    ok, msg = reset_user_password(db, user, body.password)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)

    write_log(db, user=current_user, action="update", target_type="user", target_id=user.id,
              target_name=user.username, detail="管理员重置密码",
              ip_address=get_client_ip(request))
    db.commit()
    return {"code": 0, "msg": "密码已重置"}


@router.get("/{user_id}/activity")
def api_user_activity(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("users.view")),
):
    """用户活跃摘要：登录统计 + 最近动态（详情抽屉用）。"""
    user = get_user(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")

    activity = get_user_activity(db, user)
    return {
        "code": 0,
        "data": {
            "login_count_30d": activity["login_count_30d"],
            "login_failed_7d": activity["login_failed_7d"],
            "last_login_at": activity["last_login_at"].isoformat() if activity["last_login_at"] else None,
            "recent_logs": [
                {
                    "id": log.id,
                    "action": log.action,
                    "target_type": log.target_type,
                    "target_name": log.target_name,
                    "detail": log.detail,
                    "ip_address": log.ip_address,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                }
                for log in activity["recent_logs"]
            ],
        },
    }


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

    write_log(db, user=current_user, action="delete", target_type="user", target_id=user.id,
              target_name=user.username, detail=f"删除用户（姓名：{user.full_name}）",
              ip_address=get_client_ip(request))
    delete_user(db, user)
    db.commit()
    return {"code": 0, "msg": "删除成功"}
