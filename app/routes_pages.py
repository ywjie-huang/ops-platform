from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import SECRET_KEY, TEMPLATES_DIR
from app.data import ALERTS, ASSETS, DASHBOARD_STATS, TICKETS

router = APIRouter(tags=["页面"])
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    if request.cookies.get("ops_session") != SECRET_KEY:
        return RedirectResponse(url="/login", status_code=302)

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "request": request,
            "stats": DASHBOARD_STATS,
            "assets": ASSETS,
            "alerts": ALERTS,
            "tickets": TICKETS,
        },
    )
