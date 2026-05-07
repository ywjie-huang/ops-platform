from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.asset import Asset


def list_assets(
    db: Session,
    *,
    keyword: str = "",
    asset_type: str = "",
    status: str = "",
) -> list[Asset]:
    stmt = select(Asset)
    keyword = keyword.strip()
    asset_type = asset_type.strip()
    status = status.strip()

    if keyword:
        like_value = f"%{keyword}%"
        stmt = stmt.where(
            or_(
                Asset.name.ilike(like_value),
                Asset.ip_address.ilike(like_value),
                Asset.owner.ilike(like_value),
            )
        )
    if asset_type:
        stmt = stmt.where(Asset.asset_type == asset_type)
    if status:
        stmt = stmt.where(Asset.status == status)

    stmt = stmt.order_by(Asset.id.desc())
    return list(db.scalars(stmt).all())


def list_recent_assets(db: Session, limit: int = 5) -> list[Asset]:
    stmt = select(Asset).order_by(Asset.created_at.desc(), Asset.id.desc()).limit(limit)
    return list(db.scalars(stmt).all())


def count_assets_by_status(db: Session) -> dict[str, int]:
    stmt = select(Asset.status, func.count(Asset.id)).group_by(Asset.status)
    return {status: count for status, count in db.execute(stmt).all()}


def count_assets_by_type(db: Session) -> dict[str, int]:
    stmt = select(Asset.asset_type, func.count(Asset.id)).group_by(Asset.asset_type).order_by(func.count(Asset.id).desc())
    return {asset_type: count for asset_type, count in db.execute(stmt).all()}


def get_asset(db: Session, asset_id: int) -> Asset | None:
    return db.get(Asset, asset_id)


def create_asset(
    db: Session,
    *,
    name: str,
    asset_type: str,
    ip_address: str,
    status: str,
    owner: str,
    description: str,
) -> Asset:
    asset = Asset(
        name=name,
        asset_type=asset_type,
        ip_address=ip_address,
        status=status,
        owner=owner,
        description=description,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


def update_asset(
    db: Session,
    asset: Asset,
    *,
    name: str,
    asset_type: str,
    ip_address: str,
    status: str,
    owner: str,
    description: str,
) -> Asset:
    asset.name = name
    asset.asset_type = asset_type
    asset.ip_address = ip_address
    asset.status = status
    asset.owner = owner
    asset.description = description
    db.commit()
    db.refresh(asset)
    return asset


def delete_asset(db: Session, asset: Asset) -> None:
    db.delete(asset)
    db.commit()
