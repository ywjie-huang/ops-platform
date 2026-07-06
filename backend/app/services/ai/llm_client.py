"""OpenAI-compatible LLM client with Chat Completions and Responses support."""
from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator

import httpx

logger = logging.getLogger(__name__)


class LLMClient:
    """Async LLM client for OpenAI-compatible APIs."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        api_mode: str = "chat_completions",
        reasoning_effort: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        top_p: float = 1.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.api_mode = api_mode or "chat_completions"
        self.reasoning_effort = (reasoning_effort or "").strip()
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_p = top_p

    async def chat_stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        if self.api_mode == "responses":
            async for event in self._responses_stream(messages, tools):
                yield event
            return

        async for event in self._chat_completions_stream(messages, tools):
            yield event

    async def _chat_completions_stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        async with self._stream_request("/chat/completions", payload) as response:
            pending_tool_calls: dict[int, dict[str, Any]] = {}
            done_yielded = False

            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data_str = line[6:].strip()
                if data_str == "[DONE]":
                    for tc in pending_tool_calls.values():
                        yield self._finalize_tool_call(tc)
                    yield {"type": "done"}
                    done_yielded = True
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

                content = delta.get("content")
                if content:
                    yield {"type": "text", "content": content}

                if delta.get("tool_calls"):
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
                        if tc_delta.get("id"):
                            tc["id"] = tc_delta["id"]
                        if "function" in tc_delta:
                            fn = tc_delta["function"]
                            if fn.get("name"):
                                tc["name"] = fn["name"]
                            if "arguments" in fn:
                                tc["arguments"] += fn["arguments"]

                if finish_reason == "tool_calls":
                    for tc in pending_tool_calls.values():
                        yield self._finalize_tool_call(tc)
                    pending_tool_calls.clear()
                    done_yielded = True
                    return

                if finish_reason == "stop":
                    yield {"type": "done"}
                    done_yielded = True
                    return

            if not done_yielded:
                for tc in pending_tool_calls.values():
                    yield self._finalize_tool_call(tc)
                yield {"type": "done"}

    async def _responses_stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        payload: dict[str, Any] = {
            "model": self.model,
            "input": self._build_responses_input(messages),
            "stream": True,
            "max_output_tokens": self.max_tokens,
        }
        if self.reasoning_effort:
            payload["reasoning"] = {"effort": self.reasoning_effort}
        if tools:
            payload["tools"] = self._build_responses_tools(tools)
            payload["tool_choice"] = "auto"
        else:
            payload["temperature"] = self.temperature
            payload["top_p"] = self.top_p

        pending_tool_calls: dict[str, dict[str, Any]] = {}
        emitted_tool_ids: set[str] = set()
        response_items: list[dict[str, Any]] = []
        raw_lines: list[str] = []
        saw_sse = False

        async with self._stream_request("/responses", payload) as response:
            async for line in response.aiter_lines():
                raw_lines.append(line)
                if not line.startswith("data: "):
                    continue
                saw_sse = True
                data_str = line[6:].strip()
                if data_str == "[DONE]":
                    for tool_call in self._flush_pending_response_tool_calls(
                        pending_tool_calls, emitted_tool_ids, response_items
                    ):
                        yield tool_call
                    yield {"type": "done"}
                    return

                try:
                    event = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                event_type = event.get("type")
                if event_type == "response.output_text.delta":
                    delta = event.get("delta")
                    if delta:
                        yield {"type": "text", "content": delta}
                    continue

                if event_type == "response.function_call_arguments.delta":
                    item_id = event.get("item_id") or event.get("call_id")
                    if not item_id:
                        continue
                    pending = pending_tool_calls.setdefault(
                        item_id,
                        {"type": "tool_call", "id": item_id, "name": "", "arguments": ""},
                    )
                    pending["arguments"] += event.get("delta", "")
                    continue

                if event_type == "response.output_item.added":
                    item = event.get("item") or {}
                    if item.get("type") == "function_call":
                        item_id = item.get("id") or item.get("call_id")
                        if not item_id:
                            continue
                        pending = pending_tool_calls.setdefault(
                            item_id,
                            {"type": "tool_call", "id": item_id, "name": "", "arguments": ""},
                        )
                        pending["id"] = item.get("call_id") or pending["id"]
                        pending["name"] = item.get("name") or pending["name"]
                    continue

                if event_type == "response.output_item.done":
                    item = event.get("item") or {}
                    item_type = item.get("type")
                    if item_type in ("function_call", "message", "reasoning"):
                        response_items.append(self._response_item_for_input(item))
                    if item_type != "function_call":
                        continue
                    item_id = item.get("id") or item.get("call_id")
                    if not item_id:
                        continue
                    pending = pending_tool_calls.setdefault(
                        item_id,
                        {"type": "tool_call", "id": item_id, "name": "", "arguments": ""},
                    )
                    pending["id"] = item.get("call_id") or pending["id"]
                    pending["name"] = item.get("name") or pending["name"]
                    if item.get("arguments"):
                        pending["arguments"] = item["arguments"]
                    pending["response_item"] = self._response_item_for_input(item)
                    pending["response_items"] = list(response_items)
                    emitted_tool_ids.add(item_id)
                    yield self._finalize_tool_call(pending)
                    continue

                if event_type in ("response.completed", "response.done"):
                    for tool_call in self._flush_pending_response_tool_calls(
                        pending_tool_calls, emitted_tool_ids, response_items
                    ):
                        yield tool_call
                    yield {"type": "done"}
                    return

            if not saw_sse:
                plain_body = "\n".join(raw_lines).strip()
                if plain_body:
                    try:
                        body = json.loads(plain_body)
                    except json.JSONDecodeError:
                        body = None
                    if body:
                        for event in self._parse_plain_responses_body(body):
                            yield event
                        yield {"type": "done"}
                        return

            for tool_call in self._flush_pending_response_tool_calls(
                pending_tool_calls, emitted_tool_ids, response_items
            ):
                yield tool_call
            yield {"type": "done"}

    def _build_responses_input(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for message in messages:
            role = message.get("role")
            if role in ("system", "user"):
                result.append({"role": role, "content": message.get("content", "")})
                continue

            if role == "assistant":
                tool_calls = message.get("tool_calls") or []
                text_content = message.get("content")
                if tool_calls:
                    response_items = self._collect_response_items(tool_calls)
                    if response_items:
                        result.extend(response_items)
                    else:
                        for tool_call in tool_calls:
                            fn = tool_call.get("function", {})
                            call_id = tool_call.get("id", "")
                            result.append(
                                {
                                    "id": tool_call.get("response_item_id") or call_id,
                                    "type": "function_call",
                                    "call_id": call_id,
                                    "name": fn.get("name", ""),
                                    "arguments": fn.get("arguments", "{}"),
                                }
                            )
                    continue

                content: list[dict[str, Any]] = []
                if text_content:
                    content.append({"type": "output_text", "text": text_content})
                if content:
                    result.append({"role": "assistant", "content": content})
                continue

            if role == "tool" and message.get("tool_call_id"):
                result.append(
                    {
                        "type": "function_call_output",
                        "call_id": message["tool_call_id"],
                        "output": message.get("content", ""),
                    }
                )

        return result

    def _build_responses_tools(self, tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        response_tools = []
        for tool in tools:
            fn = tool.get("function", {})
            response_tools.append(
                {
                    "type": "function",
                    "name": fn.get("name", ""),
                    "description": fn.get("description", ""),
                    "parameters": fn.get("parameters", {"type": "object", "properties": {}}),
                }
            )
        return response_tools

    def _finalize_tool_call(self, tool_call: dict[str, Any]) -> dict[str, Any]:
        finalized = dict(tool_call)
        try:
            finalized["arguments"] = json.loads(finalized.get("arguments") or "{}")
        except (json.JSONDecodeError, TypeError):
            finalized["arguments"] = {}
        return finalized

    def _collect_response_items(self, tool_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        seen: set[tuple[str, str, str]] = set()
        for tool_call in tool_calls:
            raw_items = list(tool_call.get("response_items") or [])
            if tool_call.get("response_item"):
                raw_items.append(tool_call["response_item"])
            for raw_item in raw_items:
                item = self._response_item_for_input(raw_item)
                marker = (
                    item.get("id", ""),
                    item.get("type", ""),
                    item.get("call_id", ""),
                )
                if marker in seen:
                    continue
                seen.add(marker)
                items.append(item)
        return items

    def _response_item_for_input(self, item: dict[str, Any]) -> dict[str, Any]:
        item_type = item.get("type", "")
        if item_type == "function_call":
            call_id = item.get("call_id") or item.get("id", "")
            return {
                "id": item.get("id") or call_id,
                "type": "function_call",
                "call_id": call_id,
                "name": item.get("name", ""),
                "arguments": item.get("arguments", "{}"),
            }

        if item_type == "reasoning":
            keys = ("id", "type", "summary", "content", "encrypted_content", "status")
            return {key: item[key] for key in keys if key in item}

        if item_type == "message":
            keys = ("id", "type", "role", "content", "status")
            return {key: item[key] for key in keys if key in item}

        return dict(item)

    def _flush_pending_response_tool_calls(
        self,
        pending_tool_calls: dict[str, dict[str, Any]],
        emitted_tool_ids: set[str],
        response_items: list[dict[str, Any]] | None = None,
    ):
        for item_id, tool_call in pending_tool_calls.items():
            if item_id in emitted_tool_ids:
                continue
            if not tool_call.get("name"):
                continue
            if response_items and not tool_call.get("response_items"):
                tool_call["response_items"] = list(response_items)
            yield self._finalize_tool_call(tool_call)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }

    def _parse_plain_responses_body(self, body: dict[str, Any]) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        for item in body.get("output", []):
            item_type = item.get("type")
            if item_type == "message":
                for content in item.get("content", []):
                    text = content.get("text") or content.get("delta")
                    if content.get("type") == "output_text" and text:
                        events.append({"type": "text", "content": text})
            elif item_type == "function_call":
                events.append(
                    self._finalize_tool_call(
                        {
                            "type": "tool_call",
                            "id": item.get("call_id") or item.get("id", ""),
                            "name": item.get("name", ""),
                            "arguments": item.get("arguments", "{}"),
                        }
                    )
                )
        return events

    def _stream_request(self, path: str, payload: dict[str, Any]):
        client = httpx.AsyncClient(timeout=120, follow_redirects=True)
        response_cm = client.stream(
            "POST",
            f"{self.base_url}{path}",
            headers=self._headers(),
            json=payload,
        )
        return _ValidatedStream(client, response_cm)


class _ValidatedStream:
    def __init__(self, client: httpx.AsyncClient, response_cm):
        self._client = client
        self._response_cm = response_cm
        self._response = None

    async def __aenter__(self):
        await self._client.__aenter__()
        self._response = await self._response_cm.__aenter__()
        if self._response.status_code != 200:
            body = await self._response.aread()
            await self._response_cm.__aexit__(None, None, None)
            await self._client.__aexit__(None, None, None)
            raise RuntimeError(
                f"LLM API error {self._response.status_code}: {body.decode()[:500]}"
            )
        return self._response

    async def __aexit__(self, exc_type, exc, tb):
        await self._response_cm.__aexit__(exc_type, exc, tb)
        await self._client.__aexit__(exc_type, exc, tb)
        return False
