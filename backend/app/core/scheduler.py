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
