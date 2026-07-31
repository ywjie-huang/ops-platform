"""SSE 事件格式化公共工具。

供 AI 助手 SSE 流、Docker 日志 SSE 流等复用，避免重复实现。
"""
from __future__ import annotations

import json
from typing import Any


def sse_event(data: dict[str, Any]) -> str:
    """格式化为一次 SSE 事件（data 行 + 两个换行结尾）。"""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
