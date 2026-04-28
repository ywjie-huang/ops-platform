from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import TEMPLATES_DIR
from app.db.database import get_db
from app.models.asset import Asset
from app.models.dashboard import DashboardStats
from app.services_assets import create_asset, delete_asset, get_asset, list_assets, update_asset

router = APIRouter(tags=["页面"])
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def require_login(request: Request):
    if not request.cookies.get("ops_session"):
        return RedirectResponse(url="/login", status_code=302)
    return None


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    redirect = require_login(request)
    if redirect:
        return redirect

    assets = list_assets(db)
    stats = DashboardStats(
        asset_total=len(assets),
        online_hosts=sum(1 for item in assets if item.status == "在线"),
        open_alerts=3,
        pending_tickets=5,
    )

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "request": request,
            "stats": stats,
            "assets": assets,
            "editing_asset": None,
        },
    )


@router.post("/assets/create")
def asset_create(
    request: Request,
    name: str = Form(...),
    asset_type: str = Form(...),
    ip_address: str = Form(...),
    status: str = Form(...),
    owner: str = Form(""),
    description: str = Form(""),
    db: Session = Depends(get_db),
):
    redirect = require_login(request)
    if redirect:
        return redirect

    create_asset(
        db,
        name=name,
        asset_type=asset_type,
        ip_address=ip_address,
        status=status,
        owner=owner,
        description=description,
    )
    return RedirectResponse(url="/", status_code=302)


@router.get("/assets/{asset_id}/edit", response_class=HTMLResponse)
def asset_edit_page(asset_id: int, request: Request, db: Session = Depends(get_db)):
    redirect = require_login(request)
    if redirect:
        return redirect

    assets = list_assets(db)
    asset = get_asset(db, asset_id)
    if asset is None:
        return RedirectResponse(url="/", status_code=302)

    stats = DashboardStats(
        asset_total=len(assets),
        online_hosts=sum(1 for item in assets if item.status == "在线"),
        open_alerts=3,
        pending_tickets=5,
    )

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "request": request,
            "stats": stats,
            "assets": assets,
            "editing_asset": asset,
        },
    )


@router.post("/assets/{asset_id}/update")
def asset_update(
    asset_id: int,
    request: Request,
    name: str = Form(...),
    asset_type: str = Form(...),
    ip_address: str = Form(...),
    status: str = Form(...),
    owner: str = Form(""),
    description: str = Form(""),
    db: Session = Depends(get_db),
):
    redirect = require_login(request)
    if redirect:
        return redirect

    asset = get_asset(db, asset_id)
    if asset is None:
        return RedirectResponse(url="/", status_code=302)

    update_asset(
        db,
        asset,
        name=name,
        asset_type=asset_type,
        ip_address=ip_address,
        status=status,
        owner=owner,
        description=description,
    )
    return RedirectResponse(url="/", status_code=302)


@router.post("/assets/{asset_id}/delete")
def asset_remove(asset_id: int, request: Request, db: Session = Depends(get_db)):
    redirect = require_login(request)
    if redirect:
        return redirect

    asset = get_asset(db, asset_id)
    if asset is not None:
        delete_asset(db, asset)
    return RedirectResponse(url="/", status_code=302)
