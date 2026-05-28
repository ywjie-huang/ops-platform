"""对话管理 — 基于数据库的对话和消息 CRUD。"""
from __future__ import annotations

import json
import uuid
from datetime import datetime

from app.core.config import CHINA_TZ
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
        conv.updated_at = datetime.now(CHINA_TZ)

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
