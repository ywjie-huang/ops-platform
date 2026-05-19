from fastapi import APIRouter

from app.api import auth, users, roles, dashboard, containers, monitoring, reports, audit, password, assets, alerts, tickets, ssh, alertmanager, settings, batch_exec, patrol, ai, docker_mgmt

router = APIRouter(prefix="/api/v1")

# 认证
router.include_router(auth.router)

# 核心业务
router.include_router(dashboard.router)
router.include_router(assets.router)
router.include_router(users.router)
router.include_router(roles.router)

# 业务模块
router.include_router(tickets.router)
router.include_router(alerts.router)
router.include_router(containers.router)
router.include_router(monitoring.router)
router.include_router(reports.router)
router.include_router(audit.router)
router.include_router(password.router)
router.include_router(ssh.router)
router.include_router(alertmanager.router)
router.include_router(settings.router)
router.include_router(batch_exec.router)
router.include_router(patrol.router)
router.include_router(ai.router)
router.include_router(docker_mgmt.router)
