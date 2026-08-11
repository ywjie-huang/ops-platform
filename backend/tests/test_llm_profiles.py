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


def test_list_llm_models_endpoint_parses_openai_compatible_payload(monkeypatch):
    from app.api import settings as settings_api

    class FakeResp:
        status_code = 200

        def json(self):
            return {
                "data": [
                    {"id": "deepseek-chat", "owned_by": "deepseek"},
                    {"id": "deepseek-reasoner", "owned_by": "deepseek"},
                    {"id": "deepseek-chat", "owned_by": "dup"},
                ]
            }

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, url, headers=None):
            assert url.endswith("/models")
            return FakeResp()

    class FakeDb:
        pass

    monkeypatch.setattr(settings_api.httpx if hasattr(settings_api, "httpx") else __import__("httpx"), "Client", FakeClient)
    # patch where used: inside function imports httpx, so patch httpx.Client globally
    import httpx

    monkeypatch.setattr(httpx, "Client", FakeClient)
    monkeypatch.setattr(settings_api, "resolve_profile_api_key", lambda db, api_key="", profile_id=None: "sk-test")

    body = settings_api.LLMModelsBody(
        base_url="https://api.deepseek.com/v1",
        api_key="sk-test",
        provider="deepseek",
    )
    result = settings_api.api_list_llm_models(body, db=FakeDb(), _=object())
    assert result["data"]["ok"] is True
    ids = [x["id"] for x in result["data"]["items"]]
    assert ids == ["deepseek-chat", "deepseek-reasoner"]


def test_list_llm_models_allows_local_without_key(monkeypatch):
    from app.api import settings as settings_api
    import httpx

    class FakeResp:
        status_code = 200

        def json(self):
            return {"data": [{"id": "qwen2.5:7b"}]}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, url, headers=None):
            assert "Authorization" not in (headers or {})
            return FakeResp()

    monkeypatch.setattr(httpx, "Client", FakeClient)
    monkeypatch.setattr(settings_api, "resolve_profile_api_key", lambda db, api_key="", profile_id=None: "")

    body = settings_api.LLMModelsBody(
        base_url="http://localhost:11434/v1",
        api_key="",
        provider="ollama",
    )
    result = settings_api.api_list_llm_models(body, db=object(), _=object())
    assert result["data"]["ok"] is True
    assert result["data"]["items"][0]["id"] == "qwen2.5:7b"


def test_list_llm_models_anthropic_uses_xapikey_and_v1_path(monkeypatch):
    """Anthropic 协议：请求 /v1/models（base_url 不含 /v1），用 x-api-key 头而非 Bearer。
    智谱/Claude 的 anthropic 兼容端点都提供 OpenAI 风格的 {data:[...]} 响应。"""
    from app.api import settings as settings_api
    import httpx

    captured = {}

    class FakeResp:
        status_code = 200

        def json(self):
            return {"data": [
                {"id": "glm-4.6", "display_name": "GLM-4.6"},
                {"id": "glm-5.2", "display_name": "GLM-5.2"},
            ]}

    class FakeClient:
        def __init__(self, *a, **kw):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, url, headers=None):
            captured["url"] = url
            captured["headers"] = headers
            return FakeResp()

    monkeypatch.setattr(httpx, "Client", FakeClient)
    monkeypatch.setattr(settings_api, "resolve_profile_api_key", lambda db, api_key="", profile_id=None: "sk-test")

    body = settings_api.LLMModelsBody(
        base_url="https://open.bigmodel.cn/api/anthropic",
        api_key="sk-test",
        provider="zhipu",
        api_mode="anthropic",
    )
    result = settings_api.api_list_llm_models(body, db=object(), _=object())

    # 请求路径是 /v1/models（不是 /models），头是 x-api-key
    assert captured["url"] == "https://open.bigmodel.cn/api/anthropic/v1/models"
    assert captured["headers"]["x-api-key"] == "sk-test"
    assert captured["headers"]["anthropic-version"] == "2023-06-01"
    assert "Authorization" not in captured["headers"]

    assert result["data"]["ok"] is True
    ids = [x["id"] for x in result["data"]["items"]]
    assert ids == ["glm-4.6", "glm-5.2"]


class _MemDb:
    """Minimal stand-in for settings helpers that only need get/set_config behavior."""

    def __init__(self, values=None):
        self.values = dict(values or {})

    def scalar(self, _stmt):
        return None


def test_get_llm_config_prefers_active_profile(monkeypatch):
    from app.core import settings as core

    profiles = [
        _profile(id="a", is_active=False, model="m-a", api_key="sk-a"),
        _profile(id="b", is_active=True, model="m-b", api_key="sk-b", base_url="https://b.example/v1"),
    ]
    monkeypatch.setattr(core, "get_llm_profiles", lambda db: profiles)
    # avoid auto-migration side effects
    monkeypatch.setattr(core, "ensure_llm_profiles_migrated", lambda db: profiles)

    cfg = core.get_llm_config(object())
    assert cfg["model"] == "m-b"
    assert cfg["api_key"] == "sk-b"
    assert cfg["base_url"] == "https://b.example/v1"


def test_ensure_llm_profiles_migrated_from_legacy(monkeypatch):
    from app.core import settings as core

    store: dict[str, str] = {
        "llm.base_url": "https://api.deepseek.com/v1",
        "llm.api_key": "sk-legacy",
        "llm.model": "deepseek-chat",
        "llm.api_mode": "chat_completions",
        "llm.reasoning_effort": "",
        "llm.temperature": "0.3",
        "llm.max_tokens": "2048",
        "llm.top_p": "0.9",
        "llm.system_prompt": "ops",
        "llm.profiles": "[]",
    }

    def fake_get_config(db, key):
        return store.get(key, core._DEFAULTS.get(key, ""))

    def fake_set_config(db, key, value, description=""):
        store[key] = value
        return object()

    monkeypatch.setattr(core, "get_config", fake_get_config)
    monkeypatch.setattr(core, "set_config", fake_set_config)

    profiles = core.ensure_llm_profiles_migrated(object())
    assert len(profiles) == 1
    assert profiles[0]["api_key"] == "sk-legacy"
    assert profiles[0]["model"] == "deepseek-chat"
    assert profiles[0]["is_active"] is True
    assert store["llm.profiles"] != "[]"
    assert store["llm.api_key"] == "sk-legacy"


def test_is_llm_configured_allows_local_without_key():
    from app.core.settings import is_llm_configured

    assert is_llm_configured({
        "base_url": "http://localhost:11434/v1",
        "api_key": "",
        "model": "qwen2.5:7b",
    })
    assert not is_llm_configured({
        "base_url": "https://api.deepseek.com/v1",
        "api_key": "",
        "model": "deepseek-chat",
    })
    assert is_llm_configured({
        "base_url": "https://api.deepseek.com/v1",
        "api_key": "sk-x",
        "model": "deepseek-chat",
    })


def test_guess_provider_from_url_covers_all_presets():
    """provider URL 推断覆盖所有内置预设的 base_url，与前端 PROVIDER_PRESETS 对齐。"""
    from app.core.settings import guess_provider_from_url

    cases = {
        "https://api.openai.com/v1": "openai",
        "https://open.bigmodel.cn/api/paas/v4/": "zhipu",
        "https://open.bigmodel.cn/api/anthropic": "zhipu",
        "https://api.anthropic.com": "claude",
        "https://api.moonshot.cn/v1": "moonshot",
        "https://api.moonshot.ai/v1": "moonshot",
        "https://api.deepseek.com/v1": "deepseek",
        "https://dashscope.aliyuncs.com/compatible-mode/v1": "qwen",
        "https://ark.cn-beijing.volces.com/api/v3": "doubao",
        "https://qianfan.baidubce.com/v2": "wenxin",
        "http://localhost:11434/v1": "ollama",
        "https://my-gateway.example/v1": "custom",
        "": "custom",
    }
    for url, expected in cases.items():
        assert guess_provider_from_url(url) == expected, (
            f"{url!r} 应推断为 {expected!r}，实际得到 {guess_provider_from_url(url)!r}"
        )
