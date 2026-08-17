"""审计日志 API。"""
import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import api_permission_required
from app.core.config import CHINA_TZ
from app.db.database import get_db
from app.models.user import User
from app.services.audit import (
    ACTION_LABELS,
    TARGET_LABELS,
    get_stats,
    list_logs,
    query_logs_for_export,
)

router = APIRouter(prefix="/audit", tags=["审计日志"])


def _serialize(log) -> dict:
    return {
        "id": log.id,
        "user": log.username,
        "action": log.action,
        "target_type": log.target_type,
        "target_id": log.target_id,
        "target_name": log.target_name,
        "detail": log.detail,
        "ip_address": log.ip_address,
        "created_at": log.created_at.isoformat(),
    }


@router.get("/logs")
def api_list_logs(
    keyword: str = "",
    action: str = "",
    target_type: str = "",
    days: int = 0,
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("audit.view")),
):
    items, total = list_logs(
        db, keyword=keyword, action=action, target_type=target_type,
        days=days, page=page, page_size=page_size,
    )
    return {
        "code": 0,
        "data": {
            "items": [_serialize(log) for log in items],
            "total": total,
            "page": page,
            "page_size": page_size,
        },
    }


@router.get("/stats")
def api_stats(
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("audit.view")),
):
    return {"code": 0, "data": get_stats(db)}


@router.get("/logs/export")
def api_export_logs(
    keyword: str = "",
    action: str = "",
    target_type: str = "",
    days: int = 0,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("audit.view")),
):
    rows = query_logs_for_export(db, keyword=keyword, action=action, target_type=target_type, days=days)

    buf = io.StringIO()
    # utf-8-sig BOM：让 Excel 正确识别中文
    buf.write("﻿")
    writer = csv.writer(buf)
    writer.writerow(["ID", "操作人", "操作", "对象类型", "对象ID", "对象名称", "详情", "IP", "时间"])
    for log in rows:
        writer.writerow([
            log.id,
            log.username,
            ACTION_LABELS.get(log.action, log.action),
            TARGET_LABELS.get(log.target_type, log.target_type),
            log.target_id or "",
            log.target_name,
            log.detail,
            log.ip_address,
            log.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        ])
    buf.seek(0)

    filename = f"audit_logs_{datetime.now(CHINA_TZ):%Y%m%d_%H%M%S}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/meta/actions")
def api_action_labels(_: User = Depends(api_permission_required("audit.view"))):
    return {"code": 0, "data": ACTION_LABELS}


@router.get("/meta/target-types")
def api_target_labels(_: User = Depends(api_permission_required("audit.view"))):
    return {"code": 0, "data": TARGET_LABELS}
