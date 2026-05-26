"""
AI 运维助手 API — SSE 流式对话 + 工具调用 + 写操作确认。
"""
from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_api_user
from app.db.database import get_db
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI 助手"])

SYSTEM_PROMPT = """使用工具来帮助用户完成运维操作。
查询类操作直接执行。写操作（执行命令、巡检、创建工单）先说明要做什么，等用户确认。
不需要工具的问题直接回答。回复使用中文，简洁明了。"""


class ChatRequest(BaseModel):
    message: str
    conversation_id: str = ""


class ConfirmRequest(BaseModel):
    pending_id: str
    conversation_id: str


@router.post("/chat")
async def api_chat(
    body: ChatRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_api_user),
):
    """SSE 流式对话接口。"""
    from app.core.settings import get_llm_config
    from app.services.ai.conversations import (
        add_message,
        get_conversation,
        new_conversation,
        store_pending_action,
    )
    from app.services.ai.dispatcher import dispatch_tool, is_readonly
    from app.services.ai.llm_client import LLMClient
    from app.services.ai.tools import TOOL_DEFINITIONS

    config = get_llm_config(db)
    if not config["base_url"] or not config["api_key"] or not config["model"]:
        async def error_stream():
            yield _sse_event({"type": "error", "content": "LLM 未配置，请在系统设置中配置 AI 模型。"})
        return StreamingResponse(error_stream(), media_type="text/event-stream")

    # 初始化对话
    cid = body.conversation_id or new_conversation()
    history = get_conversation(cid)

    # 追加用户消息
    add_message(cid, {"role": "user", "content": body.message})

    client = LLMClient(config["base_url"], config["api_key"], config["model"])

    async def event_stream():
        # 循环处理（可能有多轮 tool call）
        max_rounds = 10  # 防止无限循环
        for round_idx in range(max_rounds):
            # 每轮重新构建 messages，确保包含最新的工具结果
            messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history
            # 检查客户端是否断开
            if await request.is_disconnected():
                break

            full_text = ""
            tool_calls = []

            try:
                async for event in client.chat_stream(messages, TOOL_DEFINITIONS):
                    if event["type"] == "text":
                        full_text += event["content"]
                        yield _sse_event({"type": "text", "content": event["content"]})

                    elif event["type"] == "tool_call":
                        tool_calls.append(event)

                    elif event["type"] == "done":
                        break
            except Exception as e:
                logger.exception("LLM stream error")
                yield _sse_event({"type": "error", "content": f"LLM 调用失败: {str(e)}"})
                return

            # 没有工具调用 — 对话结束
            if not tool_calls:
                if full_text:
                    add_message(cid, {"role": "assistant", "content": full_text})
                yield _sse_event({"type": "done", "conversation_id": cid})
                return

            # 有工具调用 — 处理每个 tool call
            # 先把 assistant 的 tool_calls 消息加入历史
            assistant_msg: dict[str, Any] = {"role": "assistant", "content": full_text or None, "tool_calls": []}
            for tc in tool_calls:
                assistant_msg["tool_calls"].append({
                    "id": tc["id"],
                    "type": "function",
                    "function": {"name": tc["name"], "arguments": json.dumps(tc["arguments"], ensure_ascii=False)},
                })
            add_message(cid, assistant_msg)

            for tc in tool_calls:
                tool_name = tc["name"]
                tool_args = tc["arguments"]
                tool_call_id = tc["id"]

                if is_readonly(tool_name):
                    # 只读 — 直接执行
                    yield _sse_event({"type": "tool_start", "tool": tool_name, "args": tool_args})
                    result = await dispatch_tool(db, tool_name, tool_args)
                    result_text = result.get("result", result.get("error", "执行失败"))
                    yield _sse_event({"type": "tool_result", "tool": tool_name, "result": result_text})
                    add_message(cid, {"role": "tool", "tool_call_id": tool_call_id, "content": result_text})
                else:
                    # 写操作 — 返回确认请求
                    pending_id = store_pending_action(cid, tool_name, tool_args, tool_call_id)
                    asset_info = ""
                    if tool_name == "execute_command" and "asset_id" in tool_args:
                        from app.models.asset import Asset
                        asset = db.get(Asset, tool_args["asset_id"])
                        if asset:
                            asset_info = f"服务器: {asset.name} ({asset.ip_address})\n"
                    yield _sse_event({
                        "type": "tool_confirm",
                        "pending_id": pending_id,
                        "tool": tool_name,
                        "args": tool_args,
                        "description": f"{asset_info}操作: {tool_name}\n参数: {json.dumps(tool_args, ensure_ascii=False, indent=2)}",
                    })
                    # 暂停此轮，等用户确认后通过 /confirm 接口继续
                    return

            # 所有工具执行完毕，继续下一轮 LLM 调用

        yield _sse_event({"type": "done", "conversation_id": cid})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/chat/confirm")
async def api_chat_confirm(
    body: ConfirmRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_api_user),
):
    """确认执行写操作，继续 LLM 对话。"""
    from app.core.settings import get_llm_config
    from app.services.ai.conversations import (
        add_message,
        get_conversation,
        get_pending_action,
        remove_pending_action,
    )
    from app.services.ai.dispatcher import dispatch_tool
    from app.services.ai.llm_client import LLMClient
    from app.services.ai.tools import TOOL_DEFINITIONS

    pending = get_pending_action(body.pending_id)
    if not pending:
        async def error_stream():
            yield _sse_event({"type": "error", "content": "该操作已过期或不存在。"})
        return StreamingResponse(error_stream(), media_type="text/event-stream")

    cid = pending["conversation_id"]
    tool_name = pending["tool_name"]
    tool_args = pending["arguments"]
    tool_call_id = pending["tool_call_id"]

    remove_pending_action(body.pending_id)

    # 执行工具
    result = await dispatch_tool(db, tool_name, tool_args)
    result_text = result.get("result", result.get("error", "执行失败"))

    # 把工具结果加入对话历史
    add_message(cid, {"role": "tool", "tool_call_id": tool_call_id, "content": result_text})

    # 继续 LLM 对话
    config = get_llm_config(db)
    client = LLMClient(config["base_url"], config["api_key"], config["model"])
    history = get_conversation(cid)

    async def event_stream():
        yield _sse_event({"type": "tool_start", "tool": tool_name, "args": tool_args})
        yield _sse_event({"type": "tool_result", "tool": tool_name, "result": result_text})

        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history
        full_text = ""

        try:
            async for event in client.chat_stream(messages, TOOL_DEFINITIONS):
                if event["type"] == "text":
                    full_text += event["content"]
                    yield _sse_event({"type": "text", "content": event["content"]})
                elif event["type"] == "done":
                    break
        except Exception as e:
            logger.exception("LLM stream error after confirm")
            yield _sse_event({"type": "error", "content": f"LLM 调用失败: {str(e)}"})
            return

        if full_text:
            add_message(cid, {"role": "assistant", "content": full_text})
        yield _sse_event({"type": "done", "conversation_id": cid})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/chat/reject")
async def api_chat_reject(
    body: ConfirmRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_api_user),
):
    """拒绝写操作，告知 LLM 用户拒绝了。"""
    from app.core.settings import get_llm_config
    from app.services.ai.conversations import (
        add_message,
        get_conversation,
        get_pending_action,
        remove_pending_action,
    )
    from app.services.ai.llm_client import LLMClient
    from app.services.ai.tools import TOOL_DEFINITIONS

    pending = get_pending_action(body.pending_id)
    if not pending:
        async def error_stream():
            yield _sse_event({"type": "error", "content": "该操作已过期或不存在。"})
        return StreamingResponse(error_stream(), media_type="text/event-stream")

    cid = pending["conversation_id"]
    tool_call_id = pending["tool_call_id"]
    remove_pending_action(body.pending_id)

    # 告知 LLM 用户拒绝了
    add_message(cid, {"role": "tool", "tool_call_id": tool_call_id, "content": "用户拒绝了该操作的执行。"})

    config = get_llm_config(db)
    client = LLMClient(config["base_url"], config["api_key"], config["model"])
    history = get_conversation(cid)

    async def event_stream():
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history
        full_text = ""

        try:
            async for event in client.chat_stream(messages, TOOL_DEFINITIONS):
                if event["type"] == "text":
                    full_text += event["content"]
                    yield _sse_event({"type": "text", "content": event["content"]})
                elif event["type"] == "done":
                    break
        except Exception as e:
            yield _sse_event({"type": "error", "content": f"LLM 调用失败: {str(e)}"})
            return

        if full_text:
            add_message(cid, {"role": "assistant", "content": full_text})
        yield _sse_event({"type": "done", "conversation_id": cid})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _sse_event(data: dict[str, Any]) -> str:
    """格式化 SSE 事件。"""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
