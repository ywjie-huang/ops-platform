"""LLM profile settings: secret masking, merge, connection test helpers."""

from __future__ import annotations

import json

from app.core.settings import (
    UNCHANGED_SECRET,
    classify_llm_http_error,
    is_local_llm,
    mask_api_key,
    merge_profile_secrets,
    public_profile,
)


def _profile(**overrides):
    base = {
        "id": "p1",
        "name": "DeepSeek",
        "provider": "deepseek",
        "icon": "DS",
        "base_url": "https://api.deepseek.com/v1",
        "api_key": "sk-secret-old-key-1234",
        "model": "deepseek-chat",
        "api_mode": "chat_completions",
        "reasoning_effort": "",
        "temperature": 0.7,
        "max_tokens": 4096,
        "top_p": 1.0,
        "system_prompt": "",
        "is_active": True,
    }
    base.update(overrides)
    return base


def test_mask_api_key_hides_middle():
    assert mask_api_key("") == ""
    assert mask_api_key("short") == "*****"
    masked = mask_api_key("sk-secret-old-key-1234")
    assert masked.startswith("sk-")
    assert masked.endswith("1234")
    assert "secret-old-key" not in masked
    assert "****" in masked


def test_public_profile_strips_plaintext_key():
    item = public_profile(_profile())
    assert item["api_key"] == ""
    assert item["has_api_key"] is True
    assert item["api_key_masked"]
    assert "sk-secret-old-key-1234" not in json.dumps(item, ensure_ascii=False)

    empty = public_profile(_profile(api_key=""))
    assert empty["has_api_key"] is False
    assert empty["api_key_masked"] == ""


def test_merge_profile_secrets_keeps_old_key_when_blank_or_unchanged():
    old = [_profile(id="p1", api_key="sk-old-aaaa")]
    incoming_blank = [_profile(id="p1", api_key="", temperature=0.2)]
    merged = merge_profile_secrets(old, incoming_blank)
    assert merged[0]["api_key"] == "sk-old-aaaa"
    assert merged[0]["temperature"] == 0.2

    incoming_token = [_profile(id="p1", api_key=UNCHANGED_SECRET, model="deepseek-reasoner")]
    merged2 = merge_profile_secrets(old, incoming_token)
    assert merged2[0]["api_key"] == "sk-old-aaaa"
    assert merged2[0]["model"] == "deepseek-reasoner"


def test_merge_profile_secrets_overwrites_when_new_key_provided():
    old = [_profile(id="p1", api_key="sk-old-aaaa")]
    incoming = [_profile(id="p1", api_key="sk-new-bbbb")]
    merged = merge_profile_secrets(old, incoming)
    assert merged[0]["api_key"] == "sk-new-bbbb"


def test_merge_profile_secrets_new_id_without_key_stays_empty():
    old = [_profile(id="p1", api_key="sk-old-aaaa")]
    incoming = [_profile(id="p2", api_key="", is_active=False)]
    merged = merge_profile_secrets(old, incoming)
    assert merged[0]["id"] == "p2"
    assert merged[0]["api_key"] == ""


def test_merge_profile_secrets_copy_api_key_from_source():
    old = [_profile(id="p1", api_key="sk-source-zzzz")]
    incoming = [
        _profile(
            id="p2",
            api_key="",
            is_active=False,
            copy_api_key_from="p1",
        )
    ]
    merged = merge_profile_secrets(old, incoming)
    assert merged[0]["api_key"] == "sk-source-zzzz"
    assert "copy_api_key_from" not in merged[0]


def test_is_local_llm_detects_ollama_and_loopback():
    assert is_local_llm("http://localhost:11434/v1", "custom") is True
    assert is_local_llm("http://127.0.0.1:11434/v1") is True
    assert is_local_llm("https://example.com/v1", "ollama") is True
    assert is_local_llm("https://api.deepseek.com/v1", "deepseek") is False


def test_classify_llm_http_error():
    assert classify_llm_http_error(401, "unauthorized") == "auth"
    assert classify_llm_http_error(403, "forbidden") == "auth"
    assert classify_llm_http_error(404, "model not found") == "model_not_found"
    assert classify_llm_http_error(400, 'model "x" does not exist') == "model_not_found"
    assert classify_llm_http_error(500, "boom") == "protocol"
