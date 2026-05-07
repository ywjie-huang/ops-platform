"""资产管理 API。"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import api_permission_required
from app.db.database import get_db
from app.models.user import User
from app.services.assets import (
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
    status: str = "在线"
    owner: str = ""
    description: str = ""


def _asset_dict(a) -> dict:
    return {
        "id": a.id,
        "name": a.name,
        "asset_type": a.asset_type,
        "ip_address": a.ip_address,
        "status": a.status,
        "owner": a.owner,
        "description": a.description,
        "created_at": a.created_at.isoformat(),
    }


@router.get("/")
def api_list_assets(
    keyword: str = "",
    asset_type: str = "",
    status: str = "",
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("assets.view")),
):
    items = list_assets(db, keyword=keyword, asset_type=asset_type, status=status)
    return {
        "code": 0,
        "data": {
            "items": [_asset_dict(a) for a in items],
            "total": len(items),
        },
    }


@router.post("/")
def api_create_asset(
    body: AssetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("assets.create")),
):
    asset = create_asset_record(
        db,
        name=body.name.strip(),
        asset_type=body.asset_type.strip(),
        ip_address=body.ip_address.strip(),
        status=body.status.strip() or "在线",
        owner=body.owner.strip(),
        description=body.description.strip(),
    )
    write_log(db, user=current_user, action="create", target_type="asset", target_id=asset.id, target_name=asset.name, ip_address="")
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
    )
    write_log(db, user=current_user, action="update", target_type="asset", target_id=asset.id, target_name=asset.name, ip_address="")
    db.commit()
    return {"code": 0, "msg": "更新成功", "data": _asset_dict(asset)}


@router.delete("/{asset_id}")
def api_delete_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("assets.delete")),
):
    asset = get_asset(db, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="资产不存在")

    write_log(db, user=current_user, action="delete", target_type="asset", target_id=asset.id, target_name=asset.name, ip_address="")
    delete_asset(db, asset)
    db.commit()
    return {"code": 0, "msg": "删除成功"}
