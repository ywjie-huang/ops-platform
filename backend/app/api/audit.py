"""审计日志 API。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import api_permission_required
from app.db.database import get_db
from app.models.user import User
from app.services.audit import ACTION_LABELS, TARGET_LABELS, list_logs

router = APIRouter(prefix="/audit", tags=["审计日志"])


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
    items = list_logs(db, keyword=keyword, action=action, target_type=target_type, days=days)
    total = len(items)
    start = (max(page, 1) - 1) * page_size
    return {
        "code": 0,
        "data": {
            "items": [
                {
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
                for log in items[start:start + page_size]
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        },
    }


@router.get("/meta/actions")
def api_action_labels(_: User = Depends(api_permission_required("audit.view"))):
    return {"code": 0, "data": ACTION_LABELS}


@router.get("/meta/target-types")
def api_target_labels(_: User = Depends(api_permission_required("audit.view"))):
    return {"code": 0, "data": TARGET_LABELS}
