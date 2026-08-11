"""系统配置 API。"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import api_permission_required, get_client_ip
from app.core.settings import (
    classify_llm_http_error,
    ensure_llm_profiles_migrated,
    get_config,
    set_config,
    get_llm_profiles,
    set_llm_profiles,
    is_local_llm,
    mask_api_key,
    merge_profile_secrets,
    public_profile,
    resolve_profile_api_key,
    sync_active_llm_config,
)
from app.db.database import get_db
from app.models.system_config import SystemConfig
from app.models.user import User
from app.services.audit import write_log

router = APIRouter(prefix="/settings", tags=["系统配置"])

# 可配置的 key 清单及描述
_CONFIG_SPECS: dict[str, str] = {
    "prometheus.url": "Prometheus 服务地址（例：http://prometheus:9090）",
    "alertmanager.url": "Alertmanager 服务地址（例：http://alertmanager:9093）",
    "jenkins_config": "Jenkins 配置（JSON：url, username, token）",
    "llm.base_url": "LLM API 地址（OpenAI 兼容，例：https://api.openai.com/v1）",
    "llm.api_key": "LLM API Key",
    "llm.model": "LLM 模型名称（例：gpt-4o、deepseek-chat、qwen-plus）",
    "llm.api_mode": "LLM 接口模式（chat_completions 或 responses）",
    "llm.reasoning_effort": "推理强度（low、medium、high，仅 Responses 模式使用）",
    "llm.temperature": "模型温度（0-2，越低越精确）",
    "llm.max_tokens": "最大输出 Token 数",
    "llm.top_p": "Top P 采样参数（0-1）",
    "llm.system_prompt": "自定义系统提示词",
    "llm.profiles": "LLM 模型配置列表（JSON）",
    "elasticsearch.url": "Elasticsearch 服务地址（例：http://elasticsearch:9200）",
    "elasticsearch.username": "Elasticsearch 用户名（可选，如 elastic）",
    "elasticsearch.password": "Elasticsearch 密码（可选）",
    "elasticsearch.index": "日志索引模式（例：filebeat-* 或 logs-*）",
    "kibana.url": "Kibana 服务地址（可选，用于外部跳转深度分析）",
}

# 敏感配置：列表/详情接口只回传掩码
_MASKED_KEYS = {"llm.api_key", "elasticsearch.password"}


class ConfigUpdate(BaseModel):
    value: str


class LLMProfile(BaseModel):
    id: str
    name: str
    provider: str
    icon: str
    base_url: str
    api_key: str = ""
    model: str
    api_mode: str = "chat_completions"
    reasoning_effort: str = ""
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 1.0
    system_prompt: str = ""
    is_active: bool = False
    # 复制配置时沿用源 profile 密钥（写路径专用，不会回读）
    copy_api_key_from: str | None = None


class LLMProfilesUpdate(BaseModel):
    profiles: list[LLMProfile]


class LLMTestBody(BaseModel):
    base_url: str
    api_key: str = ""
    model: str
    api_mode: str = "chat_completions"
    reasoning_effort: str = ""
    provider: str = ""
    profile_id: str | None = None


class LLMTestChatBody(BaseModel):
    base_url: str
    api_key: str = ""
    model: str
    api_mode: str = "chat_completions"
    reasoning_effort: str = ""
    temperature: float = 0.7
    max_tokens: int = 256
    top_p: float = 1.0
    system_prompt: str = ""
    message: str
    provider: str = ""
    profile_id: str | None = None


class LLMModelsBody(BaseModel):
    base_url: str
    api_key: str = ""
    provider: str = ""
    api_mode: str = ""
    profile_id: str | None = None


class TestConnectionBody(BaseModel):
    url: str
    username: str = ""
    token: str = ""


# ── 具体路由（必须在通配符路由之前） ──


@router.get("/llm/profiles")
def api_get_llm_profiles(
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("settings.view")),
):
    """获取 LLM 模型配置列表（API Key 仅返回掩码）。"""
    raw_profiles = ensure_llm_profiles_migrated(db)
    # 迁移可能写库，这里提交以持久化（只读权限场景也允许自动升级数据）
    try:
        db.commit()
    except Exception:
        db.rollback()
        raw_profiles = get_llm_profiles(db)
    profiles = [public_profile(p) for p in raw_profiles]
    return {"code": 0, "data": {"items": profiles}}


@router.put("/llm/profiles")
def api_update_llm_profiles(
    body: LLMProfilesUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("settings.update")),
):
    """更新 LLM 模型配置列表（全量替换；空 api_key 保留旧值）。"""
    old_profiles = get_llm_profiles(db)
    incoming = [p.model_dump(exclude_none=True) for p in body.profiles]
    profiles_data = merge_profile_secrets(old_profiles, incoming)
    set_llm_profiles(db, profiles_data)

    # 同步激活配置到独立的 key（使用 merge 后的真实密钥）
    active = next((p for p in profiles_data if p.get("is_active")), None)
    key_changed = False
    if active:
        old_active = next((p for p in old_profiles if p.get("id") == active.get("id")), None)
        old_key = (old_active or {}).get("api_key") or ""
        new_key = active.get("api_key") or ""
        key_changed = old_key != new_key
        sync_active_llm_config(db, active)

    write_log(
        db,
        user=current_user,
        action="update",
        target_type="settings",
        target_id=0,
        target_name="llm.profiles",
        detail=(
            f"更新模型配置列表，共 {len(profiles_data)} 个配置"
            f"{'，已变更 API Key' if key_changed else '，未变更 API Key'}"
        ),
        ip_address=get_client_ip(request),
    )
    db.commit()
    return {"code": 0, "msg": "模型配置已更新", "data": {"items": [public_profile(p) for p in profiles_data]}}


def _llm_result(
    *,
    ok: bool,
    msg: str,
    error_code: str | None = None,
    latency_ms: int | None = None,
    status_code: int | None = None,
    model: str | None = None,
    content: str | None = None,
) -> dict:
    data: dict = {
        "ok": ok,
        "latency_ms": latency_ms,
        "status_code": status_code,
        "model": model,
        "error_code": error_code,
    }
    if content is not None:
        data["content"] = content
    # 测试类接口统一 code=0，业务成败看 data.ok，避免前端拦截器丢掉结构化错误
    return {"code": 0, "msg": msg, "data": data}


@router.post("/llm/models")
def api_list_llm_models(
    body: LLMModelsBody,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("settings.view")),
):
    """代理查询模型列表（OpenAI / Anthropic 协议均支持 /models）；失败返回空列表。"""
    import httpx

    base_url = body.base_url.strip().rstrip("/")
    provider = (body.provider or "").strip()
    api_mode = (body.api_mode or "").strip()
    api_key = resolve_profile_api_key(db, api_key=body.api_key, profile_id=body.profile_id)

    if not base_url:
        return {
            "code": 0,
            "msg": "请填写 API 地址",
            "data": {"items": [], "ok": False, "error_code": "validation"},
        }
    if not api_key and not is_local_llm(base_url, provider):
        return {
            "code": 0,
            "msg": "请填写 API Key",
            "data": {"items": [], "ok": False, "error_code": "validation"},
        }

    # Anthropic 协议：x-api-key 头 + /v1/models 路径（base_url 不含 /v1）
    # OpenAI 协议：Bearer 头 + /models 路径（base_url 已含 /v1）
    if api_mode == "anthropic":
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        }
        models_path = "/v1/models"
    else:
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        models_path = "/models"

    try:
        with httpx.Client(timeout=15, follow_redirects=True) as client:
            resp = client.get(f"{base_url}{models_path}", headers=headers)
            if resp.status_code != 200:
                detail = resp.text[:200]
                return {
                    "code": 0,
                    "msg": f"拉取模型失败: HTTP {resp.status_code}",
                    "data": {
                        "items": [],
                        "ok": False,
                        "error_code": classify_llm_http_error(resp.status_code, detail),
                        "status_code": resp.status_code,
                    },
                }
            payload = resp.json()
            raw_items = payload.get("data") if isinstance(payload, dict) else None
            if not isinstance(raw_items, list):
                raw_items = payload if isinstance(payload, list) else []
            items = []
            for item in raw_items:
                if isinstance(item, str):
                    items.append({"id": item, "owned_by": ""})
                    continue
                if not isinstance(item, dict):
                    continue
                model_id = item.get("id") or item.get("name") or item.get("model")
                if not model_id:
                    continue
                items.append({
                    "id": str(model_id),
                    "owned_by": str(item.get("owned_by") or item.get("organization") or ""),
                })
            # 稳定去重
            seen: set[str] = set()
            unique = []
            for it in items:
                if it["id"] in seen:
                    continue
                seen.add(it["id"])
                unique.append(it)
            unique.sort(key=lambda x: x["id"])
            return {
                "code": 0,
                "msg": "ok",
                "data": {"items": unique, "ok": True, "error_code": None},
            }
    except httpx.TimeoutException:
        return {
            "code": 0,
            "msg": "拉取模型超时",
            "data": {"items": [], "ok": False, "error_code": "timeout"},
        }
    except httpx.ConnectError as e:
        return {
            "code": 0,
            "msg": f"无法连接: {e}",
            "data": {"items": [], "ok": False, "error_code": "connect"},
        }
    except Exception as e:
        return {
            "code": 0,
            "msg": f"拉取模型失败: {e}",
            "data": {"items": [], "ok": False, "error_code": "unknown"},
        }


@router.post("/test-connection/llm")
def api_test_llm_connection(
    body: LLMTestBody,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("settings.view")),
):
    """测试 LLM API 连通性（支持草稿配置 / 本地空 key）。"""
    import time

    import httpx

    base_url = body.base_url.strip().rstrip("/")
    model = body.model.strip()
    api_mode = (body.api_mode or "chat_completions").strip() or "chat_completions"
    reasoning_effort = (body.reasoning_effort or "").strip()
    provider = (body.provider or "").strip()
    api_key = resolve_profile_api_key(db, api_key=body.api_key, profile_id=body.profile_id)

    if not base_url or not model:
        return _llm_result(ok=False, msg="请填写 API 地址和模型名称", error_code="validation", model=model or None)
    if not api_key and not is_local_llm(base_url, provider):
        return _llm_result(ok=False, msg="请填写 API Key", error_code="validation", model=model)

    headers = {"Content-Type": "application/json"}
    if api_mode == "anthropic":
        headers["x-api-key"] = api_key
        headers["anthropic-version"] = "2023-06-01"
    elif api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        started = time.perf_counter()
        with httpx.Client(timeout=15, follow_redirects=True) as client:
            if api_mode == "anthropic":
                test_url = f"{base_url}/v1/messages"
                payload: dict = {
                    "model": model,
                    "messages": [{"role": "user", "content": "hi"}],
                    "max_tokens": 16,
                }
            elif api_mode == "responses":
                test_url = f"{base_url}/responses"
                payload: dict = {
                    "model": model,
                    "input": [{"role": "user", "content": "hi"}],
                    "max_output_tokens": 16,
                }
                if reasoning_effort:
                    payload["reasoning"] = {"effort": reasoning_effort}
            else:
                test_url = f"{base_url}/chat/completions"
                payload = {
                    "model": model,
                    "messages": [{"role": "user", "content": "hi"}],
                    "max_tokens": 5,
                }
            resp = client.post(test_url, headers=headers, json=payload)
            latency_ms = int((time.perf_counter() - started) * 1000)
            if resp.status_code == 200:
                return _llm_result(
                    ok=True,
                    msg="LLM 连接成功",
                    latency_ms=latency_ms,
                    status_code=200,
                    model=model,
                )
            detail = resp.text[:200]
            error_code = classify_llm_http_error(resp.status_code, detail)
            return _llm_result(
                ok=False,
                msg=f"LLM 返回状态码 {resp.status_code}: {detail}",
                error_code=error_code,
                latency_ms=latency_ms,
                status_code=resp.status_code,
                model=model,
            )
    except httpx.TimeoutException:
        return _llm_result(ok=False, msg="LLM 连接超时", error_code="timeout", model=model)
    except httpx.ConnectError as e:
        return _llm_result(ok=False, msg=f"LLM 连接失败: {e}", error_code="connect", model=model)
    except Exception as e:
        return _llm_result(ok=False, msg=f"LLM 连接失败: {e}", error_code="unknown", model=model)


@router.post("/llm/test-chat")
def api_test_llm_chat(
    body: LLMTestChatBody,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("settings.view")),
):
    """对草稿配置发起短试聊，不读写会话，不依赖当前激活配置。"""
    import time

    import httpx

    base_url = body.base_url.strip().rstrip("/")
    model = body.model.strip()
    message = (body.message or "").strip()
    api_mode = (body.api_mode or "chat_completions").strip() or "chat_completions"
    reasoning_effort = (body.reasoning_effort or "").strip()
    provider = (body.provider or "").strip()
    api_key = resolve_profile_api_key(db, api_key=body.api_key, profile_id=body.profile_id)
    max_tokens = max(16, min(int(body.max_tokens or 256), 512))

    if not base_url or not model:
        return _llm_result(ok=False, msg="请填写 API 地址和模型名称", error_code="validation", model=model or None)
    if not message:
        return _llm_result(ok=False, msg="请输入测试消息", error_code="validation", model=model or None)
    if not api_key and not is_local_llm(base_url, provider):
        return _llm_result(ok=False, msg="请填写 API Key", error_code="validation", model=model)

    headers = {"Content-Type": "application/json"}
    if api_mode == "anthropic":
        headers["x-api-key"] = api_key
        headers["anthropic-version"] = "2023-06-01"
    elif api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    system_prompt = (body.system_prompt or "").strip()

    try:
        started = time.perf_counter()
        with httpx.Client(timeout=30, follow_redirects=True) as client:
            if api_mode == "anthropic":
                test_url = f"{base_url}/v1/messages"
                payload: dict = {
                    "model": model,
                    "messages": [{"role": "user", "content": message}],
                    "max_tokens": max_tokens,
                    "temperature": body.temperature,
                    "top_p": body.top_p,
                }
                if system_prompt:
                    payload["system"] = system_prompt
            elif api_mode == "responses":
                test_url = f"{base_url}/responses"
                inputs: list[dict] = []
                if system_prompt:
                    inputs.append({"role": "system", "content": system_prompt})
                inputs.append({"role": "user", "content": message})
                payload = {
                    "model": model,
                    "input": inputs,
                    "max_output_tokens": max_tokens,
                    "temperature": body.temperature,
                    "top_p": body.top_p,
                }
                if reasoning_effort:
                    payload["reasoning"] = {"effort": reasoning_effort}
            else:
                test_url = f"{base_url}/chat/completions"
                messages: list[dict] = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": message})
                payload = {
                    "model": model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": body.temperature,
                    "top_p": body.top_p,
                }
            resp = client.post(test_url, headers=headers, json=payload)
            latency_ms = int((time.perf_counter() - started) * 1000)
            if resp.status_code != 200:
                detail = resp.text[:200]
                return _llm_result(
                    ok=False,
                    msg=f"LLM 返回状态码 {resp.status_code}: {detail}",
                    error_code=classify_llm_http_error(resp.status_code, detail),
                    latency_ms=latency_ms,
                    status_code=resp.status_code,
                    model=model,
                )

            data = resp.json()
            content = ""
            if api_mode == "anthropic":
                # Anthropic Messages: content[].text
                for part in data.get("content") or []:
                    if part.get("type") == "text" and part.get("text"):
                        content += part["text"]
            elif api_mode == "responses":
                # Responses API: output[].content[].text
                for item in data.get("output") or []:
                    for part in item.get("content") or []:
                        if part.get("type") in ("output_text", "text") and part.get("text"):
                            content += part["text"]
                if not content:
                    content = data.get("output_text") or ""
            else:
                choices = data.get("choices") or []
                if choices:
                    content = ((choices[0].get("message") or {}).get("content")) or ""
                    if isinstance(content, list):
                        content = "".join(
                            part.get("text", "") if isinstance(part, dict) else str(part)
                            for part in content
                        )

            if not content:
                return _llm_result(
                    ok=False,
                    msg="LLM 返回空内容",
                    error_code="protocol",
                    latency_ms=latency_ms,
                    status_code=resp.status_code,
                    model=model,
                )

            return _llm_result(
                ok=True,
                msg="试聊成功",
                latency_ms=latency_ms,
                status_code=resp.status_code,
                model=model,
                content=content,
            )
    except httpx.TimeoutException:
        return _llm_result(ok=False, msg="LLM 试聊超时", error_code="timeout", model=model)
    except httpx.ConnectError as e:
        return _llm_result(ok=False, msg=f"LLM 连接失败: {e}", error_code="connect", model=model)
    except Exception as e:
        return _llm_result(ok=False, msg=f"LLM 试聊失败: {e}", error_code="unknown", model=model)


@router.post("/test-connection/{service}")
def api_test_connection(
    service: str,
    body: TestConnectionBody,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("settings.view")),
):
    """测试 Prometheus / Alertmanager / Jenkins / Elasticsearch / Kibana 连通性。"""
    import httpx
    from urllib.parse import urlparse

    url = body.url.strip()
    if not url:
        return {"code": 1, "msg": "URL 不能为空", "data": {"url": url, "ok": False}}

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return {"code": 1, "msg": f"URL 格式无效: {url}", "data": {"url": url, "ok": False}}

    if service == "prometheus":
        test_url = f"{url.rstrip('/')}/api/v1/status/config"
    elif service == "alertmanager":
        test_url = f"{url.rstrip('/')}/api/v2/status"
    elif service == "jenkins":
        test_url = f"{url.rstrip('/')}/api/json"
    elif service == "elasticsearch":
        test_url = f"{url.rstrip('/')}/"
    elif service == "kibana":
        test_url = f"{url.rstrip('/')}/api/status"
    else:
        raise HTTPException(status_code=400, detail=f"不支持的服务: {service}")

    try:
        auth = None
        if body.username and service in ("jenkins", "elasticsearch", "kibana"):
            password = body.token
            if not password and service == "elasticsearch":
                # 表单未填密码时回退到已保存的凭据，避免误报认证失败
                password = get_config(db, "elasticsearch.password")
            if password:
                auth = httpx.BasicAuth(body.username, password)

        with httpx.Client(timeout=5, follow_redirects=False, auth=auth) as client:
            resp = client.get(test_url)
            if resp.status_code == 200:
                if service == "elasticsearch":
                    try:
                        version = (resp.json().get("version") or {}).get("number", "")
                    except Exception:
                        version = ""
                    suffix = f"（版本 {version}）" if version else ""
                    return {"code": 0, "msg": f"{service} 连接成功{suffix}", "data": {"url": url, "ok": True}}
                return {"code": 0, "msg": f"{service} 连接成功", "data": {"url": url, "ok": True}}
            # Kibana 开启安全认证时 /api/status 返回 401 属正常（浏览器访问时由用户登录）
            if service == "kibana" and resp.status_code in (401, 403):
                return {"code": 0, "msg": "Kibana 服务可达（需要登录认证，属正常）", "data": {"url": url, "ok": True}}
            if resp.status_code in (401, 403):
                return {"code": 1, "msg": f"{service} 认证失败（{resp.status_code}），请检查用户名/密码", "data": {"url": url, "ok": False}}
            return {"code": 1, "msg": f"{service} 返回状态码 {resp.status_code}", "data": {"url": url, "ok": False}}
    except httpx.TimeoutException:
        return {"code": 1, "msg": f"{service} 连接超时", "data": {"url": url, "ok": False}}
    except httpx.ConnectError as e:
        return {"code": 1, "msg": f"{service} 连接失败: 无法到达目标地址 ({e})", "data": {"url": url, "ok": False}}
    except Exception as e:
        return {"code": 1, "msg": f"{service} 连接失败: {e}", "data": {"url": url, "ok": False}}


# ── 通配符路由（放在最后） ──


@router.get("/")
def api_list_configs(
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("settings.view")),
):
    """获取所有可配置项及其当前值。"""
    rows = db.scalars(select(SystemConfig).where(SystemConfig.key.in_(_CONFIG_SPECS.keys()))).all()
    row_map = {r.key: r for r in rows}

    items = []
    for key, desc in _CONFIG_SPECS.items():
        row = row_map.get(key)
        value = row.value if row else ""
        # 敏感配置不回传明文
        if key in _MASKED_KEYS or key == "llm.profiles":
            if key in _MASKED_KEYS:
                value = mask_api_key(value)
            else:
                value = ""
        items.append({
            "key": key,
            "value": value,
            "description": desc,
            "updated_at": row.updated_at.isoformat() if row else None,
        })
    return {"code": 0, "data": {"items": items}}


@router.put("/{key:path}")
def api_update_config(
    key: str,
    body: ConfigUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("settings.update")),
):
    """更新指定配置项。"""
    if key not in _CONFIG_SPECS:
        raise HTTPException(status_code=400, detail=f"不支持的配置项: {key}")

    set_config(db, key, body.value.strip(), _CONFIG_SPECS[key])
    write_log(db, user=current_user, action="update", target_type="settings",
              target_id=0, target_name=key, detail=f"更新为 {body.value.strip()}",
              ip_address=get_client_ip(request))
    db.commit()
    return {"code": 0, "msg": "配置已更新"}


@router.get("/{key:path}")
def api_get_config(
    key: str,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("settings.view")),
):
    """获取单个配置项。"""
    if key not in _CONFIG_SPECS:
        raise HTTPException(status_code=400, detail=f"不支持的配置项: {key}")

    value = get_config(db, key)
    if key in _MASKED_KEYS:
        value = mask_api_key(value)
    elif key == "llm.profiles":
        value = ""
    return {"code": 0, "data": {"key": key, "value": value, "description": _CONFIG_SPECS[key]}}
