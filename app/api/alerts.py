"""告警中心 API."""
from fastapi import APIRouter

router = APIRouter(prefix="/alerts", tags=["告警中心"])


@router.get("/")
def list_alerts():
    return {"items": [], "total": 0}
