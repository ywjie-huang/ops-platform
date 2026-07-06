import json

from app.api.ai import _build_assistant_tool_calls


def test_build_assistant_tool_calls_preserves_responses_metadata():
    tool_calls = [
        {
            "id": "call_1",
            "name": "query_containers",
            "arguments": {"host_ip": "172.16.100.1"},
            "response_item": {
                "id": "fc_1",
                "type": "function_call",
                "call_id": "call_1",
                "name": "query_containers",
                "arguments": "{\"host_ip\":\"172.16.100.1\"}",
            },
            "response_items": [
                {"id": "rs_1", "type": "reasoning", "summary": []},
                {
                    "id": "fc_1",
                    "type": "function_call",
                    "call_id": "call_1",
                    "name": "query_containers",
                    "arguments": "{\"host_ip\":\"172.16.100.1\"}",
                },
            ],
        }
    ]

    stored = _build_assistant_tool_calls(tool_calls)

    assert stored == [
        {
            "id": "call_1",
            "type": "function",
            "function": {
                "name": "query_containers",
                "arguments": json.dumps({"host_ip": "172.16.100.1"}, ensure_ascii=False),
            },
            "response_item": {
                "id": "fc_1",
                "type": "function_call",
                "call_id": "call_1",
                "name": "query_containers",
                "arguments": "{\"host_ip\":\"172.16.100.1\"}",
            },
            "response_items": [
                {"id": "rs_1", "type": "reasoning", "summary": []},
                {
                    "id": "fc_1",
                    "type": "function_call",
                    "call_id": "call_1",
                    "name": "query_containers",
                    "arguments": "{\"host_ip\":\"172.16.100.1\"}",
                },
            ],
        }
    ]
