"""工具调度器 — 执行工具调用，区分读/写操作。"""
from __future__ import annotations

import importlib
import inspect
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.models.user import User
from app.services.ai.tools import READONLY_TOOLS, TOOL_HANDLERS, TOOL_PERMISSIONS
from app.services.permissions import has_permission

logger = logging.getLogger(__name__)


async def dispatch_tool(
    db: Session,
    tool_name: str,
    arguments: dict[str, Any],
    user: User | None = None,
) -> dict[str, Any]:
    """
    执行一个工具调用（自动处理 sync/async handler）。

    执行前会按 ``TOOL_PERMISSIONS`` 校验 ``user`` 是否具备该工具所需权限，
    防止 AI 对话绕过全站 RBAC。

    返回:
        {"ok": True, "result": str, "readonly": True}  — 读操作，已执行
        {"ok": True, "result": str, "readonly": False}  — 写操作，已执行（确认后）
        {"ok": False, "error": str}                     — 执行失败
    """
    handler_path = TOOL_HANDLERS.get(tool_name)
    if not handler_path:
        return {"ok": False, "error": f"未知工具: {tool_name}"}

    # 权限校验：未配置所需权限码的工具保持向后兼容（放行）。
    required_permission = TOOL_PERMISSIONS.get(tool_name)
    if required_permission and not has_permission(user, required_permission):
        return {"ok": False, "error": f"没有执行该操作所需的权限 ({required_permission})"}

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
