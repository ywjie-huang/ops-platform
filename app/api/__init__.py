from fastapi import APIRouter
from app.api import assets, alerts, tickets, audit

router = APIRouter(prefix="/api/v1")
router.include_router(assets.router)
router.include_router(alerts.router)
router.include_router(tickets.router)
router.include_router(audit.router)
