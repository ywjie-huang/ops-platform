"""Alertmanager API — 对接 Alertmanager v2 接口 + Webhook 接收。"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import api_permission_required
from app.db.database import get_db
from app.models.user import User
from app.services.alertmanager import (
    check_alertmanager_health,
    create_silence,
    delete_silence,
    get_alerts,
    get_rule_event_stats,
    get_rules,
    get_rules_hosts,
    get_silences,
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


@router.get("/rules/hosts")
async def api_rules_hosts(
    names: list[str] | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("monitoring.view")),
):
    """获取每条告警规则关联的主机列表。"""
    mapping = await get_rules_hosts(db, rule_names=names)
    return {"code": 0, "data": mapping}


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
    _: User = Depends(api_permission_required("monitoring.view")),
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


class SilenceMatcher(BaseModel):
    name: str
    value: str
    is_regex: bool = False


class SilenceCreate(BaseModel):
    matchers: list[SilenceMatcher]
    duration_minutes: int = 60
    comment: str = ""
    created_by: str = "ops-platform"


@router.get("/silences")
async def api_silences(
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("monitoring.view")),
):
    """获取静默列表。"""
    silences = await get_silences(db)
    return {"code": 0, "data": silences}


@router.post("/silences")
async def api_create_silence(
    body: SilenceCreate,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("monitoring.view")),
):
    """创建静默（默认持续 1 小时）。"""
    if not body.matchers:
        raise HTTPException(status_code=400, detail="matchers 不能为空")
    duration = min(max(body.duration_minutes, 1), 7 * 24 * 60)
    now = datetime.now(timezone.utc)
    silence_id = await create_silence(
        db,
        matchers=[m.model_dump() for m in body.matchers],
        starts_at=now.isoformat(),
        ends_at=(now + timedelta(minutes=duration)).isoformat(),
        created_by=body.created_by,
        comment=body.comment,
    )
    if not silence_id:
        raise HTTPException(status_code=502, detail="Alertmanager 静默创建失败")
    return {"code": 0, "data": {"id": silence_id}}


@router.delete("/silences/{silence_id}")
async def api_delete_silence(
    silence_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("monitoring.view")),
):
    """解除静默。"""
    ok = await delete_silence(db, silence_id)
    if not ok:
        raise HTTPException(status_code=502, detail="Alertmanager 静默解除失败")
    return {"code": 0, "data": {"deleted": True}}


@router.get("/rules/{rule_name}/events")
def api_rule_events(
    rule_name: str,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("monitoring.view")),
):
    """单条规则的告警事件统计（近 7 天每日触发数 + 最近记录）。"""
    stats = get_rule_event_stats(db, rule_name)
    return {"code": 0, "data": stats}
