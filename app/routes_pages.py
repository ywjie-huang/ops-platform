from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import TEMPLATES_DIR
from app.db.database import get_db
from app.models.dashboard import DashboardStats, NavItem
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
NAV_ITEMS = [
    NavItem("仪表盘", "/", "dashboard"),
    NavItem("资产管理", "/assets", "assets"),
    NavItem("用户管理", "/users", "users"),
]


def require_login(request: Request):
    session_user_id = request.cookies.get("ops_session")
    if not session_user_id:
        return RedirectResponse(url="/login", status_code=302)
    return None


def base_context(request: Request, active_nav: str):
    return {
        "request": request,
        "nav_items": NAV_ITEMS,
        "active_nav": active_nav,
    }


def build_dashboard_stats(db: Session) -> DashboardStats:
    assets = list_assets(db)
    users = list_users(db)
    return DashboardStats(
        asset_total=len(assets),
        online_hosts=sum(1 for item in assets if item.status == "在线"),
        open_alerts=3,
        pending_tickets=5,
        user_total=len(users),
    )


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    redirect = require_login(request)
    if redirect:
        return redirect

    context = base_context(request, "dashboard")
    context["stats"] = build_dashboard_stats(db)
    return templates.TemplateResponse(request=request, name="dashboard_home.html", context=context)


@router.get("/assets", response_class=HTMLResponse)
def assets_page(request: Request, db: Session = Depends(get_db)):
    redirect = require_login(request)
    if redirect:
        return redirect

    context = base_context(request, "assets")
    context["assets"] = list_assets(db)
    context["editing_asset"] = None
    return templates.TemplateResponse(request=request, name="assets.html", context=context)


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
    return RedirectResponse(url="/assets", status_code=302)


@router.get("/assets/{asset_id}/edit", response_class=HTMLResponse)
def asset_edit_page(asset_id: int, request: Request, db: Session = Depends(get_db)):
    redirect = require_login(request)
    if redirect:
        return redirect

    asset = get_asset(db, asset_id)
    if asset is None:
        return RedirectResponse(url="/assets", status_code=302)

    context = base_context(request, "assets")
    context["assets"] = list_assets(db)
    context["editing_asset"] = asset
    return templates.TemplateResponse(request=request, name="assets.html", context=context)


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
        return RedirectResponse(url="/assets", status_code=302)

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
    return RedirectResponse(url="/assets", status_code=302)


@router.post("/assets/{asset_id}/delete")
def asset_remove(asset_id: int, request: Request, db: Session = Depends(get_db)):
    redirect = require_login(request)
    if redirect:
        return redirect

    asset = get_asset(db, asset_id)
    if asset is not None:
        delete_asset(db, asset)
    return RedirectResponse(url="/assets", status_code=302)


@router.get("/users", response_class=HTMLResponse)
def users_page(request: Request, db: Session = Depends(get_db)):
    redirect = require_login(request)
    if redirect:
        return redirect

    context = base_context(request, "users")
    context["users"] = list_users(db)
    context["editing_user"] = None
    context["user_error"] = ""
    context["session_user_id"] = request.cookies.get("ops_session")
    return templates.TemplateResponse(request=request, name="users.html", context=context)


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
        context = base_context(request, "users")
        context["users"] = list_users(db)
        context["editing_user"] = None
        context["user_error"] = "用户名已存在，换一个吧"
        context["session_user_id"] = request.cookies.get("ops_session")
        return templates.TemplateResponse(request=request, name="users.html", context=context)

    create_user(db, username=username, full_name=full_name, password=password)
    return RedirectResponse(url="/users", status_code=302)


@router.get("/users/{user_id}/edit", response_class=HTMLResponse)
def user_edit_page(user_id: int, request: Request, db: Session = Depends(get_db)):
    redirect = require_login(request)
    if redirect:
        return redirect

    user = get_user(db, user_id)
    if user is None:
        return RedirectResponse(url="/users", status_code=302)

    context = base_context(request, "users")
    context["users"] = list_users(db)
    context["editing_user"] = user
    context["user_error"] = ""
    context["session_user_id"] = request.cookies.get("ops_session")
    return templates.TemplateResponse(request=request, name="users.html", context=context)


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
        return RedirectResponse(url="/users", status_code=302)

    duplicate = get_user_by_username(db, username)
    if duplicate and duplicate.id != user.id:
        context = base_context(request, "users")
        context["users"] = list_users(db)
        context["editing_user"] = user
        context["user_error"] = "用户名已存在，无法保存"
        context["session_user_id"] = request.cookies.get("ops_session")
        return templates.TemplateResponse(request=request, name="users.html", context=context)

    update_user(db, user, username=username, full_name=full_name, password=password)
    return RedirectResponse(url="/users", status_code=302)


@router.post("/users/{user_id}/delete")
def user_remove(user_id: int, request: Request, db: Session = Depends(get_db)):
    redirect = require_login(request)
    if redirect:
        return redirect

    session_user_id = request.cookies.get("ops_session")
    user = get_user(db, user_id)
    if user is not None and str(user.id) != str(session_user_id):
        delete_user(db, user)
    return RedirectResponse(url="/users", status_code=302)
