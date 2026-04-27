"""工单协作 API."""
from fastapi import APIRouter

router = APIRouter(prefix="/tickets", tags=["工单协作"])


@router.get("/")
def list_tickets():
    return {"items": [], "total": 0}


@router.post("/")
def create_ticket(data: dict):
    return {"msg": "ticket created", "data": data}
