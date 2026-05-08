"""监控 API。"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import api_permission_required
from app.db.database import get_db
from app.models.user import User
from app.services.monitoring import (
    create_metric,
    delete_metric,
    get_host_detail,
    get_host_monitoring_list,
    get_metric,
    get_metric_categories,
    list_metrics,
    update_metric,
)

router = APIRouter(prefix="/monitoring", tags=["监控"])


class MetricCreate(BaseModel):
    name: str
    code: str
    unit: str = ""
    category: str = ""
    warning_threshold: str = ""
    critical_threshold: str = ""


@router.get("/metrics")
def api_list_metrics(
    keyword: str = "", category: str = "",
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("monitoring.view")),
):
    items = list_metrics(db, keyword=keyword, category=category)
    return {
        "code": 0,
        "data": [
            {
                "id": m.id, "name": m.name, "code": m.code, "unit": m.unit,
                "category": m.category, "is_system": m.is_system,
                "warning_threshold": m.warning_threshold, "critical_threshold": m.critical_threshold,
            }
            for m in items
        ],
    }


@router.get("/metrics/categories")
def api_metric_categories(db: Session = Depends(get_db), _: User = Depends(api_permission_required("monitoring.view"))):
    cats = get_metric_categories(db)
    return {"code": 0, "data": cats}


@router.post("/metrics")
def api_create_metric(body: MetricCreate, db: Session = Depends(get_db), _: User = Depends(api_permission_required("monitoring.create"))):
    m = create_metric(db, name=body.name.strip(), code=body.code.strip(), unit=body.unit.strip(), category=body.category.strip(), warning_threshold=body.warning_threshold.strip(), critical_threshold=body.critical_threshold.strip())
    return {"code": 0, "msg": "创建成功", "data": {"id": m.id, "name": m.name}}


@router.put("/metrics/{metric_id}")
def api_update_metric(metric_id: int, body: MetricCreate, db: Session = Depends(get_db), _: User = Depends(api_permission_required("monitoring.update"))):
    m = get_metric(db, metric_id)
    if m is None:
        raise HTTPException(status_code=404, detail="指标不存在")
    update_metric(db, m, name=body.name.strip(), unit=body.unit.strip(), category=body.category.strip(), warning_threshold=body.warning_threshold.strip(), critical_threshold=body.critical_threshold.strip())
    return {"code": 0, "msg": "更新成功"}


@router.delete("/metrics/{metric_id}")
def api_delete_metric(metric_id: int, db: Session = Depends(get_db), _: User = Depends(api_permission_required("monitoring.delete"))):
    m = get_metric(db, metric_id)
    if m is None:
        raise HTTPException(status_code=404, detail="指标不存在")
    if m.is_system:
        raise HTTPException(status_code=400, detail="系统内置指标不可删除")
    delete_metric(db, m)
    return {"code": 0, "msg": "删除成功"}


@router.get("/hosts")
def api_host_list(db: Session = Depends(get_db), _: User = Depends(api_permission_required("monitoring.view"))):
    from app.services.assets import list_assets
    assets = list_assets(db)
    items = get_host_monitoring_list(assets)
    return {
        "code": 0,
        "data": [
            {
                "id": h["asset_id"], "name": h["name"], "ip_address": h["ip"], "owner": h["owner"],
                "cpu": h["cpu"], "memory": h["memory"], "disk": h["disk"],
                "network_in": h["net_in"], "network_out": h["net_out"], "load": h["load"],
            }
            for h in items
        ],
    }


@router.get("/hosts/{host_id}")
def api_host_detail(host_id: int, db: Session = Depends(get_db), _: User = Depends(api_permission_required("monitoring.view"))):
    from app.services.assets import get_asset
    asset = get_asset(db, host_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="主机不存在")
    detail = get_host_detail(asset.id, asset.name, asset.ip_address)
    return {"code": 0, "data": detail}
