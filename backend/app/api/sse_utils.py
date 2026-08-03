"""SSE 公共工具：事件格式化 + 日志行时间戳解析。

供 AI 助手 SSE 流、Docker / K8s 日志 SSE 流复用，避免重复实现。
"""
from __future__ import annotations

import asyncio
import json
import re
import time
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable


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


async def polling_log_stream(
    request: Any,
    interval: int,
    since_arg: int | None,
    fetch_fn: Callable[[int], Awaitable[str]],
) -> AsyncGenerator[str, None]:
    """通用轮询日志 SSE 流。

    封装 Docker / K8s 日志流共有的逻辑：初始 ready 事件、断连检测、
    相邻批次秒级去重、时间戳游标推进、append/heartbeat/done 事件。

    ``fetch_fn(last_ts)`` 为调用方提供的异步拉取函数，返回本批原始日志
    文本（多行）；抛异常时发送 ``error`` 事件并在下一轮重试。
    """
    last_ts = int(since_arg) if since_arg is not None else int(time.time())
    prev_batch: set[str] = set()
    yield sse_event({"type": "ready", "since": last_ts})

    tick = 0
    while True:
        if await request.is_disconnected():
            break
        try:
            raw = await fetch_fn(last_ts)
        except Exception as e:  # noqa: BLE001
            yield sse_event({"type": "error", "message": str(e)})
            await asyncio.sleep(interval)
            continue

        batch_lines = raw.splitlines() if raw else []
        new_lines = [ln for ln in batch_lines if ln not in prev_batch]
        prev_batch = set(batch_lines)

        if new_lines:
            timestamps = [ts for ts in (log_line_ts_to_unix(ln) for ln in batch_lines) if ts is not None]
            if timestamps:
                last_ts = max(timestamps)
            yield sse_event({
                "type": "append",
                "lines": "\n".join(new_lines),
                "count": len(new_lines),
            })

        tick += 1
        if tick % 15 == 0:  # ~30s 心跳，防代理掐断空闲连接
            yield sse_event({"type": "heartbeat"})

        await asyncio.sleep(interval)

    yield sse_event({"type": "done"})
