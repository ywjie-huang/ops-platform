"""认证 API：登录 / 登出 / 当前用户信息。"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.jwt import create_access_token
from app.db.database import get_db
from app.models.user import User
from app.api.deps import get_current_api_user
from app.services_auth import authenticate_user
from app.services_audit import write_log
from app.services_permissions import build_permission_map

router = APIRouter(prefix="/auth", tags=["认证"])


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserInfo(BaseModel):
    id: int
    username: str
    full_name: str
    roles: list[str]
    permissions: dict[str, bool]


@router.post("/login")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, body.username, body.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="账号或密码不正确",
        )
    write_log(
        db, user=user, action="login", target_type="auth",
        target_name=user.username,
        ip_address="",
    )
    db.commit()

    token = create_access_token({"sub": str(user.id), "username": user.username})
    return {
        "code": 0,
        "msg": "登录成功",
        "data": {
            "access_token": token,
            "token_type": "bearer",
        },
    }


@router.get("/me")
def get_me(current_user: User = Depends(get_current_api_user)):
    return {
        "code": 0,
        "data": {
            "id": current_user.id,
            "username": current_user.username,
            "full_name": current_user.full_name,
            "roles": [r.name for r in current_user.roles],
            "permissions": build_permission_map(current_user),
        },
    }


@router.post("/logout")
def logout(current_user: User = Depends(get_current_api_user), db: Session = Depends(get_db)):
    write_log(
        db, user=current_user, action="logout", target_type="auth",
        target_name=current_user.username,
        ip_address="",
    )
    db.commit()
    return {"code": 0, "msg": "已退出登录"}
