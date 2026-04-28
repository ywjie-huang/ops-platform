from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import SECRET_KEY, TEMPLATES_DIR
from app.db.database import get_db
from app.services_auth import authenticate_user

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
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = authenticate_user(db, username, password)
    if not user:
        return RedirectResponse(url="/login?error=账号或密码不正确", status_code=302)

    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie("ops_session", str(user.id), httponly=True, samesite="lax")
    return response


@router.get("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("ops_session")
    return response
