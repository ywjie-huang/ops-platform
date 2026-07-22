from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.asset import Asset
from app.models.asset import generate_asset_public_id


def list_assets(
    db: Session,
    *,
    keyword: str = "",
    asset_type: str = "",
    status: str = "",
    ssh: str = "",
    ordering: str = "",
) -> list[Asset]:
    stmt = select(Asset)
    keyword = keyword.strip()
    asset_type = asset_type.strip()
    status = status.strip()
    ssh = ssh.strip()

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
    if ssh == "ready":
        stmt = stmt.where(or_(Asset.ssh_key_id.isnot(None), func.coalesce(Asset.ssh_password, "") != ""))
    elif ssh == "key":
        stmt = stmt.where(Asset.ssh_key_id.isnot(None))
    elif ssh == "missing":
        stmt = stmt.where(Asset.ssh_key_id.is_(None), func.coalesce(Asset.ssh_password, "") == "")

    stmt = stmt.order_by(Asset.id.desc())
    items = list(db.scalars(stmt).all())
    return sort_assets(items, ordering)


def _has_text(value: Optional[str]) -> bool:
    return bool(value and value.strip())


def asset_ssh_state(asset: Asset) -> str:
    """与前端 assetDisplay.getAssetSshState 口径保持一致。"""
    if asset.ssh_key_id:
        return "key"
    if asset.ssh_password:
        return "password"
    if _has_text(asset.ssh_username):
        return "partial"
    return "missing"


def asset_completeness(asset: Asset) -> int:
    """与前端 assetDisplay.getAssetCompleteness 口径保持一致。"""
    checks = [
        _has_text(asset.name),
        _has_text(asset.ip_address),
        _has_text(asset.asset_type),
        _has_text(asset.status),
        _has_text(asset.owner),
        _has_text(asset.spec),
        _has_text(asset.os),
        asset_ssh_state(asset) != "missing",
    ]
    return round(sum(1 for ok in checks if ok) / len(checks) * 100)


def asset_risk_score(asset: Asset) -> int:
    """与前端 assetDisplay.assetRiskScore 口径保持一致。"""
    score = 0
    ssh_state = asset_ssh_state(asset)
    completeness = asset_completeness(asset)
    if ssh_state == "missing":
        score += 400
    if ssh_state == "partial":
        score += 260
    if completeness < 65:
        score += 220
    elif completeness < 90:
        score += 140
    if asset.status == "已关机":
        score += 80
    if asset.status == "已删除":
        score += 40
    return score


def sort_assets(items: list[Asset], ordering: str) -> list[Asset]:
    """ordering 采用 Django 风格：'name' 升序 / '-name' 降序；'risk' 表示风险分降序；空值保持默认（id 倒序）。"""
    from datetime import datetime

    ordering = (ordering or "").strip()
    if not ordering:
        return items
    descending = ordering.startswith("-")
    key = ordering.lstrip("-")

    if key == "name":
        return sorted(items, key=lambda a: (a.name or ""), reverse=descending)
    if key == "owner":
        return sorted(items, key=lambda a: (a.owner or ""), reverse=descending)
    if key == "created":
        return sorted(items, key=lambda a: a.created_at or datetime.min, reverse=descending)
    if key == "completeness":
        return sorted(items, key=asset_completeness, reverse=descending)
    # 风险排序：'risk' = 风险分降序（默认），'-risk' = 风险分升序，同分按名称
    return sorted(
        items,
        key=lambda a: (asset_risk_score(a) * (-1 if not descending else 1), a.name or ""),
    )


def count_assets_by_ssh(db: Session) -> dict[str, int]:
    ready_stmt = select(func.count(Asset.id)).where(
        or_(Asset.ssh_key_id.isnot(None), func.coalesce(Asset.ssh_password, "") != "")
    )
    ready = db.scalar(ready_stmt) or 0
    total = db.scalar(select(func.count(Asset.id))) or 0
    return {"ssh_ready": ready, "ssh_missing": total - ready}


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


def get_asset_by_public_id(db: Session, public_id: str) -> Asset | None:
    return db.scalar(select(Asset).where(Asset.public_id == public_id))


def allocate_asset_public_id(db: Session) -> str:
    for _ in range(5):
        public_id = generate_asset_public_id()
        if get_asset_by_public_id(db, public_id) is None:
            return public_id
    raise RuntimeError("Unable to allocate a unique asset public ID")


def create_asset(
    db: Session,
    *,
    name: str,
    asset_type: str,
    ip_address: str,
    status: str,
    owner: str,
    description: str,
    spec: str = "",
    os: str = "",
    ssh_port: int = 22,
    ssh_username: str = "root",
    ssh_password: str = "",
    ssh_key_id: Optional[int] = None,
) -> Asset:
    asset = Asset(
        public_id=allocate_asset_public_id(db),
        name=name,
        asset_type=asset_type,
        ip_address=ip_address,
        status=status,
        owner=owner,
        description=description,
        spec=spec,
        os=os,
        ssh_port=ssh_port,
        ssh_username=ssh_username,
        ssh_password=ssh_password,
        ssh_key_id=ssh_key_id,
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
    spec: str = "",
    os: str = "",
    ssh_port: int = 22,
    ssh_username: str = "root",
    ssh_password: str = "",
    ssh_key_id: Optional[int] = None,
) -> Asset:
    asset.name = name
    asset.asset_type = asset_type
    asset.ip_address = ip_address
    asset.status = status
    asset.owner = owner
    asset.description = description
    asset.spec = spec
    asset.os = os
    asset.ssh_port = ssh_port
    asset.ssh_username = ssh_username
    if ssh_password:  # 只在提供新密码时更新
        asset.ssh_password = ssh_password
    asset.ssh_key_id = ssh_key_id
    db.commit()
    db.refresh(asset)
    return asset


def delete_asset(db: Session, asset: Asset) -> None:
    db.delete(asset)
    db.commit()
