"""资产管理 API。"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import api_permission_required, get_client_ip
from app.db.database import get_db
from app.models.user import User
from app.services.assets import (
    count_assets_by_status,
    create_asset as create_asset_record,
    delete_asset,
    get_asset,
    list_assets,
    update_asset,
)
from app.services.audit import write_log

router = APIRouter(prefix="/assets", tags=["资产管理"])


class AssetCreate(BaseModel):
    name: str
    asset_type: str
    ip_address: str
    status: str = "使用中"
    owner: str = ""
    description: str = ""
    spec: str = ""
    os: str = ""
    ssh_port: int = 22
    ssh_username: str = "root"
    ssh_password: str = ""
    ssh_key_id: Optional[int] = None


def _asset_dict(a) -> dict:
    return {
        "id": a.id,
        "name": a.name,
        "asset_type": a.asset_type,
        "ip_address": a.ip_address,
        "status": a.status,
        "owner": a.owner,
        "description": a.description,
        "spec": a.spec,
        "os": a.os,
        "ssh_port": a.ssh_port,
        "ssh_username": a.ssh_username,
        "has_ssh_password": bool(a.ssh_password),
        "ssh_key_id": a.ssh_key_id,
        "created_at": a.created_at.isoformat(),
    }


@router.get("/stats")
def api_asset_stats(
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("assets.view")),
):
    counts = count_assets_by_status(db)
    total = sum(counts.values())
    return {
        "code": 0,
        "data": {
            "total": total,
            "active": counts.get("使用中", 0),
            "shutdown": counts.get("已关机", 0),
            "deleted": counts.get("已删除", 0),
        },
    }


@router.get("/")
def api_list_assets(
    keyword: str = "",
    asset_type: str = "",
    status: str = "",
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("assets.view")),
):
    items = list_assets(db, keyword=keyword, asset_type=asset_type, status=status)
    total = len(items)
    start = (max(page, 1) - 1) * page_size
    return {
        "code": 0,
        "data": {
            "items": [_asset_dict(a) for a in items[start:start + page_size]],
            "total": total,
            "page": page,
            "page_size": page_size,
        },
    }


@router.post("/")
def api_create_asset(
    body: AssetCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("assets.create")),
):
    asset = create_asset_record(
        db,
        name=body.name.strip(),
        asset_type=body.asset_type.strip(),
        ip_address=body.ip_address.strip(),
        status=body.status.strip() or "使用中",
        owner=body.owner.strip(),
        description=body.description.strip(),
        spec=body.spec.strip(),
        os=body.os.strip(),
        ssh_port=body.ssh_port,
        ssh_username=body.ssh_username.strip(),
        ssh_password=body.ssh_password,
        ssh_key_id=body.ssh_key_id,
    )
    write_log(db, user=current_user, action="create", target_type="asset", target_id=asset.id, target_name=asset.name, ip_address=get_client_ip(request))
    db.commit()
    return {"code": 0, "msg": "创建成功", "data": _asset_dict(asset)}


@router.get("/{asset_id}")
def api_get_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("assets.view")),
):
    asset = get_asset(db, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="资产不存在")
    return {"code": 0, "data": _asset_dict(asset)}


@router.put("/{asset_id}")
def api_update_asset(
    asset_id: int,
    body: AssetCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("assets.update")),
):
    asset = get_asset(db, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="资产不存在")

    update_asset(
        db, asset,
        name=body.name.strip(),
        asset_type=body.asset_type.strip(),
        ip_address=body.ip_address.strip(),
        status=body.status.strip(),
        owner=body.owner.strip(),
        description=body.description.strip(),
        spec=body.spec.strip(),
        os=body.os.strip(),
        ssh_port=body.ssh_port,
        ssh_username=body.ssh_username.strip(),
        ssh_password=body.ssh_password,
        ssh_key_id=body.ssh_key_id,
    )
    write_log(db, user=current_user, action="update", target_type="asset", target_id=asset.id, target_name=asset.name, ip_address=get_client_ip(request))
    db.commit()
    return {"code": 0, "msg": "更新成功", "data": _asset_dict(asset)}


@router.delete("/{asset_id}")
def api_delete_asset(
    asset_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("assets.delete")),
):
    asset = get_asset(db, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="资产不存在")

    write_log(db, user=current_user, action="delete", target_type="asset", target_id=asset.id, target_name=asset.name, ip_address=get_client_ip(request))
    delete_asset(db, asset)
    db.commit()
    return {"code": 0, "msg": "删除成功"}
