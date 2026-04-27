"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api import router as api_router
from app.config import STATIC_DIR
from app.routes_auth import router as auth_router
from app.routes_pages import router as pages_router

app = FastAPI(title="运维管理系统", version="0.2.0")
app.include_router(pages_router)
app.include_router(auth_router)
app.include_router(api_router)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/health")
def health():
    return {"status": "ok"}
