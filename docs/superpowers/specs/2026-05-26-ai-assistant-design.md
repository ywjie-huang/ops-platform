# AI 运维助手 — 设计文档

## 概述

将现有的关键词匹配 stub AI 助手升级为基于 LLM Function Calling 的真正 AI Agent。用户通过自然语言与系统交互，AI 自动选择合适的工具完成运维操作。

## 设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| LLM 对接方式 | OpenAI 兼容 API（httpx 直调） | 最灵活，支持 OpenAI/DeepSeek/Qwen/Ollama 等 |
| 工具执行模式 | 读操作自动执行，写操作需用户确认 | 安全优先 |
| 输出方式 | SSE 流式输出 | 用户体验好 |
| 对话模式 | 多轮对话（后端维护 messages 数组） | 支持上下文指代 |
| LLM 配置 | 用户可在系统设置页面配置 base_url/api_key/model | 灵活，不锁定供应商 |

## 架构

```
┌─────────────────────────────────────────────────────┐
│  Frontend (AiView.vue)                              │
│  用户输入 → POST /ai/chat → SSE 流式接收             │
│  消息气泡 + 工具执行状态卡片 + 写操作确认按钮          │
└──────────────┬──────────────────────────────────────┘
               │ SSE
┌──────────────▼──────────────────────────────────────┐
│  Backend API (api/ai.py)                            │
│  /ai/chat → AI Service → 流式返回                   │
│  /ai/chat/confirm → 执行已确认的写操作               │
└──────────────┬──────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────┐
│  AI Service (services/ai.py)                        │
│  ┌──────────────┐  ┌───────────────┐                │
│  │ LLM Client   │  │ Tool Registry │                │
│  │ (httpx SSE)  │  │ (name→func)   │                │
│  └──────┬───────┘  └───────┬───────┘                │
│         │                  │                         │
│  ┌──────▼──────────────────▼───────┐                │
│  │ Tool Dispatcher                  │                │
│  │ 读操作 → 直接执行                 │                │
│  │ 写操作 → 返回确认请求             │                │
│  └──────────────────────────────────┘                │
└──────────────┬──────────────────────────────────────┘
               │ 调用已有 service
┌──────────────▼──────────────────────────────────────┐
│  Existing Services                                  │
│  patrol.run_patrol()  batch_exec._ssh_exec()        │
│  prometheus.get_hosts_summary()  assets.list_assets()│
│  docker_agent.pull_from_agent()  k8s.get_cluster_info│
└─────────────────────────────────────────────────────┘
```

## LLM 配置

扩展现有 `system_config` 表和设置页面，新增三个配置项：

| 配置 key | 说明 | 示例 |
|----------|------|------|
| `llm.base_url` | API 地址（OpenAI 兼容） | `https://api.openai.com/v1` |
| `llm.api_key` | API Key | `sk-xxx` |
| `llm.model` | 模型名称 | `gpt-4o` |

- 配置项加入 `settings.py` 的 `_DEFAULTS` 和 `settings.py` 的 `_CONFIG_SPECS`
- 设置页面增加「AI 模型配置」分组
- 增加「测试连接」按钮，发一条简单消息验证连通性

## 工具定义

### 读操作（自动执行）

| 工具 | 描述 | 参数 | 底层实现 |
|------|------|------|----------|
| `query_assets` | 查询服务器列表 | `keyword`, `status` | `assets.list_assets()` |
| `query_host_metrics` | 查询服务器指标 | `asset_id`, `metrics[]` | `prometheus.get_hosts_summary()` |
| `query_alerts` | 查询告警事件 | `severity`, `limit` | 直接查 `AlertEvent` 表 |
| `query_containers` | 查询 Docker 容器 | `host_id`, `keyword`, `status` | `docker_agent.list_docker_containers()` |
| `query_k8s` | 查询 K8s 集群状态 | `cluster_id` | `k8s.get_cluster_info()` |
| `query_tickets` | 查询工单 | `status`, `limit` | 直接查 `Ticket` 表 |
| `get_patrol_reports` | 查询巡检报告 | `limit` | 直接查 `PatrolReport` 表 |

### 写操作（需用户确认）

| 工具 | 描述 | 参数 | 底层实现 |
|------|------|------|----------|
| `execute_command` | 在服务器上执行 shell 命令 | `asset_id`, `command`, `timeout` | `batch_exec._ssh_exec()` |
| `run_patrol` | 执行全量巡检 | 无 | `patrol.run_patrol()` |
| `create_ticket` | 创建工单 | `title`, `description`, `priority` | `Ticket` 表写入 |

`execute_command` 是万能原语——部署服务、重启进程、查日志、管理容器等操作由 LLM 拆解为具体 shell 命令。

## 对话循环

```
1. 用户发送消息
2. 拼接 messages: system_prompt + conversation_history + user_message
3. 调用 LLM API (stream=True, tools=[...])
4. 处理流式响应：
   a. LLM 返回 text delta → 通过 SSE 推给前端
   b. LLM 返回 tool_call →
      - readonly=True: 执行工具，结果作为 tool message 喂回 LLM，跳到步骤 3
      - readonly=False: 返回 tool_confirm 事件给前端，暂停，等待用户确认
5. 用户确认后 → 执行工具 → 结果喂回 LLM → 继续生成
```

### System Prompt 核心内容

```
你是运维平台的 AI 助手。你可以：
- 查询服务器状态和指标
- 查询告警、工单、K8s 集群信息
- 执行巡检
- 在服务器上执行命令

根据用户意图选择合适的工具。对于写操作，先向用户说明要做什么。
回复使用中文，简洁明了。
```

## 写操作确认流程

```
前端展示确认卡片（黄色警告样式）：
┌─────────────────────────────────────────┐
│ ⚠️ AI 请求执行以下操作                    │
│                                          │
│ 服务器：10.0.0.5                         │
│ 命令：docker run -d --name nginx ...     │
│                                          │
│    [拒绝]            [确认执行]           │
└─────────────────────────────────────────┘

确认 → POST /ai/chat/confirm { pending_id }
拒绝 → POST /ai/chat/reject { pending_id }
```

## 对话历史

- 后端维护 `conversations: dict[str, list[message]]`
- 每个会话一个 `conversation_id`（UUID）
- 存内存即可，不落库
- 前端首次请求不带 `conversation_id`，后端创建并返回
- 前端后续请求携带 `conversation_id` 维持上下文
- 清空对话时重置

## API 设计

### POST /ai/chat

请求：
```json
{
  "message": "帮我巡检一下 10.0.0.5 这台服务器",
  "conversation_id": "optional-uuid"
}
```

响应：SSE 流，事件类型：
- `text` — AI 文本回复 delta
- `tool_start` — 工具开始执行（显示 loading 状态）
- `tool_result` — 工具执行完成（读操作，自动执行的结果）
- `tool_confirm` — 写操作待确认（含 pending_id）
- `error` — 错误信息
- `done` — 流结束（含 conversation_id）

### POST /ai/chat/confirm

请求：
```json
{
  "pending_id": "uuid-xxx",
  "conversation_id": "uuid-yyy"
}
```

响应：SSE 流（执行工具后继续 LLM 生成）

### POST /ai/chat/reject

请求：
```json
{
  "pending_id": "uuid-xxx",
  "conversation_id": "uuid-yyy"
}
```

响应：SSE 流（告知 LLM 用户拒绝了操作）

## 前端改动

### AiView.vue

1. **SSE 接入**：`sendAiMessage` 改为 `fetch` + `ReadableStream`，逐步拼接 AI 回复
2. **工具状态展示**：消息列表中显示中间状态（如"正在查询服务器指标..."）
3. **确认卡片组件**：展示待确认操作 + 拒绝/确认按钮
4. **流式打字效果**：AI 回复逐字显示

### api/ai.ts

- `sendAiMessage` 改为返回 `ReadableStream` 的 fetch 调用
- 新增 `confirmAiAction` 和 `rejectAiAction` 函数

## 后端文件变更

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `backend/app/services/ai.py` | 新建 | LLM 客户端 + 工具注册 + 对话循环 |
| `backend/app/api/ai.py` | 重写 | SSE 流式接口 + 确认接口 |
| `backend/app/core/settings.py` | 修改 | 增加 LLM 配置默认值 |
| `backend/app/api/settings.py` | 修改 | 增加 LLM 配置项 + 测试连接 |
| `backend/requirements.txt` | 修改 | 无需新依赖（httpx 已有） |
| `frontend/src/views/ai/AiView.vue` | 重写 | SSE + 确认卡片 + 工具状态 |
| `frontend/src/api/ai.ts` | 重写 | SSE fetch + 确认/拒绝 API |

## 安全考量

1. **写操作确认**：所有 `readonly=False` 的工具执行前必须经过用户确认
2. **命令注入**：`execute_command` 的参数直接传给 SSH，LLM 生成的命令在展示给用户确认时已可见
3. **API Key 保护**：`llm.api_key` 在设置页面查询时脱敏显示（只显示前 8 位 + ***）
4. **权限控制**：AI 聊天接口使用现有 `get_current_api_user` 认证，操作权限复用现有 RBAC
5. **超时控制**：`execute_command` 默认 30 秒超时，LLM API 调用 120 秒超时
