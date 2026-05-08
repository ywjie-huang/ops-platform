"""FastAPI application entry point — 纯 API 模式。"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import router as api_router
from app.db.init_db import init_db
from app.models import alert, asset, audit, container, monitoring, rbac, ticket, user  # noqa: F401

app = FastAPI(title="运维管理系统 API", version="1.0.0")

# CORS — 前后端分离
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制为具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 路由（v1）
app.include_router(api_router)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}
