"""告警中心 API。"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import api_permission_required
from app.db.database import get_db
from app.models.user import User
from app.services.alerts import (
    create_alert,
    delete_alert,
    get_alert,
    list_alerts,
    update_alert,
)
from app.services.audit import write_log

router = APIRouter(prefix="/alerts", tags=["告警中心"])


class AlertCreate(BaseModel):
    title: str
    description: str = ""
    level: str = "medium"
    status: str = "pending"
    source: str = ""
    asset_id: int | None = None


def _alert_dict(a) -> dict:
    return {
        "id": a.id,
        "title": a.title,
        "description": a.description,
        "level": a.level,
        "status": a.status,
        "source": a.source,
        "asset_id": a.asset_id,
        "asset_name": a.asset.name if a.asset else None,
        "handler_id": a.handler_id,
        "created_at": a.created_at.isoformat(),
        "updated_at": a.updated_at.isoformat(),
    }


@router.get("/")
def api_list_alerts(
    keyword: str = "",
    status: str = "",
    level: str = "",
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("alerts.view")),
):
    items = list_alerts(db, keyword=keyword, status=status, level=level)
    return {
        "code": 0,
        "data": {
            "items": [_alert_dict(a) for a in items],
            "total": len(items),
        },
    }


@router.post("/")
def api_create_alert(
    body: AlertCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("alerts.create")),
):
    alert = create_alert(
        db,
        title=body.title.strip(),
        description=body.description.strip(),
        level=body.level.strip() or "medium",
        status=body.status.strip() or "pending",
        source=body.source.strip(),
        asset_id=body.asset_id,
        handler_id=None,
    )
    write_log(db, user=current_user, action="create", target_type="alert", target_id=alert.id, target_name=alert.title, ip_address="")
    db.commit()
    return {"code": 0, "msg": "创建成功", "data": _alert_dict(alert)}


@router.get("/{alert_id}")
def api_get_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("alerts.view")),
):
    alert = get_alert(db, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="告警不存在")
    return {"code": 0, "data": _alert_dict(alert)}


@router.put("/{alert_id}")
def api_update_alert(
    alert_id: int,
    body: AlertCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("alerts.update")),
):
    alert = get_alert(db, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="告警不存在")

    handler_id = current_user.id if body.status in ("confirmed", "resolved") else alert.handler_id
    update_alert(
        db, alert,
        title=body.title.strip(),
        description=body.description.strip(),
        level=body.level.strip(),
        status=body.status.strip(),
        source=body.source.strip(),
        asset_id=body.asset_id,
        handler_id=handler_id,
    )
    write_log(db, user=current_user, action="update", target_type="alert", target_id=alert.id, target_name=alert.title, ip_address="")
    db.commit()
    return {"code": 0, "msg": "更新成功", "data": _alert_dict(alert)}


@router.delete("/{alert_id}")
def api_delete_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("alerts.delete")),
):
    alert = get_alert(db, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="告警不存在")

    write_log(db, user=current_user, action="delete", target_type="alert", target_id=alert.id, target_name=alert.title, ip_address="")
    delete_alert(db, alert)
    db.commit()
    return {"code": 0, "msg": "删除成功"}
