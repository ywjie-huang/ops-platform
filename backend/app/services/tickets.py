"""Ticket service — CRUD + status queries."""
from datetime import datetime

from app.core.config import CHINA_TZ

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.ticket import Ticket


def list_tickets(
    db: Session,
    *,
    keyword: str = "",
    status: str = "",
    priority: str = "",
) -> list[Ticket]:
    stmt = select(Ticket).options(
        selectinload(Ticket.asset),
        selectinload(Ticket.creator),
    )
    keyword = keyword.strip()
    status = status.strip()
    priority = priority.strip()

    if keyword:
        like_val = f"%{keyword}%"
        stmt = stmt.where(
            or_(Ticket.title.ilike(like_val), Ticket.assignee.ilike(like_val))
        )
    if status:
        stmt = stmt.where(Ticket.status == status)
    if priority:
        stmt = stmt.where(Ticket.priority == priority)

    stmt = stmt.order_by(Ticket.id.desc())
    return list(db.scalars(stmt).unique().all())


def get_ticket(db: Session, ticket_id: int) -> Ticket | None:
    stmt = select(Ticket).options(
        selectinload(Ticket.asset),
        selectinload(Ticket.creator),
    ).where(Ticket.id == ticket_id)
    return db.scalar(stmt)


def create_ticket(
    db: Session,
    *,
    title: str,
    description: str,
    priority: str,
    status: str,
    assignee: str,
    asset_id: int | None,
    creator_id: int | None,
) -> Ticket:
    ticket = Ticket(
        title=title,
        description=description,
        priority=priority,
        status=status,
        assignee=assignee,
        asset_id=asset_id,
        creator_id=creator_id,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return get_ticket(db, ticket.id) or ticket


def update_ticket(
    db: Session,
    ticket: Ticket,
    *,
    title: str,
    description: str,
    priority: str,
    status: str,
    assignee: str,
    asset_id: int | None,
) -> Ticket:
    ticket.title = title
    ticket.description = description
    ticket.priority = priority
    ticket.status = status
    ticket.assignee = assignee
    ticket.asset_id = asset_id
    ticket.updated_at = datetime.now(CHINA_TZ)
    db.commit()
    db.refresh(ticket)
    return get_ticket(db, ticket.id) or ticket


def delete_ticket(db: Session, ticket: Ticket) -> None:
    db.delete(ticket)
    db.commit()


def count_tickets_by_status(db: Session) -> dict[str, int]:
    stmt = select(Ticket.status, func.count(Ticket.id)).group_by(Ticket.status)
    return {s: c for s, c in db.execute(stmt).all()}


def count_open_tickets(db: Session) -> int:
    stmt = select(func.count(Ticket.id)).where(Ticket.status.in_(["open", "in_progress"]))
    return db.scalar(stmt) or 0
