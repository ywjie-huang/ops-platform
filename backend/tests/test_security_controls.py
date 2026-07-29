from dataclasses import replace

import pytest
from fastapi import HTTPException

from app.api import create_api_router
from app.api import sftp
from app.api import deps
from app.api.deploy import validate_deploy_webhook_signature
from app.core.security_controls import (
    EmergencyAccessControls,
    ensure_feature_enabled,
    parse_env_bool,
)


def route_paths(controls: EmergencyAccessControls) -> set[str]:
    return {route.path for route in create_api_router(controls).routes}


def test_parse_env_bool_accepts_only_explicit_truthy_values():
    assert parse_env_bool(None) is False
    assert parse_env_bool("") is False
    assert parse_env_bool("false") is False
    assert parse_env_bool("0") is False
    assert parse_env_bool("TRUE") is True
    assert parse_env_bool(" yes ") is True
    assert parse_env_bool("on") is True
    assert parse_env_bool("1") is True


def test_controls_load_from_explicit_environment_values():
    controls = EmergencyAccessControls.from_env({
        "ENABLE_SSH_TERMINAL": "true",
        "ENABLE_SFTP": "1",
        "ENABLE_BATCH_EXEC": "yes",
        "ENABLE_DEPLOY_WEBHOOK": "TRUE",
    })

    assert controls == EmergencyAccessControls(
        ssh_terminal=True,
        sftp=True,
        batch_exec=True,
        deploy_webhook=True,
    )


def test_high_risk_routes_are_disabled_by_default():
    controls = EmergencyAccessControls()
    paths = route_paths(controls)

    assert "/api/v1/ws/ssh/{asset_id}" not in paths
    assert not any("/sftp/" in path for path in paths)
    assert "/api/v1/batch-exec/ws/exec" not in paths
    assert "/api/v1/batch-exec/history" in paths
    # SSH 密钥管理已接入 JWT + RBAC，始终注册
    assert any(path.startswith("/api/v1/ssh-keys") for path in paths)
    assert controls.deploy_webhook is False


def test_high_risk_routes_require_explicit_individual_enablement():
    controls = replace(
        EmergencyAccessControls(),
        ssh_terminal=True,
        sftp=True,
        batch_exec=True,
    )
    paths = route_paths(controls)

    assert "/api/v1/ws/ssh/{asset_id}" in paths
    assert any("/sftp/" in path for path in paths)
    assert "/api/v1/batch-exec/ws/exec" in paths
    assert any(path.startswith("/api/v1/ssh-keys") for path in paths)


def test_sftp_routes_require_ssh_terminal_permission(monkeypatch):
    user = object()
    seen = {}

    def has_permission(candidate, code):
        seen["user"] = candidate
        seen["code"] = code
        return True

    monkeypatch.setattr(deps, "has_permission", has_permission)
    dependency = sftp.router.dependencies[0].dependency

    assert dependency(user) is user
    assert seen == {"user": user, "code": "ssh_terminal.connect"}


def test_disabled_feature_guard_returns_service_unavailable():
    with pytest.raises(HTTPException) as exc_info:
        ensure_feature_enabled(False, "部署产物 Webhook")

    assert exc_info.value.status_code == 503
    assert "已临时关闭" in str(exc_info.value.detail)


def test_enabled_feature_guard_allows_request():
    ensure_feature_enabled(True, "部署产物 Webhook")


def test_deploy_webhook_rejects_missing_secret():
    with pytest.raises(HTTPException) as exc_info:
        validate_deploy_webhook_signature(b"{}", "", "")

    assert exc_info.value.status_code == 503
    assert "签名密钥" in str(exc_info.value.detail)


def test_deploy_webhook_rejects_invalid_signature():
    with pytest.raises(HTTPException) as exc_info:
        validate_deploy_webhook_signature(b"{}", "sha256=invalid", "secret")

    assert exc_info.value.status_code == 401


def test_deploy_webhook_accepts_valid_signature():
    import hashlib
    import hmac

    body = b'{"status":"success"}'
    digest = hmac.new(b"secret", body, hashlib.sha256).hexdigest()

    validate_deploy_webhook_signature(body, f"sha256={digest}", "secret")
