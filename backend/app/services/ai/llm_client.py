"""OpenAI 兼容 LLM 客户端，支持 SSE 流式和 function calling。"""
from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator

import httpx

logger = logging.getLogger(__name__)


class LLMClient:
    """调用 OpenAI 兼容 API 的异步客户端。"""

    def __init__(self, base_url: str, api_key: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    async def chat_stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        发送聊天请求，以 SSE 流式返回。

        Yields 解析后的 SSE 事件：
        - {"type": "text", "content": "..."}                 — 文本 delta
        - {"type": "tool_call", "id": "...", "name": "...", "arguments": {...}}  — 工具调用
        - {"type": "done"}                                    — 流结束
        """
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": True,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # 累积 tool_call 的参数（流式返回时 arguments 是分片的）
        pending_tool_calls: dict[int, dict[str, Any]] = {}

        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            ) as response:
                if response.status_code != 200:
                    body = await response.aread()
                    raise RuntimeError(
                        f"LLM API error {response.status_code}: {body.decode()[:500]}"
                    )

                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        # 流结束，发出所有累积的 tool_call
                        for tc in pending_tool_calls.values():
                            yield tc
                        yield {"type": "done"}
                        return

                    try:
                        chunk = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue

                    choices = chunk.get("choices", [])
                    if not choices:
                        continue

                    delta = choices[0].get("delta", {})
                    finish_reason = choices[0].get("finish_reason")

                    # 文本内容
                    if "content" in delta and delta["content"]:
                        yield {"type": "text", "content": delta["content"]}

                    # 工具调用（流式累积）
                    if "tool_calls" in delta:
                        for tc_delta in delta["tool_calls"]:
                            idx = tc_delta["index"]
                            if idx not in pending_tool_calls:
                                pending_tool_calls[idx] = {
                                    "type": "tool_call",
                                    "id": tc_delta.get("id", ""),
                                    "name": tc_delta.get("function", {}).get("name", ""),
                                    "arguments": "",
                                }
                            tc = pending_tool_calls[idx]
                            if "id" in tc_delta and tc_delta["id"]:
                                tc["id"] = tc_delta["id"]
                            if "function" in tc_delta:
                                if "name" in tc_delta["function"] and tc_delta["function"]["name"]:
                                    tc["name"] = tc_delta["function"]["name"]
                                if "arguments" in tc_delta["function"]:
                                    tc["arguments"] += tc_delta["function"]["arguments"]

                    # finish_reason == "tool_calls" 时，tool_calls 已完整，发出
                    if finish_reason == "tool_calls":
                        for tc in pending_tool_calls.values():
                            # 解析 arguments JSON 字符串
                            try:
                                tc["arguments"] = json.loads(tc["arguments"])
                            except (json.JSONDecodeError, TypeError):
                                tc["arguments"] = {}
                            yield tc
                        pending_tool_calls.clear()

                    # finish_reason == "stop" — 正常结束
                    if finish_reason == "stop":
                        yield {"type": "done"}
                        return
