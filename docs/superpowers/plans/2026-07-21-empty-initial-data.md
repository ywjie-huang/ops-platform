# Empty Initial Data Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make new deployments start without demo assets, tickets, or inherited monitoring rules, while safely cleaning untouched legacy demo records.

**Architecture:** Database initialization will replace demo seeding with an idempotent exact-match cleanup. Monitoring integrations will use empty defaults and short-circuit before creating HTTP clients when no endpoint is configured.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2, httpx, pytest

---

### Task 1: Legacy demo data cleanup

**Files:**
- Create: `backend/tests/test_empty_initial_data.py`
- Modify: `backend/app/db/init_db.py`

- [x] **Step 1: Write failing tests for exact-match cleanup**

Create SQLite-backed tests that insert the original three demo assets and three demo tickets, call `_cleanup_legacy_demo_data(db)`, and assert all six are deleted. Add separate records with one modified field and assert they remain.

```python
def test_cleanup_removes_only_untouched_legacy_demo_records(db):
    seed_legacy_demo_records(db)
    modified = Asset(name="web-prod-01", ip_address="10.10.1.12", owner="real-owner", ...)
    db.add(modified)
    db.commit()

    _cleanup_legacy_demo_data(db)
    db.commit()

    assert db.scalar(select(func.count()).select_from(Asset)) == 1
    assert db.scalar(select(Asset).where(Asset.id == modified.id)) is not None
```

- [x] **Step 2: Run the focused test and verify RED**

Run: `python -m pytest backend/tests/test_empty_initial_data.py -v`

Expected: import failure because `_cleanup_legacy_demo_data` does not exist.

- [x] **Step 3: Implement exact-match cleanup and remove seed calls**

Add immutable tuples containing every original stable field. Delete matching demo tickets before matching assets, using SQLAlchemy `delete()` with conjunctions across all fields. Remove `_seed_assets()` and `_seed_tickets()` from `init_db()` and call `_cleanup_legacy_demo_data(db)` instead.

```python
def _cleanup_legacy_demo_data(db: Session) -> None:
    for spec in _LEGACY_DEMO_TICKETS:
        db.execute(delete(Ticket).where(*(getattr(Ticket, key) == value for key, value in spec.items())))
    for spec in _LEGACY_DEMO_ASSETS:
        db.execute(delete(Asset).where(*(getattr(Asset, key) == value for key, value in spec.items())))
    db.flush()
```

- [x] **Step 4: Run focused tests and verify GREEN**

Run: `python -m pytest backend/tests/test_empty_initial_data.py -v`

Expected: all cleanup tests pass.

### Task 2: Empty monitoring defaults

**Files:**
- Modify: `backend/tests/test_empty_initial_data.py`
- Modify: `backend/app/core/config.py`
- Modify: `backend/app/core/settings.py`
- Modify: `backend/app/services/prometheus.py`
- Modify: `backend/app/services/alertmanager.py`

- [x] **Step 1: Write failing tests for unconfigured integrations**

Patch `httpx.AsyncClient` to raise if constructed. Assert Prometheus health is false, targets/instances/host summaries are empty, Alertmanager health is false, and alerts/rules are empty when the resolved URL is empty.

```python
async def test_unconfigured_alert_rules_return_empty_without_http(monkeypatch):
    monkeypatch.setattr(alertmanager, "get_prometheus_url", lambda db: "")
    monkeypatch.setattr(httpx, "AsyncClient", fail_if_called)
    assert await alertmanager.get_rules(object()) == []
```

- [x] **Step 2: Run focused tests and verify RED**

Run: `python -m pytest backend/tests/test_empty_initial_data.py -v`

Expected: HTTP client construction assertion fails.

- [x] **Step 3: Implement empty defaults and service short-circuits**

Read integration defaults from environment variables and default them to an empty string. Add `if not url: return ...` guards immediately after URL resolution in every externally calling public service used by monitoring and alert pages.

```python
PROMETHEUS_URL: Final = os.environ.get("PROMETHEUS_URL", "").strip().rstrip("/")
ALERTMANAGER_URL: Final = os.environ.get("ALERTMANAGER_URL", "").strip().rstrip("/")
```

- [x] **Step 4: Run focused tests and verify GREEN**

Run: `python -m pytest backend/tests/test_empty_initial_data.py -v`

Expected: all empty-configuration tests pass without constructing an HTTP client.

### Task 3: Regression verification and delivery

**Files:**
- Modify: `docs/superpowers/plans/2026-07-21-empty-initial-data.md` (checkbox status only)

- [x] **Step 1: Run backend full suite**

Run: `python -m pytest backend`

Expected: all tests pass.

- [x] **Step 2: Inspect final diff and initialization calls**

Run: `git diff --check` and `rg -n "_seed_assets|_seed_tickets|172\\.16\\.24\\.31" backend/app`

Expected: no whitespace errors, seed calls, or environment-specific monitoring addresses remain.

- [ ] **Step 3: Commit implementation**

```bash
git add backend/app backend/tests/test_empty_initial_data.py docs/superpowers/plans/2026-07-21-empty-initial-data.md
git commit -m "fix(init): remove demo operational data"
```
