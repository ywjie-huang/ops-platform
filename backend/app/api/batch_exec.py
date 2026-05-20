"""批量执行 API — WebSocket 实时输出 + 执行历史。"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import api_permission_required
from app.db.database import SessionLocal, get_db
from app.models.asset import Asset
from app.models.batch_exec import BatchExecution
from app.models.user import User
from app.services.batch_exec import execute_on_hosts
from app.services.audit import write_log

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/batch-exec", tags=["批量执行"])


# ─── WebSocket：实时批量执行 ────────────────────────────────


def _get_assets_sync(asset_ids: list[int]) -> list[Asset]:
    """同步获取资产列表。"""
    db = SessionLocal()
    try:
        return list(db.query(Asset).filter(Asset.id.in_(asset_ids)).all())
    finally:
        db.close()


def _save_execution(command: str, asset_ids: list[int], asset_names: list[str],
                    success: int, failed: int, operator: str) -> None:
    """保存执行记录到数据库。"""
    db = SessionLocal()
    try:
        total = success + failed
        status = "completed" if failed == 0 else "failed"
        record = BatchExecution(
            command=command,
            asset_ids=",".join(str(i) for i in asset_ids),
            asset_names=",".join(asset_names),
            total_hosts=total,
            success_hosts=success,
            failed_hosts=failed,
            status=status,
            operator=operator,
            finished_at=datetime.now(timezone.utc),
        )
        db.add(record)
        db.commit()
    except Exception as e:
        logger.error("Failed to save batch execution record: %s", e)
        db.rollback()
    finally:
        db.close()


@router.websocket("/ws/exec")
async def ws_batch_exec(websocket: WebSocket):
    """
    WebSocket 批量执行端点。
    客户端发送：{ "asset_ids": [1,2,3], "command": "uptime", "timeout": 30 }
    服务端推送：exec_start → exec_result（每台） → exec_done
    """
    await websocket.accept()

    try:
        # 等待客户端发送执行指令
        raw = await websocket.receive_text()
        params = json.loads(raw)
    except (json.JSONDecodeError, Exception) as e:
        await websocket.send_text(json.dumps({"type": "error", "message": f"无效的请求: {e}"}))
        await websocket.close()
        return

    asset_ids = params.get("asset_ids", [])
    command = params.get("command", "").strip()
    timeout = min(params.get("timeout", 30), 300)  # 最大 300 秒

    if not asset_ids or not command:
        await websocket.send_text(json.dumps({"type": "error", "message": "请选择主机并输入命令"}))
        await websocket.close()
        return

    # 获取资产信息
    assets = _get_assets_sync(asset_ids)
    if not assets:
        await websocket.send_text(json.dumps({"type": "error", "message": "未找到指定主机"}))
        await websocket.close()
        return

    # 构建主机列表
    hosts = []
    for a in assets:
        if not a.ssh_password:
            continue
        hosts.append({
            "id": a.id,
            "name": a.name,
            "ip": a.ip_address,
            "port": a.ssh_port or 22,
            "user": a.ssh_username or "root",
            "pwd": a.ssh_password,
        })

    if not hosts:
        await websocket.send_text(json.dumps({"type": "error", "message": "所选主机均未配置 SSH 密码"}))
        await websocket.close()
        return

    # 发送开始消息
    await websocket.send_text(json.dumps({
        "type": "exec_begin",
        "command": command,
        "hosts": [{"id": h["id"], "name": h["name"], "ip": h["ip"]} for h in hosts],
    }))

    # 执行命令
    async def send_message(data: dict):
        try:
            await websocket.send_text(json.dumps(data, ensure_ascii=False))
        except Exception as e:
            logger.debug('WS send failed: %s', e)

    result = await execute_on_hosts(hosts, command, send_message, timeout)

    # 保存执行记录
    asset_names = [a.name for a in assets]
    _save_execution(
        command=command,
        asset_ids=asset_ids,
        asset_names=asset_names,
        success=result["success"],
        failed=result["failed"],
        operator="",
    )

    try:
        await websocket.close()
    except Exception as e:
        logger.debug('WS close failed: %s', e)


# ─── REST：执行历史 ────────────────────────────────────────


@router.get("/history")
def api_exec_history(
    keyword: str = "",
    status: str = "",
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("batch_exec.view")),
):
    """查询批量执行历史。"""
    stmt = select(BatchExecution)
    count_stmt = select(BatchExecution)

    keyword = keyword.strip()
    if keyword:
        like = f"%{keyword}%"
        cond = BatchExecution.command.ilike(like) | BatchExecution.asset_names.ilike(like)
        stmt = stmt.where(cond)
        count_stmt = count_stmt.where(cond)
    if status:
        stmt = stmt.where(BatchExecution.status == status)
        count_stmt = count_stmt.where(BatchExecution.status == status)

    total = db.scalar(select(func.count()).select_from(count_stmt.subquery())) or 0

    stmt = stmt.order_by(BatchExecution.id.desc()).offset((max(page, 1) - 1) * page_size).limit(page_size)
    items = list(db.scalars(stmt).all())

    return {
        "code": 0,
        "data": {
            "items": [
                {
                    "id": r.id,
                    "command": r.command,
                    "asset_ids": r.asset_ids,
                    "asset_names": r.asset_names,
                    "total_hosts": r.total_hosts,
                    "success_hosts": r.success_hosts,
                    "failed_hosts": r.failed_hosts,
                    "status": r.status,
                    "operator": r.operator,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "finished_at": r.finished_at.isoformat() if r.finished_at else None,
                }
                for r in items
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        },
    }


@router.delete("/history/{exec_id}")
def api_delete_history(
    exec_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("batch_exec.delete")),
):
    """删除执行记录。"""
    record = db.scalar(select(BatchExecution).where(BatchExecution.id == exec_id))
    if record is None:
        return {"code": 1, "msg": "记录不存在"}
    db.delete(record)
    db.commit()
    return {"code": 0, "msg": "删除成功"}
