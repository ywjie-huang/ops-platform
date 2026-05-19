"""认证 API：登录 / 登出 / 当前用户信息。"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.jwt import create_access_token
from app.db.database import get_db
from app.models.user import User
from app.api.deps import get_client_ip, get_current_api_user
from app.services.auth import authenticate_user
from app.services.audit import write_log
from app.services.captcha import generate, verify
from app.services.permissions import build_permission_map

router = APIRouter(prefix="/auth", tags=["认证"])


class LoginRequest(BaseModel):
    username: str
    password: str
    captcha_id: str
    captcha_code: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserInfo(BaseModel):
    id: int
    username: str
    full_name: str
    roles: list[str]
    permissions: dict[str, bool]


@router.get("/captcha")
def get_captcha():
    """获取图形验证码。"""
    captcha_id, image_bytes = generate()
    return StreamingResponse(
        iter([image_bytes]),
        media_type="image/png",
        headers={"X-Captcha-Id": captcha_id},
    )


@router.post("/login")
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    if not verify(body.captcha_id, body.captcha_code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证码错误",
        )
    user = authenticate_user(db, body.username, body.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="账号或密码不正确",
        )
    write_log(
        db, user=user, action="login", target_type="auth",
        target_name=user.username,
        ip_address=get_client_ip(request),
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
def logout(request: Request, current_user: User = Depends(get_current_api_user), db: Session = Depends(get_db)):
    write_log(
        db, user=current_user, action="logout", target_type="auth",
        target_name=current_user.username,
        ip_address=get_client_ip(request),
    )
    db.commit()
    return {"code": 0, "msg": "已退出登录"}
