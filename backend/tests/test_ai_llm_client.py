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
        {"type": "item_reference", "id": "rs_1"},
        {"type": "item_reference", "id": "call_1"},
        {
            "type": "function_call_output",
            "call_id": "call_1",
            "output": "done",
        },
    ]


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
