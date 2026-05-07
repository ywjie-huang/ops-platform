"""API 依赖注入：认证 + 权限校验。"""
from fastapi import Cookie, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.jwt import decode_access_token
from app.db.database import get_db
from app.models.user import User
from app.services_permissions import get_permission_codes, has_permission
from app.services_users import get_user


def get_current_api_user(
    request: Request,
    db: Session = Depends(get_db),
    access_token: str | None = Cookie(None),
) -> User:
    """从 JWT 或 Cookie 中获取当前用户（API 优先用 Header）。"""
    # 优先 Authorization header
    auth_header = request.headers.get("Authorization", "")
    token = None
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    elif access_token:
        token = access_token

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录或登录已失效",
        )

    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录已过期，请重新登录",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的登录凭证",
        )

    user = get_user(db, int(user_id))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
        )
    return user


def api_permission_required(code: str):
    """API 权限校验装饰器。"""
    def dependency(current_user: User = Depends(get_current_api_user)):
        if not has_permission(current_user, code):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限执行该操作",
            )
        return current_user
    return dependency


def optional_api_user(
    request: Request,
    db: Session = Depends(get_db),
    access_token: str | None = Cookie(None),
) -> User | None:
    """可选认证：未登录返回 None，不抛异常。"""
    auth_header = request.headers.get("Authorization", "")
    token = None
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    elif access_token:
        token = access_token

    if not token:
        return None

    payload = decode_access_token(token)
    if payload is None:
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    return get_user(db, int(user_id))
