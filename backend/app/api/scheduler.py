"""定时任务 API。"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import api_permission_required, get_client_ip
from app.db.database import get_db
from app.models.scheduled_task import ScheduledTask
from app.models.user import User
from app.services.audit import write_log
from app.services.scheduler import (
    execute_task,
    get_supported_task_types,
    get_task,
    list_task_logs,
    list_tasks,
)
from app.core.scheduler import sync_task_to_scheduler

router = APIRouter(prefix="/scheduler", tags=["定时任务"])


# ─── Pydantic 模型 ──────────────────────────────────────────


class TaskCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    task_type: str = Field(min_length=1, max_length=50)
    cron_expr: str = Field(min_length=1, max_length=100)
    params: dict | None = None
    description: str = Field(default="", max_length=500)


class TaskUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    task_type: str | None = Field(default=None, min_length=1, max_length=50)
    cron_expr: str | None = Field(default=None, min_length=1, max_length=100)
    params: dict | None = None
    description: str | None = Field(default=None, max_length=500)
    enabled: bool | None = None


# ─── API 路由 ──────────────────────────────────────────────


@router.get("/tasks")
def api_list_tasks(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("settings.view")),
):
    """查询定时任务列表。"""
    items, total = list_tasks(db, page=page, page_size=page_size)
    return {
        "code": 0,
        "data": {
            "items": [
                {
                    "id": t.id,
                    "name": t.name,
                    "task_type": t.task_type,
                    "cron_expr": t.cron_expr,
                    "params": t.params,
                    "enabled": t.enabled,
                    "description": t.description,
                    "last_run_at": t.last_run_at.isoformat() if t.last_run_at else None,
                    "last_status": t.last_status,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                }
                for t in items
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        },
    }


@router.get("/task-types")
def api_task_types(
    _: User = Depends(api_permission_required("settings.view")),
):
    """返回支持的任务类型。"""
    types = get_supported_task_types()
    return {"code": 0, "data": {"items": [{"key": k, "label": v} for k, v in types.items()]}}


@router.post("/tasks")
def api_create_task(
    body: TaskCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("settings.edit")),
):
    """创建定时任务。"""
    supported = get_supported_task_types()
    if body.task_type not in supported:
        raise HTTPException(status_code=400, detail=f"不支持的任务类型: {body.task_type}")

    from app.core.scheduler import parse_cron
    try:
        parse_cron(body.cron_expr)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    task = ScheduledTask(
        name=body.name,
        task_type=body.task_type,
        cron_expr=body.cron_expr,
        params=body.params,
        description=body.description,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    sync_task_to_scheduler(task.id)

    write_log(db, user=current_user, action="create", target_type="scheduler",
              target_name=task.name, detail=f"创建定时任务: {task.task_type} ({task.cron_expr})",
              ip_address=get_client_ip(request))
    db.commit()

    return {"code": 0, "msg": "创建成功", "data": {"id": task.id}}


@router.put("/tasks/{task_id}")
def api_update_task(
    task_id: int,
    body: TaskUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("settings.edit")),
):
    """更新定时任务。"""
    task = get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")

    if body.cron_expr is not None:
        from app.core.scheduler import parse_cron
        try:
            parse_cron(body.cron_expr)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    if body.task_type is not None:
        supported = get_supported_task_types()
        if body.task_type not in supported:
            raise HTTPException(status_code=400, detail=f"不支持的任务类型: {body.task_type}")

    if body.name is not None:
        task.name = body.name
    if body.task_type is not None:
        task.task_type = body.task_type
    if body.cron_expr is not None:
        task.cron_expr = body.cron_expr
    if body.params is not None:
        task.params = body.params
    if body.description is not None:
        task.description = body.description
    if body.enabled is not None:
        task.enabled = body.enabled

    task.updated_at = datetime.now(timezone.utc)
    db.commit()

    sync_task_to_scheduler(task.id)

    write_log(db, user=current_user, action="update", target_type="scheduler",
              target_name=task.name, detail="更新定时任务",
              ip_address=get_client_ip(request))
    db.commit()

    return {"code": 0, "msg": "更新成功"}


@router.delete("/tasks/{task_id}")
def api_delete_task(
    task_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("settings.edit")),
):
    """删除定时任务。"""
    task = get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")

    task_name = task.name
    db.delete(task)
    db.commit()

    sync_task_to_scheduler(task_id)

    write_log(db, user=current_user, action="delete", target_type="scheduler",
              target_name=task_name, detail="删除定时任务",
              ip_address=get_client_ip(request))
    db.commit()

    return {"code": 0, "msg": "删除成功"}


@router.post("/tasks/{task_id}/toggle")
def api_toggle_task(
    task_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("settings.edit")),
):
    """启用/禁用定时任务。"""
    task = get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")

    task.enabled = not task.enabled
    task.updated_at = datetime.now(timezone.utc)
    db.commit()

    sync_task_to_scheduler(task.id)

    action_label = "启用" if task.enabled else "禁用"
    write_log(db, user=current_user, action="update", target_type="scheduler",
              target_name=task.name, detail=f"{action_label}定时任务",
              ip_address=get_client_ip(request))
    db.commit()

    return {"code": 0, "msg": f"已{action_label}", "data": {"enabled": task.enabled}}


@router.post("/tasks/{task_id}/run")
async def api_run_task_now(
    task_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("settings.edit")),
):
    """立即执行一次定时任务。"""
    task = get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")

    await execute_task(task_id)

    write_log(db, user=current_user, action="update", target_type="scheduler",
              target_name=task.name, detail="手动触发执行定时任务",
              ip_address=get_client_ip(request))
    db.commit()

    return {"code": 0, "msg": "任务已触发执行"}


@router.get("/tasks/{task_id}/logs")
def api_task_logs(
    task_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("settings.view")),
):
    """查看任务执行日志。"""
    task = get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")

    items, total = list_task_logs(db, task_id, page=page, page_size=page_size)
    return {
        "code": 0,
        "data": {
            "items": [
                {
                    "id": log.id,
                    "task_id": log.task_id,
                    "started_at": log.started_at.isoformat() if log.started_at else None,
                    "finished_at": log.finished_at.isoformat() if log.finished_at else None,
                    "status": log.status,
                    "result": log.result,
                    "error": log.error,
                }
                for log in items
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        },
    }
