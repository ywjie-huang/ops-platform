# AI 运维助手 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the keyword-matching stub AI assistant with a real LLM-powered agent that uses function calling to execute运维操作.

**Architecture:** Backend calls OpenAI-compatible LLM API via httpx with SSE streaming. A tool registry maps tool names to existing service functions. Read tools execute automatically; write tools require user confirmation via a two-step SSE flow. Frontend uses `fetch` + `ReadableStream` for real-time streaming display.

**Tech Stack:** Python httpx (LLM API calls), FastAPI SSE (streaming responses), Vue 3 + Element Plus (frontend), existing service layer (patrol, SSH, prometheus, etc.)

---

## File Structure

```
backend/app/services/ai/
├── __init__.py          # Re-exports for convenience
├── llm_client.py        # OpenAI-compatible LLM client with SSE streaming
├── tools.py             # Tool schemas + handler functions
├── dispatcher.py        # Tool dispatch logic (read auto-exec, write pending)
└── conversations.py     # In-memory conversation history

backend/app/api/ai.py    # Rewrite: SSE chat endpoint + confirm/reject

backend/app/core/settings.py  # Add LLM config defaults
backend/app/api/settings.py   # Add LLM config specs + test-connection

frontend/src/api/ai.ts            # Rewrite: SSE fetch + confirm/reject
frontend/src/views/ai/AiView.vue  # Rewrite: streaming + tool status + confirm cards
frontend/src/views/settings/SettingsView.vue  # Add LLM config section
```

---

## Task 1: LLM Configuration — Backend

**Files:**
- Modify: `backend/app/core/settings.py`
- Modify: `backend/app/api/settings.py`

- [ ] **Step 1: Add LLM config defaults to settings.py**

In `backend/app/core/settings.py`, add three entries to the `_DEFAULTS` dict:

```python
_DEFAULTS: dict[str, str] = {
    "prometheus.url": "http://172.16.24.31:30001",
    "alertmanager.url": "http://172.16.24.31:30093",
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
}
```

Add a helper function at the bottom:

```python
def get_llm_config(db: Session) -> dict[str, str]:
    """读取 LLM 配置，返回 {base_url, api_key, model}。"""
    return {
        "base_url": get_config(db, "llm.base_url"),
        "api_key": get_config(db, "llm.api_key"),
        "model": get_config(db, "llm.model"),
    }
```

- [ ] **Step 2: Add LLM config specs to settings API**

In `backend/app/api/settings.py`, extend `_CONFIG_SPECS`:

```python
_CONFIG_SPECS: dict[str, str] = {
    "prometheus.url": "Prometheus 服务地址（例：http://172.16.24.31:30001）",
    "alertmanager.url": "Alertmanager 服务地址（例：http://172.16.24.31:30093）",
    "llm.base_url": "LLM API 地址（OpenAI 兼容，例：https://api.openai.com/v1）",
    "llm.api_key": "LLM API Key",
    "llm.model": "LLM 模型名称（例：gpt-4o、deepseek-chat、qwen-plus）",
}
```

- [ ] **Step 3: Add LLM test-connection endpoint**

In `backend/app/api/settings.py`, extend the `api_test_connection` function to handle `llm` service. Add this block before the `httpx` request logic (after the `if service == "alertmanager"` block):

```python
    elif service == "llm":
        # 从请求 body 或配置中获取 LLM 信息
        api_key = ""
        model = ""
        # 尝试从 body 解析 JSON（body.url 在这里当作 base_url 用）
        test_url = f"{url.rstrip('/')}/models"
        # 需要带 Authorization header
        try:
            with httpx.Client(timeout=10, follow_redirects=False) as client:
                resp = client.get(test_url, headers={"Authorization": f"Bearer {api_key}"})
                if resp.status_code == 200:
                    return {"code": 0, "msg": "LLM 连接成功", "data": {"url": url, "ok": True}}
                return {"code": 1, "msg": f"LLM 返回状态码 {resp.status_code}", "data": {"url": url, "ok": False}}
        except Exception as e:
            return {"code": 1, "msg": f"LLM 连接失败: {e}", "data": {"url": url, "ok": False}}
```

Wait — the existing test-connection pattern only takes a `url` in the body. For LLM we also need `api_key`. Let me revise this. Instead of reusing the generic endpoint, add a dedicated LLM test endpoint:

```python
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
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/core/settings.py backend/app/api/settings.py
git commit -m "feat(ai): add LLM configuration to settings system"
```

---

## Task 2: LLM Configuration — Frontend

**Files:**
- Modify: `frontend/src/views/settings/SettingsView.vue`
- Modify: `frontend/src/api/settings.ts`

- [ ] **Step 1: Add LLM test function to settings API**

In `frontend/src/api/settings.ts`, add:

```typescript
export function testLLMConnection(data: { base_url: string; api_key: string; model: string }) {
  return request.post('/settings/test-connection/llm', data)
}
```

- [ ] **Step 2: Add LLM config section to SettingsView.vue**

In the `<template>`, add a new divider and form section after the Alertmanager block and before the save button:

```html
        <el-divider content-position="left">AI 模型</el-divider>

        <el-form-item label="API 地址">
          <el-input v-model="configs['llm.base_url']" placeholder="https://api.openai.com/v1" />
          <div class="form-tip">OpenAI 兼容 API 地址，支持 OpenAI / DeepSeek / Qwen / Ollama 等</div>
        </el-form-item>

        <el-form-item label="API Key">
          <el-input v-model="configs['llm.api_key']" placeholder="sk-xxx" show-password />
          <div class="form-tip">API 密钥</div>
        </el-form-item>

        <el-form-item label="模型名称">
          <el-input v-model="configs['llm.model']" placeholder="gpt-4o" />
          <div class="form-tip">模型标识，如 gpt-4o、deepseek-chat、qwen-plus</div>
        </el-form-item>

        <el-form-item>
          <el-button :loading="testing === 'llm'" @click="handleTestLLM">测试连接</el-button>
          <el-tag v-if="testResults['llm'] !== undefined" :type="testResults['llm'] ? 'success' : 'danger'" style="margin-left:8px">
            {{ testResults['llm'] ? '连接成功' : '连接失败' }}
          </el-tag>
        </el-form-item>
```

In the `<script setup>`, import the new function and add the handler:

```typescript
import { getSettings, updateSetting, testConnection, testLLMConnection } from '@/api/settings'

async function handleTestLLM() {
  testing.value = 'llm'
  testResults['llm'] = undefined
  const base_url = configs['llm.base_url']?.trim()
  const api_key = configs['llm.api_key']?.trim()
  const model = configs['llm.model']?.trim()
  if (!base_url || !api_key || !model) {
    ElMessage.warning('请填写完整的 LLM 配置')
    testing.value = ''
    return
  }
  try {
    const res: any = await testLLMConnection({ base_url, api_key, model })
    testResults['llm'] = res.data?.ok ?? false
    if (testResults['llm']) {
      ElMessage.success(res.msg)
    } else {
      ElMessage.warning(res.msg)
    }
  } catch {
    testResults['llm'] = false
  } finally { testing.value = '' }
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/settings.ts frontend/src/views/settings/SettingsView.vue
git commit -m "feat(ai): add LLM configuration UI to settings page"
```

---

## Task 3: LLM Client Service

**Files:**
- Create: `backend/app/services/ai/__init__.py`
- Create: `backend/app/services/ai/llm_client.py`

- [ ] **Step 1: Create the ai service package**

`backend/app/services/ai/__init__.py`:

```python
"""AI 助手服务包。"""
```

- [ ] **Step 2: Create the LLM client**

`backend/app/services/ai/llm_client.py`:

```python
"""OpenAI 兼容 LLM 客户端，支持 SSE 流式和 function calling。"""
from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator

import httpx

logger = logging.getLogger(__name__)


class LLMClient:
    """调用 OpenAI 兼容 API 的异步客户端。"""

    def __init__(self, base_url: str, api_key: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    async def chat_stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        发送聊天请求，以 SSE 流式返回。

        Yields 解析后的 SSE 事件：
        - {"type": "text", "content": "..."}                 — 文本 delta
        - {"type": "tool_call", "id": "...", "name": "...", "arguments": {...}}  — 工具调用
        - {"type": "done"}                                    — 流结束
        """
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": True,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # 累积 tool_call 的参数（流式返回时 arguments 是分片的）
        pending_tool_calls: dict[int, dict[str, Any]] = {}

        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            ) as response:
                if response.status_code != 200:
                    body = await response.aread()
                    raise RuntimeError(
                        f"LLM API error {response.status_code}: {body.decode()[:500]}"
                    )

                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        # 流结束，发出所有累积的 tool_call
                        for tc in pending_tool_calls.values():
                            yield tc
                        yield {"type": "done"}
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

                    # 文本内容
                    if "content" in delta and delta["content"]:
                        yield {"type": "text", "content": delta["content"]}

                    # 工具调用（流式累积）
                    if "tool_calls" in delta:
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
                            if "id" in tc_delta and tc_delta["id"]:
                                tc["id"] = tc_delta["id"]
                            if "function" in tc_delta:
                                if "name" in tc_delta["function"] and tc_delta["function"]["name"]:
                                    tc["name"] = tc_delta["function"]["name"]
                                if "arguments" in tc_delta["function"]:
                                    tc["arguments"] += tc_delta["function"]["arguments"]

                    # finish_reason == "tool_calls" 时，tool_calls 已完整，发出
                    if finish_reason == "tool_calls":
                        for tc in pending_tool_calls.values():
                            # 解析 arguments JSON 字符串
                            try:
                                tc["arguments"] = json.loads(tc["arguments"])
                            except (json.JSONDecodeError, TypeError):
                                tc["arguments"] = {}
                            yield tc
                        pending_tool_calls.clear()

                    # finish_reason == "stop" — 正常结束
                    if finish_reason == "stop":
                        yield {"type": "done"}
                        return
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/ai/
git commit -m "feat(ai): add LLM client with SSE streaming and function calling"
```

---

## Task 4: Tool Definitions

**Files:**
- Create: `backend/app/services/ai/tools.py`

- [ ] **Step 1: Create tool schemas and handler functions**

`backend/app/services/ai/tools.py`:

```python
"""AI 工具定义 — schema + handler 函数。"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.alert_event import AlertEvent
from app.models.asset import Asset
from app.models.patrol import PatrolReport
from app.models.ticket import Ticket

logger = logging.getLogger(__name__)

# ─── OpenAI function calling 格式的工具 schema ──────────────

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "query_assets",
            "description": "查询服务器/资产列表。可按关键词（名称、IP）、状态过滤。返回资产 ID、名称、IP、状态等信息。",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "搜索关键词，匹配名称或 IP",
                    },
                    "status": {
                        "type": "string",
                        "description": "资产状态过滤：使用中、已关机、已删除",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_host_metrics",
            "description": "查询指定服务器的实时性能指标（CPU、内存、磁盘、网络、负载）。需要 asset_id，可通过 query_assets 获取。",
            "parameters": {
                "type": "object",
                "properties": {
                    "asset_id": {
                        "type": "integer",
                        "description": "资产 ID",
                    },
                },
                "required": ["asset_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_alerts",
            "description": "查询告警事件列表。可按严重级别过滤。",
            "parameters": {
                "type": "object",
                "properties": {
                    "severity": {
                        "type": "string",
                        "description": "严重级别：critical、warning、info",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回数量，默认 10",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_containers",
            "description": "查询 Docker 容器列表和状态。",
            "parameters": {
                "type": "object",
                "properties": {
                    "host_id": {
                        "type": "integer",
                        "description": "Docker 主机 ID",
                    },
                    "keyword": {
                        "type": "string",
                        "description": "搜索关键词",
                    },
                    "status": {
                        "type": "string",
                        "description": "容器状态过滤：running、stopped 等",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_k8s",
            "description": "查询 Kubernetes 集群状态，包括节点和 Pod 信息。",
            "parameters": {
                "type": "object",
                "properties": {
                    "cluster_id": {
                        "type": "integer",
                        "description": "K8s 集群 ID",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_tickets",
            "description": "查询工单列表和统计。",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "工单状态：open、in_progress、resolved、closed",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回数量，默认 10",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_patrol_reports",
            "description": "查询巡检报告列表。",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "返回数量，默认 5",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "execute_command",
            "description": "在指定服务器上通过 SSH 执行 shell 命令。可用于部署服务、查看日志、管理容器等操作。这是一个写操作，需要用户确认。",
            "parameters": {
                "type": "object",
                "properties": {
                    "asset_id": {
                        "type": "integer",
                        "description": "目标服务器的资产 ID",
                    },
                    "command": {
                        "type": "string",
                        "description": "要执行的 shell 命令",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "超时秒数，默认 30",
                    },
                },
                "required": ["asset_id", "command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_patrol",
            "description": "执行一次全量巡检，检查所有服务器的 CPU、内存、磁盘等指标。这是一个写操作，需要用户确认。",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_ticket",
            "description": "创建一个新工单。这是一个写操作，需要用户确认。",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "工单标题",
                    },
                    "description": {
                        "type": "string",
                        "description": "工单描述",
                    },
                    "priority": {
                        "type": "string",
                        "description": "优先级：low、medium、high、urgent",
                    },
                },
                "required": ["title"],
            },
        },
    },
]

# ─── 只读工具集合 ──────────────────────────────────────────

READONLY_TOOLS = {
    "query_assets",
    "query_host_metrics",
    "query_alerts",
    "query_containers",
    "query_k8s",
    "query_tickets",
    "get_patrol_reports",
}

# ─── 工具 handler 函数 ──────────────────────────────────────

# handler 函数签名: (db: Session, args: dict) -> str
# 部分 handler 是 async 的（调用了 async service），dispatcher 需要区分处理
TOOL_HANDLERS: dict[str, str] = {
    "query_assets": "app.services.ai.tools.handle_query_assets",
    "query_host_metrics": "app.services.ai.tools.handle_query_host_metrics",  # async
    "query_alerts": "app.services.ai.tools.handle_query_alerts",
    "query_containers": "app.services.ai.tools.handle_query_containers",
    "query_k8s": "app.services.ai.tools.handle_query_k8s",
    "query_tickets": "app.services.ai.tools.handle_query_tickets",
    "get_patrol_reports": "app.services.ai.tools.handle_get_patrol_reports",
    "execute_command": "app.services.ai.tools.handle_execute_command",
    "run_patrol": "app.services.ai.tools.handle_run_patrol",  # async
    "create_ticket": "app.services.ai.tools.handle_create_ticket",
}


def handle_query_assets(db: Session, args: dict[str, Any]) -> str:
    """查询资产列表。"""
    from app.services.assets import list_assets

    keyword = args.get("keyword", "")
    status = args.get("status", "")
    assets = list_assets(db, keyword=keyword, status=status)

    if not assets:
        return "未找到匹配的资产。"

    lines = [f"共找到 {len(assets)} 台资产：\n"]
    for a in assets[:20]:
        lines.append(f"- ID:{a.id} {a.name} | {a.ip_address} | 状态:{a.status} | 类型:{a.asset_type or 'N/A'}")
    if len(assets) > 20:
        lines.append(f"... 还有 {len(assets) - 20} 台未显示")
    return "\n".join(lines)


async def handle_query_host_metrics(db: Session, args: dict[str, Any]) -> str:
    """查询单台主机的实时指标。"""
    from app.services.prometheus import get_hosts_summary

    asset_id = args.get("asset_id")
    if not asset_id:
        return "缺少 asset_id 参数。"

    asset = db.get(Asset, asset_id)
    if not asset:
        return f"未找到 ID 为 {asset_id} 的资产。"

    # get_hosts_summary 需要 asset 列表
    results = await get_hosts_summary([asset], db)
    if not results:
        return f"无法获取 {asset.name}({asset.ip_address}) 的指标数据，请检查 Prometheus 配置和 node_exporter。"

    r = results[0]
    lines = [f"**{asset.name}** ({asset.ip_address}) 指标：\n"]
    for key, val in r.items():
        if key.startswith("_"):
            continue
        if isinstance(val, dict):
            lines.append(f"- {key}: {val.get('value', 'N/A')} {val.get('unit', '')}")
        else:
            lines.append(f"- {key}: {val}")
    return "\n".join(lines)


def handle_query_alerts(db: Session, args: dict[str, Any]) -> str:
    """查询告警事件。"""
    severity = args.get("severity", "")
    limit = args.get("limit", 10)

    stmt = select(AlertEvent)
    if severity:
        stmt = stmt.where(AlertEvent.severity == severity)
    stmt = stmt.order_by(AlertEvent.id.desc()).limit(limit)

    alerts = list(db.scalars(stmt).all())
    if not alerts:
        return "没有告警事件。"

    lines = [f"最近 {len(alerts)} 条告警：\n"]
    for a in alerts:
        emoji = {"critical": "🔴", "warning": "🟡", "info": "🔵"}.get(a.severity, "⚪")
        lines.append(f"- {emoji} [{a.severity}] {a.alert_name} | {a.instance or 'N/A'} | {a.status}")
    return "\n".join(lines)


def handle_query_containers(db: Session, args: dict[str, Any]) -> str:
    """查询 Docker 容器。"""
    from app.services.docker_agent import list_docker_containers

    host_id = args.get("host_id")
    keyword = args.get("keyword", "")
    status = args.get("status", "")

    containers = list_docker_containers(db, host_id=host_id, keyword=keyword, status=status)
    if not containers:
        return "没有找到容器。"

    lines = [f"共 {len(containers)} 个容器：\n"]
    for c in containers[:20]:
        lines.append(f"- {c.name} | {c.image} | {c.status} | CPU:{c.cpu_percent}% | 内存:{c.memory_usage}")
    if len(containers) > 20:
        lines.append(f"... 还有 {len(containers) - 20} 个未显示")
    return "\n".join(lines)


def handle_query_k8s(db: Session, args: dict[str, Any]) -> str:
    """查询 K8s 集群状态。"""
    from app.models.container import ContainerCluster
    from app.services.k8s import get_cluster_info

    cluster_id = args.get("cluster_id")

    if cluster_id:
        cluster = db.get(ContainerCluster, cluster_id)
        if not cluster:
            return f"未找到 ID 为 {cluster_id} 的集群。"
        clusters = [cluster]
    else:
        clusters = list(db.scalars(select(ContainerCluster)).all())

    if not clusters:
        return "暂未接入 K8s 集群。"

    lines = []
    for c in clusters:
        if not c.agent_key:  # agent_key 存 token
            lines.append(f"- {c.name}: 未配置 token，跳过")
            continue
        info = get_cluster_info(c.api_endpoint or "", c.agent_key)
        status = "✅ 正常" if info.get("ok") else "❌ 异常"
        lines.append(f"**{c.name}** {status}")
        if info.get("nodes"):
            for n in info["nodes"][:5]:
                lines.append(f"  - 节点 {n.get('name', '?')}: {n.get('status', '?')}")
        if info.get("pods_failed"):
            lines.append(f"  - ⚠️ {info['pods_failed']} 个 Pod 异常")
    return "\n".join(lines)


def handle_query_tickets(db: Session, args: dict[str, Any]) -> str:
    """查询工单。"""
    status = args.get("status", "")
    limit = args.get("limit", 10)

    stmt = select(Ticket)
    if status:
        stmt = stmt.where(Ticket.status == status)
    stmt = stmt.order_by(Ticket.id.desc()).limit(limit)

    tickets = list(db.scalars(stmt).all())
    if not tickets:
        return "没有工单记录。"

    lines = [f"最近 {len(tickets)} 个工单：\n"]
    for t in tickets:
        lines.append(f"- [{t.priority}] {t.title} | 状态:{t.status} | 负责人:{t.assignee or '未分配'}")
    return "\n".join(lines)


def handle_get_patrol_reports(db: Session, args: dict[str, Any]) -> str:
    """查询巡检报告。"""
    limit = args.get("limit", 5)
    reports = list(db.scalars(
        select(PatrolReport).order_by(PatrolReport.id.desc()).limit(limit)
    ).all())

    if not reports:
        return "暂无巡检报告。"

    lines = [f"最近 {len(reports)} 份巡检报告：\n"]
    for r in reports:
        emoji = {"normal": "✅", "warning": "⚠️", "critical": "🔴"}.get(r.status, "❓")
        time_str = r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "N/A"
        lines.append(f"- {emoji} {r.title} | {r.status} | 正常:{r.normal_count} 警告:{r.warning_count} 严重:{r.critical_count} | {time_str}")
    return "\n".join(lines)


def handle_execute_command(db: Session, args: dict[str, Any]) -> str:
    """在服务器上执行命令（写操作）。"""
    from app.services.batch_exec import _ssh_exec
    from app.api.ssh_common import _build_ssh_client

    asset_id = args.get("asset_id")
    command = args.get("command", "")
    timeout = args.get("timeout", 30)

    if not asset_id or not command:
        return "缺少 asset_id 或 command 参数。"

    asset = db.get(Asset, asset_id)
    if not asset:
        return f"未找到 ID 为 {asset_id} 的资产。"

    if not asset.ssh_password and not asset.ssh_key_id:
        return f"资产 {asset.name} 未配置 SSH 凭据，无法执行命令。"

    # 使用 SSH key 或 password
    try:
        ssh_client, username, hostname = _build_ssh_client(asset, {
            "key_id": asset.ssh_key_id,
            "port": asset.ssh_port or 22,
            "username": asset.ssh_username or "root",
            "password": asset.ssh_password,
        })
        ssh_client.close()
    except Exception as e:
        return f"SSH 连接失败: {e}"

    result = _ssh_exec(
        host=asset.ip_address,
        port=asset.ssh_port or 22,
        username=asset.ssh_username or "root",
        password=asset.ssh_password or "",
        command=command,
        timeout=timeout,
    )

    lines = [f"在 **{asset.name}** ({asset.ip_address}) 上执行: `{command}`\n"]
    if result["ok"]:
        lines.append(f"退出码: {result['exit_code']}")
        if result["stdout"]:
            lines.append(f"**输出：**\n```\n{result['stdout'][:3000]}\n```")
        if result["stderr"]:
            lines.append(f"**错误输出：**\n```\n{result['stderr'][:1000]}\n```")
    else:
        lines.append(f"❌ 执行失败: {result['stderr']}")

    return "\n".join(lines)


async def handle_run_patrol(db: Session, args: dict[str, Any]) -> str:
    """执行全量巡检（写操作）。"""
    from app.services.patrol import run_patrol

    report = await run_patrol(db, operator="AI助手")
    db.commit()

    emoji = {"normal": "✅", "warning": "⚠️", "critical": "🔴"}.get(report.status, "❓")
    return (
        f"巡检完成！{emoji} 状态: {report.status}\n\n"
        f"- 正常: {report.normal_count}\n"
        f"- 警告: {report.warning_count}\n"
        f"- 严重: {report.critical_count}\n\n"
        f"报告 ID: {report.id}，可在巡检中心查看详情。"
    )


def handle_create_ticket(db: Session, args: dict[str, Any]) -> str:
    """创建工单（写操作）。"""
    title = args.get("title", "")
    if not title:
        return "工单标题不能为空。"

    ticket = Ticket(
        title=title,
        description=args.get("description", ""),
        priority=args.get("priority", "medium"),
        status="open",
    )
    db.add(ticket)
    db.flush()

    return f"工单已创建：#{ticket.id} {title}（优先级: {ticket.priority}）"
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/ai/tools.py
git commit -m "feat(ai): add tool definitions and handler functions"
```

---

## Task 5: Tool Dispatcher + Conversation Manager

**Files:**
- Create: `backend/app/services/ai/dispatcher.py`
- Create: `backend/app/services/ai/conversations.py`

- [ ] **Step 1: Create the tool dispatcher**

`backend/app/services/ai/dispatcher.py`:

```python
"""工具调度器 — 执行工具调用，区分读/写操作。"""
from __future__ import annotations

import asyncio
import importlib
import inspect
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.services.ai.tools import READONLY_TOOLS, TOOL_HANDLERS

logger = logging.getLogger(__name__)


async def dispatch_tool(
    db: Session,
    tool_name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """
    执行一个工具调用（自动处理 sync/async handler）。

    返回:
        {"ok": True, "result": str, "readonly": True}  — 读操作，已执行
        {"ok": True, "result": str, "readonly": False}  — 写操作，已执行（确认后）
        {"ok": False, "error": str}                     — 执行失败
    """
    handler_path = TOOL_HANDLERS.get(tool_name)
    if not handler_path:
        return {"ok": False, "error": f"未知工具: {tool_name}"}

    # 动态导入 handler 函数
    module_path, func_name = handler_path.rsplit(".", 1)
    try:
        module = importlib.import_module(module_path)
        handler = getattr(module, func_name)
    except (ImportError, AttributeError) as e:
        return {"ok": False, "error": f"工具加载失败: {e}"}

    try:
        # 自动区分 async / sync handler
        if inspect.iscoroutinefunction(handler):
            result = await handler(db, arguments)
        else:
            result = handler(db, arguments)
        readonly = tool_name in READONLY_TOOLS
        return {"ok": True, "result": result, "readonly": readonly}
    except Exception as e:
        logger.exception("Tool execution failed: %s", tool_name)
        return {"ok": False, "error": f"工具执行失败: {e}"}


def is_readonly(tool_name: str) -> bool:
    """判断工具是否为只读操作。"""
    return tool_name in READONLY_TOOLS
```

- [ ] **Step 2: Create the conversation manager**

`backend/app/services/ai/conversations.py`:

```python
"""对话历史管理 — 内存存储，按 conversation_id 维护消息列表。"""
from __future__ import annotations

import uuid
from typing import Any

# {conversation_id: [message, ...]}
_conversations: dict[str, list[dict[str, Any]]] = {}

# {pending_id: {conversation_id, tool_name, arguments, tool_call_id}}
_pending_actions: dict[str, dict[str, Any]] = {}


def new_conversation() -> str:
    """创建新对话，返回 conversation_id。"""
    cid = str(uuid.uuid4())
    _conversations[cid] = []
    return cid


def get_conversation(conversation_id: str) -> list[dict[str, Any]]:
    """获取对话历史。不存在则创建。"""
    if conversation_id not in _conversations:
        _conversations[conversation_id] = []
    return _conversations[conversation_id]


def add_message(conversation_id: str, message: dict[str, Any]) -> None:
    """向对话历史追加一条消息。"""
    if conversation_id not in _conversations:
        _conversations[conversation_id] = []
    _conversations[conversation_id].append(message)


def clear_conversation(conversation_id: str) -> None:
    """清空对话历史。"""
    _conversations.pop(conversation_id, None)


def store_pending_action(
    conversation_id: str,
    tool_name: str,
    arguments: dict[str, Any],
    tool_call_id: str,
) -> str:
    """存储待确认的写操作，返回 pending_id。"""
    pending_id = str(uuid.uuid4())
    _pending_actions[pending_id] = {
        "conversation_id": conversation_id,
        "tool_name": tool_name,
        "arguments": arguments,
        "tool_call_id": tool_call_id,
    }
    return pending_id


def get_pending_action(pending_id: str) -> dict[str, Any] | None:
    """获取待确认操作。"""
    return _pending_actions.get(pending_id)


def remove_pending_action(pending_id: str) -> None:
    """移除已处理的待确认操作。"""
    _pending_actions.pop(pending_id, None)
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/ai/dispatcher.py backend/app/services/ai/conversations.py
git commit -m "feat(ai): add tool dispatcher and conversation manager"
```

---

## Task 6: Chat API with SSE

**Files:**
- Rewrite: `backend/app/api/ai.py`

- [ ] **Step 1: Rewrite the AI API with SSE streaming**

Replace the entire contents of `backend/app/api/ai.py`:

```python
"""
AI 运维助手 API — SSE 流式对话 + 工具调用 + 写操作确认。
"""
from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_api_user
from app.db.database import get_db
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI 助手"])

SYSTEM_PROMPT = """你是运维平台的 AI 助手。你可以帮助用户：
- 查询服务器状态和性能指标
- 查询告警事件
- 查询 Docker 容器和 K8s 集群状态
- 查询工单
- 查看巡检报告
- 在服务器上执行命令（如部署服务、查看日志、管理容器等）
- 执行巡检
- 创建工单

根据用户的意图选择合适的工具来完成操作。
对于查询类操作，直接执行并告诉用户结果。
对于写操作（执行命令、巡检、创建工单），先说明你要做什么，等用户确认后再执行。
回复使用中文，简洁明了。"""


class ChatRequest(BaseModel):
    message: str
    conversation_id: str = ""


class ConfirmRequest(BaseModel):
    pending_id: str
    conversation_id: str


@router.post("/chat")
async def api_chat(
    body: ChatRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_api_user),
):
    """SSE 流式对话接口。"""
    from app.core.settings import get_llm_config
    from app.services.ai.conversations import (
        add_message,
        get_conversation,
        new_conversation,
        store_pending_action,
    )
    from app.services.ai.dispatcher import dispatch_tool, is_readonly
    from app.services.ai.llm_client import LLMClient
    from app.services.ai.tools import TOOL_DEFINITIONS

    config = get_llm_config(db)
    if not config["base_url"] or not config["api_key"] or not config["model"]:
        async def error_stream():
            yield _sse_event({"type": "error", "content": "LLM 未配置，请在系统设置中配置 AI 模型。"})
        return StreamingResponse(error_stream(), media_type="text/event-stream")

    # 初始化对话
    cid = body.conversation_id or new_conversation()
    history = get_conversation(cid)

    # 追加用户消息
    add_message(cid, {"role": "user", "content": body.message})

    client = LLMClient(config["base_url"], config["api_key"], config["model"])

    async def event_stream():
        # 构建 messages：system + history
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history

        # 循环处理（可能有多轮 tool call）
        max_rounds = 10  # 防止无限循环
        for _ in range(max_rounds):
            # 检查客户端是否断开
            if await request.is_disconnected():
                break

            full_text = ""
            tool_calls = []

            try:
                async for event in client.chat_stream(messages, TOOL_DEFINITIONS):
                    if event["type"] == "text":
                        full_text += event["content"]
                        yield _sse_event({"type": "text", "content": event["content"]})

                    elif event["type"] == "tool_call":
                        tool_calls.append(event)

                    elif event["type"] == "done":
                        break
            except Exception as e:
                logger.exception("LLM stream error")
                yield _sse_event({"type": "error", "content": f"LLM 调用失败: {str(e)}"})
                return

            # 没有工具调用 — 对话结束
            if not tool_calls:
                if full_text:
                    add_message(cid, {"role": "assistant", "content": full_text})
                yield _sse_event({"type": "done", "conversation_id": cid})
                return

            # 有工具调用 — 处理每个 tool call
            # 先把 assistant 的 tool_calls 消息加入历史
            assistant_msg: dict[str, Any] = {"role": "assistant", "content": full_text or None, "tool_calls": []}
            for tc in tool_calls:
                assistant_msg["tool_calls"].append({
                    "id": tc["id"],
                    "type": "function",
                    "function": {"name": tc["name"], "arguments": json.dumps(tc["arguments"], ensure_ascii=False)},
                })
            add_message(cid, assistant_msg)

            for tc in tool_calls:
                tool_name = tc["name"]
                tool_args = tc["arguments"]
                tool_call_id = tc["id"]

                if is_readonly(tool_name):
                    # 只读 — 直接执行
                    yield _sse_event({"type": "tool_start", "tool": tool_name, "args": tool_args})
                    result = await dispatch_tool(db, tool_name, tool_args)
                    result_text = result.get("result", result.get("error", "执行失败"))
                    yield _sse_event({"type": "tool_result", "tool": tool_name, "result": result_text})
                    add_message(cid, {"role": "tool", "tool_call_id": tool_call_id, "content": result_text})
                else:
                    # 写操作 — 返回确认请求
                    pending_id = store_pending_action(cid, tool_name, tool_args, tool_call_id)
                    asset_info = ""
                    if tool_name == "execute_command" and "asset_id" in tool_args:
                        asset = db.get(__import__("app.models.asset", fromlist=["Asset"]).Asset, tool_args["asset_id"])
                        if asset:
                            asset_info = f"服务器: {asset.name} ({asset.ip_address})\n"
                    yield _sse_event({
                        "type": "tool_confirm",
                        "pending_id": pending_id,
                        "tool": tool_name,
                        "args": tool_args,
                        "description": f"{asset_info}操作: {tool_name}\n参数: {json.dumps(tool_args, ensure_ascii=False, indent=2)}",
                    })
                    # 暂停此轮，等用户确认后通过 /confirm 接口继续
                    return

            # 所有工具执行完毕，继续下一轮 LLM 调用
            # messages 会在下一轮循环时从 history 自动获取

        yield _sse_event({"type": "done", "conversation_id": cid})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/chat/confirm")
async def api_chat_confirm(
    body: ConfirmRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_api_user),
):
    """确认执行写操作，继续 LLM 对话。"""
    from app.core.settings import get_llm_config
    from app.services.ai.conversations import (
        add_message,
        get_conversation,
        get_pending_action,
        remove_pending_action,
    )
    from app.services.ai.dispatcher import dispatch_tool
    from app.services.ai.llm_client import LLMClient
    from app.services.ai.tools import TOOL_DEFINITIONS

    pending = get_pending_action(body.pending_id)
    if not pending:
        async def error_stream():
            yield _sse_event({"type": "error", "content": "该操作已过期或不存在。"})
        return StreamingResponse(error_stream(), media_type="text/event-stream")

    cid = pending["conversation_id"]
    tool_name = pending["tool_name"]
    tool_args = pending["arguments"]
    tool_call_id = pending["tool_call_id"]

    remove_pending_action(body.pending_id)

    # 执行工具
    yield_data = {}
    result = dispatch_tool(db, tool_name, tool_args)
    result_text = result.get("result", result.get("error", "执行失败"))

    # 把工具结果加入对话历史
    add_message(cid, {"role": "tool", "tool_call_id": tool_call_id, "content": result_text})

    # 继续 LLM 对话
    config = get_llm_config(db)
    client = LLMClient(config["base_url"], config["api_key"], config["model"])
    history = get_conversation(cid)

    async def event_stream():
        yield _sse_event({"type": "tool_start", "tool": tool_name, "args": tool_args})
        yield _sse_event({"type": "tool_result", "tool": tool_name, "result": result_text})

        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history
        full_text = ""

        try:
            async for event in client.chat_stream(messages, TOOL_DEFINITIONS):
                if event["type"] == "text":
                    full_text += event["content"]
                    yield _sse_event({"type": "text", "content": event["content"]})
                elif event["type"] == "tool_call":
                    # 确认后不应再有写操作 tool call，但如果有则忽略
                    pass
                elif event["type"] == "done":
                    break
        except Exception as e:
            logger.exception("LLM stream error after confirm")
            yield _sse_event({"type": "error", "content": f"LLM 调用失败: {str(e)}"})
            return

        if full_text:
            add_message(cid, {"role": "assistant", "content": full_text})
        yield _sse_event({"type": "done", "conversation_id": cid})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/chat/reject")
async def api_chat_reject(
    body: ConfirmRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_api_user),
):
    """拒绝写操作，告知 LLM 用户拒绝了。"""
    from app.core.settings import get_llm_config
    from app.services.ai.conversations import (
        add_message,
        get_conversation,
        get_pending_action,
        remove_pending_action,
    )
    from app.services.ai.dispatcher import dispatch_tool
    from app.services.ai.llm_client import LLMClient
    from app.services.ai.tools import TOOL_DEFINITIONS

    pending = get_pending_action(body.pending_id)
    if not pending:
        async def error_stream():
            yield _sse_event({"type": "error", "content": "该操作已过期或不存在。"})
        return StreamingResponse(error_stream(), media_type="text/event-stream")

    cid = pending["conversation_id"]
    tool_call_id = pending["tool_call_id"]
    remove_pending_action(body.pending_id)

    # 告知 LLM 用户拒绝了
    add_message(cid, {"role": "tool", "tool_call_id": tool_call_id, "content": "用户拒绝了该操作的执行。"})

    config = get_llm_config(db)
    client = LLMClient(config["base_url"], config["api_key"], config["model"])
    history = get_conversation(cid)

    async def event_stream():
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history
        full_text = ""

        try:
            async for event in client.chat_stream(messages, TOOL_DEFINITIONS):
                if event["type"] == "text":
                    full_text += event["content"]
                    yield _sse_event({"type": "text", "content": event["content"]})
                elif event["type"] == "done":
                    break
        except Exception as e:
            yield _sse_event({"type": "error", "content": f"LLM 调用失败: {str(e)}"})
            return

        if full_text:
            add_message(cid, {"role": "assistant", "content": full_text})
        yield _sse_event({"type": "done", "conversation_id": cid})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _sse_event(data: dict[str, Any]) -> str:
    """格式化 SSE 事件。"""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/api/ai.py
git commit -m "feat(ai): rewrite AI chat API with SSE streaming and tool calling"
```

---

## Task 7: Frontend — API + SSE Fetch

**Files:**
- Rewrite: `frontend/src/api/ai.ts`

- [ ] **Step 1: Rewrite the AI API module**

Replace the entire contents of `frontend/src/api/ai.ts`:

```typescript
/**
 * AI 助手 API — SSE 流式对话 + 工具确认
 */
import { getToken } from '@/utils/auth'

const BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1'

export interface SSEEvent {
  type: 'text' | 'tool_start' | 'tool_result' | 'tool_confirm' | 'error' | 'done'
  content?: string
  tool?: string
  args?: Record<string, unknown>
  result?: string
  pending_id?: string
  description?: string
  conversation_id?: string
}

/**
 * 发送消息，返回 SSE 事件流。
 */
export async function* sendAiMessageStream(
  message: string,
  conversation_id?: string,
): AsyncGenerator<SSEEvent> {
  const token = getToken()
  const resp = await fetch(`${BASE}/ai/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ message, conversation_id }),
  })

  if (!resp.ok) {
    throw new Error(`请求失败: ${resp.status}`)
  }

  const reader = resp.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          yield JSON.parse(line.slice(6)) as SSEEvent
        } catch { /* ignore malformed */ }
      }
    }
  }

  // 处理剩余 buffer
  if (buffer.startsWith('data: ')) {
    try {
      yield JSON.parse(buffer.slice(6)) as SSEEvent
    } catch { /* ignore */ }
  }
}

/**
 * 确认执行写操作，返回 SSE 事件流。
 */
export async function* confirmAiActionStream(
  pending_id: string,
  conversation_id: string,
): AsyncGenerator<SSEEvent> {
  const token = getToken()
  const resp = await fetch(`${BASE}/ai/chat/confirm`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ pending_id, conversation_id }),
  })

  if (!resp.ok) {
    throw new Error(`请求失败: ${resp.status}`)
  }

  const reader = resp.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          yield JSON.parse(line.slice(6)) as SSEEvent
        } catch { /* ignore */ }
      }
    }
  }

  if (buffer.startsWith('data: ')) {
    try {
      yield JSON.parse(buffer.slice(6)) as SSEEvent
    } catch { /* ignore */ }
  }
}

/**
 * 拒绝写操作，返回 SSE 事件流。
 */
export async function* rejectAiActionStream(
  pending_id: string,
  conversation_id: string,
): AsyncGenerator<SSEEvent> {
  const token = getToken()
  const resp = await fetch(`${BASE}/ai/chat/reject`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ pending_id, conversation_id }),
  })

  if (!resp.ok) {
    throw new Error(`请求失败: ${resp.status}`)
  }

  const reader = resp.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          yield JSON.parse(line.slice(6)) as SSEEvent
        } catch { /* ignore */ }
      }
    }
  }

  if (buffer.startsWith('data: ')) {
    try {
      yield JSON.parse(buffer.slice(6)) as SSEEvent
    } catch { /* ignore */ }
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api/ai.ts
git commit -m "feat(ai): rewrite AI API with SSE streaming support"
```

---

## Task 8: Frontend — AiView.vue Rewrite

**Files:**
- Rewrite: `frontend/src/views/ai/AiView.vue`

- [ ] **Step 1: Rewrite AiView.vue**

Replace the entire contents of `frontend/src/views/ai/AiView.vue`:

```vue
<template>
  <div class="ai-page">
    <!-- 顶部标题栏 -->
    <div class="ai-header">
      <div class="ai-title">
        <span class="ai-icon">🤖</span>
        <h2>AI 运维助手</h2>
        <el-tag type="info" size="small" style="margin-left:8px">Beta</el-tag>
      </div>
      <el-button text @click="handleClear">
        <el-icon><Delete /></el-icon> 清空对话
      </el-button>
    </div>

    <!-- 对话区域 -->
    <div class="ai-chat" ref="chatRef">
      <!-- 欢迎消息 -->
      <div v-if="!messages.length" class="ai-welcome">
        <div class="welcome-icon">🤖</div>
        <h3>你好，我是 AI 运维助手</h3>
        <p>我可以帮你查询服务器状态、执行巡检、在服务器上执行命令等，试试问我：</p>
        <div class="quick-actions">
          <div v-for="q in quickQuestions" :key="q" class="quick-item" @click="handleQuickAsk(q)">
            {{ q }}
          </div>
        </div>
      </div>

      <!-- 消息列表 -->
      <div v-for="(msg, idx) in messages" :key="idx" class="msg-row" :class="msg.role">
        <div class="msg-avatar">
          <span v-if="msg.role === 'user'">👤</span>
          <span v-else>🤖</span>
        </div>
        <div class="msg-body">
          <!-- 工具执行状态 -->
          <div v-if="msg.type === 'tool_start'" class="msg-tool-status">
            <el-icon class="is-loading"><Loading /></el-icon>
            <span>正在执行: {{ msg.tool }}</span>
          </div>
          <div v-if="msg.type === 'tool_result'" class="msg-tool-result">
            <div class="tool-result-header">📋 {{ msg.tool }} 执行结果</div>
            <div class="tool-result-content">{{ msg.result }}</div>
          </div>

          <!-- 写操作确认卡片 -->
          <div v-if="msg.type === 'tool_confirm'" class="msg-confirm-card">
            <div class="confirm-header">
              <el-icon><WarningFilled /></el-icon>
              <span>AI 请求执行以下操作</span>
            </div>
            <div class="confirm-body">
              <pre>{{ msg.description }}</pre>
            </div>
            <div class="confirm-actions">
              <el-button size="small" @click="handleReject(msg)">拒绝</el-button>
              <el-button size="small" type="primary" :loading="confirmLoading" @click="handleConfirm(msg)">
                确认执行
              </el-button>
            </div>
          </div>

          <!-- 文本消息 -->
          <div v-if="msg.content" class="msg-content" v-html="renderContent(msg.content)" />
          <div class="msg-time">{{ msg.time }}</div>
        </div>
      </div>

      <!-- 加载中 -->
      <div v-if="loading" class="msg-row assistant">
        <div class="msg-avatar">🤖</div>
        <div class="msg-body">
          <div class="msg-content loading-dots">
            <span></span><span></span><span></span>
          </div>
        </div>
      </div>
    </div>

    <!-- 输入区域 -->
    <div class="ai-input">
      <div class="input-wrap">
        <el-input
          v-model="inputText"
          type="textarea"
          :rows="1"
          :autosize="{ minRows: 1, maxRows: 4 }"
          placeholder="问我任何运维问题…（Shift+Enter 换行）"
          resize="none"
          @keydown="handleKeydown"
        />
        <el-button
          type="primary"
          :icon="Promotion"
          :loading="loading"
          :disabled="!inputText.trim()"
          circle
          @click="handleSend"
        />
      </div>
      <div class="input-tip">
        基于大语言模型，回答仅供参考，请以实际系统数据为准
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted } from 'vue'
import { Promotion, Delete, Loading, WarningFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import {
  sendAiMessageStream,
  confirmAiActionStream,
  rejectAiActionStream,
  type SSEEvent,
} from '@/api/ai'

interface Message {
  role: 'user' | 'assistant' | 'system'
  content?: string
  time: string
  type?: 'text' | 'tool_start' | 'tool_result' | 'tool_confirm'
  tool?: string
  result?: string
  description?: string
  pending_id?: string
  args?: Record<string, unknown>
}

const messages = ref<Message[]>([])
const inputText = ref('')
const loading = ref(false)
const confirmLoading = ref(false)
const chatRef = ref<HTMLElement>()
const conversationId = ref('')

const quickQuestions = [
  '今天哪台服务器资源异常？',
  '最近有什么告警？',
  '帮我巡检一下系统',
  'K8s 集群状态怎么样？',
  '帮我在服务器上看看 Docker 容器状态',
]

function now(): string {
  return new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

function scrollToBottom() {
  nextTick(() => {
    if (chatRef.value) {
      chatRef.value.scrollTop = chatRef.value.scrollHeight
    }
  })
}

function renderContent(text: string): string {
  return text
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/`(.*?)`/g, '<code>$1</code>')
    .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
    .replace(/\n/g, '<br>')
}

async function sendMessage(text: string) {
  if (!text.trim() || loading.value) return

  messages.value.push({ role: 'user', content: text, time: now(), type: 'text' })
  scrollToBottom()

  loading.value = true
  // 创建一个空的 assistant 消息，逐步填充
  const assistantMsg: Message = { role: 'assistant', content: '', time: now(), type: 'text' }
  messages.value.push(assistantMsg)

  try {
    for await (const event of sendAiMessageStream(text, conversationId.value || undefined)) {
      handleSSEEvent(event, assistantMsg)
    }
  } catch (e: any) {
    assistantMsg.content = '⚠️ 请求失败：' + (e.message || '服务暂时不可用')
  } finally {
    loading.value = false
    scrollToBottom()
  }
}

function handleSSEEvent(event: SSEEvent, assistantMsg: Message) {
  switch (event.type) {
    case 'text':
      assistantMsg.content = (assistantMsg.content || '') + event.content
      scrollToBottom()
      break

    case 'tool_start':
      messages.value.push({
        role: 'assistant',
        time: now(),
        type: 'tool_start',
        tool: event.tool,
      })
      scrollToBottom()
      break

    case 'tool_result':
      // 替换 tool_start 为 tool_result
      const startIdx = messages.value.findIndex(
        m => m.type === 'tool_start' && m.tool === event.tool,
      )
      if (startIdx !== -1) {
        messages.value.splice(startIdx, 1)
      }
      messages.value.push({
        role: 'assistant',
        time: now(),
        type: 'tool_result',
        tool: event.tool,
        result: event.result,
      })
      scrollToBottom()
      break

    case 'tool_confirm':
      messages.value.push({
        role: 'assistant',
        time: now(),
        type: 'tool_confirm',
        tool: event.tool,
        description: event.description,
        pending_id: event.pending_id,
        args: event.args,
      })
      scrollToBottom()
      break

    case 'error':
      assistantMsg.content = (assistantMsg.content || '') + '\n\n⚠️ ' + event.content
      scrollToBottom()
      break

    case 'done':
      if (event.conversation_id) {
        conversationId.value = event.conversation_id
      }
      break
  }
}

async function handleConfirm(msg: Message) {
  if (!msg.pending_id || !conversationId.value) return

  confirmLoading.value = true
  const assistantMsg: Message = { role: 'assistant', content: '', time: now(), type: 'text' }
  messages.value.push(assistantMsg)

  // 移除确认卡片
  const idx = messages.value.indexOf(msg)
  if (idx !== -1) messages.value.splice(idx, 1)

  try {
    for await (const event of confirmAiActionStream(msg.pending_id, conversationId.value)) {
      handleSSEEvent(event, assistantMsg)
    }
  } catch (e: any) {
    assistantMsg.content = '⚠️ 操作失败：' + (e.message || '服务暂时不可用')
  } finally {
    confirmLoading.value = false
    scrollToBottom()
  }
}

async function handleReject(msg: Message) {
  if (!msg.pending_id || !conversationId.value) return

  // 移除确认卡片
  const idx = messages.value.indexOf(msg)
  if (idx !== -1) messages.value.splice(idx, 1)

  const assistantMsg: Message = { role: 'assistant', content: '', time: now(), type: 'text' }
  messages.value.push(assistantMsg)

  try {
    for await (const event of rejectAiActionStream(msg.pending_id, conversationId.value)) {
      handleSSEEvent(event, assistantMsg)
    }
  } catch (e: any) {
    assistantMsg.content = '⚠️ 请求失败：' + (e.message || '服务暂时不可用')
  } finally {
    scrollToBottom()
  }
}

function handleSend() {
  const text = inputText.value.trim()
  inputText.value = ''
  sendMessage(text)
}

function handleQuickAsk(question: string) {
  sendMessage(question)
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}

function handleClear() {
  messages.value = []
  conversationId.value = ''
}

onMounted(scrollToBottom)
</script>

<style lang="scss" scoped>
.ai-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 56px);
  background: #f5f7fa;
}

.ai-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  background: #fff;
  border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;

  .ai-title {
    display: flex;
    align-items: center;
    gap: 8px;
    .ai-icon { font-size: 24px; }
    h2 { margin: 0; font-size: 16px; }
  }
}

.ai-chat {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.ai-welcome {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;

  .welcome-icon { font-size: 64px; margin-bottom: 16px; }
  h3 { font-size: 20px; margin: 0 0 8px; color: #303133; }
  p { color: var(--text-muted); margin: 0 0 24px; }

  .quick-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    justify-content: center;
    max-width: 500px;
  }

  .quick-item {
    padding: 8px 16px;
    background: #fff;
    border: 1px solid var(--border-color);
    border-radius: 20px;
    font-size: 13px;
    cursor: pointer;
    transition: all 0.2s;

    &:hover {
      border-color: var(--el-color-primary);
      color: var(--el-color-primary);
      background: rgba(59, 130, 246, 0.05);
    }
  }
}

.msg-row {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  max-width: 800px;

  &.user {
    margin-left: auto;
    flex-direction: row-reverse;
    .msg-body { align-items: flex-end; }
    .msg-content {
      background: var(--el-color-primary);
      color: #fff;
      border-radius: 16px 16px 4px 16px;
    }
  }

  &.assistant {
    .msg-content {
      background: #fff;
      color: #303133;
      border-radius: 16px 16px 16px 4px;
      border: 1px solid var(--border-color);
    }
  }
}

.msg-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
  background: #f0f2f5;
}

.msg-body {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-width: 70%;
}

.msg-content {
  padding: 10px 16px;
  font-size: 14px;
  line-height: 1.6;
  word-break: break-word;

  :deep(code) {
    background: rgba(0, 0, 0, 0.06);
    padding: 1px 4px;
    border-radius: 3px;
    font-size: 13px;
    font-family: 'Cascadia Code', 'Fira Code', monospace;
  }

  :deep(pre) {
    background: #1e1e1e;
    color: #d4d4d4;
    padding: 12px;
    border-radius: 8px;
    overflow-x: auto;
    margin: 8px 0;

    code {
      background: none;
      color: inherit;
      padding: 0;
    }
  }

  :deep(strong) { font-weight: 600; }
}

.msg-time {
  font-size: 11px;
  color: var(--text-muted);
  padding: 0 4px;
}

// 工具执行状态
.msg-tool-status {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: #f0f9ff;
  border: 1px solid #bae6fd;
  border-radius: 8px;
  font-size: 13px;
  color: #0369a1;
}

.msg-tool-result {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 8px;
  overflow: hidden;

  .tool-result-header {
    padding: 8px 12px;
    font-size: 13px;
    font-weight: 600;
    color: #15803d;
    border-bottom: 1px solid #bbf7d0;
  }

  .tool-result-content {
    padding: 10px 12px;
    font-size: 13px;
    line-height: 1.5;
    white-space: pre-wrap;
    max-height: 300px;
    overflow-y: auto;
    color: #374151;
  }
}

// 确认卡片
.msg-confirm-card {
  background: #fffbeb;
  border: 1px solid #fcd34d;
  border-radius: 12px;
  overflow: hidden;

  .confirm-header {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 10px 14px;
    background: #fef3c7;
    font-size: 14px;
    font-weight: 600;
    color: #92400e;
  }

  .confirm-body {
    padding: 12px 14px;

    pre {
      margin: 0;
      font-size: 13px;
      line-height: 1.5;
      white-space: pre-wrap;
      color: #374151;
      font-family: 'Cascadia Code', 'Fira Code', monospace;
    }
  }

  .confirm-actions {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    padding: 10px 14px;
    border-top: 1px solid #fcd34d;
  }
}

.loading-dots {
  display: flex;
  gap: 4px;
  padding: 14px 20px !important;

  span {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #c0c4cc;
    animation: dot-bounce 1.4s ease-in-out infinite;

    &:nth-child(2) { animation-delay: 0.2s; }
    &:nth-child(3) { animation-delay: 0.4s; }
  }
}

@keyframes dot-bounce {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}

.ai-input {
  padding: 12px 20px 16px;
  background: #fff;
  border-top: 1px solid var(--border-color);
  flex-shrink: 0;

  .input-wrap {
    display: flex;
    gap: 8px;
    align-items: flex-end;

    :deep(.el-textarea__inner) {
      border-radius: 20px;
      padding: 8px 16px;
      resize: none;
    }

    .el-button {
      flex-shrink: 0;
      width: 40px;
      height: 40px;
    }
  }

  .input-tip {
    text-align: center;
    font-size: 11px;
    color: var(--text-muted);
    margin-top: 8px;
  }
}
</style>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/views/ai/AiView.vue
git commit -m "feat(ai): rewrite AI chat UI with SSE streaming and confirmation cards"
```

---

## Task 9: Integration Testing

- [ ] **Step 1: Start the backend and verify LLM config**

```bash
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Go to `http://localhost:8000/docs`, find the `/api/v1/settings/` endpoint, verify `llm.base_url`, `llm.api_key`, `llm.model` appear in the response.

- [ ] **Step 2: Configure LLM via API or settings UI**

```bash
curl -X PUT http://localhost:8000/api/v1/settings/llm.base_url \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"value": "https://api.openai.com/v1"}'

curl -X PUT http://localhost:8000/api/v1/settings/llm.api_key \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"value": "sk-xxx"}'

curl -X PUT http://localhost:8000/api/v1/settings/llm.model \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"value": "gpt-4o"}'
```

- [ ] **Step 3: Test the chat endpoint with curl**

```bash
curl -N http://localhost:8000/api/v1/ai/chat \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"message": "你好"}'
```

Expected: SSE stream with text events.

- [ ] **Step 4: Test tool calling**

```bash
curl -N http://localhost:8000/api/v1/ai/chat \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"message": "帮我查一下有哪些服务器"}'
```

Expected: SSE stream with tool_start (query_assets) → tool_result → text response.

- [ ] **Step 5: Test write operation confirmation**

```bash
curl -N http://localhost:8000/api/v1/ai/chat \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"message": "帮我巡检一下系统"}'
```

Expected: SSE stream with tool_confirm event containing pending_id.

- [ ] **Step 6: Start the frontend and test full flow**

```bash
cd frontend
npm run dev
```

Open `http://localhost:3000`, navigate to AI 助手, test:
1. Quick question buttons work
2. Streaming text display
3. Tool execution status shows
4. Write operation confirmation card appears
5. Confirm/reject buttons work
6. Multi-turn conversation works

- [ ] **Step 7: Final commit**

```bash
git add -A
git commit -m "feat(ai): complete AI assistant with LLM function calling"
```
