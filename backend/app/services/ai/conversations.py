"""对话历史管理 — 内存存储，按 conversation_id 维护消息列表。"""
from __future__ import annotations

import uuid
from typing import Any

# {conversation_id: [message, ...]}
_conversations: dict[str, list[dict[str, Any]]] = {}

# {pending_id: {conversation_id, tool_name, arguments, tool_call_id}}
_pending_actions: dict[str, dict[str, Any]] = {}


def new_conversation() -> str:
    """创建新对话，返回 conversation_id。"""
    cid = str(uuid.uuid4())
    _conversations[cid] = []
    return cid


def get_conversation(conversation_id: str) -> list[dict[str, Any]]:
    """获取对话历史。不存在则创建。"""
    if conversation_id not in _conversations:
        _conversations[conversation_id] = []
    return _conversations[conversation_id]


def add_message(conversation_id: str, message: dict[str, Any]) -> None:
    """向对话历史追加一条消息。"""
    if conversation_id not in _conversations:
        _conversations[conversation_id] = []
    _conversations[conversation_id].append(message)


def clear_conversation(conversation_id: str) -> None:
    """清空对话历史。"""
    _conversations.pop(conversation_id, None)


def store_pending_action(
    conversation_id: str,
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
