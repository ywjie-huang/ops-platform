"""系统配置 API。"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import api_permission_required, get_client_ip
from app.core.settings import get_config, set_config, get_llm_profiles, set_llm_profiles
from app.db.database import get_db
from app.models.system_config import SystemConfig
from app.models.user import User
from app.services.audit import write_log

router = APIRouter(prefix="/settings", tags=["系统配置"])

# 可配置的 key 清单及描述
_CONFIG_SPECS: dict[str, str] = {
    "prometheus.url": "Prometheus 服务地址（例：http://172.16.24.31:30001）",
    "alertmanager.url": "Alertmanager 服务地址（例：http://172.16.24.31:30093）",
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
}


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


class LLMProfilesUpdate(BaseModel):
    profiles: list[LLMProfile]


class LLMTestBody(BaseModel):
    base_url: str
    api_key: str
    model: str
    api_mode: str = "chat_completions"
    reasoning_effort: str = ""


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
    """获取 LLM 模型配置列表。"""
    profiles = get_llm_profiles(db)
    return {"code": 0, "data": {"items": profiles}}


@router.put("/llm/profiles")
def api_update_llm_profiles(
    body: LLMProfilesUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(api_permission_required("settings.update")),
):
    """更新 LLM 模型配置列表（全量替换）。"""
    profiles_data = [p.model_dump() for p in body.profiles]
    set_llm_profiles(db, profiles_data)

    # 同步激活配置到独立的 key
    active = next((p for p in body.profiles if p.is_active), None)
    if active:
        set_config(db, "llm.base_url", active.base_url, _CONFIG_SPECS["llm.base_url"])
        set_config(db, "llm.api_key", active.api_key, _CONFIG_SPECS["llm.api_key"])
        set_config(db, "llm.model", active.model, _CONFIG_SPECS["llm.model"])
        set_config(db, "llm.api_mode", active.api_mode, _CONFIG_SPECS["llm.api_mode"])
        set_config(
            db,
            "llm.reasoning_effort",
            active.reasoning_effort,
            _CONFIG_SPECS["llm.reasoning_effort"],
        )
        set_config(db, "llm.temperature", str(active.temperature), _CONFIG_SPECS["llm.temperature"])
        set_config(db, "llm.max_tokens", str(active.max_tokens), _CONFIG_SPECS["llm.max_tokens"])
        set_config(db, "llm.top_p", str(active.top_p), _CONFIG_SPECS["llm.top_p"])
        set_config(db, "llm.system_prompt", active.system_prompt, _CONFIG_SPECS["llm.system_prompt"])

    write_log(db, user=current_user, action="update", target_type="settings",
              target_id=0, target_name="llm.profiles",
              detail=f"更新模型配置列表，共 {len(profiles_data)} 个配置",
              ip_address=get_client_ip(request))
    db.commit()
    return {"code": 0, "msg": "模型配置已更新"}


@router.post("/test-connection/llm")
def api_test_llm_connection(
    body: LLMTestBody,
    _: User = Depends(api_permission_required("settings.view")),
):
    """测试 LLM API 连通性。"""
    import httpx

    base_url = body.base_url.strip().rstrip("/")
    api_key = body.api_key.strip()
    model = body.model.strip()
    api_mode = (body.api_mode or "chat_completions").strip() or "chat_completions"
    reasoning_effort = (body.reasoning_effort or "").strip()

    if not base_url or not api_key or not model:
        return {"code": 1, "msg": "请填写完整的 LLM 配置", "data": {"ok": False}}

    try:
        with httpx.Client(timeout=15, follow_redirects=True) as client:
            if api_mode == "responses":
                test_url = f"{base_url}/responses"
                payload = {
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
            resp = client.post(
                test_url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            if resp.status_code == 200:
                return {"code": 0, "msg": "LLM 连接成功", "data": {"ok": True}}
            detail = resp.text[:200]
            return {"code": 1, "msg": f"LLM 返回状态码 {resp.status_code}: {detail}", "data": {"ok": False}}
    except httpx.TimeoutException:
        return {"code": 1, "msg": "LLM 连接超时", "data": {"ok": False}}
    except httpx.ConnectError as e:
        return {"code": 1, "msg": f"LLM 连接失败: {e}", "data": {"ok": False}}
    except Exception as e:
        return {"code": 1, "msg": f"LLM 连接失败: {e}", "data": {"ok": False}}


@router.post("/test-connection/{service}")
def api_test_connection(
    service: str,
    body: TestConnectionBody,
    _: User = Depends(api_permission_required("settings.view")),
):
    """测试 Prometheus / Alertmanager 连通性。"""
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
    else:
        raise HTTPException(status_code=400, detail=f"不支持的服务: {service}")

    try:
        auth = None
        if service == "jenkins" and body.username and body.token:
            auth = httpx.BasicAuth(body.username, body.token)

        with httpx.Client(timeout=5, follow_redirects=False, auth=auth) as client:
            resp = client.get(test_url)
            if resp.status_code == 200:
                return {"code": 0, "msg": f"{service} 连接成功", "data": {"url": url, "ok": True}}
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
        items.append({
            "key": key,
            "value": row.value if row else "",
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
    return {"code": 0, "data": {"key": key, "value": value, "description": _CONFIG_SPECS[key]}}
