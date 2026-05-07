from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.config import TEMPLATES_DIR
from app.db.database import get_db
from app.models.dashboard import (
    DashboardActivityItem,
    DashboardDistributionItem,
    DashboardQuickStat,
    DashboardStats,
    DashboardSummary,
    DashboardTypeBreakdown,
    NavItem,
)
from app.models.user import User
from app.services.assets import (
    count_assets_by_status,
    count_assets_by_type,
    create_asset,
    delete_asset,
    get_asset,
    list_assets,
    list_recent_assets,
    update_asset,
)
from app.services.permissions import build_permission_map, require_permission
from app.services.roles import (
    _get_permissions_by_ids,
    count_users_by_role,
    create_role,
    delete_role,
    get_role,
    get_role_by_code,
    get_role_by_name,
    list_permissions,
    list_roles,
    update_role,
)
from app.services.users import (
    change_password,
    count_new_users_since,
    create_user,
    delete_user,
    get_user,
    get_user_by_username,
    list_recent_users,
    list_users,
    update_user,
)
from app.services.audit import write_log
from app.services.alerts import (
    count_alerts_by_level,
    count_alerts_by_status,
    count_pending_alerts,
    create_alert,
    delete_alert,
    get_alert,
    list_alerts,
    update_alert,
)
from app.services.tickets import (
    count_open_tickets,
    count_tickets_by_status,
    create_ticket,
    delete_ticket,
    get_ticket,
    list_tickets,
    update_ticket,
)
from app.services.reports import (
    list_preset_reports,
    get_preset_report,
    query_report_data,
    list_data_sources,
    list_dimensions,
    query_custom_report,
    export_csv,
)
from app.services.monitoring import (
    list_metrics,
    get_metric,
    get_metric_by_code,
    create_metric,
    update_metric,
    delete_metric,
    get_host_monitoring_list,
    get_host_detail,
    get_metric_categories,
)
from app.services.containers import (
    list_clusters,
    get_cluster,
    create_cluster,
    update_cluster,
    delete_cluster,
    container_overview,
    list_deployments,
    get_deployment,
    create_deployment,
    update_deployment,
    delete_deployment,
    list_pods as list_container_pods,
    get_pod,
    delete_pod,
    list_services as list_container_services,
    get_service,
    delete_service,
)

router = APIRouter(tags=["页面"])
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
NAV_ITEMS = [
    NavItem("仪表盘", "/", "dashboard"),
    NavItem("报表中心", "/reports", "reports"),
    NavItem("主机管理", "/assets", "assets"),
    NavItem("容器管理", "/containers", "containers"),
    NavItem("工单协作", "/tickets", "tickets"),
    NavItem("告警中心", "/alerts", "alerts"),
    NavItem("监控指标", "/monitoring", "monitoring"),
    NavItem("主机监控", "/monitoring/host", "monitoring_host"),
    NavItem("用户管理", "/users", "users"),
    NavItem("角色权限", "/roles", "roles"),
    NavItem("审计日志", "/audit", "audit"),
]

# 侧边栏分组配置
NAV_GROUPS = {
    "report": {
        "label": "报表大屏",
        "keys": ["dashboard", "reports"],
    },
    "asset": {
        "label": "资产管理",
        "keys": ["assets", "containers"],
    },
    "monitor": {
        "label": "监控告警",
        "keys": ["monitoring", "monitoring_host"],
    },
    "user": {
        "label": "用户管理",
        "keys": ["users", "roles"],
    },
    "system": {
        "label": "系统管理",
        "keys": ["audit"],
    },
}

PERMISSION_LABELS = {
    "dashboard": "仪表盘",
    "reports": "报表中心",
    "assets": "主机管理",
    "containers": "容器管理",
    "tickets": "工单协作",
    "alerts": "告警中心",
    "monitoring": "监控指标",
    "monitoring_host": "主机监控",
    "users": "用户管理",
    "roles": "角色权限",
    "audit": "审计日志",
}


def base_context(request: Request, active_nav: str, current_user: User | None = None):
    return {
        "request": request,
        "nav_items": NAV_ITEMS,
        "active_nav": active_nav,
        "current_user": current_user,
        "can": build_permission_map(current_user),
    }


def build_dashboard_stats(db: Session) -> DashboardStats:
    assets = list_assets(db)
    users = list_users(db)
    roles = list_roles(db)
    status_counts = count_assets_by_status(db)
    return DashboardStats(
        asset_total=len(assets),
        online_hosts=status_counts.get("在线", 0),
        open_alerts=count_pending_alerts(db),
        pending_tickets=count_open_tickets(db),
        user_total=len(users),
        role_total=len(roles),
        offline_assets=status_counts.get("离线", 0),
        maintenance_assets=status_counts.get("维护中", 0),
        user_growth_7d=count_new_users_since(db, 7),
    )


def build_dashboard_summary(db: Session) -> DashboardSummary:
    recent_assets = list_recent_assets(db, limit=5)
    recent_users = list_recent_users(db, limit=5)
    role_distribution = count_users_by_role(db)
    status_counts = count_assets_by_status(db)
    type_counts = count_assets_by_type(db)
    total_assets = len(list_assets(db))

    open_tickets = count_open_tickets(db)
    pending_alerts = count_pending_alerts(db)

    quick_stats = [
        DashboardQuickStat("在线率", _format_ratio(status_counts.get("在线", 0), total_assets), "按资产状态实时统计", "green"),
        DashboardQuickStat("待处理工单", str(open_tickets), "包含 open 和 in_progress 状态", "blue" if open_tickets == 0 else "orange"),
        DashboardQuickStat("待处理告警", str(pending_alerts), "包含待确认和已确认告警", "green" if pending_alerts == 0 else "red"),
    ]

    TYPE_COLORS = {
        "云主机": "#3b82f6",
        "数据库": "#8b5cf6",
        "网络设备": "#06b6d4",
        "中间件": "#f59e0b",
        "其他": "#94a3b8",
    }
    type_breakdown = [
        DashboardTypeBreakdown(label=t, value=c, color=TYPE_COLORS.get(t, "#64748b"))
        for t, c in type_counts.items()
    ]
    max_type_value = max((item.value for item in type_breakdown), default=0)

    STATUS_TONES = {"在线": "green", "离线": "red", "维护中": "orange"}
    asset_changes = [
        DashboardActivityItem(
            title=asset.name,
            meta=f"{asset.asset_type} · {asset.ip_address}",
            detail=f"负责人 {asset.owner or '未填写'}，当前状态 {asset.status}",
            tag=asset.status,
            tone=STATUS_TONES.get(asset.status, "default"),
        )
        for asset in recent_assets
    ]
    if not asset_changes:
        asset_changes = [
            DashboardActivityItem("还没有资产记录", "先去资产管理页录入第一批资产", "录入后这里会展示最近变更", "空")
        ]

    user_items = [
        DashboardActivityItem(
            title=user.full_name,
            meta=f"{user.username} · {user.created_at.strftime('%Y-%m-%d %H:%M')}",
            detail=("角色：" + "、".join(role.name for role in user.roles)) if user.roles else "暂未分配角色",
            tag="新增",
            tone="blue",
        )
        for user in recent_users
    ]
    if not user_items:
        user_items = [
            DashboardActivityItem("还没有新增用户", "创建账号后这里会显示最近加入成员", "方便首页直接扫一眼人员变化", "空")
        ]

    # 最近工单
    recent_tickets = list_tickets(db)[:5]
    TICKET_TONES = {"open": "blue", "in_progress": "orange", "resolved": "green", "closed": "default"}
    ticket_items = [
        DashboardActivityItem(
            title=t.title,
            meta=f"{t.priority} · {t.assignee or '未指派'} · {t.created_at.strftime('%Y-%m-%d %H:%M')}",
            detail=t.description[:80] + "..." if len(t.description) > 80 else t.description,
            tag=t.status,
            tone=TICKET_TONES.get(t.status, "default"),
        )
        for t in recent_tickets
    ]

    # 最近告警
    recent_alerts_list = list_alerts(db)[:5]
    ALERT_TONES = {"pending": "red", "confirmed": "orange", "resolved": "green", "ignored": "default"}
    alert_items = [
        DashboardActivityItem(
            title=a.title,
            meta=f"{a.level} · {a.source or '未知来源'} · {a.created_at.strftime('%Y-%m-%d %H:%M')}",
            detail=a.description[:80] + "..." if len(a.description) > 80 else a.description,
            tag=a.status,
            tone=ALERT_TONES.get(a.status, "default"),
        )
        for a in recent_alerts_list
    ]

    role_items = [
        DashboardDistributionItem(
            label=role.name,
            value=user_count,
            tone="primary" if role.is_system else "neutral",
        )
        for role, user_count in role_distribution[:6]
    ]
    if not role_items:
        role_items = [DashboardDistributionItem(label="暂无角色数据", value=0)]

    return DashboardSummary(
        quick_stats=quick_stats,
        recent_asset_changes=asset_changes,
        recent_users=user_items,
        role_distribution=role_items,
        type_breakdown=type_breakdown,
        max_type_value=max_type_value,
        recent_tickets=ticket_items,
        recent_alerts=alert_items,
    )


def _format_ratio(numerator: int, denominator: int) -> str:
    if denominator <= 0:
        return "0%"
    return f"{round(numerator / denominator * 100)}%"


@router.get("/forbidden", response_class=HTMLResponse)
def forbidden_page(request: Request):
    context = {
        "request": request,
        "nav_items": [],
        "active_nav": "",
        "current_user": None,
        "can": {},
    }
    return templates.TemplateResponse(request=request, name="forbidden.html", context=context)


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    permission_result = require_permission(request, db, "dashboard.view")
    if permission_result.redirect:
        return permission_result.redirect

    context = base_context(request, "dashboard", permission_result.current_user)
    context["stats"] = build_dashboard_stats(db)
    context["summary"] = build_dashboard_summary(db)
    return templates.TemplateResponse(request=request, name="dashboard_home.html", context=context)


@router.get("/assets", response_class=HTMLResponse)
def assets_page(
    request: Request,
    keyword: str = "",
    asset_type: str = "",
    status: str = "",
    db: Session = Depends(get_db),
):
    permission_result = require_permission(request, db, "assets.view")
    if permission_result.redirect:
        return permission_result.redirect

    context = base_context(request, "assets", permission_result.current_user)
    context["assets"] = list_assets(db, keyword=keyword, asset_type=asset_type, status=status)
    context["editing_asset"] = None
    context["asset_filters"] = {
        "keyword": keyword,
        "asset_type": asset_type,
        "status": status,
    }
    context["asset_type_options"] = ["云主机", "数据库", "网络设备", "中间件", "其他"]
    context["asset_status_options"] = ["在线", "离线", "维护中"]
    return templates.TemplateResponse(request=request, name="assets.html", context=context)


@router.get("/assets/{asset_id}", response_class=HTMLResponse)
def asset_detail_page(asset_id: int, request: Request, db: Session = Depends(get_db)):
    permission_result = require_permission(request, db, "assets.view")
    if permission_result.redirect:
        return permission_result.redirect

    asset = get_asset(db, asset_id)
    if asset is None:
        return RedirectResponse(url="/assets", status_code=302)

    from app.services.tickets import list_tickets
    from app.services.alerts import list_alerts

    context = base_context(request, "assets", permission_result.current_user)
    context["asset"] = asset
    context["tickets"] = [t for t in list_tickets(db) if t.asset_id == asset.id]
    context["alerts"] = [a for a in list_alerts(db) if a.asset_id == asset.id]
    return templates.TemplateResponse(request=request, name="asset_detail.html", context=context)


@router.post("/assets/create")
def asset_create_page(
    request: Request,
    name: str = Form(...),
    asset_type: str = Form(...),
    ip_address: str = Form(...),
    status: str = Form(...),
    owner: str = Form(""),
    description: str = Form(""),
    db: Session = Depends(get_db),
):
    permission_result = require_permission(request, db, "assets.create")
    if permission_result.redirect:
        return permission_result.redirect

    asset = create_asset(
        db,
        name=name.strip(),
        asset_type=asset_type.strip(),
        ip_address=ip_address.strip(),
        status=status.strip(),
        owner=owner.strip(),
        description=description.strip(),
    )
    write_log(db, user=permission_result.current_user, action="create", target_type="asset", target_id=asset.id, target_name=asset.name, ip_address=request.client.host if request.client else "")
    db.commit()
    return RedirectResponse(url="/assets", status_code=302)


@router.get("/assets/{asset_id}/edit", response_class=HTMLResponse)
def asset_edit_page(asset_id: int, request: Request, db: Session = Depends(get_db)):
    permission_result = require_permission(request, db, "assets.update")
    if permission_result.redirect:
        return permission_result.redirect

    asset = get_asset(db, asset_id)
    if asset is None:
        return RedirectResponse(url="/assets", status_code=302)

    context = base_context(request, "assets", permission_result.current_user)
    context["assets"] = list_assets(db)
    context["editing_asset"] = asset
    context["asset_filters"] = {
        "keyword": "",
        "asset_type": "",
        "status": "",
    }
    context["asset_type_options"] = ["云主机", "数据库", "网络设备", "中间件", "其他"]
    context["asset_status_options"] = ["在线", "离线", "维护中"]
    return templates.TemplateResponse(request=request, name="assets.html", context=context)


@router.post("/assets/{asset_id}/update")
def asset_update_page(
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
    permission_result = require_permission(request, db, "assets.update")
    if permission_result.redirect:
        return permission_result.redirect

    asset = get_asset(db, asset_id)
    if asset is None:
        return RedirectResponse(url="/assets", status_code=302)

    update_asset(
        db,
        asset,
        name=name.strip(),
        asset_type=asset_type.strip(),
        ip_address=ip_address.strip(),
        status=status.strip(),
        owner=owner.strip(),
        description=description.strip(),
    )
    write_log(db, user=permission_result.current_user, action="update", target_type="asset", target_id=asset.id, target_name=asset.name, ip_address=request.client.host if request.client else "")
    db.commit()
    return RedirectResponse(url="/assets", status_code=302)


@router.post("/assets/{asset_id}/delete")
def asset_remove(asset_id: int, request: Request, db: Session = Depends(get_db)):
    permission_result = require_permission(request, db, "assets.delete")
    if permission_result.redirect:
        return permission_result.redirect

    asset = get_asset(db, asset_id)
    if asset is not None:
        write_log(db, user=permission_result.current_user, action="delete", target_type="asset", target_id=asset.id, target_name=asset.name, ip_address=request.client.host if request.client else "")
        delete_asset(db, asset)
        db.commit()
        return RedirectResponse(url="/assets", status_code=302)
    return RedirectResponse(url="/assets", status_code=302)


@router.get("/users", response_class=HTMLResponse)
def users_page(
    request: Request,
    keyword: str = "",
    role_id: int | None = None,
    db: Session = Depends(get_db),
):
    permission_result = require_permission(request, db, "users.view")
    if permission_result.redirect:
        return permission_result.redirect

    context = build_users_context(request, db, permission_result.current_user, None, "", keyword=keyword, role_id=role_id)
    return templates.TemplateResponse(request=request, name="users.html", context=context)


@router.post("/users/create")
def user_create_page(
    request: Request,
    username: str = Form(...),
    full_name: str = Form(...),
    password: str = Form(...),
    role_ids: list[int] = Form([]),
    db: Session = Depends(get_db),
):
    permission_result = require_permission(request, db, "users.create")
    if permission_result.redirect:
        return permission_result.redirect

    username = username.strip()
    full_name = full_name.strip()
    if get_user_by_username(db, username):
        context = build_users_context(request, db, permission_result.current_user, None, "用户名已存在，换一个吧")
        return templates.TemplateResponse(request=request, name="users.html", context=context)

    user = create_user(db, username=username, full_name=full_name, password=password, role_ids=role_ids)
    write_log(db, user=permission_result.current_user, action="create", target_type="user", target_id=user.id, target_name=user.username, ip_address=request.client.host if request.client else "")
    db.commit()
    return RedirectResponse(url="/users", status_code=302)


@router.get("/users/{user_id}/edit", response_class=HTMLResponse)
def user_edit_page(user_id: int, request: Request, db: Session = Depends(get_db)):
    permission_result = require_permission(request, db, "users.update")
    if permission_result.redirect:
        return permission_result.redirect

    user = get_user(db, user_id)
    if user is None:
        return RedirectResponse(url="/users", status_code=302)

    context = build_users_context(request, db, permission_result.current_user, user, "")
    return templates.TemplateResponse(request=request, name="users.html", context=context)


@router.post("/users/{user_id}/update")
def user_update_page(
    user_id: int,
    request: Request,
    username: str = Form(...),
    full_name: str = Form(...),
    password: str = Form(""),
    role_ids: list[int] = Form([]),
    db: Session = Depends(get_db),
):
    permission_result = require_permission(request, db, "users.update")
    if permission_result.redirect:
        return permission_result.redirect

    user = get_user(db, user_id)
    if user is None:
        return RedirectResponse(url="/users", status_code=302)

    username = username.strip()
    full_name = full_name.strip()
    duplicate = get_user_by_username(db, username)
    if duplicate and duplicate.id != user.id:
        context = build_users_context(request, db, permission_result.current_user, user, "用户名已存在，无法保存")
        return templates.TemplateResponse(request=request, name="users.html", context=context)

    update_user(db, user, username=username, full_name=full_name, password=password, role_ids=role_ids)
    write_log(db, user=permission_result.current_user, action="update", target_type="user", target_id=user.id, target_name=user.username, ip_address=request.client.host if request.client else "")
    db.commit()
    return RedirectResponse(url="/users", status_code=302)


@router.post("/users/{user_id}/delete")
def user_remove(user_id: int, request: Request, db: Session = Depends(get_db)):
    permission_result = require_permission(request, db, "users.delete")
    if permission_result.redirect:
        return permission_result.redirect

    session_user_id = request.cookies.get("ops_session")
    user = get_user(db, user_id)
    if user is not None and str(user.id) != str(session_user_id):
        write_log(db, user=permission_result.current_user, action="delete", target_type="user", target_id=user.id, target_name=user.username, ip_address=request.client.host if request.client else "")
        delete_user(db, user)
        db.commit()
        return RedirectResponse(url="/users", status_code=302)
    return RedirectResponse(url="/users", status_code=302)


@router.get("/roles", response_class=HTMLResponse)
def roles_page(
    request: Request,
    keyword: str = "",
    system_only: bool = False,
    db: Session = Depends(get_db),
):
    permission_result = require_permission(request, db, "roles.view")
    if permission_result.redirect:
        return permission_result.redirect

    context = build_roles_context(request, db, permission_result.current_user, None, "", keyword=keyword, system_only=system_only)
    return templates.TemplateResponse(request=request, name="roles.html", context=context)


@router.post("/roles/create")
def role_create_page(
    request: Request,
    name: str = Form(...),
    code: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db),
):
    permission_result = require_permission(request, db, "roles.create")
    if permission_result.redirect:
        return permission_result.redirect

    name = name.strip()
    code = code.strip()
    description = description.strip()
    if get_role_by_name(db, name) or get_role_by_code(db, code):
        context = build_roles_context(request, db, permission_result.current_user, None, "角色名称或编码已存在")
        return templates.TemplateResponse(request=request, name="roles.html", context=context)

    role = create_role(db, name=name, code=code, description=description, permission_ids=[])
    write_log(db, user=permission_result.current_user, action="create", target_type="role", target_id=role.id, target_name=role.name, ip_address=request.client.host if request.client else "")
    db.commit()
    return RedirectResponse(url="/roles", status_code=302)


@router.get("/roles/{role_id}/edit", response_class=HTMLResponse)
def role_edit_page(role_id: int, request: Request, db: Session = Depends(get_db)):
    permission_result = require_permission(request, db, "roles.update")
    if permission_result.redirect:
        return permission_result.redirect

    role = get_role(db, role_id)
    if role is None:
        return RedirectResponse(url="/roles", status_code=302)

    context = build_roles_context(request, db, permission_result.current_user, role, "")
    return templates.TemplateResponse(request=request, name="roles.html", context=context)


@router.post("/roles/{role_id}/permissions")
def role_permissions_save(
    role_id: int,
    request: Request,
    permission_ids: list[int] = Form([]),
    db: Session = Depends(get_db),
):
    permission_result = require_permission(request, db, "roles.update")
    if permission_result.redirect:
        return permission_result.redirect

    role = get_role(db, role_id)
    if role is None:
        return RedirectResponse(url="/roles", status_code=302)

    role.permissions = _get_permissions_by_ids(db, permission_ids)
    write_log(db, user=permission_result.current_user, action="update", target_type="role", target_id=role.id, target_name=role.name, detail="分配菜单权限", ip_address=request.client.host if request.client else "")
    db.commit()
    return RedirectResponse(url="/roles", status_code=302)


@router.post("/roles/{role_id}/update")
def role_update_page(
    role_id: int,
    request: Request,
    name: str = Form(...),
    code: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db),
):
    permission_result = require_permission(request, db, "roles.update")
    if permission_result.redirect:
        return permission_result.redirect

    role = get_role(db, role_id)
    if role is None:
        return RedirectResponse(url="/roles", status_code=302)

    name = name.strip()
    code = code.strip()
    description = description.strip()
    duplicate_by_name = get_role_by_name(db, name)
    if duplicate_by_name and duplicate_by_name.id != role.id:
        context = build_roles_context(request, db, permission_result.current_user, role, "角色名称已存在")
        return templates.TemplateResponse(request=request, name="roles.html", context=context)

    duplicate_by_code = get_role_by_code(db, code)
    if duplicate_by_code and duplicate_by_code.id != role.id:
        context = build_roles_context(request, db, permission_result.current_user, role, "角色编码已存在")
        return templates.TemplateResponse(request=request, name="roles.html", context=context)

    if role.is_system and role.code != code:
        context = build_roles_context(request, db, permission_result.current_user, role, "系统内置角色不允许修改编码")
        return templates.TemplateResponse(request=request, name="roles.html", context=context)

    update_role(db, role, name=name, code=code, description=description, permission_ids=[p.id for p in role.permissions])
    write_log(db, user=permission_result.current_user, action="update", target_type="role", target_id=role.id, target_name=role.name, ip_address=request.client.host if request.client else "")
    db.commit()
    return RedirectResponse(url="/roles", status_code=302)


@router.post("/roles/{role_id}/delete")
def role_remove(role_id: int, request: Request, db: Session = Depends(get_db)):
    permission_result = require_permission(request, db, "roles.delete")
    if permission_result.redirect:
        return permission_result.redirect

    role = get_role(db, role_id)
    if role is not None and not role.is_system and not role.users:
        write_log(db, user=permission_result.current_user, action="delete", target_type="role", target_id=role.id, target_name=role.name, ip_address=request.client.host if request.client else "")
        delete_role(db, role)
        db.commit()
        return RedirectResponse(url="/roles", status_code=302)
    return RedirectResponse(url="/roles", status_code=302)


def build_users_context(
    request: Request,
    db: Session,
    current_user: User | None,
    editing_user: User | None,
    error_message: str,
    keyword: str = "",
    role_id: int | None = None,
):
    context = base_context(request, "users", current_user)
    roles = list_roles(db)
    context["users"] = list_users(db, keyword=keyword, role_id=role_id)
    context["roles"] = roles
    context["editing_user"] = editing_user
    context["user_error"] = error_message
    context["session_user_id"] = request.cookies.get("ops_session")
    context["selected_role_ids"] = [role.id for role in editing_user.roles] if editing_user else []
    context["show_user_form"] = editing_user is not None or context["can"].get("users.create", False)
    context["user_filters"] = {"keyword": keyword, "role_id": role_id}
    return context


def _build_permission_tree(permissions):
    """构建三级权限树：父页面 -> 子页面 -> 功能。"""
    MODULE_PARENT = {
        "dashboard": ("报表大屏", 1),
        "reports": ("报表大屏", 1),
        "assets": ("资产管理", 2),
        "containers": ("资产管理", 2),
        "monitoring": ("监控告警", 3),
        "tickets": ("工单协作", 4),
        "alerts": ("告警中心", 5),
        "users": ("用户管理", 6),
        "roles": ("用户管理", 6),
        "audit": ("系统管理", 7),
    }
    PARENT_ORDER = {"报表大屏": 1, "资产管理": 2, "监控告警": 3, "工单协作": 4, "告警中心": 5, "用户管理": 6, "系统管理": 7}

    children: dict[str, dict[str, list]] = {}
    child_order: dict[str, list[str]] = {}
    for perm in permissions:
        parent, _ = MODULE_PARENT.get(perm.module, (perm.module, 99))
        if parent not in children:
            children[parent] = {}
            child_order[parent] = []
        if perm.module not in children[parent]:
            children[parent][perm.module] = []
            child_order[parent].append(perm.module)
        children[parent][perm.module].append(perm)

    tree = []
    for parent_name in sorted(children.keys(), key=lambda x: PARENT_ORDER.get(x, 99)):
        child_modules = []
        for mod in child_order[parent_name]:
            child_modules.append({
                "module": mod,
                "label": PERMISSION_LABELS.get(mod, mod),
                "permissions": children[parent_name][mod],
            })
        tree.append({"parent": parent_name, "children": child_modules})
    return tree


def build_roles_context(
    request: Request,
    db: Session,
    current_user: User | None,
    editing_role,
    error_message: str,
    keyword: str = "",
    system_only: bool = False,
):
    context = base_context(request, "roles", current_user)
    permissions = list_permissions(db)
    context["roles"] = list_roles(db, keyword=keyword, system_only=system_only)
    context["perm_tree"] = _build_permission_tree(permissions)
    context["editing_role"] = editing_role
    context["role_error"] = error_message
    context["selected_permission_ids"] = [item.id for item in editing_role.permissions] if editing_role else []
    context["show_role_form"] = editing_role is not None or context["can"].get("roles.create", False)
    context["role_filters"] = {"keyword": keyword, "system_only": system_only}
    return context


# ──────────────────────────────────────────────
# 工单协作
# ──────────────────────────────────────────────
@router.get("/tickets", response_class=HTMLResponse)
def tickets_page(
    request: Request,
    keyword: str = "",
    status: str = "",
    priority: str = "",
    db: Session = Depends(get_db),
):
    permission_result = require_permission(request, db, "tickets.view")
    if permission_result.redirect:
        return permission_result.redirect

    context = base_context(request, "tickets", permission_result.current_user)
    context["tickets"] = list_tickets(db, keyword=keyword, status=status, priority=priority)
    context["editing_ticket"] = None
    context["ticket_filters"] = {"keyword": keyword, "status": status, "priority": priority}
    context["ticket_status_options"] = ["open", "in_progress", "resolved", "closed"]
    context["ticket_priority_options"] = ["low", "normal", "high", "critical"]
    context["assets"] = list_assets(db)
    context["show_ticket_form"] = context["can"].get("tickets.create", False)
    return templates.TemplateResponse(request=request, name="tickets.html", context=context)


@router.get("/tickets/{ticket_id}", response_class=HTMLResponse)
def ticket_detail_page(ticket_id: int, request: Request, db: Session = Depends(get_db)):
    permission_result = require_permission(request, db, "tickets.view")
    if permission_result.redirect:
        return permission_result.redirect

    ticket = get_ticket(db, ticket_id)
    if ticket is None:
        return RedirectResponse(url="/tickets", status_code=302)

    context = base_context(request, "tickets", permission_result.current_user)
    context["ticket"] = ticket
    return templates.TemplateResponse(request=request, name="ticket_detail.html", context=context)


@router.post("/tickets/create")
def ticket_create_page(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    priority: str = Form("normal"),
    status: str = Form("open"),
    assignee: str = Form(""),
    asset_id: int | None = Form(None),
    db: Session = Depends(get_db),
):
    permission_result = require_permission(request, db, "tickets.create")
    if permission_result.redirect:
        return permission_result.redirect

    ticket = create_ticket(
        db,
        title=title.strip(),
        description=description.strip(),
        priority=priority.strip(),
        status=status.strip(),
        assignee=assignee.strip(),
        asset_id=asset_id,
        creator_id=permission_result.current_user.id,
    )
    write_log(db, user=permission_result.current_user, action="create", target_type="ticket", target_id=ticket.id, target_name=ticket.title, ip_address=request.client.host if request.client else "")
    db.commit()
    return RedirectResponse(url="/tickets", status_code=302)


@router.get("/tickets/{ticket_id}/edit", response_class=HTMLResponse)
def ticket_edit_page(ticket_id: int, request: Request, db: Session = Depends(get_db)):
    permission_result = require_permission(request, db, "tickets.update")
    if permission_result.redirect:
        return permission_result.redirect

    ticket = get_ticket(db, ticket_id)
    if ticket is None:
        return RedirectResponse(url="/tickets", status_code=302)

    context = base_context(request, "tickets", permission_result.current_user)
    context["tickets"] = list_tickets(db)
    context["editing_ticket"] = ticket
    context["ticket_filters"] = {"keyword": "", "status": "", "priority": ""}
    context["ticket_status_options"] = ["open", "in_progress", "resolved", "closed"]
    context["ticket_priority_options"] = ["low", "normal", "high", "critical"]
    context["assets"] = list_assets(db)
    context["show_ticket_form"] = True
    return templates.TemplateResponse(request=request, name="tickets.html", context=context)


@router.post("/tickets/{ticket_id}/update")
def ticket_update_page(
    ticket_id: int,
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    priority: str = Form("normal"),
    status: str = Form("open"),
    assignee: str = Form(""),
    asset_id: int | None = Form(None),
    db: Session = Depends(get_db),
):
    permission_result = require_permission(request, db, "tickets.update")
    if permission_result.redirect:
        return permission_result.redirect

    ticket = get_ticket(db, ticket_id)
    if ticket is None:
        return RedirectResponse(url="/tickets", status_code=302)

    update_ticket(
        db,
        ticket,
        title=title.strip(),
        description=description.strip(),
        priority=priority.strip(),
        status=status.strip(),
        assignee=assignee.strip(),
        asset_id=asset_id,
    )
    write_log(db, user=permission_result.current_user, action="update", target_type="ticket", target_id=ticket.id, target_name=ticket.title, ip_address=request.client.host if request.client else "")
    db.commit()
    return RedirectResponse(url="/tickets", status_code=302)


@router.post("/tickets/{ticket_id}/delete")
def ticket_remove(ticket_id: int, request: Request, db: Session = Depends(get_db)):
    permission_result = require_permission(request, db, "tickets.delete")
    if permission_result.redirect:
        return permission_result.redirect

    ticket = get_ticket(db, ticket_id)
    if ticket is not None:
        write_log(db, user=permission_result.current_user, action="delete", target_type="ticket", target_id=ticket.id, target_name=ticket.title, ip_address=request.client.host if request.client else "")
        delete_ticket(db, ticket)
        db.commit()
        return RedirectResponse(url="/tickets", status_code=302)
    return RedirectResponse(url="/tickets", status_code=302)


# ──────────────────────────────────────────────
# 告警中心
# ──────────────────────────────────────────────
@router.get("/alerts", response_class=HTMLResponse)
def alerts_page(
    request: Request,
    keyword: str = "",
    status: str = "",
    level: str = "",
    db: Session = Depends(get_db),
):
    permission_result = require_permission(request, db, "alerts.view")
    if permission_result.redirect:
        return permission_result.redirect

    context = base_context(request, "alerts", permission_result.current_user)
    context["alerts"] = list_alerts(db, keyword=keyword, status=status, level=level)
    context["editing_alert"] = None
    context["alert_filters"] = {"keyword": keyword, "status": status, "level": level}
    context["alert_status_options"] = ["pending", "confirmed", "resolved", "ignored"]
    context["alert_level_options"] = ["low", "medium", "high", "critical"]
    context["assets"] = list_assets(db)
    context["show_alert_form"] = context["can"].get("alerts.create", False)
    return templates.TemplateResponse(request=request, name="alerts.html", context=context)


@router.get("/alerts/{alert_id}", response_class=HTMLResponse)
def alert_detail_page(alert_id: int, request: Request, db: Session = Depends(get_db)):
    permission_result = require_permission(request, db, "alerts.view")
    if permission_result.redirect:
        return permission_result.redirect

    alert = get_alert(db, alert_id)
    if alert is None:
        return RedirectResponse(url="/alerts", status_code=302)

    context = base_context(request, "alerts", permission_result.current_user)
    context["alert"] = alert
    return templates.TemplateResponse(request=request, name="alert_detail.html", context=context)


@router.post("/alerts/create")
def alert_create_page(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    level: str = Form("medium"),
    status: str = Form("pending"),
    source: str = Form(""),
    asset_id: int | None = Form(None),
    db: Session = Depends(get_db),
):
    permission_result = require_permission(request, db, "alerts.create")
    if permission_result.redirect:
        return permission_result.redirect

    alert = create_alert(
        db,
        title=title.strip(),
        description=description.strip(),
        level=level.strip(),
        status=status.strip(),
        source=source.strip(),
        asset_id=asset_id,
        handler_id=None,
    )
    write_log(db, user=permission_result.current_user, action="create", target_type="alert", target_id=alert.id, target_name=alert.title, ip_address=request.client.host if request.client else "")
    db.commit()
    return RedirectResponse(url="/alerts", status_code=302)


@router.get("/alerts/{alert_id}/edit", response_class=HTMLResponse)
def alert_edit_page(alert_id: int, request: Request, db: Session = Depends(get_db)):
    permission_result = require_permission(request, db, "alerts.update")
    if permission_result.redirect:
        return permission_result.redirect

    alert = get_alert(db, alert_id)
    if alert is None:
        return RedirectResponse(url="/alerts", status_code=302)

    context = base_context(request, "alerts", permission_result.current_user)
    context["alerts"] = list_alerts(db)
    context["editing_alert"] = alert
    context["alert_filters"] = {"keyword": "", "status": "", "level": ""}
    context["alert_status_options"] = ["pending", "confirmed", "resolved", "ignored"]
    context["alert_level_options"] = ["low", "medium", "high", "critical"]
    context["assets"] = list_assets(db)
    context["show_alert_form"] = True
    return templates.TemplateResponse(request=request, name="alerts.html", context=context)


@router.post("/alerts/{alert_id}/update")
def alert_update_page(
    alert_id: int,
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    level: str = Form("medium"),
    status: str = Form("pending"),
    source: str = Form(""),
    asset_id: int | None = Form(None),
    db: Session = Depends(get_db),
):
    permission_result = require_permission(request, db, "alerts.update")
    if permission_result.redirect:
        return permission_result.redirect

    alert = get_alert(db, alert_id)
    if alert is None:
        return RedirectResponse(url="/alerts", status_code=302)

    handler_id = permission_result.current_user.id if status in ("confirmed", "resolved") else alert.handler_id
    update_alert(
        db,
        alert,
        title=title.strip(),
        description=description.strip(),
        level=level.strip(),
        status=status.strip(),
        source=source.strip(),
        asset_id=asset_id,
        handler_id=handler_id,
    )
    write_log(db, user=permission_result.current_user, action="update", target_type="alert", target_id=alert.id, target_name=alert.title, ip_address=request.client.host if request.client else "")
    db.commit()
    return RedirectResponse(url="/alerts", status_code=302)


@router.post("/alerts/{alert_id}/delete")
def alert_remove(alert_id: int, request: Request, db: Session = Depends(get_db)):
    permission_result = require_permission(request, db, "alerts.delete")
    if permission_result.redirect:
        return permission_result.redirect

    alert = get_alert(db, alert_id)
    if alert is not None:
        write_log(db, user=permission_result.current_user, action="delete", target_type="alert", target_id=alert.id, target_name=alert.title, ip_address=request.client.host if request.client else "")
        delete_alert(db, alert)
        db.commit()
        return RedirectResponse(url="/alerts", status_code=302)
    return RedirectResponse(url="/alerts", status_code=302)


# ──────────────────────────────────────────────
# 审计日志
# ──────────────────────────────────────────────
@router.get("/audit", response_class=HTMLResponse)
def audit_page(
    request: Request,
    keyword: str = "",
    action: str = "",
    target_type: str = "",
    days: str = "",
    db: Session = Depends(get_db),
):
    permission_result = require_permission(request, db, "audit.view")
    if permission_result.redirect:
        return permission_result.redirect

    from app.services.audit import ACTION_LABELS, TARGET_LABELS, list_logs

    days_int = int(days) if days.isdigit() else 0
    context = base_context(request, "audit", permission_result.current_user)
    context["logs"] = list_logs(db, keyword=keyword, action=action, target_type=target_type, days=days_int)
    context["audit_filters"] = {"keyword": keyword, "action": action, "target_type": target_type, "days": days}
    context["action_options"] = ACTION_LABELS
    context["target_options"] = TARGET_LABELS
    return templates.TemplateResponse(request=request, name="audit.html", context=context)


# ──────────────────────────────────────────────
# 修改密码
# ──────────────────────────────────────────────
@router.get("/password", response_class=HTMLResponse)
def password_page(request: Request, db: Session = Depends(get_db)):
    permission_result = require_permission(request, db, "dashboard.view")
    if permission_result.redirect:
        return permission_result.redirect

    context = base_context(request, "", permission_result.current_user)
    context["password_error"] = ""
    context["password_success"] = ""
    return templates.TemplateResponse(request=request, name="password.html", context=context)


@router.post("/password")
def password_change(
    request: Request,
    old_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db),
):
    permission_result = require_permission(request, db, "dashboard.view")
    if permission_result.redirect:
        return permission_result.redirect

    context = base_context(request, "", permission_result.current_user)
    if new_password != confirm_password:
        context["password_error"] = "两次输入的新密码不一致"
        context["password_success"] = ""
        return templates.TemplateResponse(request=request, name="password.html", context=context)

    ok, err = change_password(db, permission_result.current_user, old_password, new_password)
    if not ok:
        context["password_error"] = err
        context["password_success"] = ""
        return templates.TemplateResponse(request=request, name="password.html", context=context)

    write_log(db, user=permission_result.current_user, action="update", target_type="auth", target_name=permission_result.current_user.username, detail="修改密码", ip_address=request.client.host if request.client else "")
    db.commit()
    return RedirectResponse(url="/", status_code=302)


# ──────────────────────────────────────────────
# 报表中心
# ──────────────────────────────────────────────
@router.get("/reports", response_class=HTMLResponse)
def reports_page(request: Request, db: Session = Depends(get_db)):
    permission_result = require_permission(request, db, "reports.view")
    if permission_result.redirect:
        return permission_result.redirect

    context = base_context(request, "reports", permission_result.current_user)
    context["preset_reports"] = list_preset_reports()
    context["data_sources"] = list_data_sources()
    return templates.TemplateResponse(request=request, name="reports.html", context=context)


@router.get("/reports/preset/{report_id}", response_class=HTMLResponse)
def report_preset_detail(report_id: str, request: Request, days: int = 30, db: Session = Depends(get_db)):
    permission_result = require_permission(request, db, "reports.view")
    if permission_result.redirect:
        return permission_result.redirect

    report_def = get_preset_report(report_id)
    if report_def is None:
        return RedirectResponse(url="/reports", status_code=302)

    report_data = query_report_data(db, report_id, days)
    context = base_context(request, "reports", permission_result.current_user)
    context["report"] = report_def
    context["data"] = report_data
    context["days"] = days
    return templates.TemplateResponse(request=request, name="report_detail.html", context=context)


@router.get("/reports/custom", response_class=HTMLResponse)
def report_custom_page(request: Request, source: str = "", dimension: str = "", days: int = 30, db: Session = Depends(get_db)):
    permission_result = require_permission(request, db, "reports.view")
    if permission_result.redirect:
        return permission_result.redirect

    context = base_context(request, "reports", permission_result.current_user)
    context["data_sources"] = list_data_sources()
    context["dimensions"] = list_dimensions(source) if source else []
    context["selected_source"] = source
    context["selected_dimension"] = dimension
    context["days"] = days
    context["result"] = query_custom_report(db, source, dimension, days) if source and dimension else None
    return templates.TemplateResponse(request=request, name="report_custom.html", context=context)


@router.get("/reports/export/{report_id}")
def report_export_csv(report_id: str, request: Request, days: int = 30, db: Session = Depends(get_db)):
    permission_result = require_permission(request, db, "reports.view")
    if permission_result.redirect:
        return permission_result.redirect

    from fastapi.responses import Response

    csv_content = export_csv(db, report_id, days)
    if not csv_content:
        return RedirectResponse(url="/reports", status_code=302)

    write_log(db, user=permission_result.current_user, action="export", target_type="report", target_name=report_id, detail=f"导出报表 CSV (近{days}天)", ip_address=request.client.host if request.client else "")
    db.commit()

    return Response(
        content="\ufeff" + csv_content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{report_id}_{days}d.csv"'},
    )


@router.get("/reports/schedule", response_class=HTMLResponse)
def report_schedule_page(request: Request, db: Session = Depends(get_db)):
    permission_result = require_permission(request, db, "reports.view")
    if permission_result.redirect:
        return permission_result.redirect

    context = base_context(request, "reports", permission_result.current_user)
    context["preset_reports"] = list_preset_reports()
    return templates.TemplateResponse(request=request, name="report_schedule.html", context=context)


# ──────────────────────────────────────────────
# 容器管理
# ──────────────────────────────────────────────
@router.get("/containers", response_class=HTMLResponse)
def containers_page(request: Request, keyword: str = "", db: Session = Depends(get_db)):
    permission_result = require_permission(request, db, "containers.view")
    if permission_result.redirect:
        return permission_result.redirect

    context = base_context(request, "containers", permission_result.current_user)
    context["clusters"] = list_clusters(db, keyword=keyword)
    context["overview"] = container_overview(db)
    context["keyword"] = keyword
    return templates.TemplateResponse(request=request, name="containers.html", context=context)


@router.post("/containers/clusters/create")
def cluster_create_page(
    request: Request,
    name: str = Form(...),
    provider: str = Form("kubernetes"),
    version: str = Form(""),
    endpoint: str = Form(""),
    status: str = Form("running"),
    node_count: int = Form(0),
    description: str = Form(""),
    db: Session = Depends(get_db),
):
    permission_result = require_permission(request, db, "containers.create")
    if permission_result.redirect:
        return permission_result.redirect

    create_cluster(db, name=name.strip(), provider=provider.strip(), version=version.strip(), endpoint=endpoint.strip(), status=status.strip(), node_count=node_count, description=description.strip())
    write_log(db, user=permission_result.current_user, action="create", target_type="cluster", target_name=name.strip(), detail="新增集群", ip_address=request.client.host if request.client else "")
    db.commit()
    return RedirectResponse(url="/containers", status_code=302)


@router.post("/containers/clusters/{cluster_id}/update")
def cluster_update_page(
    cluster_id: int,
    request: Request,
    name: str = Form(...),
    provider: str = Form("kubernetes"),
    version: str = Form(""),
    endpoint: str = Form(""),
    status: str = Form("running"),
    node_count: int = Form(0),
    description: str = Form(""),
    db: Session = Depends(get_db),
):
    permission_result = require_permission(request, db, "containers.update")
    if permission_result.redirect:
        return permission_result.redirect

    cluster = get_cluster(db, cluster_id)
    if cluster is None:
        return RedirectResponse(url="/containers", status_code=302)

    update_cluster(db, cluster, name=name.strip(), provider=provider.strip(), version=version.strip(), endpoint=endpoint.strip(), status=status.strip(), node_count=node_count, description=description.strip())
    write_log(db, user=permission_result.current_user, action="update", target_type="cluster", target_name=name.strip(), detail="编辑集群", ip_address=request.client.host if request.client else "")
    db.commit()
    return RedirectResponse(url="/containers", status_code=302)


@router.post("/containers/clusters/{cluster_id}/delete")
def cluster_remove(cluster_id: int, request: Request, db: Session = Depends(get_db)):
    permission_result = require_permission(request, db, "containers.delete")
    if permission_result.redirect:
        return permission_result.redirect

    cluster = get_cluster(db, cluster_id)
    if cluster is not None:
        write_log(db, user=permission_result.current_user, action="delete", target_type="cluster", target_name=cluster.name, detail="删除集群", ip_address=request.client.host if request.client else "")
        delete_cluster(db, cluster)
        db.commit()
    return RedirectResponse(url="/containers", status_code=302)


@router.get("/containers/pods", response_class=HTMLResponse)
def pods_page(request: Request, keyword: str = "", cluster_id: int = 0, status: str = "", db: Session = Depends(get_db)):
    permission_result = require_permission(request, db, "containers.view")
    if permission_result.redirect:
        return permission_result.redirect

    context = base_context(request, "containers", permission_result.current_user)
    context["pods"] = list_container_pods(db, keyword=keyword, cluster_id=cluster_id or None, status=status)
    context["clusters"] = list_clusters(db)
    context["keyword"] = keyword
    context["selected_cluster"] = cluster_id
    context["selected_status"] = status
    return templates.TemplateResponse(request=request, name="pods.html", context=context)


@router.get("/containers/services", response_class=HTMLResponse)
def services_page(request: Request, keyword: str = "", cluster_id: int = 0, db: Session = Depends(get_db)):
    permission_result = require_permission(request, db, "containers.view")
    if permission_result.redirect:
        return permission_result.redirect

    context = base_context(request, "containers", permission_result.current_user)
    context["services"] = list_container_services(db, keyword=keyword, cluster_id=cluster_id or None)
    context["clusters"] = list_clusters(db)
    context["keyword"] = keyword
    context["selected_cluster"] = cluster_id
    return templates.TemplateResponse(request=request, name="services.html", context=context)


@router.post("/containers/pods/{pod_id}/delete")
def pod_remove(pod_id: int, request: Request, db: Session = Depends(get_db)):
    permission_result = require_permission(request, db, "containers.delete")
    if permission_result.redirect:
        return permission_result.redirect

    pod = get_pod(db, pod_id)
    if pod is not None:
        write_log(db, user=permission_result.current_user, action="delete", target_type="pod", target_name=pod.name, detail="删除 Pod", ip_address=request.client.host if request.client else "")
        delete_pod(db, pod)
        db.commit()
    return RedirectResponse(url="/containers/pods", status_code=302)


@router.post("/containers/services/{svc_id}/delete")
def service_remove(svc_id: int, request: Request, db: Session = Depends(get_db)):
    permission_result = require_permission(request, db, "containers.delete")
    if permission_result.redirect:
        return permission_result.redirect

    svc = get_service(db, svc_id)
    if svc is not None:
        write_log(db, user=permission_result.current_user, action="delete", target_type="service", target_name=svc.name, detail="删除 Service", ip_address=request.client.host if request.client else "")
        delete_service(db, svc)
        db.commit()
    return RedirectResponse(url="/containers/services", status_code=302)


# ──────────────────────────────────────────────
# 监控告警
# ──────────────────────────────────────────────
@router.get("/monitoring", response_class=HTMLResponse)
def monitoring_page(request: Request, keyword: str = "", category: str = "", db: Session = Depends(get_db)):
    permission_result = require_permission(request, db, "monitoring.view")
    if permission_result.redirect:
        return permission_result.redirect

    context = base_context(request, "monitoring", permission_result.current_user)
    context["metrics"] = list_metrics(db, keyword=keyword, category=category)
    context["categories"] = get_metric_categories(db)
    context["keyword"] = keyword
    context["selected_category"] = category
    return templates.TemplateResponse(request=request, name="monitoring.html", context=context)


@router.post("/monitoring/create")
def metric_create(
    request: Request,
    name: str = Form(...),
    code: str = Form(...),
    unit: str = Form("%"),
    category: str = Form("自定义"),
    description: str = Form(""),
    threshold_warning: float = Form(80.0),
    threshold_critical: float = Form(95.0),
    db: Session = Depends(get_db),
):
    permission_result = require_permission(request, db, "monitoring.create")
    if permission_result.redirect:
        return permission_result.redirect

    create_metric(db, name=name.strip(), code=code.strip(), unit=unit.strip(), category=category.strip(), description=description.strip(), threshold_warning=threshold_warning, threshold_critical=threshold_critical)
    write_log(db, user=permission_result.current_user, action="create", target_type="metric", target_name=name.strip(), detail="新增监控指标", ip_address=request.client.host if request.client else "")
    db.commit()
    return RedirectResponse(url="/monitoring", status_code=302)


@router.post("/monitoring/{metric_id}/update")
def metric_update(
    metric_id: int,
    request: Request,
    name: str = Form(...),
    unit: str = Form("%"),
    category: str = Form("自定义"),
    description: str = Form(""),
    threshold_warning: float = Form(80.0),
    threshold_critical: float = Form(95.0),
    is_enabled: bool = Form(True),
    db: Session = Depends(get_db),
):
    permission_result = require_permission(request, db, "monitoring.update")
    if permission_result.redirect:
        return permission_result.redirect

    metric = get_metric(db, metric_id)
    if metric is None:
        return RedirectResponse(url="/monitoring", status_code=302)

    update_metric(db, metric, name=name.strip(), unit=unit.strip(), category=category.strip(), description=description.strip(), threshold_warning=threshold_warning, threshold_critical=threshold_critical, is_enabled=is_enabled)
    write_log(db, user=permission_result.current_user, action="update", target_type="metric", target_name=name.strip(), detail="编辑监控指标", ip_address=request.client.host if request.client else "")
    db.commit()
    return RedirectResponse(url="/monitoring", status_code=302)


@router.post("/monitoring/{metric_id}/delete")
def metric_remove(metric_id: int, request: Request, db: Session = Depends(get_db)):
    permission_result = require_permission(request, db, "monitoring.delete")
    if permission_result.redirect:
        return permission_result.redirect

    metric = get_metric(db, metric_id)
    if metric is not None:
        if metric.is_system:
            return RedirectResponse(url="/monitoring", status_code=302)
        write_log(db, user=permission_result.current_user, action="delete", target_type="metric", target_name=metric.name, detail="删除监控指标", ip_address=request.client.host if request.client else "")
        delete_metric(db, metric)
        db.commit()
    return RedirectResponse(url="/monitoring", status_code=302)


@router.get("/monitoring/host", response_class=HTMLResponse)
def monitoring_host_page(request: Request, db: Session = Depends(get_db)):
    permission_result = require_permission(request, db, "monitoring.view")
    if permission_result.redirect:
        return permission_result.redirect

    from app.services.assets import list_assets
    assets = list_assets(db)
    context = base_context(request, "monitoring_host", permission_result.current_user)
    context["hosts"] = get_host_monitoring_list(assets)
    return templates.TemplateResponse(request=request, name="monitoring_host.html", context=context)


@router.get("/monitoring/host/{asset_id}", response_class=HTMLResponse)
def monitoring_host_detail_page(asset_id: int, request: Request, db: Session = Depends(get_db)):
    permission_result = require_permission(request, db, "monitoring.view")
    if permission_result.redirect:
        return permission_result.redirect

    from app.services.assets import get_asset
    asset = get_asset(db, asset_id)
    if asset is None:
        return RedirectResponse(url="/monitoring/host", status_code=302)

    context = base_context(request, "monitoring_host", permission_result.current_user)
    context["host"] = get_host_detail(asset.id, asset.name, asset.ip_address)
    return templates.TemplateResponse(request=request, name="monitoring_host_detail.html", context=context)
