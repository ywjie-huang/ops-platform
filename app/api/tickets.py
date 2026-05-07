"""工单协作 API。"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import api_permission_required
from app.db.database import get_db
from app.models.user import User
from app.services_audit import write_log
from app.services_tickets import (
    create_ticket,
    delete_ticket,
    get_ticket,
    list_tickets,
    update_ticket,
)

router = APIRouter(prefix="/tickets", tags=["工单协作"])


class TicketCreate(BaseModel):
    title: str
    description: str = ""
    priority: str = "normal"
    status: str = "open"
    assignee: str = ""
    asset_id: int | None = None


def _ticket_dict(t) -> dict:
    return {
        "id": t.id,
        "title": t.title,
        "description": t.description,
        "priority": t.priority,
        "status": t.status,
        "assignee": t.assignee,
        "asset_id": t.asset_id,
        "asset_name": t.asset.name if t.asset else None,
        "creator_id": t.creator_id,
        "created_at": t.created_at.isoformat(),
        "updated_at": t.updated_at.isoformat(),
    }


@router.get("/")
def api_list_tickets(
    keyword: str = "",
    status: str = "",
    priority: str = "",
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("tickets.view")),
):
    items = list_tickets(db, keyword=keyword, status=status, priority=priority)
    return {
        "code": 0,
        "data": {
            "items": [_ticket_dict(t) for t in items],
            "total": len(items),
        },
    }


@router.post("/")
def api_create_ticket(
    body: TicketCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("tickets.create")),
):
    ticket = create_ticket(
        db,
        title=body.title.strip(),
        description=body.description.strip(),
        priority=body.priority.strip() or "normal",
        status=body.status.strip() or "open",
        assignee=body.assignee.strip(),
        asset_id=body.asset_id,
        creator_id=current_user.id,
    )
    write_log(db, user=current_user, action="create", target_type="ticket", target_id=ticket.id, target_name=ticket.title, ip_address="")
    db.commit()
    return {"code": 0, "msg": "创建成功", "data": _ticket_dict(ticket)}


@router.get("/{ticket_id}")
def api_get_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("tickets.view")),
):
    ticket = get_ticket(db, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="工单不存在")
    return {"code": 0, "data": _ticket_dict(ticket)}


@router.put("/{ticket_id}")
def api_update_ticket(
    ticket_id: int,
    body: TicketCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("tickets.update")),
):
    ticket = get_ticket(db, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="工单不存在")

    update_ticket(
        db, ticket,
        title=body.title.strip(),
        description=body.description.strip(),
        priority=body.priority.strip(),
        status=body.status.strip(),
        assignee=body.assignee.strip(),
        asset_id=body.asset_id,
    )
    write_log(db, user=current_user, action="update", target_type="ticket", target_id=ticket.id, target_name=ticket.title, ip_address="")
    db.commit()
    return {"code": 0, "msg": "更新成功", "data": _ticket_dict(ticket)}


@router.delete("/{ticket_id}")
def api_delete_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("tickets.delete")),
):
    ticket = get_ticket(db, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="工单不存在")

    write_log(db, user=current_user, action="delete", target_type="ticket", target_id=ticket.id, target_name=ticket.title, ip_address="")
    delete_ticket(db, ticket)
    db.commit()
    return {"code": 0, "msg": "删除成功"}
