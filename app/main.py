"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import router as api_router
from app.config import STATIC_DIR, TEMPLATES_DIR
from app.db.init_db import init_db
from app.models import alert, asset, audit, container, monitoring, rbac, ticket, user  # noqa: F401
from app.routes_auth import router as auth_router
from app.routes_pages import router as pages_router

app = FastAPI(title="运维管理系统", version="0.7.0")

# CORS — 支持前后端分离开发
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制为具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 路由（v1）
app.include_router(api_router)

# 页面路由（兼容旧版 SSR）
app.include_router(pages_router)
app.include_router(auth_router)

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
