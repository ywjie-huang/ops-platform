from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.config import SECRET_KEY, TEMPLATES_DIR
from app.db.database import get_db
from app.services.auth import authenticate_user
from app.services.audit import write_log

router = APIRouter(tags=["页面"])
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, error: str = ""):
    if request.cookies.get("ops_session"):
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"request": request, "error": error},
    )


@router.post("/login")
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = authenticate_user(db, username, password)
    if not user:
        return RedirectResponse(url="/login?error=账号或密码不正确", status_code=302)

    write_log(db, user=user, action="login", target_type="auth", target_name=user.username, ip_address=request.client.host if request.client else "")
    db.commit()
    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(
        "ops_session",
        str(user.id),
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=60 * 60 * 12,
    )
    return response


@router.get("/logout")
def logout(request: Request, db: Session = Depends(get_db)):
    from app.services.permissions import get_current_user
    current_user = get_current_user(request, db)
    if current_user:
        write_log(db, user=current_user, action="logout", target_type="auth", target_name=current_user.username, ip_address=request.client.host if request.client else "")
        db.commit()
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("ops_session")
    return response
