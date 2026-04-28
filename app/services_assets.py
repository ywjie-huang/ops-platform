from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.asset import Asset


def list_assets(db: Session) -> list[Asset]:
    return list(db.scalars(select(Asset).order_by(Asset.id.desc())).all())


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
