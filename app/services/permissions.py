from dataclasses import dataclass

from fastapi import Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.models.user import User
from app.services.users import get_user


@dataclass
class PermissionResult:
    current_user: User | None
    redirect: RedirectResponse | None = None


def get_current_user(request: Request, db: Session) -> User | None:
    session_user_id = request.cookies.get("ops_session")
    if not session_user_id:
        return None
    if not session_user_id.isdigit():
        return None
    return get_user(db, int(session_user_id))


def get_permission_codes(user: User | None) -> set[str]:
    if not user:
        return set()
    return {
        permission.code
        for role in user.roles
        for permission in role.permissions
    }


def has_permission(user: User | None, code: str) -> bool:
    return code in get_permission_codes(user)


def build_permission_map(user: User | None) -> dict[str, bool]:
    return {code: True for code in get_permission_codes(user)}


def require_permission(request: Request, db: Session, code: str) -> PermissionResult:
    current_user = get_current_user(request, db)
    if current_user is None:
        return PermissionResult(
            current_user=None,
            redirect=RedirectResponse(url="/login", status_code=302),
        )
    if not has_permission(current_user, code):
        return PermissionResult(
            current_user=current_user,
            redirect=RedirectResponse(url="/forbidden", status_code=302),
        )
    return PermissionResult(current_user=current_user)
