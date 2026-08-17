"""定时任务执行服务。"""
import asyncio
import importlib
import logging
import traceback
from datetime import datetime

from app.core.config import CHINA_TZ

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.models.scheduled_task import ScheduledTask, TaskExecutionLog

logger = logging.getLogger(__name__)

# 内置任务执行函数映射
_TASK_FUNCTIONS: dict[str, str] = {
    "patrol": "app.services.patrol.run_patrol",
    # 预留:
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
        log_entry.finished_at = datetime.now(CHINA_TZ)
        log_entry.status = "success"
        log_entry.result = result_text
        task.last_run_at = datetime.now(CHINA_TZ)
        task.last_status = "success"
        db.commit()

        logger.info("定时任务执行成功: %s — %s", task.name, result_text)

    except Exception as e:
        logger.error("定时任务执行失败 (id=%d): %s", task_id, e, exc_info=True)
        if log_entry:
            log_entry.finished_at = datetime.now(CHINA_TZ)
            log_entry.status = "failed"
            log_entry.error = traceback.format_exc()[:4000]
        # 更新任务状态
        if task is not None:
            task.last_run_at = datetime.now(CHINA_TZ)
            task.last_status = "failed"
        try:
            db.commit()
        except Exception:
            db.rollback()
    finally:
        db.close()


def list_tasks(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 20,
    keyword: str = "",
    status: str = "",
    task_type: str = "",
) -> tuple[list[ScheduledTask], int]:
    """查询定时任务列表。status: enabled / disabled / running / failed（上次执行失败）。"""
    conds = []
    keyword = keyword.strip()
    if keyword:
        conds.append(ScheduledTask.name.ilike(f"%{keyword}%"))
    task_type = task_type.strip()
    if task_type:
        conds.append(ScheduledTask.task_type == task_type)
    if status == "enabled":
        conds.append(ScheduledTask.enabled.is_(True))
    elif status == "disabled":
        conds.append(ScheduledTask.enabled.is_(False))
    elif status in ("running", "failed"):
        conds.append(ScheduledTask.last_status == status)

    total = db.scalar(select(func.count()).select_from(ScheduledTask).where(*conds)) or 0
    offset = (max(page, 1) - 1) * page_size
    items = list(db.scalars(
        select(ScheduledTask).where(*conds).order_by(ScheduledTask.id.desc()).offset(offset).limit(page_size)
    ).all())
    return items, total


def get_task_stats(db: Session) -> dict:
    """调度中心概览：任务规模 + 今日执行情况。"""
    from datetime import timedelta

    now = datetime.now(CHINA_TZ)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    total_tasks = db.scalar(select(func.count()).select_from(ScheduledTask)) or 0
    enabled_count = db.scalar(
        select(func.count()).select_from(ScheduledTask).where(ScheduledTask.enabled.is_(True))
    ) or 0

    today_logs = list(db.scalars(
        select(TaskExecutionLog).where(TaskExecutionLog.started_at >= today_start)
    ).all())
    today_runs = len(today_logs)
    today_failed = sum(1 for log in today_logs if log.status == "failed")
    today_success = sum(1 for log in today_logs if log.status == "success")
    duration_sum = sum(
        (log.finished_at - log.started_at).total_seconds()
        for log in today_logs
        if log.finished_at and log.started_at
    )

    latest_failure = db.scalar(
        select(TaskExecutionLog)
        .where(TaskExecutionLog.status == "failed")
        .order_by(TaskExecutionLog.id.desc())
        .limit(1)
    )
    failure_task_name = ""
    if latest_failure:
        failed_task = db.scalar(select(ScheduledTask).where(ScheduledTask.id == latest_failure.task_id))
        failure_task_name = failed_task.name if failed_task else ""

    return {
        "total_tasks": total_tasks,
        "enabled_count": enabled_count,
        "today_runs": today_runs,
        "today_duration_sec": round(duration_sum),
        "today_success": today_success,
        "today_failed": today_failed,
        "success_rate": round(today_success / (today_success + today_failed) * 100) if (today_success + today_failed) else None,
        "latest_failure": {
            "started_at": latest_failure.started_at.isoformat() if latest_failure else None,
            "task_name": failure_task_name,
            "error": (latest_failure.error or "")[:80] if latest_failure else "",
        } if latest_failure else None,
    }


def get_task_log_summary(db: Session, task_id: int) -> dict:
    """单个任务近 7 天执行摘要（日志抽屉顶部用）。"""
    from datetime import timedelta

    since = datetime.now(CHINA_TZ) - timedelta(days=7)
    logs = list(db.scalars(
        select(TaskExecutionLog).where(
            TaskExecutionLog.task_id == task_id,
            TaskExecutionLog.started_at >= since,
        )
    ).all())
    total = len(logs)
    success = sum(1 for log in logs if log.status == "success")
    finished = sum(1 for log in logs if log.status in ("success", "failed"))
    durations = [
        (log.finished_at - log.started_at).total_seconds()
        for log in logs
        if log.finished_at and log.started_at
    ]
    return {
        "total_7d": total,
        "success_rate_7d": round(success / finished * 100, 1) if finished else None,
        "avg_duration_sec_7d": round(sum(durations) / len(durations)) if durations else None,
    }


def compute_next_run(cron_expr: str, enabled: bool) -> datetime | None:
    """由 cron 表达式计算下次执行时间（禁用的任务返回 None）。"""
    if not enabled:
        return None
    try:
        from app.core.scheduler import parse_cron
        trigger = parse_cron(cron_expr)
        return trigger.get_next_fire_time(None, datetime.now(CHINA_TZ))
    except Exception:
        return None


def get_task(db: Session, task_id: int) -> ScheduledTask | None:
    return db.scalar(select(ScheduledTask).where(ScheduledTask.id == task_id))


def get_last_logs_map(db: Session, task_ids: list[int]) -> dict[int, TaskExecutionLog]:
    """批量取每个任务最近一次执行日志（列表页展示耗时用，避免 N+1）。"""
    if not task_ids:
        return {}
    latest_ids = (
        select(TaskExecutionLog.task_id, func.max(TaskExecutionLog.id).label("mid"))
        .where(TaskExecutionLog.task_id.in_(task_ids))
        .group_by(TaskExecutionLog.task_id)
        .subquery()
    )
    rows = db.scalars(
        select(TaskExecutionLog).join(latest_ids, TaskExecutionLog.id == latest_ids.c.mid)
    ).all()
    return {log.task_id: log for log in rows}


def list_task_logs(db: Session, task_id: int, *, page: int = 1, page_size: int = 20) -> tuple[list[TaskExecutionLog], int]:
    """查询任务执行日志。"""
    stmt = select(TaskExecutionLog).where(TaskExecutionLog.task_id == task_id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    offset = (max(page, 1) - 1) * page_size
    items = list(db.scalars(
        stmt.order_by(TaskExecutionLog.id.desc()).offset(offset).limit(page_size)
    ).all())
    return items, total
