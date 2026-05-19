"""密码修改 API。"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_client_ip, get_current_api_user
from app.db.database import get_db
from app.models.user import User
from app.services.audit import write_log
from app.services.users import change_password

router = APIRouter(prefix="/password", tags=["密码"])


class PasswordChange(BaseModel):
    old_password: str
    new_password: str
    confirm_password: str


@router.post("/")
def api_change_password(
    body: PasswordChange,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_api_user),
):
    if body.new_password != body.confirm_password:
        raise HTTPException(status_code=400, detail="两次输入的新密码不一致")

    ok, err = change_password(db, current_user, body.old_password, body.new_password)
    if not ok:
        raise HTTPException(status_code=400, detail=err)

    write_log(db, user=current_user, action="update", target_type="auth", target_name=current_user.username, detail="修改密码",
              ip_address=get_client_ip(request))
    db.commit()
    return {"code": 0, "msg": "密码修改成功"}
