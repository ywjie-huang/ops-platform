"""资产管理 API."""
from fastapi import APIRouter

router = APIRouter(prefix="/assets", tags=["资产管理"])


@router.get("/")
def list_assets():
    return {"items": [], "total": 0}


@router.post("/")
def create_asset(data: dict):
    return {"msg": "asset created", "data": data}
