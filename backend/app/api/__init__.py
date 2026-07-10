from fastapi import APIRouter

from app.api import (
    ai,
    alertmanager,
    alerts,
    assets,
    audit,
    auth,
    batch_exec,
    batch_presets,
    containers,
    dashboard,
    deploy,
    docker_mgmt,
    monitoring,
    password,
    patrol,
    reports,
    roles,
    scheduler,
    settings,
    sftp,
    ssh_keys,
    ssh_terminal,
    tickets,
    users,
)
from app.core.security_controls import EmergencyAccessControls, SECURITY_CONTROLS


def create_api_router(controls: EmergencyAccessControls = SECURITY_CONTROLS) -> APIRouter:
    """Build the v1 API router with emergency-closed high-risk capabilities."""
    api_router = APIRouter(prefix="/api/v1")

    # 认证
    api_router.include_router(auth.router)

    # 核心业务
    api_router.include_router(dashboard.router)
    api_router.include_router(assets.router)
    api_router.include_router(users.router)
    api_router.include_router(roles.router)

    # 业务模块
    api_router.include_router(tickets.router)
    api_router.include_router(alerts.router)
    api_router.include_router(containers.router)
    api_router.include_router(monitoring.router)
    api_router.include_router(reports.router)
    api_router.include_router(audit.router)
    api_router.include_router(password.router)
    api_router.include_router(alertmanager.router)
    api_router.include_router(settings.router)
    api_router.include_router(batch_exec.router)
    api_router.include_router(batch_presets.router)
    api_router.include_router(patrol.router)
    api_router.include_router(ai.router)
    api_router.include_router(docker_mgmt.router)

    # 紧急止血：以下高风险入口默认不注册，必须通过环境变量显式开启。
    if controls.ssh_terminal:
        api_router.include_router(ssh_terminal.router)
    if controls.sftp:
        api_router.include_router(sftp.router)
    if controls.batch_exec:
        api_router.include_router(batch_exec.websocket_router)
    if controls.ssh_key_management:
        api_router.include_router(ssh_keys.router)

    # 定时任务
    api_router.include_router(scheduler.router)

    # 应用发布（产物 Webhook 在端点级别通过独立开关保护）
    api_router.include_router(deploy.router)

    return api_router


router = create_api_router()