"""Alert service — CRUD + status queries."""
from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.alert import Alert


def list_alerts(
    db: Session,
    *,
    keyword: str = "",
    status: str = "",
    level: str = "",
) -> list[Alert]:
    stmt = select(Alert).options(
        selectinload(Alert.asset),
        selectinload(Alert.handler),
    )
    keyword = keyword.strip()
    status = status.strip()
    level = level.strip()

    if keyword:
        like_val = f"%{keyword}%"
        stmt = stmt.where(
            or_(Alert.title.ilike(like_val), Alert.source.ilike(like_val))
        )
    if status:
        stmt = stmt.where(Alert.status == status)
    if level:
        stmt = stmt.where(Alert.level == level)

    stmt = stmt.order_by(Alert.id.desc())
    return list(db.scalars(stmt).unique().all())


def get_alert(db: Session, alert_id: int) -> Alert | None:
    stmt = select(Alert).options(
        selectinload(Alert.asset),
        selectinload(Alert.handler),
    ).where(Alert.id == alert_id)
    return db.scalar(stmt)


def create_alert(
    db: Session,
    *,
    title: str,
    description: str,
    level: str,
    status: str,
    source: str,
    asset_id: int | None,
    handler_id: int | None,
) -> Alert:
    alert = Alert(
        title=title,
        description=description,
        level=level,
        status=status,
        source=source,
        asset_id=asset_id,
        handler_id=handler_id,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return get_alert(db, alert.id) or alert


def update_alert(
    db: Session,
    alert: Alert,
    *,
    title: str,
    description: str,
    level: str,
    status: str,
    source: str,
    asset_id: int | None,
    handler_id: int | None,
) -> Alert:
    alert.title = title
    alert.description = description
    alert.level = level
    alert.status = status
    alert.source = source
    alert.asset_id = asset_id
    alert.handler_id = handler_id
    alert.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(alert)
    return get_alert(db, alert.id) or alert


def delete_alert(db: Session, alert: Alert) -> None:
    db.delete(alert)
    db.commit()


def count_alerts_by_status(db: Session) -> dict[str, int]:
    stmt = select(Alert.status, func.count(Alert.id)).group_by(Alert.status)
    return {s: c for s, c in db.execute(stmt).all()}


def count_alerts_by_level(db: Session) -> dict[str, int]:
    stmt = select(Alert.level, func.count(Alert.id)).group_by(Alert.level)
    return {l: c for l, c in db.execute(stmt).all()}


def count_pending_alerts(db: Session) -> int:
    stmt = select(func.count(Alert.id)).where(Alert.status.in_(["pending", "confirmed"]))
    return db.scalar(stmt) or 0
