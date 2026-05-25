"""定时任务执行服务。"""
import asyncio
import importlib
import logging
import traceback
from datetime import datetime, timezone

from sqlalchemy import func, select
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
    task = None
    log_entry = None
    try:
        task = db.scalar(select(ScheduledTask).where(ScheduledTask.id == task_id))
        if task is None:
            logger.warning("定时任务 %d 不存在，跳过执行", task_id)
            return

        # 并发保护：如果任务正在执行中，跳过本次
        if task.last_status == "running":
            logger.warning("定时任务 %s 正在执行中，跳过本次触发", task.name)
            return

        # 创建执行日志
        log_entry = TaskExecutionLog(task_id=task_id, status="running")
        db.add(log_entry)
        task.last_status = "running"
        db.commit()
        db.refresh(log_entry)

        logger.info("开始执行定时任务: %s (type=%s)", task.name, task.task_type)

        # 解析执行函数
        task_func = _resolve_task_func(task.task_type)
        params = task.params or {}

        # 给任务函数独立的 session，避免事务交叉
        task_db = SessionLocal()
        try:
            if asyncio.iscoroutinefunction(task_func):
                result = await task_func(task_db, **params)
            else:
                result = task_func(task_db, **params)
        finally:
            task_db.close()

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
            log_entry.error = traceback.format_exc()[:4000]
        # 更新任务状态
        if task is not None:
            task.last_run_at = datetime.now(timezone.utc)
            task.last_status = "failed"
        try:
            db.commit()
        except Exception:
            db.rollback()
    finally:
        db.close()


def list_tasks(db: Session, *, page: int = 1, page_size: int = 20) -> tuple[list[ScheduledTask], int]:
    """查询定时任务列表。"""
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
    stmt = select(TaskExecutionLog).where(TaskExecutionLog.task_id == task_id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    offset = (max(page, 1) - 1) * page_size
    items = list(db.scalars(
        stmt.order_by(TaskExecutionLog.id.desc()).offset(offset).limit(page_size)
    ).all())
    return items, total
