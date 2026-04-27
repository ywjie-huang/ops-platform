"""审计日志 API."""
from fastapi import APIRouter

router = APIRouter(prefix="/audit", tags=["审计日志"])


@router.get("/logs")
def list_audit_logs():
    return {"items": [], "total": 0}
