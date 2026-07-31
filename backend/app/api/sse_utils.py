"""SSE 公共工具：事件格式化 + 日志行时间戳解析。

供 AI 助手 SSE 流、Docker / K8s 日志 SSE 流复用，避免重复实现。
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any


def sse_event(data: dict[str, Any]) -> str:
    """格式化为一次 SSE 事件（data 行 + 两个换行结尾）。"""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


_LOG_TS_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})")


def log_line_ts_to_unix(line: str) -> int | None:
    """解析 docker/k8s timestamps 行首时间戳到 unix 秒。

    docker / k8s 在 ``timestamps=true`` 时产出形如
    ``2026-07-31T10:23:45.123456789Z <text>`` 的行；只取到秒
    （规避纳秒小数 fromisoformat 解析坑；二者也均按秒过滤）。
    """
    m = _LOG_TS_RE.match(line or "")
    if not m:
        return None
    try:
        return int(
            datetime.strptime(m.group(1), "%Y-%m-%dT%H:%M:%S")
            .replace(tzinfo=timezone.utc)
            .timestamp()
        )
    except ValueError:
        return None
