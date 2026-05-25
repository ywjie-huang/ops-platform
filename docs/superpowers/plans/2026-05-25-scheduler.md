# 定时任务框架 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a scheduled task framework to the ops platform using APScheduler, with MySQL-backed task definitions and execution logs, starting with timed patrol as the first built-in task.

**Architecture:** APScheduler runs in-memory (AsyncIOScheduler). Task definitions live in our own `scheduled_tasks` table. On startup, enabled tasks are loaded from DB and registered in the scheduler. UI changes sync DB → scheduler memory (one-way). Execution logs are written to `task_execution_logs`.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2.0, APScheduler 3.10+, Vue 3, Element Plus, TypeScript

---

### Task 1: Add APScheduler dependency and create models

**Files:**
- Modify: `backend/requirements.txt`
- Create: `backend/app/models/scheduled_task.py`

- [ ] **Step 1: Add apscheduler to requirements.txt**

Append to `backend/requirements.txt`:
```
apscheduler>=3.10.0
```

- [ ] **Step 2: Create ScheduledTask and TaskExecutionLog models**

Create `backend/app/models/scheduled_task.py`:

```python
"""定时任务模型。"""
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class ScheduledTask(Base):
    """定时任务定义。"""
    __tablename__ = "scheduled_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    task_type: Mapped[str] = mapped_column(String(50))  # patrol / report / backup
    cron_expr: Mapped[str] = mapped_column(String(100))  # 5-field cron: "min hour day month weekday"
    params: Mapped[dict | None] = mapped_column(JSON, default=None)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    description: Mapped[str] = mapped_column(String(500), default="")
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    last_status: Mapped[str] = mapped_column(String(20), default="")  # success / failed / running
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class TaskExecutionLog(Base):
    """定时任务执行日志。"""
    __tablename__ = "task_execution_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_id: Mapped[int] = mapped_column(Integer, ForeignKey("scheduled_tasks.id"), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    status: Mapped[str] = mapped_column(String(20), default="running")  # running / success / failed
    result: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str] = mapped_column(Text, default="")
```

- [ ] **Step 3: Register model import in main.py**

In `backend/app/main.py`, add `scheduled_task` to the model imports on line 12:

```python
from app.models import alert, alert_event, asset, audit, batch_exec, container, patrol, rbac, ticket, user, system_config, monitoring, ssh_key, scheduled_task  # noqa: F401
```

- [ ] **Step 4: Verify models load without error**

Run: `cd backend && python -c "from app.models.scheduled_task import ScheduledTask, TaskExecutionLog; print('OK')"`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add backend/requirements.txt backend/app/models/scheduled_task.py backend/app/main.py
git commit -m "feat(scheduler): add APScheduler dependency and task models"
```

---

### Task 2: Create scheduler core module

**Files:**
- Create: `backend/app/core/scheduler.py`

- [ ] **Step 1: Create the scheduler core**

Create `backend/app/core/scheduler.py`:

```python
"""定时任务调度器核心。"""
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

# 任务类型 → 执行函数映射（在 service 层注册）
TASK_REGISTRY: dict[str, str] = {}


def register_task_type(task_type: str, func_path: str) -> None:
    """注册任务类型及其执行函数的导入路径。"""
    TASK_REGISTRY[task_type] = func_path


def parse_cron(expr: str) -> CronTrigger:
    """解析 5 字段 cron 表达式为 CronTrigger。

    格式: minute hour day month day_of_week
    示例: "0 2 * * *" = 每天凌晨 2 点
    """
    parts = expr.strip().split()
    if len(parts) != 5:
        raise ValueError(f"无效的 cron 表达式: {expr}（需要 5 个字段）")
    return CronTrigger(
        minute=parts[0],
        hour=parts[1],
        day=parts[2],
        month=parts[3],
        day_of_week=parts[4],
    )


async def startup_scheduler() -> None:
    """启动调度器：从 DB 加载已启用的任务并注册。"""
    from app.db.database import SessionLocal
    from app.models.scheduled_task import ScheduledTask
    from sqlalchemy import select

    db = SessionLocal()
    try:
        tasks = db.scalars(select(ScheduledTask).where(ScheduledTask.enabled == True)).all()
        for task in tasks:
            _add_job(task)
        logger.info("调度器已启动，加载 %d 个定时任务", len(tasks))
    finally:
        db.close()

    scheduler.start()


async def shutdown_scheduler() -> None:
    """优雅关闭调度器。"""
    scheduler.shutdown(wait=False)
    logger.info("调度器已关闭")


def _add_job(task) -> None:
    """将一个 ScheduledTask 注册到 scheduler。"""
    from app.services.scheduler import execute_task

    job_id = f"scheduled_task_{task.id}"
    # 先移除旧 job（如果存在）
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

    try:
        trigger = parse_cron(task.cron_expr)
    except ValueError as e:
        logger.error("任务 %s 的 cron 表达式无效: %s", task.name, e)
        return

    scheduler.add_job(
        execute_task,
        trigger=trigger,
        id=job_id,
        args=[task.id],
        name=task.name,
        replace_existing=True,
    )
    logger.info("已注册定时任务: %s (cron: %s)", task.name, task.cron_expr)


def sync_task_to_scheduler(task_id: int) -> None:
    """从 DB 读取任务并同步到 scheduler（创建/更新/禁用）。"""
    from app.db.database import SessionLocal
    from app.models.scheduled_task import ScheduledTask
    from sqlalchemy import select

    db = SessionLocal()
    try:
        task = db.scalar(select(ScheduledTask).where(ScheduledTask.id == task_id))
        if task is None:
            # 任务已删除，移除 job
            job_id = f"scheduled_task_{task_id}"
            if scheduler.get_job(job_id):
                scheduler.remove_job(job_id)
                logger.info("已移除定时任务 job: %s", job_id)
            return

        if task.enabled:
            _add_job(task)
        else:
            # 禁用：移除 job 但保留 DB 记录
            job_id = f"scheduled_task_{task.id}"
            if scheduler.get_job(job_id):
                scheduler.remove_job(job_id)
                logger.info("已禁用定时任务: %s", task.name)
    finally:
        db.close()
```

- [ ] **Step 2: Verify module imports cleanly**

Run: `cd backend && python -c "from app.core.scheduler import scheduler, startup_scheduler, shutdown_scheduler, sync_task_to_scheduler; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/core/scheduler.py
git commit -m "feat(scheduler): add scheduler core with cron parsing and job management"
```

---

### Task 3: Create scheduler service with execution callback

**Files:**
- Create: `backend/app/services/scheduler.py`

- [ ] **Step 1: Create the scheduler service**

Create `backend/app/services/scheduler.py`:

```python
"""定时任务执行服务。"""
import asyncio
import importlib
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.models.scheduled_task import ScheduledTask, TaskExecutionLog

logger = logging.getLogger(__name__)

# 内置任务执行函数映射
_TASK_FUNCTIONS: dict[str, str] = {
    "patrol": "app.services.patrol.run_patrol",
    # 预留:
    # "report": "app.services.reports.generate_scheduled_report",
    # "backup": "app.services.backup.run_backup",
}


def _resolve_task_func(task_type: str):
    """根据 task_type 动态导入执行函数。"""
    func_path = _TASK_FUNCTIONS.get(task_type)
    if func_path is None:
        raise ValueError(f"不支持的任务类型: {task_type}")

    module_path, func_name = func_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, func_name)


def get_supported_task_types() -> dict[str, str]:
    """返回支持的任务类型及其描述。"""
    return {
        "patrol": "定时巡检",
        # "report": "定时报表",
        # "backup": "定时备份",
    }


async def execute_task(task_id: int) -> None:
    """APScheduler 回调：执行指定任务并记录日志。"""
    db = SessionLocal()
    log_entry = None
    try:
        task = db.scalar(select(ScheduledTask).where(ScheduledTask.id == task_id))
        if task is None:
            logger.warning("定时任务 %d 不存在，跳过执行", task_id)
            return

        # 创建执行日志
        log_entry = TaskExecutionLog(task_id=task_id, status="running")
        db.add(log_entry)
        task.last_status = "running"
        db.commit()
        db.refresh(log_entry)

        logger.info("开始执行定时任务: %s (type=%s)", task.name, task.task_type)

        # 解析并调用执行函数
        func = _resolve_task_func(task.task_type)

        # 处理参数
        params = task.params or {}

        # 调用函数（支持 sync 和 async）
        if asyncio.iscoroutinefunction(func):
            result = await func(db, **params)
        else:
            result = func(db, **params)

        # 提取结果摘要
        if hasattr(result, "summary"):
            result_text = result.summary
        elif hasattr(result, "id"):
            result_text = f"完成，ID: {result.id}"
        else:
            result_text = str(result) if result else "执行完成"

        # 更新日志和任务状态
        log_entry.finished_at = datetime.now(timezone.utc)
        log_entry.status = "success"
        log_entry.result = result_text
        task.last_run_at = datetime.now(timezone.utc)
        task.last_status = "success"
        db.commit()

        logger.info("定时任务执行成功: %s — %s", task.name, result_text)

    except Exception as e:
        logger.error("定时任务执行失败 (id=%d): %s", task_id, e, exc_info=True)
        if log_entry:
            log_entry.finished_at = datetime.now(timezone.utc)
            log_entry.status = "failed"
            log_entry.error = str(e)[:2000]
        # 更新任务状态
        try:
            task = db.scalar(select(ScheduledTask).where(ScheduledTask.id == task_id))
            if task:
                task.last_run_at = datetime.now(timezone.utc)
                task.last_status = "failed"
        except Exception:
            pass
        try:
            db.commit()
        except Exception:
            db.rollback()
    finally:
        db.close()


def list_tasks(db: Session, *, page: int = 1, page_size: int = 20) -> tuple[list[ScheduledTask], int]:
    """查询定时任务列表。"""
    from sqlalchemy import func

    total = db.scalar(select(func.count()).select_from(ScheduledTask)) or 0
    offset = (max(page, 1) - 1) * page_size
    items = list(db.scalars(
        select(ScheduledTask).order_by(ScheduledTask.id.desc()).offset(offset).limit(page_size)
    ).all())
    return items, total


def get_task(db: Session, task_id: int) -> ScheduledTask | None:
    return db.scalar(select(ScheduledTask).where(ScheduledTask.id == task_id))


def list_task_logs(db: Session, task_id: int, *, page: int = 1, page_size: int = 20) -> tuple[list[TaskExecutionLog], int]:
    """查询任务执行日志。"""
    from sqlalchemy import func

    stmt = select(TaskExecutionLog).where(TaskExecutionLog.task_id == task_id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    offset = (max(page, 1) - 1) * page_size
    items = list(db.scalars(
        stmt.order_by(TaskExecutionLog.id.desc()).offset(offset).limit(page_size)
    ).all())
    return items, total
```

- [ ] **Step 2: Verify module imports cleanly**

Run: `cd backend && python -c "from app.services.scheduler import execute_task, get_supported_task_types; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/scheduler.py
git commit -m "feat(scheduler): add scheduler service with task execution and logging"
```

---

### Task 4: Create scheduler API routes

**Files:**
- Create: `backend/app/api/scheduler.py`

- [ ] **Step 1: Create the scheduler API**

Create `backend/app/api/scheduler.py`:

```python
"""定时任务 API。"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
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
    name: str
    task_type: str
    cron_expr: str
    params: dict | None = None
    description: str = ""


class TaskUpdate(BaseModel):
    name: str | None = None
    task_type: str | None = None
    cron_expr: str | None = None
    params: dict | None = None
    description: str | None = None
    enabled: bool | None = None


# ─── API 路由 ──────────────────────────────────────────────


@router.get("/tasks")
def api_list_tasks(
    page: int = 1,
    page_size: int = 20,
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
    # 校验任务类型
    supported = get_supported_task_types()
    if body.task_type not in supported:
        raise HTTPException(status_code=400, detail=f"不支持的任务类型: {body.task_type}")

    # 校验 cron 表达式
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

    # 同步到调度器
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

    # 校验 cron 表达式（如果更新了）
    if body.cron_expr is not None:
        from app.core.scheduler import parse_cron
        try:
            parse_cron(body.cron_expr)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # 校验任务类型（如果更新了）
    if body.task_type is not None:
        supported = get_supported_task_types()
        if body.task_type not in supported:
            raise HTTPException(status_code=400, detail=f"不支持的任务类型: {body.task_type}")

    # 更新字段
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

    # 同步到调度器
    sync_task_to_scheduler(task.id)

    write_log(db, user=current_user, action="update", target_type="scheduler",
              target_name=task.name, detail=f"更新定时任务",
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

    # 从调度器移除
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

    # 同步到调度器
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
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("settings.edit")),
):
    """立即执行一次定时任务。"""
    task = get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")

    await execute_task(task_id)

    return {"code": 0, "msg": "任务已触发执行"}


@router.get("/tasks/{task_id}/logs")
def api_task_logs(
    task_id: int,
    page: int = 1,
    page_size: int = 20,
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
```

- [ ] **Step 2: Register API router and scheduler lifecycle hooks**

In `backend/app/api/__init__.py`, add the import and router registration:

Add `scheduler` to the import line:
```python
from app.api import auth, users, roles, dashboard, containers, monitoring, reports, audit, password, assets, alerts, tickets, ssh_terminal, sftp, alertmanager, settings, batch_exec, batch_presets, patrol, ai, docker_mgmt, ssh_keys, scheduler
```

Add before the SSH key section:
```python
# 定时任务
router.include_router(scheduler.router)
```

- [ ] **Step 3: Wire scheduler startup/shutdown in main.py**

In `backend/app/main.py`, update the `on_startup` function and add `on_shutdown`:

```python
@app.on_event("startup")
async def on_startup():
    init_db()
    # 启动定时任务调度器
    from app.core.scheduler import startup_scheduler
    await startup_scheduler()
    # 启动 Docker Agent 后台轮询线程（每 10 秒拉取一次）
    def _poll_docker_agents():
        while True:
            time.sleep(10)
            try:
                db = SessionLocal()
                try:
                    sync_all_hosts(db)
                finally:
                    db.close()
            except Exception as e:
                logger.error("Docker Agent 轮询失败: %s", e)

    t = threading.Thread(target=_poll_docker_agents, daemon=True)
    t.start()
    logger.info("Docker Agent 后台轮询线程已启动")


@app.on_event("shutdown")
async def on_shutdown():
    from app.core.scheduler import shutdown_scheduler
    await shutdown_scheduler()
```

- [ ] **Step 4: Verify API routes load**

Run: `cd backend && python -c "from app.api.scheduler import router; print('OK')"`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/scheduler.py backend/app/api/__init__.py backend/app/main.py
git commit -m "feat(scheduler): add scheduler API routes and lifecycle hooks"
```

---

### Task 5: Create frontend API module

**Files:**
- Create: `frontend/src/api/scheduler.ts`

- [ ] **Step 1: Create the scheduler API module**

Create `frontend/src/api/scheduler.ts`:

```typescript
import request from './request'

export interface ScheduledTask {
  id: number
  name: string
  task_type: string
  cron_expr: string
  params: Record<string, any> | null
  enabled: boolean
  description: string
  last_run_at: string | null
  last_status: string
  created_at: string | null
}

export interface TaskExecutionLog {
  id: number
  task_id: number
  started_at: string | null
  finished_at: string | null
  status: string
  result: string
  error: string
}

export function getSchedulerTasks(params?: { page?: number; page_size?: number }) {
  return request.get('/scheduler/tasks', { params })
}

export function getTaskTypes() {
  return request.get('/scheduler/task-types')
}

export function createSchedulerTask(data: {
  name: string
  task_type: string
  cron_expr: string
  params?: Record<string, any> | null
  description?: string
}) {
  return request.post('/scheduler/tasks', data)
}

export function updateSchedulerTask(id: number, data: {
  name?: string
  task_type?: string
  cron_expr?: string
  params?: Record<string, any> | null
  description?: string
  enabled?: boolean
}) {
  return request.put(`/scheduler/tasks/${id}`, data)
}

export function deleteSchedulerTask(id: number) {
  return request.delete(`/scheduler/tasks/${id}`)
}

export function toggleSchedulerTask(id: number) {
  return request.post(`/scheduler/tasks/${id}/toggle`)
}

export function runSchedulerTaskNow(id: number) {
  return request.post(`/scheduler/tasks/${id}/run`)
}

export function getTaskExecutionLogs(taskId: number, params?: { page?: number; page_size?: number }) {
  return request.get(`/scheduler/tasks/${taskId}/logs`, { params })
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api/scheduler.ts
git commit -m "feat(scheduler): add frontend API module for scheduler"
```

---

### Task 6: Create SchedulerView frontend page

**Files:**
- Create: `frontend/src/views/settings/SchedulerView.vue`

- [ ] **Step 1: Create the SchedulerView component**

Create `frontend/src/views/settings/SchedulerView.vue`:

```vue
<template>
  <div>
    <div class="page-header">
      <h2 class="page-title">定时任务</h2>
      <el-button type="primary" @click="showDialog()">
        <el-icon><Plus /></el-icon>新建任务
      </el-button>
    </div>

    <!-- 任务列表 -->
    <div class="data-card">
      <el-table :data="items" v-loading="loading" stripe>
        <el-table-column prop="name" label="任务名称" min-width="140" />
        <el-table-column label="任务类型" width="120">
          <template #default="{ row }">
            <el-tag>{{ taskTypeLabels[row.task_type] || row.task_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="cron_expr" label="Cron 表达式" width="140" />
        <el-table-column label="启用" width="80" align="center">
          <template #default="{ row }">
            <el-switch v-model="row.enabled" @change="handleToggle(row)" />
          </template>
        </el-table-column>
        <el-table-column label="上次执行" width="180">
          <template #default="{ row }">
            <template v-if="row.last_run_at">
              <div>{{ formatTime(row.last_run_at) }}</div>
              <el-tag :type="statusType(row.last_status)" size="small">
                {{ statusLabels[row.last_status] || row.last_status }}
              </el-tag>
            </template>
            <span v-else class="text-muted">未执行</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="showDialog(row)">编辑</el-button>
            <el-button link type="primary" size="small" @click="handleRunNow(row)">立即执行</el-button>
            <el-button link type="primary" size="small" @click="showLogs(row)">日志</el-button>
            <el-popconfirm title="确认删除该任务？" @confirm="handleDelete(row)">
              <template #reference>
                <el-button link type="danger" size="small">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-wrap" v-if="total > pageSize">
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="fetchData"
        />
      </div>
    </div>

    <!-- 新建/编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑任务' : '新建任务'" width="520px" destroy-on-close>
      <el-form :model="form" :rules="rules" ref="formRef" label-width="110px">
        <el-form-item label="任务名称" prop="name">
          <el-input v-model="form.name" placeholder="如：每日凌晨巡检" />
        </el-form-item>
        <el-form-item label="任务类型" prop="task_type">
          <el-select v-model="form.task_type" style="width:100%">
            <el-option v-for="t in taskTypes" :key="t.key" :label="t.label" :value="t.key" />
          </el-select>
        </el-form-item>
        <el-form-item label="Cron 表达式" prop="cron_expr">
          <el-input v-model="form.cron_expr" placeholder="如：0 2 * * *（每天凌晨 2 点）" />
          <div class="form-tip">格式：分 时 日 月 星期（5 个字段，空格分隔）</div>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <!-- 执行日志抽屉 -->
    <el-drawer v-model="logsVisible" :title="`${logsTaskName} — 执行日志`" size="560px" destroy-on-close>
      <el-table :data="logs" v-loading="logsLoading" stripe size="small">
        <el-table-column label="开始时间" width="160">
          <template #default="{ row }">{{ formatTime(row.started_at) }}</template>
        </el-table-column>
        <el-table-column label="耗时" width="80">
          <template #default="{ row }">{{ calcDuration(row) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">
              {{ statusLabels[row.status] || row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="result" label="结果" show-overflow-tooltip />
        <el-table-column prop="error" label="错误" show-overflow-tooltip />
      </el-table>
      <div class="pagination-wrap" v-if="logsTotal > logsPageSize">
        <el-pagination
          v-model:current-page="logsPage"
          :page-size="logsPageSize"
          :total="logsTotal"
          layout="total, prev, pager, next"
          @current-change="fetchLogs"
        />
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, type FormInstance } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import {
  getSchedulerTasks, getTaskTypes, createSchedulerTask, updateSchedulerTask,
  deleteSchedulerTask, toggleSchedulerTask, runSchedulerTaskNow, getTaskExecutionLogs,
  type ScheduledTask, type TaskExecutionLog,
} from '@/api/scheduler'

const loading = ref(false)
const saving = ref(false)
const items = ref<ScheduledTask[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20

const taskTypes = ref<{ key: string; label: string }[]>([])
const taskTypeLabels: Record<string, string> = {}

const statusLabels: Record<string, string> = {
  success: '成功',
  failed: '失败',
  running: '执行中',
}

// 弹窗
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const formRef = ref<FormInstance>()
const form = reactive({
  name: '',
  task_type: 'patrol',
  cron_expr: '',
  description: '',
})
const rules = {
  name: [{ required: true, message: '请输入任务名称', trigger: 'blur' }],
  task_type: [{ required: true, message: '请选择任务类型', trigger: 'change' }],
  cron_expr: [{ required: true, message: '请输入 Cron 表达式', trigger: 'blur' }],
}

// 日志抽屉
const logsVisible = ref(false)
const logsLoading = ref(false)
const logsTaskName = ref('')
const logsTaskId = ref(0)
const logs = ref<TaskExecutionLog[]>([])
const logsTotal = ref(0)
const logsPage = ref(1)
const logsPageSize = 20

function formatTime(iso: string | null): string {
  if (!iso) return '-'
  return new Date(iso).toLocaleString('zh-CN')
}

function statusType(status: string): '' | 'success' | 'danger' | 'warning' {
  if (status === 'success') return 'success'
  if (status === 'failed') return 'danger'
  if (status === 'running') return 'warning'
  return ''
}

function calcDuration(row: TaskExecutionLog): string {
  if (!row.started_at || !row.finished_at) return '-'
  const ms = new Date(row.finished_at).getTime() - new Date(row.started_at).getTime()
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

async function fetchTaskTypes() {
  try {
    const res: any = await getTaskTypes()
    taskTypes.value = res.data?.items || []
    for (const t of taskTypes.value) {
      taskTypeLabels[t.key] = t.label
    }
  } catch { /* ignore */ }
}

async function fetchData() {
  loading.value = true
  try {
    const res: any = await getSchedulerTasks({ page: page.value, page_size: pageSize })
    items.value = res.data?.items || []
    total.value = res.data?.total || 0
  } finally { loading.value = false }
}

function showDialog(task?: ScheduledTask) {
  if (task) {
    editingId.value = task.id
    form.name = task.name
    form.task_type = task.task_type
    form.cron_expr = task.cron_expr
    form.description = task.description
  } else {
    editingId.value = null
    form.name = ''
    form.task_type = 'patrol'
    form.cron_expr = ''
    form.description = ''
  }
  dialogVisible.value = true
}

async function handleSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    if (editingId.value) {
      await updateSchedulerTask(editingId.value, {
        name: form.name,
        task_type: form.task_type,
        cron_expr: form.cron_expr,
        description: form.description,
      })
      ElMessage.success('更新成功')
    } else {
      await createSchedulerTask({
        name: form.name,
        task_type: form.task_type,
        cron_expr: form.cron_expr,
        description: form.description,
      })
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchData()
  } finally { saving.value = false }
}

async function handleToggle(row: ScheduledTask) {
  try {
    await toggleSchedulerTask(row.id)
    ElMessage.success(row.enabled ? '已启用' : '已禁用')
  } catch { row.enabled = !row.enabled }
}

async function handleRunNow(row: ScheduledTask) {
  try {
    await runSchedulerTaskNow(row.id)
    ElMessage.success('任务已触发')
    fetchData()
  } catch { /* handled by interceptor */ }
}

async function handleDelete(row: ScheduledTask) {
  await deleteSchedulerTask(row.id)
  ElMessage.success('删除成功')
  fetchData()
}

async function showLogs(row: ScheduledTask) {
  logsTaskId.value = row.id
  logsTaskName.value = row.name
  logsPage.value = 1
  logsVisible.value = true
  await fetchLogs()
}

async function fetchLogs() {
  logsLoading.value = true
  try {
    const res: any = await getTaskExecutionLogs(logsTaskId.value, { page: logsPage.value, page_size: logsPageSize })
    logs.value = res.data?.items || []
    logsTotal.value = res.data?.total || 0
  } finally { logsLoading.value = false }
}

onMounted(() => { fetchTaskTypes(); fetchData() })
</script>

<style scoped>
.form-tip { font-size: 12px; color: #909399; line-height: 1.4; margin-top: 4px; }
.text-muted { color: #909399; font-size: 13px; }
.pagination-wrap { display: flex; justify-content: flex-end; margin-top: 16px; }
</style>
```

- [ ] **Step 2: Verify the component compiles**

Run: `cd frontend && npx vue-tsc --noEmit --pretty 2>&1 | head -20`
Expected: No errors related to SchedulerView

- [ ] **Step 3: Commit**

```bash
git add frontend/src/views/settings/SchedulerView.vue
git commit -m "feat(scheduler): add scheduler management page"
```

---

### Task 7: Add route and sidebar entry

**Files:**
- Modify: `frontend/src/router/modules/routes.ts`

- [ ] **Step 1: Add scheduler route under /system**

In `frontend/src/router/modules/routes.ts`, add a new child to the `/system` route's children array (after the Settings route, before the closing `]`):

```typescript
      {
        path: 'scheduler',
        name: 'Scheduler',
        component: () => import('@/views/settings/SchedulerView.vue'),
        meta: { title: '定时任务', icon: 'Odometer', permission: 'settings.view' },
      },
```

- [ ] **Step 2: Verify dev server starts without errors**

Run: `cd frontend && npm run dev` (check for compilation errors in terminal output)
Expected: No route-related errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/router/modules/routes.ts
git commit -m "feat(scheduler): add route for scheduler page under system menu"
```

---

### Task 8: Install dependency and smoke test

- [ ] **Step 1: Install apscheduler**

Run: `cd backend && pip install apscheduler>=3.10.0`
Expected: Successfully installed apscheduler

- [ ] **Step 2: Start backend and verify scheduler loads**

Run: `cd backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`
Expected log line: `调度器已启动，加载 0 个定时任务`

- [ ] **Step 3: Test API endpoints via curl**

```bash
# 列表（应返回空）
curl -s http://127.0.0.1:8000/api/v1/scheduler/tasks -H "Authorization: Bearer <token>"

# 任务类型
curl -s http://127.0.0.1:8000/api/v1/scheduler/task-types -H "Authorization: Bearer <token>"

# 创建一个测试任务
curl -s -X POST http://127.0.0.1:8000/api/v1/scheduler/tasks \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name":"测试巡检","task_type":"patrol","cron_expr":"*/30 * * * *","description":"每30分钟巡检"}'

# 再查列表（应有 1 条）
curl -s http://127.0.0.1:8000/api/v1/scheduler/tasks -H "Authorization: Bearer <token>"

# 立即执行
curl -s -X POST http://127.0.0.1:8000/api/v1/scheduler/tasks/1/run -H "Authorization: Bearer <token>"

# 查看日志
curl -s http://127.0.0.1:8000/api/v1/scheduler/tasks/1/logs -H "Authorization: Bearer <token>"
```

- [ ] **Step 4: Verify frontend page renders**

Open `http://localhost:3000/system/scheduler` in browser, verify table renders and CRUD works.

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "feat(scheduler): complete scheduled task framework with patrol support"
```
