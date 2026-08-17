"""认证 API：登录 / 登出 / 当前用户信息。"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.jwt import create_access_token, decode_access_token
from app.db.database import get_db
from app.models.user import User
from app.api.deps import get_client_ip, get_current_api_user
from app.services.auth import authenticate_user
from app.services.audit import write_log
from app.services.captcha import generate, verify
from app.services.login_guard import clear as clear_login_failures, is_locked, record_failure
from app.services.permissions import build_permission_map
from app.services.token_blacklist import revoke

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
    client_ip = get_client_ip(request)

    locked, remaining = is_locked(body.username, client_ip)
    if locked:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"登录失败次数过多，请 {max(remaining // 60, 1)} 分钟后再试",
        )

    if not verify(body.captcha_id, body.captcha_code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证码错误",
        )
    user = authenticate_user(db, body.username, body.password)
    if not user:
        fails = record_failure(body.username, client_ip)
        write_log(
            db, user=None, username=body.username, action="login_failed", target_type="auth",
            target_name=body.username,
            detail=f"账号或密码错误（连续第 {fails} 次失败）",
            ip_address=client_ip,
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="账号或密码不正确",
        )
    clear_login_failures(body.username, client_ip)
    write_log(
        db, user=user, action="login", target_type="auth",
        target_name=user.username,
        detail="密码登录成功",
        ip_address=client_ip,
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
    # 吊销当前 token（加入黑名单，剩余有效期内拒绝访问）
    auth_header = request.headers.get("Authorization", "")
    token = auth_header[7:] if auth_header.startswith("Bearer ") else request.cookies.get("access_token")
    if token:
        payload = decode_access_token(token)
        if payload and payload.get("jti") and payload.get("exp"):
            revoke(payload["jti"], float(payload["exp"]))

    write_log(
        db, user=current_user, action="logout", target_type="auth",
        target_name=current_user.username,
        detail="用户主动登出",
        ip_address=get_client_ip(request),
    )
    db.commit()
    return {"code": 0, "msg": "已退出登录"}
