"""报表 API。"""
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import api_permission_required
from app.db.database import get_db
from app.models.user import User
from app.services.reports import (
    export_csv,
    list_data_sources,
    list_dimensions,
    list_preset_reports,
    get_preset_report,
    query_custom_report,
    query_report_data,
)

router = APIRouter(prefix="/reports", tags=["报表"])


@router.get("/presets")
def api_preset_reports(
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("reports.view")),
):
    reports = list_preset_reports()
    return {
        "code": 0,
        "data": [
            {"id": r["id"], "name": r["name"], "description": r["description"], "icon": r.get("icon", "📊")}
            for r in reports
        ],
    }


@router.get("/presets/{report_id}")
def api_preset_detail(
    report_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("reports.view")),
):
    report = get_preset_report(report_id)
    if report is None:
        return {"code": 1, "msg": "报表不存在"}
    data = query_report_data(db, report)
    return {"code": 0, "data": {"report": {"id": report["id"], "name": report["name"], "description": report["description"]}, "data": data}}


@router.get("/data-sources")
def api_data_sources(_: User = Depends(api_permission_required("reports.view"))):
    return {"code": 0, "data": list_data_sources()}


@router.get("/dimensions")
def api_dimensions(_: User = Depends(api_permission_required("reports.view"))):
    return {"code": 0, "data": list_dimensions()}


@router.post("/custom")
def api_custom_report(
    body: dict,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("reports.view")),
):
    data_source = body.get("data_source", "")
    dimension = body.get("dimension", "")
    days = body.get("days", 30)
    result = query_custom_report(db, data_source=data_source, dimension=dimension, days=days)
    return {"code": 0, "data": result}


@router.get("/export/{report_id}")
def api_export_csv(
    report_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("reports.view")),
):
    report = get_preset_report(report_id)
    if report is None:
        return {"code": 1, "msg": "报表不存在"}
    data = query_report_data(db, report)
    csv_content = export_csv(report, data)
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={report_id}.csv"},
    )
