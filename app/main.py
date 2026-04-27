"""FastAPI application entry point."""
from fastapi import FastAPI
from app.api import router

app = FastAPI(title="运维管理系统", version="0.1.0")
app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok"}
