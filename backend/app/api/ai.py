"""AI 运维助手 API — SSE 流式对话 + 工具调用 + 写操作确认。"""
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


def _build_system_prompt(model_name: str) -> str:
    return f"""你是 {model_name}，一个真实存在的大语言模型。你不是什么"运维助手"，不要编造身份。

你可以使用提供的工具来帮助用户完成运维操作：
- 查询类操作直接执行
- 写操作（执行命令、巡检、创建工单）先说明要做什么，等用户确认
- 不需要工具的问题直接回答，就像普通聊天一样

当用户问你是什么模型、你是谁时，如实回答你是 {model_name}。
回复使用中文，简洁明了。工具返回的是原始数据，由你来决定如何组织和呈现给用户。"""


@router.get("/info")
def api_ai_info(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_api_user),
):
    """获取 AI 模型配置信息。"""
    from app.core.settings import get_llm_config

    config = get_llm_config(db)
    configured = bool(config["base_url"] and config["api_key"] and config["model"])
    return {
        "code": 0,
        "data": {
            "model": config["model"],
            "configured": configured,
        },
    }


@router.get("/conversations")
def api_list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_api_user),
):
    """获取对话列表。"""
    from app.services.ai.conversations import get_conversations

    convs = get_conversations(db, user_id=current_user.id)
    return {
        "code": 0,
        "data": [
            {
                "id": c.id,
                "title": c.title,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "updated_at": c.updated_at.isoformat() if c.updated_at else None,
            }
            for c in convs
        ],
    }


@router.get("/conversations/{conversation_id}/messages")
def api_get_messages(
    conversation_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_api_user),
):
    """获取对话的消息列表。"""
    from app.services.ai.conversations import get_messages

    messages = get_messages(db, conversation_id)
    return {
        "code": 0,
        "data": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "tool_calls": json.loads(m.tool_calls) if m.tool_calls else None,
                "tool_call_id": m.tool_call_id,
                "tool_name": m.tool_name,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in messages
        ],
    }


@router.delete("/conversations/{conversation_id}")
def api_delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_api_user),
):
    """删除对话。"""
    from app.services.ai.conversations import delete_conversation

    delete_conversation(db, conversation_id)
    return {"code": 0, "msg": "已删除"}


class ChatRequest(BaseModel):
    message: str
    conversation_id: int | None = None


class ConfirmRequest(BaseModel):
    pending_id: str
    conversation_id: int


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
        build_llm_messages,
        create_conversation,
        get_conversation,
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

    # 获取或创建对话
    if body.conversation_id:
        conv = get_conversation(db, body.conversation_id)
        if not conv:
            async def error_stream():
                yield _sse_event({"type": "error", "content": "对话不存在。"})
            return StreamingResponse(error_stream(), media_type="text/event-stream")
        cid = conv.id
    else:
        conv = create_conversation(db, user_id=current_user.id)
        cid = conv.id

    # 追加用户消息
    add_message(db, cid, "user", body.message)
    db.commit()

    client = LLMClient(config["base_url"], config["api_key"], config["model"])

    async def event_stream():
        max_rounds = 10
        for _round in range(max_rounds):
            if await request.is_disconnected():
                break

            # 构建消息列表
            history = build_llm_messages(db, cid)
            messages = [{"role": "system", "content": _build_system_prompt(config["model"])}] + history

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

            if not tool_calls:
                if full_text:
                    add_message(db, cid, "assistant", full_text)
                    db.commit()
                yield _sse_event({"type": "done", "conversation_id": cid})
                return

            # 处理工具调用
            assistant_tool_calls = []
            for tc in tool_calls:
                assistant_tool_calls.append({
                    "id": tc["id"],
                    "type": "function",
                    "function": {"name": tc["name"], "arguments": json.dumps(tc["arguments"], ensure_ascii=False)},
                })
            add_message(db, cid, "assistant", full_text or None, tool_calls=assistant_tool_calls)

            for tc in tool_calls:
                tool_name = tc["name"]
                tool_args = tc["arguments"]
                tool_call_id = tc["id"]

                if is_readonly(tool_name):
                    yield _sse_event({"type": "tool_start", "tool": tool_name, "args": tool_args})
                    result = await dispatch_tool(db, tool_name, tool_args)
                    result_text = result.get("result", result.get("error", "执行失败"))
                    yield _sse_event({"type": "tool_result", "tool": tool_name, "result": result_text})
                    add_message(db, cid, "tool", result_text, tool_call_id=tool_call_id, tool_name=tool_name)
                else:
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
                    db.commit()
                    return

            db.commit()

        yield _sse_event({"type": "done", "conversation_id": cid})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/chat/confirm")
async def api_chat_confirm(
    body: ConfirmRequest,
    request: Request,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_api_user),
):
    """确认执行写操作，继续 LLM 对话。"""
    from app.core.settings import get_llm_config
    from app.services.ai.conversations import (
        add_message,
        build_llm_messages,
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

    result = await dispatch_tool(db, tool_name, tool_args)
    result_text = result.get("result", result.get("error", "执行失败"))

    add_message(db, cid, "tool", result_text, tool_call_id=tool_call_id, tool_name=tool_name)
    db.commit()

    config = get_llm_config(db)
    client = LLMClient(config["base_url"], config["api_key"], config["model"])

    async def event_stream():
        yield _sse_event({"type": "tool_start", "tool": tool_name, "args": tool_args})
        yield _sse_event({"type": "tool_result", "tool": tool_name, "result": result_text})

        history = build_llm_messages(db, cid)
        messages = [{"role": "system", "content": _build_system_prompt(config["model"])}] + history
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
            add_message(db, cid, "assistant", full_text)
            db.commit()
        yield _sse_event({"type": "done", "conversation_id": cid})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/chat/reject")
async def api_chat_reject(
    body: ConfirmRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_api_user),
):
    """拒绝写操作，告知 LLM 用户拒绝了。"""
    from app.core.settings import get_llm_config
    from app.services.ai.conversations import (
        add_message,
        build_llm_messages,
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

    add_message(db, cid, "tool", "用户拒绝了该操作的执行。", tool_call_id=tool_call_id)
    db.commit()

    config = get_llm_config(db)
    client = LLMClient(config["base_url"], config["api_key"], config["model"])

    async def event_stream():
        history = build_llm_messages(db, cid)
        messages = [{"role": "system", "content": _build_system_prompt(config["model"])}] + history
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
            add_message(db, cid, "assistant", full_text)
            db.commit()
        yield _sse_event({"type": "done", "conversation_id": cid})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _sse_event(data: dict[str, Any]) -> str:
    """格式化 SSE 事件。"""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
