"""SSE 端点的 query-param token 鉴权。

EventSource 无法自定义请求头，因此 SSE 鉴权走 ``?token=<JWT>``，
无法复用 FastAPI 的依赖注入鉴权。此模块封装与 WebSocket 鉴权一致的校验链：
decode → 黑名单 → 取用户 → 权限，供 Docker / K8s 日志 SSE 流共用。
"""
from __future__ import annotations

from app.core.jwt import decode_access_token
from app.db.database import SessionLocal
from app.models.user import User
from app.services.permissions import has_permission
from app.services.token_blacklist import is_revoked
from app.services.users import get_user


def validate_stream_token(token: str | None, permission: str) -> tuple[User | None, str | None]:
    """校验 ``?token=`` 里的 JWT，返回 (user, err)。

    ``permission`` 为该 SSE 端点要求的权限码。失败时调用方应 ``raise HTTPException(401)``：
    EventSource 规范下首次响应非 200 → ``readyState=CLOSED`` 且不自动重连。
    """
    if not token or not token.strip():
        return None, "Authentication required"
    payload = decode_access_token(token)
    if payload is None:
        return None, "Authentication failed"
    if is_revoked(payload.get("jti")):
        return None, "Session expired"
    subject = payload.get("sub")
    if isinstance(subject, bool):
        return None, "Authentication failed"
    try:
        user_id = int(subject)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None, "Authentication failed"

    db = SessionLocal()
    try:
        user = get_user(db, user_id)
        if user is None:
            return None, "Authentication failed"
        if not has_permission(user, permission):
            return None, "Permission denied"
        return user, None
    finally:
        db.close()
