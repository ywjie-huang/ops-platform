from datetime import datetime
from pathlib import Path
from string import hexdigits

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.assets import _asset_dict, router
from app.models.asset import Asset, generate_asset_public_id
from app.models.container import ContainerCluster  # noqa: F401
from app.models.ssh_key import SSHKey
from app.services.assets import allocate_asset_public_id, get_asset_by_public_id


def _sqlite_session() -> tuple[Session, object]:
    engine = create_engine("sqlite://")
    SSHKey.__table__.create(engine)
    Asset.__table__.create(engine)
    return Session(engine), engine


def test_generate_asset_public_id_is_prefixed_lowercase_uuid_hex():
    public_id = generate_asset_public_id()

    assert public_id.startswith("ast_")
    assert len(public_id) == 36
    assert all(char in hexdigits.lower() for char in public_id[4:])
    assert public_id == public_id.lower()


def test_asset_public_ids_are_unique():
    assert generate_asset_public_id() != generate_asset_public_id()


def test_get_asset_by_public_id_returns_matching_asset():
    db, engine = _sqlite_session()
    try:
        asset = Asset(name="web-01", asset_type="host", ip_address="10.0.0.1")
        db.add(asset)
        db.commit()

        assert get_asset_by_public_id(db, asset.public_id).id == asset.id
        assert get_asset_by_public_id(db, "ast_" + "0" * 32) is None
    finally:
        db.close()
        engine.dispose()


def test_allocate_asset_public_id_retries_a_detected_collision(monkeypatch):
    db, engine = _sqlite_session()
    try:
        collision = "ast_" + "a" * 32
        available = "ast_" + "b" * 32
        db.add(
            Asset(
                public_id=collision,
                name="web-01",
                asset_type="host",
                ip_address="10.0.0.1",
            )
        )
        db.commit()
        generated = iter((collision, available))
        monkeypatch.setattr(
            "app.services.assets.generate_asset_public_id",
            lambda: next(generated),
        )

        assert allocate_asset_public_id(db) == available
    finally:
        db.close()
        engine.dispose()


def test_asset_public_id_migration_adds_backfills_and_indexes_column():
    init_db_path = Path(__file__).parents[1] / "app" / "db" / "init_db.py"
    source = init_db_path.read_text(encoding="utf-8")

    assert "def _ensure_asset_public_ids()" in source
    assert "ADD COLUMN public_id VARCHAR(36) NULL" in source
    assert "UPDATE assets SET public_id = %s WHERE id = %s" in source
    assert "MODIFY COLUMN public_id VARCHAR(36) NOT NULL" in source
    assert "CREATE UNIQUE INDEX ux_assets_public_id" in source
    assert "_ensure_asset_public_ids()" in source


def test_asset_response_exposes_public_id():
    asset = Asset(
        id=16,
        public_id="ast_" + "a" * 32,
        name="web-01",
        asset_type="host",
        ip_address="10.0.0.1",
        created_at=datetime(2026, 7, 16, 10, 0, 0),
    )

    assert _asset_dict(asset)["public_id"] == asset.public_id


def test_public_asset_route_is_registered_before_integer_route():
    paths = [route.path for route in router.routes]

    assert "/assets/public/{public_id}" in paths
    assert paths.index("/assets/public/{public_id}") < paths.index(
        "/assets/{asset_id}"
    )
