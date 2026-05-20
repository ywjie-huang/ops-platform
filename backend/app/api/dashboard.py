"""仪表盘 API。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import api_permission_required
from app.db.database import get_db
from app.models.user import User
from app.services.dashboard import build_activities, build_dashboard_stats, build_dashboard_summary, build_sparkline_data

router = APIRouter(prefix="/dashboard", tags=["仪表盘"])


@router.get("/stats")
def api_dashboard_stats(
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("dashboard.view")),
):
    stats = build_dashboard_stats(db)
    return {
        "code": 0,
        "data": {
            "asset_total": stats.asset_total,
            "online_hosts": stats.online_hosts,
            "open_alerts": stats.open_alerts,
            "pending_tickets": stats.pending_tickets,
            "user_total": stats.user_total,
            "role_total": stats.role_total,
            "offline_assets": stats.offline_assets,
            "maintenance_assets": stats.maintenance_assets,
            "user_growth_7d": stats.user_growth_7d,
        },
    }


@router.get("/summary")
def api_dashboard_summary(
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("dashboard.view")),
):
    summary = build_dashboard_summary(db)
    return {
        "code": 0,
        "data": {
            "quick_stats": [
                {"label": s.label, "value": s.value, "desc": s.hint, "tone": s.tone}
                for s in summary.quick_stats
            ],
            "recent_asset_changes": [
                {"title": a.title, "meta": a.meta, "detail": a.detail, "tag": a.tag, "tone": a.tone}
                for a in summary.recent_asset_changes
            ],
            "recent_users": [
                {"title": a.title, "meta": a.meta, "detail": a.detail, "tag": a.tag, "tone": a.tone}
                for a in summary.recent_users
            ],
            "role_distribution": [
                {"label": d.label, "value": d.value, "tone": d.tone}
                for d in summary.role_distribution
            ],
            "type_breakdown": [
                {"label": d.label, "value": d.value, "color": d.color}
                for d in summary.type_breakdown
            ],
            "max_type_value": summary.max_type_value,
            "recent_tickets": [
                {"title": a.title, "meta": a.meta, "detail": a.detail, "tag": a.tag, "tone": a.tone}
                for a in summary.recent_tickets
            ],
            "recent_alerts": [
                {"title": a.title, "meta": a.meta, "detail": a.detail, "tag": a.tag, "tone": a.tone}
                for a in summary.recent_alerts
            ],
        },
    }


@router.get("/sparkline")
def api_dashboard_sparkline(
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("dashboard.view")),
):
    data = build_sparkline_data(db)
    return {"code": 0, "data": data}


@router.get("/activities")
def api_dashboard_activities(
    limit: int = 20,
    type: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("dashboard.view")),
):
    items = build_activities(db, limit=limit, activity_type=type)
    return {"code": 0, "data": {"items": items}}
