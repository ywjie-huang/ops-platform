"""工具调度器 — 执行工具调用，区分读/写操作。"""
from __future__ import annotations

import importlib
import inspect
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.services.ai.tools import READONLY_TOOLS, TOOL_HANDLERS

logger = logging.getLogger(__name__)


async def dispatch_tool(
    db: Session,
    tool_name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """
    执行一个工具调用（自动处理 sync/async handler）。

    返回:
        {"ok": True, "result": str, "readonly": True}  — 读操作，已执行
        {"ok": True, "result": str, "readonly": False}  — 写操作，已执行（确认后）
        {"ok": False, "error": str}                     — 执行失败
    """
    handler_path = TOOL_HANDLERS.get(tool_name)
    if not handler_path:
        return {"ok": False, "error": f"未知工具: {tool_name}"}

    # 动态导入 handler 函数
    module_path, func_name = handler_path.rsplit(".", 1)
    try:
        module = importlib.import_module(module_path)
        handler = getattr(module, func_name)
    except (ImportError, AttributeError) as e:
        return {"ok": False, "error": f"工具加载失败: {e}"}

    try:
        # 自动区分 async / sync handler
        if inspect.iscoroutinefunction(handler):
            result = await handler(db, arguments)
        else:
            result = handler(db, arguments)
        readonly = tool_name in READONLY_TOOLS
        return {"ok": True, "result": result, "readonly": readonly}
    except Exception as e:
        logger.exception("Tool execution failed: %s", tool_name)
        return {"ok": False, "error": f"工具执行失败: {e}"}


def is_readonly(tool_name: str) -> bool:
    """判断工具是否为只读操作。"""
    return tool_name in READONLY_TOOLS
