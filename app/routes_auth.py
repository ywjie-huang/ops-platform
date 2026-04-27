from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import DEMO_PASSWORD, DEMO_USERNAME, SECRET_KEY, TEMPLATES_DIR

router = APIRouter(tags=["页面"])
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, error: str = ""):
    if request.cookies.get("ops_session") == SECRET_KEY:
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": error},
    )


@router.post("/login")
def login_submit(username: str = Form(...), password: str = Form(...)):
    if username != DEMO_USERNAME or password != DEMO_PASSWORD:
        return RedirectResponse(url="/login?error=账号或密码不正确", status_code=302)

    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie("ops_session", SECRET_KEY, httponly=True, samesite="lax")
    return response


@router.get("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("ops_session")
    return response
