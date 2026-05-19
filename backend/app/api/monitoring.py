"""监控 API — 主机监控（Prometheus 数据源）。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import api_permission_required
from app.db.database import get_db
from app.models.user import User
from app.services.prometheus import (
    check_prometheus_health,
    get_host_metrics,
    get_targets,
)

router = APIRouter(prefix="/monitoring", tags=["监控"])


@router.get("/hosts")
async def api_host_list(
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("monitoring.view")),
):
    """主机监控列表 — 从 Prometheus 批量获取真实数据。"""
    from app.services.assets import list_assets
    from app.services.prometheus import get_hosts_summary
    assets = list_assets(db)
    results = await get_hosts_summary(assets, db)
    return {"code": 0, "data": results}


@router.get("/hosts/{host_id}")
async def api_host_detail(
    host_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("monitoring.view")),
):
    """主机详情 — 从 Prometheus 获取真实数据。"""
    from app.services.assets import get_asset
    asset = get_asset(db, host_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="主机不存在")

    try:
        metrics = await get_host_metrics(asset.ip_address, asset.name, db)
        return {
            "code": 0,
            "data": {
                "asset_id": asset.id,
                "hostname": asset.name,
                "ip": asset.ip_address,
                "status": asset.status,
                "owner": asset.owner or "",
                "spec": asset.spec or "",
                "os_info": asset.os or "",
                "prometheus_ok": True,
                **metrics,
            },
        }
    except Exception as e:
        return {
            "code": 0,
            "data": {
                "asset_id": asset.id,
                "hostname": asset.name,
                "ip": asset.ip_address,
                "status": asset.status,
                "owner": asset.owner or "",
                "spec": asset.spec or "",
                "os_info": asset.os or "",
                "prometheus_ok": False,
                "error": str(e),
                "cpu": {"usage": 0, "cores": 0},
                "memory": {"usage": 0, "total_gb": 0, "used_gb": 0, "available_gb": 0},
                "disk": {"usage": 0, "total_gb": 0, "read_mb_s": 0, "write_mb_s": 0},
                "network": {"in_mbps": 0, "out_mbps": 0},
                "load": {"1m": 0, "5m": 0, "15m": 0},
                "tcp_connections": 0,
                "processes": {"running": 0},
                "uptime_hours": 0,
            },
        }


@router.get("/prometheus/health")
async def api_prometheus_health(
    db: Session = Depends(get_db),
):
    """检查 Prometheus 连接状态。"""
    ok = await check_prometheus_health(db)
    return {"code": 0, "data": {"connected": ok}}


@router.get("/prometheus/targets")
async def api_prometheus_targets(
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("monitoring.view")),
):
    """获取 Prometheus 采集目标列表。"""
    targets = await get_targets(db)
    return {"code": 0, "data": targets}


@router.get("/prometheus/instances")
async def api_prometheus_instances(
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("monitoring.view")),
):
    """调试：显示资产与 Prometheus instance 的匹配情况。"""
    from app.services.assets import list_assets
    from app.services.prometheus import _discover_instances, _find_instance
    assets = list_assets(db)
    instances = await _discover_instances()
    results = []
    for asset in assets:
        matched = _find_instance(asset.ip_address, asset.name, instances)
        results.append({
            "asset_name": asset.name,
            "asset_ip": asset.ip_address,
            "prometheus_instance": matched,
            "matched": matched is not None,
        })
    return {"code": 0, "data": {"prometheus_instances": list(instances.keys()), "asset_matching": results}}
