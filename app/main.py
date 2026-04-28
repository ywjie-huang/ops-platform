"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api import router as api_router
from app.config import STATIC_DIR, TEMPLATES_DIR
from app.db.init_db import init_db
from app.routes_auth import router as auth_router
from app.routes_pages import router as pages_router

app = FastAPI(title="运维管理系统", version="0.3.0")
app.include_router(pages_router)
app.include_router(auth_router)
app.include_router(api_router)

if not STATIC_DIR.exists():
    raise RuntimeError(f"Static directory not found: {STATIC_DIR}")

if not TEMPLATES_DIR.exists():
    raise RuntimeError(f"Templates directory not found: {TEMPLATES_DIR}")

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}
