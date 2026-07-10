"""Emergency access controls for high-risk platform entry points.

All controls intentionally default to disabled. Re-enabling a capability requires an
explicit environment variable so a fresh deployment cannot accidentally expose an
unauthenticated remote-control surface.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping

from fastapi import HTTPException, status


_TRUTHY_VALUES = frozenset({"1", "true", "yes", "on"})


def parse_env_bool(value: str | None) -> bool:
    """Return True only for an explicit, recognized truthy environment value."""
    return bool(value and value.strip().lower() in _TRUTHY_VALUES)


@dataclass(frozen=True)
class EmergencyAccessControls:
    """High-risk features that stay closed until explicitly enabled."""

    ssh_terminal: bool = False
    sftp: bool = False
    batch_exec: bool = False
    ssh_key_management: bool = False
    deploy_webhook: bool = False

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "EmergencyAccessControls":
        source = os.environ if environ is None else environ
        return cls(
            ssh_terminal=parse_env_bool(source.get("ENABLE_SSH_TERMINAL")),
            sftp=parse_env_bool(source.get("ENABLE_SFTP")),
            batch_exec=parse_env_bool(source.get("ENABLE_BATCH_EXEC")),
            ssh_key_management=parse_env_bool(source.get("ENABLE_SSH_KEY_MANAGEMENT")),
            deploy_webhook=parse_env_bool(source.get("ENABLE_DEPLOY_WEBHOOK")),
        )


SECURITY_CONTROLS = EmergencyAccessControls.from_env()


def ensure_feature_enabled(enabled: bool, feature_name: str) -> None:
    """Reject access to an emergency-disabled capability with a clear response."""
    if not enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{feature_name}已临时关闭，请联系管理员完成安全配置后再启用",
        )