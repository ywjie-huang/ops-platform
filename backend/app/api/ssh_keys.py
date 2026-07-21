"""SSH 密钥管理 API。"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.api.deps import api_permission_required, get_client_ip
from app.core.config import CHINA_TZ
from app.db.database import get_db
from app.models.ssh_key import SSHKey
from app.models.user import User
from app.services.audit import write_log

router = APIRouter(prefix="/ssh-keys", tags=["SSH 密钥管理"])


# ── Pydantic 模型 ──

class SSHKeyCreate(BaseModel):
    name: str
    auth_type: str = "password"  # password / key
    username: str = "root"
    password: str = ""
    private_key: str = ""
    passphrase: str = ""
    port: int = 22
    description: str = ""
    is_default: bool = False


class SSHKeyUpdate(BaseModel):
    name: Optional[str] = None
    auth_type: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    private_key: Optional[str] = None
    passphrase: Optional[str] = None
    port: Optional[int] = None
    description: Optional[str] = None
    is_default: Optional[bool] = None


def _key_list_item(k: SSHKey) -> dict:
    """列表/创建/更新响应：永不返回密码、私钥、口令原文。"""
    return {
        "id": k.id,
        "name": k.name,
        "auth_type": k.auth_type,
        "username": k.username,
        "has_password": bool(k.password),
        "has_private_key": bool(k.private_key),
        "has_passphrase": bool(k.passphrase),
        "port": k.port,
        "description": k.description or "",
        "is_default": bool(k.is_default),
        "created_at": k.created_at.isoformat() if k.created_at else None,
        "updated_at": k.updated_at.isoformat() if k.updated_at else None,
    }


def _clear_other_defaults(db: Session, *, exclude_id: int | None = None) -> None:
    query = db.query(SSHKey).filter(SSHKey.is_default.is_(True))
    if exclude_id is not None:
        query = query.filter(SSHKey.id != exclude_id)
    query.update({"is_default": False})


# ── 接口 ──

@router.get("/", summary="获取密钥列表")
def list_ssh_keys(
    keyword: str = Query("", description="搜索关键词"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("ssh_keys.view")),
):
    query = select(SSHKey)
    if keyword:
        query = query.where(
            SSHKey.name.contains(keyword)
            | SSHKey.username.contains(keyword)
            | SSHKey.description.contains(keyword)
        )
    query = query.order_by(SSHKey.is_default.desc(), SSHKey.id.desc())

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()

    return {
        "code": 0,
        "data": {
            "items": [_key_list_item(k) for k in items],
            "total": total,
            "page": page,
            "page_size": page_size,
        },
    }


@router.get("/{key_id}", summary="获取密钥详情")
def get_ssh_key(
    key_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("ssh_keys.view")),
):
    key = db.get(SSHKey, key_id)
    if not key:
        raise HTTPException(status_code=404, detail="密钥不存在")
    # 详情同样不返回秘密原文，编辑时采用“留空不修改”策略
    return {"code": 0, "data": _key_list_item(key)}


@router.post("/", summary="创建密钥")
def create_ssh_key(
    body: SSHKeyCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("ssh_keys.create")),
):
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="密钥名称不能为空")

    auth_type = (body.auth_type or "password").strip()
    if auth_type not in {"password", "key"}:
        raise HTTPException(status_code=400, detail="认证类型无效")

    if auth_type == "password" and not body.password:
        raise HTTPException(status_code=400, detail="请输入 SSH 密码")
    if auth_type == "key" and not body.private_key.strip():
        raise HTTPException(status_code=400, detail="请提供私钥内容")

    if body.is_default:
        _clear_other_defaults(db)

    key = SSHKey(
        name=name,
        auth_type=auth_type,
        username=(body.username or "root").strip() or "root",
        password=body.password or "",
        private_key=body.private_key or "",
        passphrase=body.passphrase or "",
        port=body.port or 22,
        description=(body.description or "").strip(),
        is_default=bool(body.is_default),
    )
    db.add(key)
    db.flush()

    write_log(
        db,
        user=current_user,
        action="ssh_key_create",
        target_type="ssh_key",
        target_id=key.id,
        target_name=key.name,
        detail=f"创建 SSH 密钥: {key.name}",
        ip_address=get_client_ip(request),
    )
    db.commit()
    db.refresh(key)

    return {"code": 0, "msg": "创建成功", "data": _key_list_item(key)}


@router.put("/{key_id}", summary="更新密钥")
def update_ssh_key(
    key_id: int,
    body: SSHKeyUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("ssh_keys.update")),
):
    key = db.get(SSHKey, key_id)
    if not key:
        raise HTTPException(status_code=404, detail="密钥不存在")

    update_data = body.model_dump(exclude_unset=True)

    if "name" in update_data:
        name = (update_data["name"] or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="密钥名称不能为空")
        update_data["name"] = name

    if "auth_type" in update_data:
        auth_type = (update_data["auth_type"] or "").strip()
        if auth_type not in {"password", "key"}:
            raise HTTPException(status_code=400, detail="认证类型无效")
        update_data["auth_type"] = auth_type

    if "username" in update_data:
        update_data["username"] = (update_data["username"] or "root").strip() or "root"

    if "description" in update_data:
        update_data["description"] = (update_data["description"] or "").strip()

    # 秘密字段：空字符串表示“不修改”，避免编辑时误清空
    for secret_field in ("password", "private_key", "passphrase"):
        if secret_field in update_data and not update_data[secret_field]:
            update_data.pop(secret_field)

    if update_data.get("is_default"):
        _clear_other_defaults(db, exclude_id=key_id)

    for field, value in update_data.items():
        setattr(key, field, value)

    key.updated_at = datetime.now(CHINA_TZ)
    db.flush()

    write_log(
        db,
        user=current_user,
        action="ssh_key_update",
        target_type="ssh_key",
        target_id=key.id,
        target_name=key.name,
        detail=f"更新 SSH 密钥: {key.name}",
        ip_address=get_client_ip(request),
    )
    db.commit()
    db.refresh(key)

    return {"code": 0, "msg": "更新成功", "data": _key_list_item(key)}


@router.delete("/{key_id}", summary="删除密钥")
def delete_ssh_key(
    key_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("ssh_keys.delete")),
):
    key = db.get(SSHKey, key_id)
    if not key:
        raise HTTPException(status_code=404, detail="密钥不存在")

    name = key.name
    db.delete(key)
    db.flush()

    write_log(
        db,
        user=current_user,
        action="ssh_key_delete",
        target_type="ssh_key",
        target_id=key_id,
        target_name=name,
        detail=f"删除 SSH 密钥: {name}",
        ip_address=get_client_ip(request),
    )
    db.commit()

    return {"code": 0, "msg": "删除成功"}
