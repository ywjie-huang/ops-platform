"""SSH 密钥管理 API。"""
from datetime import datetime

from app.core.config import CHINA_TZ
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.ssh_key import SSHKey
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


class SSHKeyOut(BaseModel):
    id: int
    name: str
    auth_type: str
    username: str
    has_password: bool
    has_private_key: bool
    passphrase: str
    port: int
    description: str
    is_default: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SSHKeyDetailOut(BaseModel):
    id: int
    name: str
    auth_type: str
    username: str
    password: str
    private_key: str
    passphrase: str
    port: int
    description: str
    is_default: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ── 接口 ──

@router.get("/", summary="获取密钥列表")
def list_ssh_keys(
    keyword: str = Query("", description="搜索关键词"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = select(SSHKey)
    if keyword:
        query = query.where(
            SSHKey.name.contains(keyword)
            | SSHKey.username.contains(keyword)
            | SSHKey.description.contains(keyword)
        )
    query = query.order_by(SSHKey.is_default.desc(), SSHKey.id.desc())

    total = db.scalar(select(func.count()).select_from(query.subquery()))
    items = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()

    # 列表接口不返回敏感字段原文
    result = []
    for k in items:
        result.append(SSHKeyOut(
            id=k.id,
            name=k.name,
            auth_type=k.auth_type,
            username=k.username,
            has_password=bool(k.password),
            has_private_key=bool(k.private_key),
            passphrase="***" if k.passphrase else "",
            port=k.port,
            description=k.description,
            is_default=k.is_default,
            created_at=k.created_at,
            updated_at=k.updated_at,
        ))

    return {"data": {"items": result, "total": total}}


@router.get("/{key_id}", summary="获取密钥详情")
def get_ssh_key(key_id: int, db: Session = Depends(get_db)):
    key = db.get(SSHKey, key_id)
    if not key:
        raise HTTPException(404, "密钥不存在")
    return {"data": SSHKeyDetailOut.model_validate(key)}


@router.post("/", summary="创建密钥")
def create_ssh_key(body: SSHKeyCreate, db: Session = Depends(get_db)):
    # 如果设为默认，先把其他默认取消
    if body.is_default:
        db.query(SSHKey).filter(SSHKey.is_default == True).update({"is_default": False})

    key = SSHKey(**body.model_dump())
    db.add(key)
    db.commit()
    db.refresh(key)

    write_log(db, user=None, action="ssh_key_create", target_type="ssh_key",
              target_id=key.id, target_name=key.name, detail=f"创建 SSH 密钥: {key.name}")
    db.commit()

    return {"data": SSHKeyOut.model_validate(key), "message": "创建成功"}


@router.put("/{key_id}", summary="更新密钥")
def update_ssh_key(key_id: int, body: SSHKeyUpdate, db: Session = Depends(get_db)):
    key = db.get(SSHKey, key_id)
    if not key:
        raise HTTPException(404, "密钥不存在")

    update_data = body.model_dump(exclude_unset=True)

    # 如果设为默认，先把其他默认取消
    if update_data.get("is_default"):
        db.query(SSHKey).filter(SSHKey.is_default == True, SSHKey.id != key_id).update({"is_default": False})

    for field, value in update_data.items():
        setattr(key, field, value)

    key.updated_at = datetime.now(CHINA_TZ)
    db.commit()
    db.refresh(key)

    write_log(db, user=None, action="ssh_key_update", target_type="ssh_key",
              target_id=key.id, target_name=key.name, detail=f"更新 SSH 密钥: {key.name}")
    db.commit()

    return {"data": SSHKeyOut.model_validate(key), "message": "更新成功"}


@router.delete("/{key_id}", summary="删除密钥")
def delete_ssh_key(key_id: int, db: Session = Depends(get_db)):
    key = db.get(SSHKey, key_id)
    if not key:
        raise HTTPException(404, "密钥不存在")

    name = key.name
    db.delete(key)
    db.commit()

    write_log(db, user=None, action="ssh_key_delete", target_type="ssh_key",
              target_id=key_id, target_name=name, detail=f"删除 SSH 密钥: {name}")
    db.commit()

    return {"message": "删除成功"}
