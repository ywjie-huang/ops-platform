from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import TEMPLATES_DIR
from app.db.database import get_db
from app.models.dashboard import DashboardStats
from app.services_assets import create_asset, delete_asset, get_asset, list_assets, update_asset
from app.services_users import (
    create_user,
    delete_user,
    get_user,
    get_user_by_username,
    list_users,
    update_user,
)

router = APIRouter(tags=["页面"])
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def require_login(request: Request):
    session_user_id = request.cookies.get("ops_session")
    if not session_user_id:
        return RedirectResponse(url="/login", status_code=302)
    return None


def build_dashboard_context(request: Request, db: Session, editing_asset=None, editing_user=None, user_error: str = ""):
    assets = list_assets(db)
    users = list_users(db)
    stats = DashboardStats(
        asset_total=len(assets),
        online_hosts=sum(1 for item in assets if item.status == "在线"),
        open_alerts=3,
        pending_tickets=5,
        user_total=len(users),
    )
    return {
        "request": request,
        "stats": stats,
        "assets": assets,
        "users": users,
        "editing_asset": editing_asset,
        "editing_user": editing_user,
        "user_error": user_error,
    }


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    redirect = require_login(request)
    if redirect:
        return redirect

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context=build_dashboard_context(request, db),
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

    asset = get_asset(db, asset_id)
    if asset is None:
        return RedirectResponse(url="/", status_code=302)

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context=build_dashboard_context(request, db, editing_asset=asset),
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


@router.post("/users/create")
def user_create(
    request: Request,
    username: str = Form(...),
    full_name: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    redirect = require_login(request)
    if redirect:
        return redirect

    if get_user_by_username(db, username):
        return templates.TemplateResponse(
            request=request,
            name="dashboard.html",
            context=build_dashboard_context(request, db, user_error="用户名已存在，换一个吧"),
        )

    create_user(db, username=username, full_name=full_name, password=password)
    return RedirectResponse(url="/", status_code=302)


@router.get("/users/{user_id}/edit", response_class=HTMLResponse)
def user_edit_page(user_id: int, request: Request, db: Session = Depends(get_db)):
    redirect = require_login(request)
    if redirect:
        return redirect

    user = get_user(db, user_id)
    if user is None:
        return RedirectResponse(url="/", status_code=302)

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context=build_dashboard_context(request, db, editing_user=user),
    )


@router.post("/users/{user_id}/update")
def user_update(
    user_id: int,
    request: Request,
    username: str = Form(...),
    full_name: str = Form(...),
    password: str = Form(""),
    db: Session = Depends(get_db),
):
    redirect = require_login(request)
    if redirect:
        return redirect

    user = get_user(db, user_id)
    if user is None:
        return RedirectResponse(url="/", status_code=302)

    duplicate = get_user_by_username(db, username)
    if duplicate and duplicate.id != user.id:
        return templates.TemplateResponse(
            request=request,
            name="dashboard.html",
            context=build_dashboard_context(
                request,
                db,
                editing_user=user,
                user_error="用户名已存在，无法保存",
            ),
        )

    update_user(db, user, username=username, full_name=full_name, password=password)
    return RedirectResponse(url="/", status_code=302)


@router.post("/users/{user_id}/delete")
def user_remove(user_id: int, request: Request, db: Session = Depends(get_db)):
    redirect = require_login(request)
    if redirect:
        return redirect

    session_user_id = request.cookies.get("ops_session")
    user = get_user(db, user_id)
    if user is not None and str(user.id) != str(session_user_id):
        delete_user(db, user)
    return RedirectResponse(url="/", status_code=302)
