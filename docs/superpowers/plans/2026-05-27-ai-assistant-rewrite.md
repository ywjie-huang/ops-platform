# AI 助手重写 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 完全重写 AI 助手功能，IDE 分栏式浅色主题 UI，支持通用聊天 + 运维工具调用 + 自主多步规划。

**Architecture:** 后端 FastAPI SSE 流式对话 + OpenAI 兼容 function calling，前端 Vue 3 IDE 分栏布局（左侧对话列表 + 右侧聊天区），对话持久化到 MySQL。

**Tech Stack:** FastAPI, SQLAlchemy, httpx, Vue 3, Element Plus, marked, highlight.js, Pinia

---

## 文件结构

### 后端（创建/修改）
- `backend/app/models/conversation.py` — 新建，对话和消息 SQLAlchemy 模型
- `backend/app/services/ai/conversations.py` — 重写，基于数据库的对话管理
- `backend/app/services/ai/llm_client.py` — 保留，小幅调整
- `backend/app/services/ai/tools.py` — 保留，已改好纯数据格式
- `backend/app/services/ai/dispatcher.py` — 保留
- `backend/app/api/ai.py` — 重写，新 API 端点
- `backend/app/db/init_db.py` — 修改，导入新模型

### 前端（创建/修改）
- `frontend/src/views/ai/AiView.vue` — 重写，IDE 分栏布局
- `frontend/src/api/ai.ts` — 重写，新增对话管理 API
- `frontend/src/stores/ai.ts` — 新建，AI 对话状态管理

---

## Task 1: 数据库模型 — 对话和消息

**Files:**
- Create: `backend/app/models/conversation.py`
- Modify: `backend/app/db/init_db.py`

- [ ] **Step 1: 创建对话和消息模型**

```python
# backend/app/models/conversation.py
"""对话和消息模型。"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), default="新对话")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("conversations.id", ondelete="CASCADE")
    )
    role: Mapped[str] = mapped_column(String(20))  # user, assistant, tool
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    tool_calls: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    tool_call_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tool_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
```

- [ ] **Step 2: 在 init_db.py 中导入模型**

在 `backend/app/db/init_db.py` 的导入区域添加：

```python
from app.models.conversation import Conversation, Message
```

- [ ] **Step 3: 验证模型能创建表**

```bash
cd backend && python -c "from app.models.conversation import Conversation, Message; print('OK')"
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/conversation.py backend/app/db/init_db.py
git commit -m "feat(ai): add conversation and message database models"
```

---

## Task 2: 对话管理服务 — 基于数据库

**Files:**
- Rewrite: `backend/app/services/ai/conversations.py`

- [ ] **Step 1: 重写对话管理服务**

```python
# backend/app/services/ai/conversations.py
"""对话管理 — 基于数据库的对话和消息 CRUD。"""
from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.conversation import Conversation, Message

# {pending_id: {conversation_id, tool_name, arguments, tool_call_id}}
_pending_actions: dict[str, dict[str, Any]] = {}


def create_conversation(db: Session, user_id: int | None = None) -> Conversation:
    """创建新对话。"""
    conv = Conversation(user_id=user_id)
    db.add(conv)
    db.flush()
    return conv


def get_conversations(db: Session, user_id: int | None = None) -> list[Conversation]:
    """获取对话列表，按更新时间倒序。"""
    stmt = select(Conversation).order_by(Conversation.updated_at.desc())
    if user_id:
        stmt = stmt.where(Conversation.user_id == user_id)
    return list(db.scalars(stmt).all())


def get_conversation(db: Session, conversation_id: int) -> Conversation | None:
    """获取单个对话。"""
    return db.get(Conversation, conversation_id)


def delete_conversation(db: Session, conversation_id: int) -> bool:
    """删除对话及其消息。"""
    conv = db.get(Conversation, conversation_id)
    if not conv:
        return False
    db.delete(conv)
    db.flush()
    return True


def add_message(
    db: Session,
    conversation_id: int,
    role: str,
    content: str | None = None,
    tool_calls: list[dict[str, Any]] | None = None,
    tool_call_id: str | None = None,
    tool_name: str | None = None,
) -> Message:
    """向对话追加一条消息。"""
    msg = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        tool_calls=json.dumps(tool_calls, ensure_ascii=False) if tool_calls else None,
        tool_call_id=tool_call_id,
        tool_name=tool_name,
    )
    db.add(msg)
    db.flush()

    # 更新对话的 updated_at
    conv = db.get(Conversation, conversation_id)
    if conv:
        from datetime import datetime, timezone
        conv.updated_at = datetime.now(timezone.utc)

    return msg


def get_messages(db: Session, conversation_id: int) -> list[Message]:
    """获取对话的所有消息。"""
    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.id)
    )
    return list(db.scalars(stmt).all())


def build_llm_messages(db: Session, conversation_id: int) -> list[dict[str, Any]]:
    """构建发送给 LLM 的消息列表。"""
    messages = get_messages(db, conversation_id)
    result = []
    for msg in messages:
        m: dict[str, Any] = {"role": msg.role}
        if msg.content is not None:
            m["content"] = msg.content
        if msg.tool_calls:
            m["tool_calls"] = json.loads(msg.tool_calls)
        if msg.tool_call_id:
            m["tool_call_id"] = msg.tool_call_id
        result.append(m)
    return result


def store_pending_action(
    conversation_id: int,
    tool_name: str,
    arguments: dict[str, Any],
    tool_call_id: str,
) -> str:
    """存储待确认的写操作，返回 pending_id。"""
    pending_id = str(uuid.uuid4())
    _pending_actions[pending_id] = {
        "conversation_id": conversation_id,
        "tool_name": tool_name,
        "arguments": arguments,
        "tool_call_id": tool_call_id,
    }
    return pending_id


def get_pending_action(pending_id: str) -> dict[str, Any] | None:
    """获取待确认操作。"""
    return _pending_actions.get(pending_id)


def remove_pending_action(pending_id: str) -> None:
    """移除已处理的待确认操作。"""
    _pending_actions.pop(pending_id, None)
```

- [ ] **Step 2: 验证导入正常**

```bash
cd backend && python -c "from app.services.ai.conversations import create_conversation; print('OK')"
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/ai/conversations.py
git commit -m "feat(ai): rewrite conversation service with database persistence"
```

---

## Task 3: 后端 API — 重写 SSE 流式对话

**Files:**
- Rewrite: `backend/app/api/ai.py`

- [ ] **Step 1: 重写 AI API**

```python
# backend/app/api/ai.py
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
```

- [ ] **Step 2: 验证后端启动**

```bash
cd backend && python -c "from app.api.ai import router; print('OK')"
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/ai.py
git commit -m "feat(ai): rewrite API with conversation persistence and new endpoints"
```

---

## Task 4: 前端 API 层 — 对话管理

**Files:**
- Rewrite: `frontend/src/api/ai.ts`

- [ ] **Step 1: 重写 AI API**

```typescript
// frontend/src/api/ai.ts
/**
 * AI 助手 API — SSE 流式对话 + 对话管理
 */
import { getToken } from '@/utils/auth'

const BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1'

export interface SSEEvent {
  type: 'text' | 'tool_start' | 'tool_result' | 'tool_confirm' | 'error' | 'done'
  content?: string
  tool?: string
  args?: Record<string, unknown>
  result?: string
  pending_id?: string
  description?: string
  conversation_id?: number
}

export interface AiInfo {
  model: string
  configured: boolean
}

export interface Conversation {
  id: number
  title: string
  created_at: string
  updated_at: string
}

export interface ChatMessage {
  id: number
  role: 'user' | 'assistant' | 'tool'
  content: string | null
  tool_calls: Array<{
    id: string
    type: string
    function: { name: string; arguments: string }
  }> | null
  tool_call_id: string | null
  tool_name: string | null
  created_at: string
}

function authHeaders(): Record<string, string> {
  const token = getToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export async function getAiInfo(): Promise<AiInfo> {
  const resp = await fetch(`${BASE}/ai/info`, { headers: authHeaders() })
  const data = await resp.json()
  return data.data
}

export async function getConversations(): Promise<Conversation[]> {
  const resp = await fetch(`${BASE}/ai/conversations`, { headers: authHeaders() })
  const data = await resp.json()
  return data.data
}

export async function getMessages(conversationId: number): Promise<ChatMessage[]> {
  const resp = await fetch(`${BASE}/ai/conversations/${conversationId}/messages`, {
    headers: authHeaders(),
  })
  const data = await resp.json()
  return data.data
}

export async function deleteConversation(conversationId: number): Promise<void> {
  await fetch(`${BASE}/ai/conversations/${conversationId}`, {
    method: 'DELETE',
    headers: authHeaders(),
  })
}

export async function* sendAiMessageStream(
  message: string,
  conversation_id?: number,
): AsyncGenerator<SSEEvent> {
  const resp = await fetch(`${BASE}/ai/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ message, conversation_id }),
  })
  if (!resp.ok) throw new Error(`请求失败: ${resp.status}`)
  yield* _readSSEStream(resp)
}

export async function* confirmAiActionStream(
  pending_id: string,
  conversation_id: number,
): AsyncGenerator<SSEEvent> {
  const resp = await fetch(`${BASE}/ai/chat/confirm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ pending_id, conversation_id }),
  })
  if (!resp.ok) throw new Error(`请求失败: ${resp.status}`)
  yield* _readSSEStream(resp)
}

export async function* rejectAiActionStream(
  pending_id: string,
  conversation_id: number,
): AsyncGenerator<SSEEvent> {
  const resp = await fetch(`${BASE}/ai/chat/reject`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ pending_id, conversation_id }),
  })
  if (!resp.ok) throw new Error(`请求失败: ${resp.status}`)
  yield* _readSSEStream(resp)
}

async function* _readSSEStream(resp: Response): AsyncGenerator<SSEEvent> {
  const reader = resp.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try { yield JSON.parse(line.slice(6)) as SSEEvent } catch { /* ignore */ }
      }
    }
  }
  if (buffer.startsWith('data: ')) {
    try { yield JSON.parse(buffer.slice(6)) as SSEEvent } catch { /* ignore */ }
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api/ai.ts
git commit -m "feat(ai): rewrite frontend API with conversation management"
```

---

## Task 5: 前端视图 — IDE 分栏布局

**Files:**
- Rewrite: `frontend/src/views/ai/AiView.vue`

这是最大的任务，完全重写前端视图。需要包含：

1. 左侧栏：对话列表 + 搜索 + 新建
2. 右侧聊天区：消息流 + 工具面板 + 输入区
3. 浅色主题白色背景
4. Markdown 渲染
5. 工具确认/拒绝交互

- [ ] **Step 1: 重写 AiView.vue**

由于文件较大，分步构建。先搭建整体布局框架：

```vue
<!-- frontend/src/views/ai/AiView.vue -->
<template>
  <div class="ai-page">
    <!-- 左侧栏 -->
    <aside class="ai-sidebar">
      <div class="sidebar-header">
        <el-input
          v-model="searchText"
          placeholder="搜索对话..."
          size="small"
          clearable
          :prefix-icon="Search"
        />
        <el-button type="primary" size="small" @click="handleNewChat">
          <el-icon><Plus /></el-icon> 新对话
        </el-button>
      </div>
      <div class="conversation-list">
        <div
          v-for="conv in filteredConversations"
          :key="conv.id"
          class="conv-item"
          :class="{ active: currentConvId === conv.id }"
          @click="handleSelectConversation(conv.id)"
        >
          <div class="conv-title">{{ conv.title }}</div>
          <div class="conv-time">{{ formatTime(conv.updated_at) }}</div>
          <el-icon class="conv-delete" @click.stop="handleDeleteConversation(conv.id)">
            <Delete />
          </el-icon>
        </div>
        <div v-if="!filteredConversations.length" class="conv-empty">
          {{ searchText ? '没有匹配的对话' : '暂无对话' }}
        </div>
      </div>
    </aside>

    <!-- 右侧聊天区 -->
    <main class="ai-main">
      <!-- 顶部栏 -->
      <header class="ai-header">
        <div class="header-left">
          <el-icon :size="18"><Monitor /></el-icon>
          <span class="header-title">AI 助手</span>
          <el-tag v-if="aiModel" type="info" size="small" effect="plain">{{ aiModel }}</el-tag>
          <el-tag v-else type="warning" size="small" effect="plain">未配置</el-tag>
        </div>
      </header>

      <!-- 消息区域 -->
      <div class="ai-messages" ref="messagesRef">
        <!-- 欢迎页 -->
        <div v-if="!displayMessages.length" class="ai-welcome">
          <el-icon :size="48" color="#409eff"><ChatDotRound /></el-icon>
          <h3>你好，我是 AI 助手</h3>
          <p>我可以帮你查询服务器状态、执行巡检、在服务器上执行命令等。也可以随便聊聊。</p>
          <div class="quick-actions">
            <div v-for="q in quickQuestions" :key="q" class="quick-item" @click="handleQuickAsk(q)">
              {{ q }}
            </div>
          </div>
        </div>

        <!-- 消息列表 -->
        <template v-for="(msg, idx) in displayMessages" :key="idx">
          <!-- 用户消息 -->
          <div v-if="msg.type === 'user'" class="msg-row user">
            <div class="msg-meta">
              <div class="msg-avatar user-avatar">U</div>
              <span class="msg-role">你</span>
              <span class="msg-time">{{ msg.time }}</span>
            </div>
            <div class="msg-bubble user-bubble">{{ msg.content }}</div>
          </div>

          <!-- 工具面板 -->
          <div v-else-if="msg.type === 'tool_start'" class="msg-row assistant">
            <div class="msg-meta">
              <div class="msg-avatar assistant-avatar">A</div>
              <span class="msg-role assistant-role">AI</span>
            </div>
            <div class="tool-panel tool-running">
              <div class="tool-header">
                <el-icon class="is-loading"><Loading /></el-icon>
                <span class="tool-name">{{ toolDisplayName(msg.tool) }}</span>
                <span class="tool-args">{{ formatArgs(msg.args) }}</span>
              </div>
            </div>
          </div>

          <div v-else-if="msg.type === 'tool_result'" class="msg-row assistant">
            <div class="msg-meta">
              <div class="msg-avatar assistant-avatar">A</div>
              <span class="msg-role assistant-role">AI</span>
            </div>
            <div class="tool-panel tool-done">
              <details>
                <summary class="tool-header">
                  <el-icon color="#67c23a"><CircleCheckFilled /></el-icon>
                  <span class="tool-name">{{ toolDisplayName(msg.tool) }}</span>
                  <span class="tool-time" v-if="msg.elapsed">{{ msg.elapsed }}ms</span>
                  <el-icon class="expand-icon"><ArrowRight /></el-icon>
                </summary>
                <div class="tool-body">
                  <div v-if="msg.args" class="tool-section">
                    <div class="tool-label">参数:</div>
                    <div class="tool-code">{{ formatArgs(msg.args) }}</div>
                  </div>
                  <div class="tool-section">
                    <div class="tool-label">结果:</div>
                    <div class="tool-code" v-html="renderMarkdown(msg.result || '')" />
                  </div>
                </div>
              </details>
            </div>
          </div>

          <!-- 写操作确认 -->
          <div v-else-if="msg.type === 'tool_confirm'" class="msg-row assistant">
            <div class="msg-meta">
              <div class="msg-avatar assistant-avatar">A</div>
              <span class="msg-role assistant-role">AI</span>
            </div>
            <div class="tool-panel tool-confirm">
              <div class="tool-header">
                <el-icon color="#e6a23c"><WarningFilled /></el-icon>
                <span class="tool-name">{{ toolDisplayName(msg.tool) }} — 需要确认</span>
              </div>
              <div class="tool-body">
                <pre class="confirm-desc">{{ msg.description }}</pre>
              </div>
              <div class="tool-actions">
                <el-button size="small" @click="handleReject(msg)">拒绝</el-button>
                <el-button size="small" type="primary" :loading="confirmLoading" @click="handleConfirm(msg)">
                  确认执行
                </el-button>
              </div>
            </div>
          </div>

          <!-- AI 文本回复 -->
          <div v-else-if="msg.type === 'text'" class="msg-row assistant">
            <div class="msg-meta">
              <div class="msg-avatar assistant-avatar">A</div>
              <span class="msg-role assistant-role">AI</span>
              <span class="msg-time">{{ msg.time }}</span>
            </div>
            <div class="msg-text markdown-body" v-html="renderMarkdown(msg.content || '')" />
          </div>
        </template>

        <!-- 加载中 -->
        <div v-if="loading" class="msg-row assistant">
          <div class="msg-meta">
            <div class="msg-avatar assistant-avatar">A</div>
            <span class="msg-role assistant-role">AI</span>
          </div>
          <div class="typing-indicator"><span /><span /><span /></div>
        </div>
      </div>

      <!-- 输入区 -->
      <div class="ai-input">
        <div class="input-wrap">
          <el-input
            v-model="inputText"
            type="textarea"
            :rows="1"
            :autosize="{ minRows: 1, maxRows: 4 }"
            placeholder="输入消息... (Shift+Enter 换行)"
            resize="none"
            @keydown="handleKeydown"
          />
          <el-button
            type="primary"
            :icon="Promotion"
            :loading="loading"
            :disabled="!inputText.trim()"
            circle
            @click="handleSend"
          />
        </div>
        <div class="input-tip">基于大语言模型，回答仅供参考</div>
      </div>
    </main>
  </div>
</template>
```

- [ ] **Step 2: 添加 script 部分**

```vue
<script setup lang="ts">
import { ref, computed, nextTick, onMounted, watch } from 'vue'
import {
  Promotion, Delete, Loading, WarningFilled, CircleCheckFilled,
  ChatDotRound, Monitor, ArrowRight, Search, Plus,
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { marked } from 'marked'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'
import {
  getAiInfo, getConversations, getMessages, deleteConversation,
  sendAiMessageStream, confirmAiActionStream, rejectAiActionStream,
  type SSEEvent, type Conversation, type ChatMessage,
} from '@/api/ai'

interface DisplayMessage {
  type: 'user' | 'text' | 'tool_start' | 'tool_result' | 'tool_confirm'
  content?: string
  tool?: string
  args?: Record<string, unknown>
  result?: string
  description?: string
  pending_id?: string
  time?: string
  elapsed?: number
}

const searchText = ref('')
const conversations = ref<Conversation[]>([])
const currentConvId = ref<number | null>(null)
const displayMessages = ref<DisplayMessage[]>([])
const inputText = ref('')
const loading = ref(false)
const confirmLoading = ref(false)
const messagesRef = ref<HTMLElement>()
const aiModel = ref('')

const quickQuestions = [
  '今天哪台服务器资源异常？',
  '最近有什么告警？',
  '帮我巡检一下系统',
  '你是什么模型？',
]

const filteredConversations = computed(() => {
  if (!searchText.value) return conversations.value
  const q = searchText.value.toLowerCase()
  return conversations.value.filter(c => c.title.toLowerCase().includes(q))
})

// Markdown 渲染
const renderer = new marked.Renderer()
renderer.code = function ({ text, lang }: { text: string; lang?: string }) {
  let highlighted: string
  if (lang && hljs.getLanguage(lang)) {
    highlighted = hljs.highlight(text, { language: lang }).value
  } else {
    highlighted = hljs.highlightAuto(text).value
  }
  return `<pre><code class="hljs${lang ? ` language-${lang}` : ''}">${highlighted}</code></pre>`
}
marked.setOptions({ breaks: true, gfm: true, renderer })

function renderMarkdown(text: string): string {
  return marked.parse(text) as string
}

const TOOL_NAMES: Record<string, string> = {
  query_assets: '查询服务器', query_host_metrics: '查询主机指标',
  query_alerts: '查询告警', query_containers: '查询容器',
  query_k8s: '查询 K8s 集群', query_tickets: '查询工单',
  get_patrol_reports: '查询巡检报告', execute_command: '执行命令',
  run_patrol: '执行巡检', create_ticket: '创建工单',
}

function toolDisplayName(tool?: string): string {
  return TOOL_NAMES[tool || ''] || tool || '未知工具'
}

function formatArgs(args?: Record<string, unknown>): string {
  if (!args) return ''
  return Object.entries(args).map(([k, v]) => `${k}: ${JSON.stringify(v)}`).join('  |  ')
}

function formatTime(iso?: string): string {
  if (!iso) return ''
  const d = new Date(iso)
  const now = new Date()
  const diff = now.getTime() - d.getTime()
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`
  return d.toLocaleDateString('zh-CN')
}

function now(): string {
  return new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesRef.value) messagesRef.value.scrollTop = messagesRef.value.scrollHeight
  })
}

async function loadConversations() {
  try {
    conversations.value = await getConversations()
  } catch { /* ignore */ }
}

async function loadMessages(convId: number) {
  try {
    const msgs = await getMessages(convId)
    displayMessages.value = msgs
      .filter(m => m.role !== 'tool')
      .map(m => {
        if (m.role === 'user') {
          return { type: 'user' as const, content: m.content || '', time: formatTime(m.created_at) }
        }
        // assistant message
        if (m.tool_calls) {
          // 有工具调用的消息 — 显示工具面板
          return { type: 'text' as const, content: m.content || '', time: formatTime(m.created_at) }
        }
        return { type: 'text' as const, content: m.content || '', time: formatTime(m.created_at) }
      })
    scrollToBottom()
  } catch { /* ignore */ }
}

function handleNewChat() {
  currentConvId.value = null
  displayMessages.value = []
}

async function handleSelectConversation(id: number) {
  currentConvId.value = id
  await loadMessages(id)
}

async function handleDeleteConversation(id: number) {
  try {
    await ElMessageBox.confirm('确定删除这个对话？', '提示', { type: 'warning' })
    await deleteConversation(id)
    conversations.value = conversations.value.filter(c => c.id !== id)
    if (currentConvId.value === id) {
      currentConvId.value = null
      displayMessages.value = []
    }
  } catch { /* cancelled */ }
}

async function handleSend() {
  const text = inputText.value.trim()
  if (!text || loading.value) return
  inputText.value = ''
  await sendMessage(text)
}

function handleQuickAsk(q: string) {
  sendMessage(q)
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}

async function sendMessage(text: string) {
  displayMessages.value.push({ type: 'user', content: text, time: now() })
  scrollToBottom()

  loading.value = true
  const textMsg: DisplayMessage = { type: 'text', content: '', time: now() }
  let textMsgPushed = false
  const toolStartTime: Record<string, number> = {}

  try {
    for await (const event of sendAiMessageStream(text, currentConvId.value || undefined)) {
      handleEvent(event, textMsg, () => {
        if (!textMsgPushed) {
          displayMessages.value.push(textMsg)
          textMsgPushed = true
        }
      }, toolStartTime)
    }
    if (!textMsgPushed) {
      displayMessages.value.push(textMsg)
    }
    await loadConversations()
  } catch (e: any) {
    textMsg.content = '请求失败：' + (e.message || '服务暂时不可用')
    if (!textMsgPushed) displayMessages.value.push(textMsg)
  } finally {
    loading.value = false
    scrollToBottom()
  }
}

function handleEvent(
  event: SSEEvent,
  textMsg: DisplayMessage,
  ensureTextMsg: () => void,
  toolStartTime: Record<string, number>,
) {
  switch (event.type) {
    case 'text':
      ensureTextMsg()
      textMsg.content = (textMsg.content || '') + event.content
      scrollToBottom()
      break
    case 'tool_start':
      toolStartTime[event.tool || ''] = Date.now()
      displayMessages.value.push({ type: 'tool_start', tool: event.tool, args: event.args })
      scrollToBottom()
      break
    case 'tool_result': {
      const startIdx = displayMessages.value.findIndex(
        m => m.type === 'tool_start' && m.tool === event.tool,
      )
      if (startIdx !== -1) displayMessages.value.splice(startIdx, 1)
      const elapsed = toolStartTime[event.tool || '']
        ? Date.now() - toolStartTime[event.tool || '']
        : undefined
      displayMessages.value.push({
        type: 'tool_result', tool: event.tool, result: event.result,
        args: event.args, elapsed,
      })
      scrollToBottom()
      break
    }
    case 'tool_confirm':
      displayMessages.value.push({
        type: 'tool_confirm', tool: event.tool,
        description: event.description, pending_id: event.pending_id,
        args: event.args,
      })
      scrollToBottom()
      break
    case 'error':
      ensureTextMsg()
      textMsg.content = (textMsg.content || '') + '\n\n' + event.content
      scrollToBottom()
      break
    case 'done':
      if (event.conversation_id && !currentConvId.value) {
        currentConvId.value = event.conversation_id
      }
      break
  }
}

async function handleConfirm(msg: DisplayMessage) {
  if (!msg.pending_id || !currentConvId.value) return
  confirmLoading.value = true

  const idx = displayMessages.value.indexOf(msg)
  if (idx !== -1) displayMessages.value.splice(idx, 1)

  const textMsg: DisplayMessage = { type: 'text', content: '', time: now() }
  let textMsgPushed = false
  const toolStartTime: Record<string, number> = {}

  try {
    for await (const event of confirmAiActionStream(msg.pending_id, currentConvId.value)) {
      handleEvent(event, textMsg, () => {
        if (!textMsgPushed) {
          displayMessages.value.push(textMsg)
          textMsgPushed = true
        }
      }, toolStartTime)
    }
    if (!textMsgPushed) displayMessages.value.push(textMsg)
    await loadConversations()
  } catch (e: any) {
    textMsg.content = '操作失败：' + (e.message || '服务暂时不可用')
    if (!textMsgPushed) displayMessages.value.push(textMsg)
  } finally {
    confirmLoading.value = false
    scrollToBottom()
  }
}

async function handleReject(msg: DisplayMessage) {
  if (!msg.pending_id || !currentConvId.value) return

  const idx = displayMessages.value.indexOf(msg)
  if (idx !== -1) displayMessages.value.splice(idx, 1)

  const textMsg: DisplayMessage = { type: 'text', content: '', time: now() }
  let textMsgPushed = false
  const toolStartTime: Record<string, number> = {}

  try {
    for await (const event of rejectAiActionStream(msg.pending_id, currentConvId.value)) {
      handleEvent(event, textMsg, () => {
        if (!textMsgPushed) {
          displayMessages.value.push(textMsg)
          textMsgPushed = true
        }
      }, toolStartTime)
    }
    if (!textMsgPushed) displayMessages.value.push(textMsg)
  } catch (e: any) {
    textMsg.content = '请求失败：' + (e.message || '服务暂时不可用')
    if (!textMsgPushed) displayMessages.value.push(textMsg)
  } finally {
    scrollToBottom()
  }
}

onMounted(async () => {
  scrollToBottom()
  try {
    const info = await getAiInfo()
    aiModel.value = info.configured ? info.model : ''
  } catch { /* ignore */ }
  await loadConversations()
})
</script>
```

- [ ] **Step 3: 添加样式部分**

```vue
<style lang="scss" scoped>
.ai-page {
  display: flex;
  height: calc(100vh - 56px);
  background: #fff;
}

// ── 左侧栏 ──
.ai-sidebar {
  width: 220px;
  background: #f8f9fa;
  border-right: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.sidebar-header {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.conversation-list {
  flex: 1;
  overflow-y: auto;
}

.conv-item {
  padding: 10px 12px;
  border-left: 3px solid transparent;
  cursor: pointer;
  position: relative;
  transition: all 0.15s;

  &:hover {
    background: #ecf5ff;
    .conv-delete { opacity: 1; }
  }

  &.active {
    background: #ecf5ff;
    border-left-color: #409eff;
    .conv-title { color: #303133; font-weight: 500; }
  }
}

.conv-title {
  font-size: 13px;
  color: #606266;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  padding-right: 20px;
}

.conv-time {
  font-size: 11px;
  color: #c0c4cc;
  margin-top: 2px;
}

.conv-delete {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  opacity: 0;
  color: #909399;
  font-size: 14px;
  transition: opacity 0.15s;
}

.conv-empty {
  padding: 20px;
  text-align: center;
  font-size: 12px;
  color: #c0c4cc;
}

// ── 右侧主区域 ──
.ai-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.ai-header {
  padding: 10px 20px;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

// ── 消息区域 ──
.ai-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
}

// ── 欢迎页 ──
.ai-welcome {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;

  h3 { margin: 12px 0 4px; font-size: 18px; color: #303133; }
  p { color: #909399; margin: 0 0 20px; max-width: 400px; line-height: 1.6; font-size: 13px; }
}

.quick-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
  max-width: 460px;
}

.quick-item {
  padding: 8px 16px;
  background: #f5f7fa;
  border: 1px solid #dcdfe6;
  border-radius: 20px;
  font-size: 12px;
  color: #606266;
  cursor: pointer;
  transition: all 0.15s;

  &:hover { border-color: #409eff; color: #409eff; }
}

// ── 消息行 ──
.msg-row {
  margin-bottom: 16px;

  &.user {
    .msg-bubble { margin-left: 28px; }
  }

  &.assistant {
    .msg-text, .tool-panel { margin-left: 28px; }
  }
}

.msg-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
}

.msg-avatar {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 600;
  flex-shrink: 0;

  &.user-avatar { background: #409eff; color: #fff; }
  &.assistant-avatar { background: #67c23a; color: #fff; }
}

.msg-role {
  font-size: 11px;
  color: #409eff;
  &.assistant-role { color: #67c23a; }
}

.msg-time {
  font-size: 10px;
  color: #c0c4cc;
}

// ── 用户消息气泡 ──
.msg-bubble {
  padding: 8px 14px;
  font-size: 13px;
  line-height: 1.7;
  word-break: break-word;

  &.user-bubble {
    background: #ecf5ff;
    border-left: 3px solid #409eff;
    border-radius: 0 8px 8px 0;
    color: #303133;
  }
}

// ── AI 文本消息 ──
.msg-text {
  font-size: 13px;
  line-height: 1.7;
  color: #303133;
}

// ── 工具面板 ──
.tool-panel {
  border-radius: 8px;
  overflow: hidden;
  font-size: 12px;
  max-width: 100%;

  .tool-header {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 12px;
  }

  .tool-name { font-weight: 500; }
  .tool-args { color: #909399; font-family: monospace; font-size: 11px; }
  .tool-time { color: #c0c4cc; font-size: 10px; margin-left: auto; }

  .tool-body {
    padding: 8px 12px;
    border-top: 1px solid rgba(0, 0, 0, 0.06);
  }

  .tool-section { margin-bottom: 6px; }
  .tool-label { font-size: 10px; color: #909399; margin-bottom: 2px; }
  .tool-code {
    font-family: monospace;
    font-size: 11px;
    color: #606266;
    line-height: 1.5;
    white-space: pre-wrap;
    word-break: break-all;
  }

  .tool-actions {
    padding: 6px 12px;
    border-top: 1px solid rgba(0, 0, 0, 0.06);
    display: flex;
    justify-content: flex-end;
    gap: 6px;
  }

  &.tool-running {
    background: #f0f9ff;
    border: 1px solid #bae6fd;
    .tool-header { color: #0369a1; }
  }

  &.tool-done {
    background: #f0fdf4;
    border: 1px solid #bbf7d0;
    .tool-header { color: #15803d; }

    details {
      &[open] .expand-icon { transform: rotate(90deg); }
    }

    summary {
      cursor: pointer;
      list-style: none;
      &::-webkit-details-marker { display: none; }
    }

    .expand-icon {
      margin-left: auto;
      font-size: 12px;
      transition: transform 0.2s;
    }
  }

  &.tool-confirm {
    background: #fdf6ec;
    border: 1px solid #f5dab1;
    .tool-header { color: #92400e; }
  }

  .confirm-desc {
    margin: 0;
    font-family: monospace;
    white-space: pre-wrap;
    word-break: break-all;
    font-size: 11px;
    line-height: 1.5;
    color: #78350f;
  }
}

// ── Markdown ──
.markdown-body {
  :deep(h1), :deep(h2), :deep(h3) {
    margin: 8px 0 4px;
    font-size: 15px;
    font-weight: 600;
  }
  :deep(p) { margin: 4px 0; }
  :deep(ul), :deep(ol) { margin: 4px 0; padding-left: 20px; }
  :deep(li) { margin: 2px 0; }
  :deep(code) {
    background: rgba(0, 0, 0, 0.06);
    padding: 1px 5px;
    border-radius: 4px;
    font-size: 12px;
    font-family: monospace;
  }
  :deep(pre) {
    background: #1e1e1e;
    border-radius: 8px;
    overflow-x: auto;
    margin: 8px 0;
    code {
      display: block;
      padding: 12px 14px;
      background: none;
      color: #d4d4d4;
      font-size: 12px;
      line-height: 1.5;
    }
  }
  :deep(blockquote) {
    border-left: 3px solid #dcdfe6;
    margin: 8px 0;
    padding: 4px 12px;
    color: #909399;
  }
  :deep(table) {
    border-collapse: collapse;
    margin: 8px 0;
    font-size: 12px;
    th, td { border: 1px solid #e4e7ed; padding: 6px 10px; }
    th { background: #f5f7fa; font-weight: 600; }
  }
  :deep(strong) { font-weight: 600; }
  :deep(hr) { border: none; border-top: 1px solid #e4e7ed; margin: 8px 0; }
}

// ── 打字指示器 ──
.typing-indicator {
  display: flex;
  gap: 4px;
  padding: 12px 16px;

  span {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #c0c4cc;
    animation: dot-bounce 1.4s ease-in-out infinite;
    &:nth-child(2) { animation-delay: 0.2s; }
    &:nth-child(3) { animation-delay: 0.4s; }
  }
}

@keyframes dot-bounce {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}

// ── 输入区 ──
.ai-input {
  padding: 12px 20px 16px;
  border-top: 1px solid #e4e7ed;
  flex-shrink: 0;
}

.input-wrap {
  display: flex;
  gap: 8px;
  align-items: flex-end;

  :deep(.el-textarea__inner) {
    border-radius: 8px;
    padding: 8px 14px;
    resize: none;
  }

  .el-button {
    flex-shrink: 0;
  }
}

.input-tip {
  font-size: 10px;
  color: #c0c4cc;
  margin-top: 4px;
  text-align: center;
}
</style>
```

- [ ] **Step 4: 验证前端编译**

```bash
cd frontend && npx vue-tsc --noEmit 2>&1 | head -20
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/ai/AiView.vue
git commit -m "feat(ai): rewrite UI with IDE split-panel layout and light theme"
```

---

## Task 6: 验证和修复

- [ ] **Step 1: 启动后端验证 API**

```bash
cd backend && python -m uvicorn app.main:app --reload --port 8000
```

检查 `/docs` 中的新 API 端点是否正常显示。

- [ ] **Step 2: 启动前端验证 UI**

```bash
cd frontend && npm run dev
```

在浏览器中打开 AI 助手页面，验证：
- 左侧对话列表正常加载
- 新建对话正常
- 发送消息正常
- 工具面板正常显示
- Markdown 渲染正常

- [ ] **Step 3: 修复发现的问题**

根据测试结果修复任何问题。

- [ ] **Step 4: 最终 Commit**

```bash
git add -A
git commit -m "fix(ai): fix issues found during testing"
```
