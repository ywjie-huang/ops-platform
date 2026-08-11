import asyncio
import json

from app.services.ai.llm_client import LLMClient


class _FakeStreamResponse:
    def __init__(self, status_code: int, lines: list[str], body: bytes = b""):
        self.status_code = status_code
        self._lines = lines
        self._body = body

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def aiter_lines(self):
        for line in self._lines:
            yield line

    async def aread(self):
        return self._body


class _FakeAsyncClient:
    def __init__(self, recorder: dict, response: _FakeStreamResponse):
        self._recorder = recorder
        self._response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def stream(self, method: str, url: str, headers=None, json=None):
        self._recorder["method"] = method
        self._recorder["url"] = url
        self._recorder["headers"] = headers
        self._recorder["json"] = json
        self._recorder.setdefault("requests", []).append(
            {"method": method, "url": url, "headers": headers, "json": json}
        )
        return self._response


def test_chat_completions_mode_posts_expected_payload(monkeypatch):
    recorder = {}
    response = _FakeStreamResponse(
        200,
        [
            'data: {"choices":[{"delta":{"content":"hello"},"finish_reason":null}]}',
            'data: [DONE]',
        ],
    )

    def fake_async_client(*args, **kwargs):
        return _FakeAsyncClient(recorder, response)

    monkeypatch.setattr("app.services.ai.llm_client.httpx.AsyncClient", fake_async_client)

    client = LLMClient(
        "https://relay.example.com/v1",
        "sk-test",
        "gpt-4o-mini",
        api_mode="chat_completions",
        temperature=0.3,
        max_tokens=512,
        top_p=0.9,
    )

    async def collect_events():
        return [event async for event in client.chat_stream([{"role": "user", "content": "hi"}])]

    events = asyncio.run(collect_events())

    assert recorder["method"] == "POST"
    assert recorder["url"] == "https://relay.example.com/v1/chat/completions"
    assert recorder["json"]["model"] == "gpt-4o-mini"
    assert recorder["json"]["messages"] == [{"role": "user", "content": "hi"}]
    assert recorder["json"]["temperature"] == 0.3
    assert recorder["json"]["max_tokens"] == 512
    assert recorder["json"]["top_p"] == 0.9
    assert events == [{"type": "text", "content": "hello"}, {"type": "done"}]


def test_responses_mode_posts_reasoning_and_parses_text_events(monkeypatch):
    recorder = {}
    response = _FakeStreamResponse(
        200,
        [
            'data: {"type":"response.output_text.delta","delta":"hello "}',
            'data: {"type":"response.output_text.delta","delta":"world"}',
            'data: {"type":"response.completed"}',
        ],
    )

    def fake_async_client(*args, **kwargs):
        return _FakeAsyncClient(recorder, response)

    monkeypatch.setattr("app.services.ai.llm_client.httpx.AsyncClient", fake_async_client)

    client = LLMClient(
        "https://relay.example.com/v1",
        "sk-test",
        "o3",
        api_mode="responses",
        reasoning_effort="high",
        temperature=0.7,
        max_tokens=2048,
        top_p=1.0,
    )

    async def collect_events():
        return [event async for event in client.chat_stream([{"role": "user", "content": "hi"}])]

    events = asyncio.run(collect_events())

    assert recorder["url"] == "https://relay.example.com/v1/responses"
    assert recorder["json"]["model"] == "o3"
    assert recorder["json"]["input"] == [{"role": "user", "content": "hi"}]
    assert recorder["json"]["max_output_tokens"] == 2048
    assert recorder["json"]["reasoning"] == {"effort": "high"}
    assert "messages" not in recorder["json"]
    assert events == [
        {"type": "text", "content": "hello "},
        {"type": "text", "content": "world"},
        {"type": "done"},
    ]


def test_responses_mode_accumulates_function_call_arguments(monkeypatch):
    recorder = {}
    response = _FakeStreamResponse(
        200,
        [
            'data: {"type":"response.function_call_arguments.delta","item_id":"fc_1","delta":"{\\"host_id\\":"}',
            'data: {"type":"response.function_call_arguments.delta","item_id":"fc_1","delta":" 1}"}',
            'data: {"type":"response.output_item.done","item":{"id":"fc_1","type":"function_call","name":"query_containers","call_id":"call_1","arguments":"{\\"host_id\\": 1}"}}',
            'data: {"type":"response.completed"}',
        ],
    )

    def fake_async_client(*args, **kwargs):
        return _FakeAsyncClient(recorder, response)

    monkeypatch.setattr("app.services.ai.llm_client.httpx.AsyncClient", fake_async_client)

    client = LLMClient(
        "https://relay.example.com/v1",
        "sk-test",
        "o3",
        api_mode="responses",
    )

    async def collect_events():
        return [event async for event in client.chat_stream([{"role": "user", "content": "hi"}])]

    events = asyncio.run(collect_events())

    assert events == [
        {
            "type": "tool_call",
            "id": "call_1",
            "name": "query_containers",
            "arguments": {"host_id": 1},
            "response_item": {
                "id": "fc_1",
                "type": "function_call",
                "call_id": "call_1",
                "name": "query_containers",
                "arguments": "{\"host_id\": 1}",
            },
            "response_items": [
                {
                    "id": "fc_1",
                    "type": "function_call",
                    "call_id": "call_1",
                    "name": "query_containers",
                    "arguments": "{\"host_id\": 1}",
                }
            ],
        },
        {"type": "done"},
    ]


def test_responses_input_conversion_for_tool_messages():
    """工具续接：assistant tool_call 携带的 response item 内联进 input，
    不再用 item_reference（依赖服务端记忆，call_id 当 id 用会 502）。"""
    client = LLMClient("https://relay.example.com/v1", "sk-test", "o3", api_mode="responses")

    converted = client._build_responses_input(
        [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "hello"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {"name": "query_assets", "arguments": json.dumps({"keyword": "db"})},
                        "response_items": [
                            {"id": "rs_1", "type": "reasoning", "content": [], "summary": []},
                            {
                                "id": "fc_1",
                                "type": "function_call",
                                "call_id": "call_1",
                                "name": "query_assets",
                                "arguments": json.dumps({"keyword": "db"}),
                            },
                        ],
                    }
                ],
            },
            {"role": "tool", "content": "done", "tool_call_id": "call_1"},
        ]
    )

    assert converted == [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "hello"},
        {"id": "rs_1", "type": "reasoning", "content": [], "summary": []},
        {
            "id": "fc_1",
            "type": "function_call",
            "call_id": "call_1",
            "name": "query_assets",
            "arguments": json.dumps({"keyword": "db"}),
        },
        {
            "type": "function_call_output",
            "call_id": "call_1",
            "output": "done",
        },
    ]


def test_responses_input_inlines_function_call_with_correct_id_not_call_id():
    """回归：function_call item 的 item_reference 旧实现误用 call_id（call_xxx）
    当 id，服务端找不到对应 item 返回 502。改为内联完整 item，id 用 fc_xxx。"""
    client = LLMClient("https://relay.example.com/v1", "sk-test", "o3", api_mode="responses")

    converted = client._build_responses_input(
        [
            {"role": "user", "content": "q"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_abc",
                        "type": "function",
                        "function": {"name": "query_logs", "arguments": "{}"},
                        "response_item": {
                            "id": "fc_xyz",
                            "type": "function_call",
                            "call_id": "call_abc",
                            "name": "query_logs",
                            "arguments": "{}",
                        },
                    }
                ],
            },
            {"role": "tool", "content": "no logs", "tool_call_id": "call_abc"},
        ]
    )

    # 不应出现任何 item_reference
    assert not any(item.get("type") == "item_reference" for item in converted)
    # function_call 应内联，且 id 是 fc_xyz（不是 call_abc）
    fc_items = [item for item in converted if item.get("type") == "function_call"]
    assert len(fc_items) == 1
    assert fc_items[0]["id"] == "fc_xyz"
    assert fc_items[0]["call_id"] == "call_abc"
    # function_call_output 的 call_id 与 function_call 对应
    fco_items = [item for item in converted if item.get("type") == "function_call_output"]
    assert len(fco_items) == 1
    assert fco_items[0]["call_id"] == "call_abc"


def test_responses_mode_retries_tool_outputs_as_plain_context_after_502(monkeypatch):
    recorder = {}
    responses = [
        _FakeStreamResponse(502, [], b""),
        _FakeStreamResponse(
            200,
            [
                'data: {"type":"response.output_text.delta","delta":"server-a CPU is high"}',
                'data: {"type":"response.completed"}',
            ],
        ),
    ]

    def fake_async_client(*args, **kwargs):
        return _FakeAsyncClient(recorder, responses.pop(0))

    monkeypatch.setattr("app.services.ai.llm_client.httpx.AsyncClient", fake_async_client)

    client = LLMClient("https://relay.example.com/v1", "sk-test", "o3", api_mode="responses")
    messages = [
        {"role": "user", "content": "今天哪台服务器资源异常？"},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {"name": "query_assets", "arguments": "{}"},
                    "response_items": [
                        {
                            "id": "fc_1",
                            "type": "function_call",
                            "call_id": "call_1",
                            "name": "query_assets",
                            "arguments": "{}",
                        }
                    ],
                }
            ],
        },
        {"role": "tool", "content": "server-a cpu=96%", "tool_call_id": "call_1"},
    ]

    async def collect_events():
        return [
            event
            async for event in client.chat_stream(
                messages,
                tools=[
                    {
                        "type": "function",
                        "function": {
                            "name": "query_assets",
                            "description": "query assets",
                            "parameters": {"type": "object", "properties": {}},
                        },
                    }
                ],
            )
        ]

    events = asyncio.run(collect_events())

    assert events == [
        {"type": "text", "content": "server-a CPU is high"},
        {"type": "done"},
    ]
    first_input = recorder["requests"][0]["json"]["input"]
    retry_input = recorder["requests"][1]["json"]["input"]
    assert any(item.get("type") == "function_call_output" for item in first_input)
    assert not any(item.get("type") in {"function_call_output", "item_reference"} for item in retry_input)
    assert retry_input[-1]["role"] == "user"
    assert "query_assets" in retry_input[-1]["content"]
    assert "server-a cpu=96%" in retry_input[-1]["content"]


def test_responses_mode_falls_back_to_plain_json_response(monkeypatch):
    recorder = {}
    response = _FakeStreamResponse(
        200,
        [
            '{"output":[{"type":"message","content":[{"type":"output_text","text":"plain json reply"}]}]}',
        ],
    )

    def fake_async_client(*args, **kwargs):
        return _FakeAsyncClient(recorder, response)

    monkeypatch.setattr("app.services.ai.llm_client.httpx.AsyncClient", fake_async_client)

    client = LLMClient(
        "https://relay.example.com/v1",
        "sk-test",
        "o3",
        api_mode="responses",
    )

    async def collect_events():
        return [event async for event in client.chat_stream([{"role": "user", "content": "hi"}])]

    events = asyncio.run(collect_events())

    assert recorder["headers"]["Accept"] == "text/event-stream"
    assert events == [
        {"type": "text", "content": "plain json reply"},
        {"type": "done"},
    ]


# ─── Anthropic Messages 协议测试 ──────────────────────────


def test_anthropic_mode_posts_messages_payload(monkeypatch):
    """Anthropic 模式：POST 到 /v1/messages，headers 用 x-api-key + anthropic-version，
    system 抽到顶层，tools 是 Anthropic 格式。"""
    recorder = {}
    response = _FakeStreamResponse(
        200,
        [
            'event: message_start',
            'data: {"type":"message_start","message":{"id":"msg_1"}}',
            'event: content_block_start',
            'data: {"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}',
            'event: content_block_delta',
            'data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"hi"}}',
            'event: content_block_stop',
            'data: {"type":"content_block_stop","index":0}',
            'event: message_stop',
            'data: {"type":"message_stop"}',
        ],
    )

    def fake_async_client(*args, **kwargs):
        return _FakeAsyncClient(recorder, response)

    monkeypatch.setattr("app.services.ai.llm_client.httpx.AsyncClient", fake_async_client)

    client = LLMClient(
        "https://api.anthropic.com",
        "sk-ant-test",
        "claude-sonnet-4-5",
        api_mode="anthropic",
        max_tokens=1024,
    )

    messages = [
        {"role": "system", "content": "你是运维助手"},
        {"role": "user", "content": "你好"},
    ]
    tools = [
        {
            "type": "function",
            "function": {
                "name": "query_logs",
                "description": "查日志",
                "parameters": {"type": "object", "properties": {"level": {"type": "string"}}},
            },
        }
    ]

    async def collect_events():
        return [event async for event in client.chat_stream(messages, tools)]

    events = asyncio.run(collect_events())

    req = recorder["requests"][0]
    assert req["url"] == "https://api.anthropic.com/v1/messages"
    assert req["headers"]["x-api-key"] == "sk-ant-test"
    assert req["headers"]["anthropic-version"] == "2023-06-01"
    # system 抽到顶层
    payload = req["json"]
    assert payload["system"] == "你是运维助手"
    assert payload["messages"] == [{"role": "user", "content": "你好"}]
    assert payload["max_tokens"] == 1024
    # tools 是 Anthropic 格式（name/description/input_schema）
    assert payload["tools"] == [
        {
            "name": "query_logs",
            "description": "查日志",
            "input_schema": {"type": "object", "properties": {"level": {"type": "string"}}},
        }
    ]
    assert events == [
        {"type": "text", "content": "hi"},
        {"type": "done"},
    ]


def test_anthropic_stream_parses_tool_use_with_split_input_json(monkeypatch):
    """Anthropic 流式 tool_use：input_json 分多个 input_json_delta 发送，
    content_block_stop 时拼完整解析成 dict。"""
    recorder = {}
    response = _FakeStreamResponse(
        200,
        [
            'event: content_block_start',
            'data: {"type":"content_block_start","index":0,"content_block":{"type":"tool_use","id":"toolu_1","name":"query_logs"}}',
            'event: content_block_delta',
            'data: {"type":"content_block_delta","index":0,"delta":{"type":"input_json_delta","partial_json":"{\\"level\\""}}',
            'event: content_block_delta',
            'data: {"type":"content_block_delta","index":0,"delta":{"type":"input_json_delta","partial_json":": \\"error\\"}"}}',
            'event: content_block_stop',
            'data: {"type":"content_block_stop","index":0}',
            'event: message_stop',
            'data: {"type":"message_stop"}',
        ],
    )

    def fake_async_client(*args, **kwargs):
        return _FakeAsyncClient(recorder, response)

    monkeypatch.setattr("app.services.ai.llm_client.httpx.AsyncClient", fake_async_client)

    client = LLMClient("https://api.anthropic.com", "sk-test", "claude", api_mode="anthropic")

    async def collect_events():
        return [event async for event in client.chat_stream([{"role": "user", "content": "查日志"}])]

    events = asyncio.run(collect_events())

    # tool_call 事件：arguments 是拼好解析的 dict
    assert events == [
        {
            "type": "tool_call",
            "id": "toolu_1",
            "name": "query_logs",
            "arguments": {"level": "error"},
        },
        {"type": "done"},
    ]


def test_anthropic_messages_conversion_handles_tool_history():
    """多轮工具对话：OpenAI tool_calls/tool 消息正确转成 Anthropic tool_use/tool_result。
    这是工具续接的关键（避免 Responses 续接 502 的同类问题）。"""
    client = LLMClient("https://api.anthropic.com", "sk-test", "claude", api_mode="anthropic")

    messages = [
        {"role": "user", "content": "查日志"},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {
                        "name": "query_logs",
                        "arguments": json.dumps({"level": "error"}),
                    },
                }
            ],
        },
        {"role": "tool", "content": "无匹配日志", "tool_call_id": "call_1"},
    ]

    system, conv = client._build_anthropic_messages(messages)

    assert system == ""
    assert conv == [
        {"role": "user", "content": "查日志"},
        {
            "role": "assistant",
            "content": [
                {"type": "tool_use", "id": "call_1", "name": "query_logs", "input": {"level": "error"}},
            ],
        },
        {
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": "call_1", "content": "无匹配日志"},
            ],
        },
    ]


def test_anthropic_system_prompt_extracted_and_merged():
    """多条 system 消息合并为顶层 system 字段（用换行分隔），不进 messages 数组。"""
    client = LLMClient("https://api.anthropic.com", "sk-test", "claude", api_mode="anthropic")

    messages = [
        {"role": "system", "content": "规则一"},
        {"role": "system", "content": "规则二"},
        {"role": "user", "content": "你好"},
    ]

    system, conv = client._build_anthropic_messages(messages)

    assert "规则一" in system and "规则二" in system
    assert all(m["role"] != "system" for m in conv)
    assert conv == [{"role": "user", "content": "你好"}]


def test_anthropic_mode_used_when_api_mode_is_anthropic(monkeypatch):
    """api_mode='anthropic' 时走 _messages_stream，不会误进 chat_completions。"""
    recorder = {}
    response = _FakeStreamResponse(
        200,
        [
            'event: message_stop',
            'data: {"type":"message_stop"}',
        ],
    )

    def fake_async_client(*args, **kwargs):
        return _FakeAsyncClient(recorder, response)

    monkeypatch.setattr("app.services.ai.llm_client.httpx.AsyncClient", fake_async_client)

    client = LLMClient("https://api.anthropic.com", "sk-test", "claude", api_mode="anthropic")

    async def collect_events():
        return [event async for event in client.chat_stream([{"role": "user", "content": "hi"}])]

    events = asyncio.run(collect_events())
    # 命中的是 /v1/messages 而不是 /chat/completions
    assert recorder["requests"][0]["url"] == "https://api.anthropic.com/v1/messages"
    assert events[-1] == {"type": "done"}
