"""FastAPI application entry point — 纯 API 模式。"""
import logging
import threading
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import router as api_router
from app.db.database import SessionLocal
from app.db.init_db import init_db
from app.models import alert, alert_event, asset, audit, batch_exec, container, patrol, rbac, ticket, user, system_config, monitoring, ssh_key, scheduled_task  # noqa: F401
from app.services.docker_agent import sync_all_hosts

logger = logging.getLogger(__name__)

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
    # 启动定时任务调度器
    from app.core.scheduler import startup_scheduler
    startup_scheduler()
    # 启动 Docker Agent 后台轮询线程（每 10 秒拉取一次）
    def _poll_docker_agents():
        while True:
            time.sleep(10)
            try:
                db = SessionLocal()
                try:
                    sync_all_hosts(db)
                finally:
                    db.close()
            except Exception as e:
                logger.error("Docker Agent 轮询失败: %s", e)

    t = threading.Thread(target=_poll_docker_agents, daemon=True)
    t.start()
    logger.info("Docker Agent 后台轮询线程已启动")


@app.on_event("shutdown")
def on_shutdown():
    from app.core.scheduler import shutdown_scheduler
    shutdown_scheduler()


@app.get("/health")
def health():
    return {"status": "ok"}
