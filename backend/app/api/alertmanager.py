"""Alertmanager API — 对接 Alertmanager v2 接口 + Webhook 接收。"""
from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import api_permission_required
from app.db.database import get_db
from app.models.user import User
from app.services.alertmanager import (
    check_alertmanager_health,
    get_alerts,
    get_rules,
    list_alert_events,
    process_webhook,
)

router = APIRouter(prefix="/alertmanager", tags=["Alertmanager"])


@router.get("/status")
async def api_status(
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("monitoring.view")),
):
    """检查 Alertmanager 连接状态。"""
    ok = await check_alertmanager_health(db)
    return {"code": 0, "data": {"connected": ok}}


@router.get("/alerts")
async def api_alerts(
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("monitoring.view")),
):
    """获取当前活跃告警。"""
    alerts = await get_alerts(db)
    return {"code": 0, "data": alerts}


@router.get("/rules")
async def api_rules(
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("monitoring.view")),
):
    """获取告警规则。"""
    rules = await get_rules(db)
    return {"code": 0, "data": rules}


@router.post("/webhook")
async def api_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Alertmanager webhook 接收端。
    Alertmanager 配置中添加：
    receivers:
      - name: 'ops-platform'
        webhook_configs:
          - url: 'http://<backend-host>:<port>/api/v1/alertmanager/webhook'
    """
    raw = await request.json()
    # Alertmanager 可能发 {alerts: [...]} 或直接 [...]
    if isinstance(raw, dict):
        payload = raw.get("alerts", [raw])
    elif isinstance(raw, list):
        payload = raw
    else:
        payload = []
    count = process_webhook(db, payload)
    return {"code": 0, "data": {"received": count}}


@router.get("/events")
def api_alert_events(
    keyword: str = "",
    severity: str = "",
    status: str = "",
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("alerts.view")),
):
    """查询告警事件历史。"""
    offset = (max(page, 1) - 1) * page_size
    items, total = list_alert_events(
        db, keyword=keyword, severity=severity, status=status,
        limit=page_size, offset=offset,
    )
    return {
        "code": 0,
        "data": {
            "items": [
                {
                    "id": e.id,
                    "fingerprint": e.fingerprint,
                    "alert_name": e.alert_name,
                    "severity": e.severity,
                    "status": e.status,
                    "alert_value": e.alert_value,
                    "summary": e.summary,
                    "description": e.description,
                    "instance": e.instance,
                    "job": e.job,
                    "firing_count": e.firing_count,
                    "generator_url": e.generator_url,
                    "raw_labels": e.raw_labels,
                    "raw_annotations": e.raw_annotations,
                    "starts_at": e.starts_at.isoformat() if e.starts_at else None,
                    "ends_at": e.ends_at.isoformat() if e.ends_at else None,
                    "received_at": e.received_at.isoformat() if e.received_at else None,
                }
                for e in items
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        },
    }
