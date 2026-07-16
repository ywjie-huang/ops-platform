# Asset Public URL Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give managed hosts canonical `/assets/hosts/{public_id}` URLs without exposing database auto-increment IDs.

**Architecture:** Keep `Asset.id` as the internal primary key and add a stable, unique `public_id` generated from UUIDv4. The backend exposes a permission-protected public-ID lookup while retaining integer command endpoints; the frontend uses the public lookup for canonical detail routes and resolves old numeric links once before replacing the URL.

**Tech Stack:** FastAPI, SQLAlchemy 2, PyMySQL/MySQL, pytest, Vue 3, Vue Router 4, TypeScript, Node test runner

---

### Task 1: Asset public identifier model and lookup

**Files:**
- Modify: `backend/app/models/asset.py`
- Modify: `backend/app/services/assets.py`
- Create: `backend/tests/test_asset_public_id.py`

- [ ] **Step 1: Write failing generation and lookup tests**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.asset import Asset, generate_asset_public_id
from app.services.assets import allocate_asset_public_id, get_asset_by_public_id


def test_generate_asset_public_id_is_prefixed_lowercase_uuid_hex():
    public_id = generate_asset_public_id()
    assert public_id.startswith("ast_")
    assert len(public_id) == 36
    assert public_id[4:].isalnum()
    assert public_id == public_id.lower()


def test_asset_public_ids_are_unique():
    assert generate_asset_public_id() != generate_asset_public_id()


def test_get_asset_by_public_id_returns_matching_asset():
    engine = create_engine("sqlite://")
    Asset.__table__.create(engine)
    with Session(engine) as db:
        asset = Asset(name="web-01", asset_type="host", ip_address="10.0.0.1")
        db.add(asset)
        db.commit()
        assert get_asset_by_public_id(db, asset.public_id).id == asset.id
        assert get_asset_by_public_id(db, "ast_" + "0" * 32) is None


def test_allocate_asset_public_id_retries_a_detected_collision(monkeypatch):
    engine = create_engine("sqlite://")
    Asset.__table__.create(engine)
    with Session(engine) as db:
        collision = "ast_" + "a" * 32
        available = "ast_" + "b" * 32
        db.add(Asset(public_id=collision, name="web-01", asset_type="host", ip_address="10.0.0.1"))
        db.commit()
        generated = iter((collision, available))
        monkeypatch.setattr("app.services.assets.generate_asset_public_id", lambda: next(generated))
        assert allocate_asset_public_id(db) == available
```

- [ ] **Step 2: Run tests and confirm they fail**

Run: `cd backend; python -m pytest tests/test_asset_public_id.py -q`

Expected: collection fails because `generate_asset_public_id` and `get_asset_by_public_id` do not exist.

- [ ] **Step 3: Add the model field and service lookup**

```python
# backend/app/models/asset.py
from uuid import uuid4


def generate_asset_public_id() -> str:
    return f"ast_{uuid4().hex}"


class Asset(Base):
    public_id: Mapped[str] = mapped_column(
        String(36),
        default=generate_asset_public_id,
        nullable=False,
        unique=True,
        index=True,
    )
```

```python
# backend/app/services/assets.py
def get_asset_by_public_id(db: Session, public_id: str) -> Asset | None:
    return db.scalar(select(Asset).where(Asset.public_id == public_id))


def allocate_asset_public_id(db: Session) -> str:
    for _ in range(5):
        public_id = generate_asset_public_id()
        if get_asset_by_public_id(db, public_id) is None:
            return public_id
    raise RuntimeError("Unable to allocate a unique asset public ID")
```

Pass `public_id=allocate_asset_public_id(db)` when `create_asset()` constructs
the model. The database unique index remains the final concurrency guard.

- [ ] **Step 4: Run the focused tests**

Run: `cd backend; python -m pytest tests/test_asset_public_id.py -q`

Expected: 4 tests pass.

- [ ] **Step 5: Commit model and service**

```bash
git add backend/app/models/asset.py backend/app/services/assets.py backend/tests/test_asset_public_id.py
git commit -m "feat(assets): add stable public identifiers"
```

### Task 2: Existing-database backfill

**Files:**
- Modify: `backend/app/db/init_db.py`
- Modify: `backend/tests/test_asset_public_id.py`

- [ ] **Step 1: Add a failing migration contract test**

```python
from pathlib import Path


def test_asset_public_id_migration_adds_backfills_and_indexes_column():
    source = Path("app/db/init_db.py").read_text(encoding="utf-8")
    assert "def _ensure_asset_public_ids()" in source
    assert "ADD COLUMN public_id VARCHAR(36) NULL" in source
    assert "UPDATE assets SET public_id = %s WHERE id = %s" in source
    assert "MODIFY COLUMN public_id VARCHAR(36) NOT NULL" in source
    assert "CREATE UNIQUE INDEX ux_assets_public_id" in source
    assert "_ensure_asset_public_ids()" in source
```

- [ ] **Step 2: Run the migration test and confirm it fails**

Run: `cd backend; python -m pytest tests/test_asset_public_id.py::test_asset_public_id_migration_adds_backfills_and_indexes_column -q`

Expected: FAIL because the migration helper is absent.

- [ ] **Step 3: Implement idempotent migration and backfill**

Add `_ensure_asset_public_ids()` beside `_ensure_asset_ssh_columns()`. It connects to MySQL, adds a nullable `VARCHAR(36)` column when missing, selects rows where the value is null or empty, assigns `generate_asset_public_id()` per row, changes the column to non-null, and creates `ux_assets_public_id` only when no index currently covers `public_id`. Call it from `init_db()` immediately after `Base.metadata.create_all()` and before seeding.

```python
def _ensure_asset_public_ids() -> None:
    conn = pymysql.connect(
        host=MYSQL_HOST, port=MYSQL_PORT, user=MYSQL_USER,
        password=MYSQL_PASSWORD, database=MYSQL_DATABASE,
    )
    try:
        with conn.cursor() as cur:
            cur.execute("SHOW COLUMNS FROM assets LIKE 'public_id'")
            if cur.fetchone() is None:
                cur.execute("ALTER TABLE assets ADD COLUMN public_id VARCHAR(36) NULL")
            cur.execute("SELECT id FROM assets WHERE public_id IS NULL OR public_id = ''")
            for (asset_id,) in cur.fetchall():
                cur.execute(
                    "UPDATE assets SET public_id = %s WHERE id = %s",
                    (generate_asset_public_id(), asset_id),
                )
            cur.execute("ALTER TABLE assets MODIFY COLUMN public_id VARCHAR(36) NOT NULL")
            cur.execute("SHOW INDEX FROM assets WHERE Column_name = 'public_id'")
            if cur.fetchone() is None:
                cur.execute("CREATE UNIQUE INDEX ux_assets_public_id ON assets (public_id)")
        conn.commit()
    finally:
        conn.close()
```

- [ ] **Step 4: Run all asset public-ID tests**

Run: `cd backend; python -m pytest tests/test_asset_public_id.py -q`

Expected: 5 tests pass.

- [ ] **Step 5: Commit migration**

```bash
git add backend/app/db/init_db.py backend/tests/test_asset_public_id.py
git commit -m "feat(assets): backfill public identifiers"
```

### Task 3: Permission-protected public lookup API

**Files:**
- Modify: `backend/app/api/assets.py`
- Modify: `backend/tests/test_asset_public_id.py`

- [ ] **Step 1: Add failing response and route tests**

```python
from app.api.assets import _asset_dict, router


def test_asset_response_exposes_public_id():
    asset = Asset(
        id=16,
        public_id="ast_" + "a" * 32,
        name="web-01",
        asset_type="host",
        ip_address="10.0.0.1",
    )
    assert _asset_dict(asset)["public_id"] == asset.public_id


def test_public_asset_route_is_registered_before_integer_route():
    paths = [route.path for route in router.routes]
    assert "/assets/public/{public_id}" in paths
    assert paths.index("/assets/public/{public_id}") < paths.index("/assets/{asset_id}")
```

- [ ] **Step 2: Run tests and confirm they fail**

Run: `cd backend; python -m pytest tests/test_asset_public_id.py -q`

Expected: response assertion and route assertion fail.

- [ ] **Step 3: Add public ID to serialization and a read-only endpoint**

Import `get_asset_by_public_id`, include `"public_id": a.public_id` in `_asset_dict`, and register this endpoint before `/{asset_id}`:

```python
@router.get("/public/{public_id}")
def api_get_asset_by_public_id(
    public_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("assets.view")),
):
    asset = get_asset_by_public_id(db, public_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="资产不存在")
    return {"code": 0, "data": _asset_dict(asset)}
```

- [ ] **Step 4: Run focused backend tests**

Run: `cd backend; python -m pytest tests/test_asset_public_id.py -q`

Expected: 7 tests pass.

- [ ] **Step 5: Commit API changes**

```bash
git add backend/app/api/assets.py backend/tests/test_asset_public_id.py
git commit -m "feat(assets): expose public host lookup"
```

### Task 4: Canonical frontend routes and legacy URL resolution

**Files:**
- Modify: `frontend/src/router/modules/routes.ts`
- Modify: `frontend/src/api/assets.ts`
- Modify: `frontend/src/views/assets/AssetListView.vue`
- Modify: `frontend/src/views/assets/AssetDetailView.vue`
- Modify: `frontend/src/utils/dashboard.ts`
- Modify: `frontend/src/utils/dashboard.test.mjs`
- Create: `frontend/src/router/modules/assetRoutes.test.mjs`

- [ ] **Step 1: Write failing route and source-contract tests**

```javascript
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'

const { default: routes } = await import('./routes.ts')
const assetGroup = routes.find((route) => route.path === '/assets')
const listSource = readFileSync(new URL('../../views/assets/AssetListView.vue', import.meta.url), 'utf8')
const detailSource = readFileSync(new URL('../../views/assets/AssetDetailView.vue', import.meta.url), 'utf8')
const apiSource = readFileSync(new URL('../../api/assets.ts', import.meta.url), 'utf8')

test('asset routes expose canonical host collection and detail paths', () => {
  assert.equal(assetGroup.redirect, '/assets/hosts')
  assert.ok(assetGroup.children.some((route) => route.path === 'hosts' && route.name === 'AssetList'))
  assert.ok(assetGroup.children.some((route) => route.path === 'hosts/:publicId' && route.name === 'AssetDetail'))
})

test('legacy list and numeric detail routes remain resolvable', () => {
  assert.ok(assetGroup.children.some((route) => route.path === 'list' && route.redirect === '/assets/hosts'))
  assert.ok(assetGroup.children.some((route) => route.path === ':legacyId(\\d+)' && route.name === 'LegacyAssetDetail'))
})

test('asset screens use public IDs for canonical navigation and lookup', () => {
  assert.match(listSource, /\/assets\/hosts\/\$\{row\.public_id\}/)
  assert.match(detailSource, /route\.params\.publicId/)
  assert.match(detailSource, /getAssetByPublicId/)
  assert.match(apiSource, /\/assets\/public\/\$\{publicId\}/)
})
```

- [ ] **Step 2: Run frontend route tests and confirm they fail**

Run: `cd frontend; node --experimental-strip-types --test src/router/modules/assetRoutes.test.mjs`

Expected: tests fail on the old `list`, `:id`, and integer lookup contracts.

- [ ] **Step 3: Implement canonical and compatibility routes**

In `routes.ts`, make `hosts` the list route, make `hosts/:publicId` the canonical detail route, add `list` as a hidden redirect, and keep `:legacyId(\\d+)` as a hidden compatibility route using the same detail component. Set all asset `activeMenu` values to `/assets/hosts`.

```typescript
{
  path: 'hosts',
  name: 'AssetList',
  component: () => import('@/views/assets/AssetListView.vue'),
  meta: { title: '主机管理', icon: 'Platform', permission: 'assets.view' },
},
{
  path: 'hosts/:publicId',
  name: 'AssetDetail',
  component: () => import('@/views/assets/AssetDetailView.vue'),
  meta: { title: '资产详情', hidden: true, permission: 'assets.view', parentTitle: '主机管理', activeMenu: '/assets/hosts' },
},
{
  path: 'list',
  redirect: '/assets/hosts',
  meta: { hidden: true },
},
{
  path: ':legacyId(\\d+)',
  name: 'LegacyAssetDetail',
  component: () => import('@/views/assets/AssetDetailView.vue'),
  meta: { title: '资产详情', hidden: true, permission: 'assets.view', parentTitle: '主机管理', activeMenu: '/assets/hosts' },
},
```

- [ ] **Step 4: Implement public lookup and legacy URL replacement**

Add `getAssetByPublicId(publicId: string)` to `api/assets.ts`. Add `public_id: string` to the list/detail asset types. The list pushes `/assets/hosts/${row.public_id}`. The detail screen:

1. Fetches with `getAssetByPublicId(String(route.params.publicId))` on canonical routes.
2. Fetches with existing `getAsset(Number(route.params.legacyId))` on legacy routes.
3. Calls `router.replace(`/assets/hosts/${asset.public_id}`)` after a legacy fetch.
4. Keeps `asset.id` for update, monitoring, and SSH command URLs.
5. Returns to `/assets/hosts`.

Update the dashboard primary action and its existing assertion from `/assets/list` to `/assets/hosts`.

- [ ] **Step 5: Run the frontend tests**

Run: `cd frontend; node --experimental-strip-types --test src/router/modules/assetRoutes.test.mjs src/utils/dashboard.test.mjs src/views/assets/assetSshEntryPolicy.test.mjs`

Expected: all selected tests pass.

- [ ] **Step 6: Commit frontend routing**

```bash
git add frontend/src/router/modules/routes.ts frontend/src/router/modules/assetRoutes.test.mjs frontend/src/api/assets.ts frontend/src/views/assets/AssetListView.vue frontend/src/views/assets/AssetDetailView.vue frontend/src/utils/dashboard.ts frontend/src/utils/dashboard.test.mjs
git commit -m "feat(assets): use canonical public host URLs"
```

### Task 5: Integrated verification

**Files:**
- Modify only if a verification failure reveals a defect in files already listed above.

- [ ] **Step 1: Run backend asset tests**

Run: `cd backend; python -m pytest tests/test_asset_public_id.py -q`

Expected: all tests pass.

- [ ] **Step 2: Run the broader backend suite**

Run: `cd backend; python -m pytest -q`

Expected: suite passes, or any environment-only failure is recorded with its exact message.

- [ ] **Step 3: Run frontend tests and production build**

Run: `cd frontend; node --experimental-strip-types --test src/router/modules/assetRoutes.test.mjs src/utils/dashboard.test.mjs src/views/assets/assetSshEntryPolicy.test.mjs`

Expected: all selected tests pass.

Run: `cd frontend; npm run build`

Expected: `vue-tsc -b && vite build` exits with code 0.

- [ ] **Step 4: Confirm only intended changes are committed**

Run: `git status --short`

Expected: pre-existing unrelated worktree changes may remain, but every file changed for this feature is committed and no unrelated file was included in feature commits.
