# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Enterprise-grade Ops Management Platform (运维管理平台) with fully decoupled frontend/backend architecture. Provides host monitoring (Prometheus), alert management (Alertmanager webhook), Kubernetes container discovery, Docker monitoring (agent pull model), SSH web terminal (xterm.js + paramiko + WebSocket + SFTP), batch execution, patrol/inspection, ticket collaboration, and RBAC permissions.

## Development Commands

### Backend (FastAPI)

```bash
cd backend
python -m venv venv && .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- API docs: `http://localhost:8000/docs`
- Tests: `cd backend && python -m pytest`
- Lint/format (dev deps): `black`, `ruff`, `mypy` (no config files yet)

### Frontend (Vue 3 + Vite)

```bash
cd frontend
npm install
npm run dev          # Vite dev server on port 3000
npm run build        # vue-tsc -b && vite build (type check + production build)
npm run preview      # Preview production build
```

### Docker Deployment

```bash
cd docker
cp .env.example .env
docker compose up -d                          # Start all services
docker compose --profile agent up -d          # Include optional Docker agent
docker compose logs -f backend                # View backend logs
docker compose up -d --build                  # Rebuild images
```

## Architecture

### Three-Layer Backend (`backend/app/`)

- **`api/`** — 22 FastAPI route modules. All endpoints prefixed `/api/v1`. Unified response: `{ "code": 0, "msg": "...", "data": {...} }`. Pagination: `{ items, total, page, page_size }`.
- **`services/`** — Business logic layer (21 modules). External integrations: `prometheus.py`, `alertmanager.py`, `k8s.py`, `docker_agent.py`.
- **`models/`** — 16 SQLAlchemy model files using `DeclarativeBase`.
- **`core/`** — `config.py` (constants/env vars), `jwt.py` (HS256, 12h expiry), `settings.py` (DB-first config with fallback to `config.py`), `pagination.py`.
- **`db/`** — `database.py` (PyMySQL + SQLAlchemy, pool_size=10), `init_db.py` (auto-create DB, run ALTER TABLE migrations, seed defaults).

### Frontend SPA (`frontend/src/`)

- **`api/`** — 20 API modules + shared Axios instance (`request.ts`) with JWT injection, 401 auto-redirect.
- **`views/`** — 15 view directories matching navigation structure.
- **`stores/`** — Pinia: `auth.ts` (login/user/permissions), `app.ts` (sidebar state).
- **`router/`** — `routes.ts` with lazy-loaded views, route guards check JWT + permissions via `meta.permission`.
- **`components/`** — Shared components (Sparkline, AlertTrendChart — pure SVG, no chart library).
- **`hooks/`** — `usePagination.ts` composable.
- **`utils/`** — `auth.ts` (localStorage token), `icons.ts` (26 Element Plus icons registered selectively).
- Path alias: `@` → `src/`. Element Plus auto-imported via `unplugin-auto-import` + `unplugin-vue-components`.

### Key Architectural Patterns

- **Auth/permissions**: `Bearer <JWT>` header. Dependency injection via `app/api/deps.py`: `get_current_api_user`, `api_permission_required(code)`.
- **DB-first config**: System config read from DB first, fallback to `config.py` constants (`app/core/settings.py`). Configurable via UI at Settings page.
- **Auto-migration**: `init_db()` on startup — creates DB/tables, ALTER TABLE for new columns, seeds default admin (`admin`/`admin123`), permissions, roles.
- **WebSocket endpoints**: SSH terminal (`/api/v1/ws/ssh/{asset_id}`), batch execution (`/api/v1/batch-exec/ws/exec`).
- **Background threads**: Docker Agent polling every 10 seconds on startup.
- **Vite proxy**: `/api` → `http://localhost:8000` with WebSocket support and client IP forwarding.

### External Dependencies

| Service | Config Location | Notes |
|---------|----------------|-------|
| MySQL | `backend/app/core/config.py` + env vars (`MYSQL_HOST/PORT/USER/PASSWORD/DATABASE`) | Default: `localhost:3306`, `root`/`123456`, DB: `ops_platform` |
| Prometheus | Config center UI or `config.py` → `PROMETHEUS_URL` | Host metrics via node_exporter |
| Alertmanager | Config center UI or `config.py` → `ALERTMANAGER_URL` | Webhook push to `/api/v1/alertmanager/webhook` |
| Kubernetes | Per-cluster in DB | API Server URL + ServiceAccount Token |
| Docker Agent | Per-host in DB | HTTP pull model, port 9001 |

### Commit Style

Conventional commits (Chinese/English mix): `feat(scope):`, `fix(scope):`, `refactor:`, `docs:`, `perf:`.
