"""系统配置读取工具 — DB 优先，fallback 到 config.py 常量。"""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import ALERTMANAGER_URL, PROMETHEUS_URL
from app.models.system_config import SystemConfig

# 前端/调用方用该标记表示“不修改已有密钥”
UNCHANGED_SECRET = "__UNCHANGED__"

# 默认值（来自原 config.py）
_DEFAULTS: dict[str, str] = {
    "prometheus.url": PROMETHEUS_URL,
    "alertmanager.url": ALERTMANAGER_URL,
    # 巡检阈值
    "patrol.cpu_warning": "80",
    "patrol.cpu_critical": "95",
    "patrol.memory_warning": "85",
    "patrol.memory_critical": "95",
    "patrol.disk_warning": "85",
    "patrol.disk_critical": "95",
    "patrol.load_warning": "5",
    "patrol.load_critical": "10",
    # LLM 配置
    "llm.base_url": "",
    "llm.api_key": "",
    "llm.model": "",
    "llm.api_mode": "chat_completions",
    "llm.reasoning_effort": "",
    "llm.temperature": "0.7",
    "llm.max_tokens": "4096",
    "llm.top_p": "1.0",
    "llm.system_prompt": "",
    "llm.profiles": "[]",
    # 日志服务（ELK）
    "elasticsearch.url": "",
    "elasticsearch.username": "",
    "elasticsearch.password": "",
    "elasticsearch.index": "filebeat-*",
    "kibana.url": "",
}


def get_config_float(db: Session, key: str) -> float:
    """读取配置并转为 float，失败返回默认值。"""
    val = get_config(db, key)
    try:
        return float(val)
    except (ValueError, TypeError):
        return float(_DEFAULTS.get(key, "0"))


def get_config(db: Session, key: str) -> str:
    """从 DB 读取配置，不存在则返回默认值。"""
    row = db.scalar(select(SystemConfig).where(SystemConfig.key == key))
    if row and row.value:
        return row.value
    return _DEFAULTS.get(key, "")


def get_prometheus_url(db: Session) -> str:
    return get_config(db, "prometheus.url")


def get_alertmanager_url(db: Session) -> str:
    return get_config(db, "alertmanager.url")


def get_elasticsearch_url(db: Session) -> str:
    return get_config(db, "elasticsearch.url").rstrip("/")


def get_elasticsearch_username(db: Session) -> str:
    return get_config(db, "elasticsearch.username")


def get_elasticsearch_password(db: Session) -> str:
    return get_config(db, "elasticsearch.password")


def get_elasticsearch_index(db: Session) -> str:
    """日志索引匹配模式，默认 filebeat-*。"""
    return get_config(db, "elasticsearch.index") or "filebeat-*"


def get_kibana_url(db: Session) -> str:
    return get_config(db, "kibana.url").rstrip("/")


def _legacy_llm_config(db: Session) -> dict[str, str]:
    """读取平铺的 llm.* 兼容字段。"""
    return {
        "base_url": get_config(db, "llm.base_url"),
        "api_key": get_config(db, "llm.api_key"),
        "model": get_config(db, "llm.model"),
        "api_mode": get_config(db, "llm.api_mode") or "chat_completions",
        "reasoning_effort": get_config(db, "llm.reasoning_effort"),
        "temperature": get_config(db, "llm.temperature") or "0.7",
        "max_tokens": get_config(db, "llm.max_tokens") or "4096",
        "top_p": get_config(db, "llm.top_p") or "1.0",
        "system_prompt": get_config(db, "llm.system_prompt"),
    }


def profile_to_llm_config(profile: dict[str, Any]) -> dict[str, str]:
    """将 profile 规范化为 AI 运行时配置。"""
    return {
        "base_url": str(profile.get("base_url") or "").strip(),
        "api_key": str(profile.get("api_key") or "").strip(),
        "model": str(profile.get("model") or "").strip(),
        "api_mode": str(profile.get("api_mode") or "chat_completions").strip() or "chat_completions",
        "reasoning_effort": str(profile.get("reasoning_effort") or "").strip(),
        "temperature": str(profile.get("temperature", "0.7")),
        "max_tokens": str(profile.get("max_tokens", "4096")),
        "top_p": str(profile.get("top_p", "1.0")),
        "system_prompt": str(profile.get("system_prompt") or ""),
    }


def guess_provider_from_url(url: str) -> str:
    u = (url or "").lower()
    if "openai" in u:
        return "openai"
    if "bigmodel" in u:
        return "zhipu"
    if "moonshot" in u:
        return "moonshot"
    if "deepseek" in u:
        return "deepseek"
    if "dashscope" in u or "aliyuncs" in u:
        return "qwen"
    if "volces.com" in u or "/ark" in u:
        return "doubao"
    if "qianfan" in u or "baidubce" in u:
        return "wenxin"
    if "11434" in u or "ollama" in u:
        return "ollama"
    return "custom"


def get_active_llm_profile(db: Session) -> dict[str, Any] | None:
    """返回当前激活 profile；无 is_active 时回退第一条。"""
    profiles = get_llm_profiles(db)
    if not profiles:
        return None
    active = next((p for p in profiles if p.get("is_active")), None)
    return active or profiles[0]


def ensure_llm_profiles_migrated(db: Session) -> list[dict[str, Any]]:
    """若 profiles 为空但存在 legacy llm.*，自动迁移为单条 active profile。"""
    profiles = get_llm_profiles(db)
    if profiles:
        return profiles

    legacy = _legacy_llm_config(db)
    if not (legacy["base_url"] or legacy["model"] or legacy["api_key"]):
        return []

    import time

    provider = guess_provider_from_url(legacy["base_url"])
    migrated = {
        "id": f"legacy-{int(time.time())}",
        "name": legacy["model"] or "默认模型",
        "provider": provider,
        "icon": {
            "openai": "AI",
            "zhipu": "ZP",
            "moonshot": "KS",
            "deepseek": "DS",
            "qwen": "QW",
            "doubao": "DB",
            "wenxin": "WX",
            "ollama": "OL",
        }.get(provider, "⚡"),
        "base_url": legacy["base_url"],
        "api_key": legacy["api_key"],
        "model": legacy["model"],
        "api_mode": legacy["api_mode"] or "chat_completions",
        "reasoning_effort": legacy["reasoning_effort"] or "",
        "temperature": float(legacy["temperature"] or 0.7),
        "max_tokens": int(float(legacy["max_tokens"] or 4096)),
        "top_p": float(legacy["top_p"] or 1.0),
        "system_prompt": legacy["system_prompt"] or "",
        "is_active": True,
    }
    set_llm_profiles(db, [migrated])
    # 同步激活字段，保持双写一致
    sync_active_llm_config(db, migrated)
    return [migrated]


def sync_active_llm_config(db: Session, active: dict[str, Any]) -> None:
    """将激活 profile 同步回写 llm.* 兼容字段。"""
    cfg = profile_to_llm_config(active)
    set_config(db, "llm.base_url", cfg["base_url"], "LLM API 地址（OpenAI 兼容，例：https://api.openai.com/v1）")
    set_config(db, "llm.api_key", cfg["api_key"], "LLM API Key")
    set_config(db, "llm.model", cfg["model"], "LLM 模型名称（例：gpt-4o、deepseek-chat、qwen-plus）")
    set_config(db, "llm.api_mode", cfg["api_mode"], "LLM 接口模式（chat_completions 或 responses）")
    set_config(db, "llm.reasoning_effort", cfg["reasoning_effort"], "推理强度（low、medium、high，仅 Responses 模式使用）")
    set_config(db, "llm.temperature", cfg["temperature"], "模型温度（0-2，越低越精确）")
    set_config(db, "llm.max_tokens", cfg["max_tokens"], "最大输出 Token 数")
    set_config(db, "llm.top_p", cfg["top_p"], "Top P 采样参数（0-1）")
    set_config(db, "llm.system_prompt", cfg["system_prompt"], "自定义系统提示词")


def get_llm_config(db: Session) -> dict[str, str]:
    """读取 LLM 配置：优先 active profile，其次 legacy llm.*。"""
    ensure_llm_profiles_migrated(db)
    active = get_active_llm_profile(db)
    if active:
        return profile_to_llm_config(active)
    return _legacy_llm_config(db)


def is_llm_configured(config: dict[str, str]) -> bool:
    """判断配置是否足够用于 AI 调用（本地模型允许空 key）。"""
    base_url = (config.get("base_url") or "").strip()
    model = (config.get("model") or "").strip()
    api_key = (config.get("api_key") or "").strip()
    if not base_url or not model:
        return False
    if api_key:
        return True
    return is_local_llm(base_url)


def get_llm_profiles(db: Session) -> list[dict[str, Any]]:
    """读取 LLM 配置列表。"""
    import json
    raw = get_config(db, "llm.profiles")
    try:
        data = json.loads(raw) if raw else []
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def set_llm_profiles(db: Session, profiles: list[dict[str, Any]]) -> None:
    """写入 LLM 配置列表。"""
    import json
    set_config(db, "llm.profiles", json.dumps(profiles, ensure_ascii=False), "LLM 模型配置列表")


def mask_api_key(api_key: str) -> str:
    """将 API Key 中间部分打码，供前端展示。"""
    key = (api_key or "").strip()
    if not key:
        return ""
    if len(key) <= 8:
        return "*" * len(key)
    return f"{key[:3]}****{key[-4:]}"


def public_profile(profile: dict[str, Any]) -> dict[str, Any]:
    """对外返回的 profile：去掉明文 key，附带掩码字段。"""
    raw_key = str(profile.get("api_key") or "")
    data = dict(profile)
    data["api_key"] = ""
    data["has_api_key"] = bool(raw_key.strip())
    data["api_key_masked"] = mask_api_key(raw_key)
    data.pop("copy_api_key_from", None)
    return data


def merge_profile_secrets(
    old_profiles: list[dict[str, Any]],
    new_profiles: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """合并写入：空 / __UNCHANGED__ 表示保留旧密钥；支持 copy_api_key_from。"""
    old_by_id = {
        str(p.get("id")): p
        for p in old_profiles
        if p.get("id") is not None and str(p.get("id"))
    }
    merged: list[dict[str, Any]] = []
    for raw in new_profiles:
        item = dict(raw)
        profile_id = str(item.get("id") or "")
        incoming = str(item.get("api_key") or "").strip()
        copy_from = str(item.pop("copy_api_key_from", "") or "").strip()

        if incoming and incoming != UNCHANGED_SECRET:
            item["api_key"] = incoming
        else:
            prev = old_by_id.get(profile_id) or {}
            kept = str(prev.get("api_key") or "")
            if not kept and copy_from:
                source = old_by_id.get(copy_from) or {}
                # 也允许从本批次已处理项拷贝（同次提交内复制）
                if not source.get("api_key"):
                    for done in merged:
                        if str(done.get("id")) == copy_from:
                            source = done
                            break
                kept = str(source.get("api_key") or "")
            item["api_key"] = kept

        merged.append(item)
    return merged


def is_local_llm(base_url: str, provider: str = "") -> bool:
    """判断是否为本地/Ollama 类模型（允许空 API Key）。"""
    u = (base_url or "").lower()
    p = (provider or "").lower()
    if p == "ollama":
        return True
    return any(
        token in u
        for token in (
            "localhost",
            "127.0.0.1",
            "0.0.0.0",
            ":11434",
            "host.docker.internal",
        )
    )


def classify_llm_http_error(status_code: int, body: str = "") -> str:
    """将 HTTP 状态码/响应体粗分类为前端可引导的 error_code。"""
    text = (body or "").lower()
    if status_code in (401, 403):
        return "auth"
    if status_code == 404 or "model" in text and (
        "not found" in text or "does not exist" in text or "unknown model" in text
    ):
        return "model_not_found"
    if status_code in (400, 422) and "model" in text:
        return "model_not_found"
    if status_code >= 500:
        return "protocol"
    return "protocol"


def resolve_profile_api_key(
    db: Session,
    *,
    api_key: str = "",
    profile_id: str | None = None,
) -> str:
    """解析测试/试聊用的真实 key：显式传入优先，否则按 profile_id 回查。"""
    incoming = (api_key or "").strip()
    if incoming and incoming != UNCHANGED_SECRET:
        return incoming
    if not profile_id:
        return ""
    for p in get_llm_profiles(db):
        if str(p.get("id")) == str(profile_id):
            return str(p.get("api_key") or "")
    return ""


def set_config(db: Session, key: str, value: str, description: str = "") -> SystemConfig:
    """写入或更新配置。"""
    row = db.scalar(select(SystemConfig).where(SystemConfig.key == key))
    if row:
        row.value = value
        if description:
            row.description = description
    else:
        row = SystemConfig(key=key, value=value, description=description)
        db.add(row)
    db.flush()
    return row
