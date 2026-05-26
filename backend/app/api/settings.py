"""系统配置 API。"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import api_permission_required, get_client_ip
from app.core.settings import get_config, set_config
from app.db.database import get_db
from app.models.system_config import SystemConfig
from app.models.user import User
from app.services.audit import write_log

router = APIRouter(prefix="/settings", tags=["系统配置"])

# 可配置的 key 清单及描述
_CONFIG_SPECS: dict[str, str] = {
    "prometheus.url": "Prometheus 服务地址（例：http://172.16.24.31:30001）",
    "alertmanager.url": "Alertmanager 服务地址（例：http://172.16.24.31:30093）",
    "llm.base_url": "LLM API 地址（OpenAI 兼容，例：https://api.openai.com/v1）",
    "llm.api_key": "LLM API Key",
    "llm.model": "LLM 模型名称（例：gpt-4o、deepseek-chat、qwen-plus）",
}


class ConfigUpdate(BaseModel):
    value: str


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


class LLMTestBody(BaseModel):
    base_url: str
    api_key: str
    model: str


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

    if not base_url or not api_key or not model:
        return {"code": 1, "msg": "请填写完整的 LLM 配置", "data": {"ok": False}}

    try:
        with httpx.Client(timeout=15, follow_redirects=True) as client:
            resp = client.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": "hi"}],
                    "max_tokens": 5,
                },
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


class TestConnectionBody(BaseModel):
    url: str


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
    else:
        raise HTTPException(status_code=400, detail=f"不支持的服务: {service}")

    try:
        with httpx.Client(timeout=5, follow_redirects=False) as client:
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
