# AI 助手重写设计文档

## 目标

完全重写 AI 助手功能，采用 IDE 分栏式浅色主题 UI，支持通用聊天 + 运维工具调用 + 自主多步规划。

## 架构

### 后端 (FastAPI)

- **SSE 流式对话** — LLM 响应通过 Server-Sent Events 推送到前端
- **OpenAI 兼容工具调用** — function calling 格式，LLM 决定调用哪些工具
- **多步 Agent** — LLM 可自主规划多步操作（查 CPU → 查进程 → 给结论）
- **写操作确认** — 执行命令、巡检、创建工单需用户确认
- **对话持久化** — 存储到数据库，支持历史对话列表

### 前端 (Vue 3 + Element Plus)

- **IDE 分栏布局** — 左侧对话列表 + 右侧聊天区
- **浅色主题** — 白色背景，清爽风格
- **Markdown 渲染** — 表格、代码块、列表、引用块
- **工具面板** — 内联在消息流中，显示参数/结果/耗时
- **快捷操作** — AI 回复下方的建议操作按钮

## UI 设计

### 左侧栏 (200px)
- 搜索框
- 新建对话按钮
- 对话历史列表（高亮当前对话，显示最后活跃时间）

### 右侧聊天区
- 消息流：用户消息（蓝色左边框）+ AI 消息
- 工具面板：绿色成功/黄色确认，显示工具名+参数+结果+耗时
- AI 文本回复：markdown 渲染，建议引用块，快捷操作按钮
- 输入区：自适应高度，Enter 发送，Shift+Enter 换行

## 数据模型

### conversations 表
- id, title, created_at, updated_at

### messages 表
- id, conversation_id, role (user/assistant), content, created_at

## API 端点

- `POST /api/v1/ai/chat` — 发送消息，SSE 流式返回
- `POST /api/v1/ai/chat/confirm` — 确认写操作
- `POST /api/v1/ai/chat/reject` — 拒绝写操作
- `GET /api/v1/ai/conversations` — 获取对话列表
- `GET /api/v1/ai/conversations/{id}/messages` — 获取对话消息
- `DELETE /api/v1/ai/conversations/{id}` — 删除对话
- `GET /api/v1/ai/info` — 获取模型配置信息

## SSE 事件格式

```
event: text
data: {"type":"text","content":"部分文本"}

event: tool_start
data: {"type":"tool_start","tool":"query_assets","args":{...}}

event: tool_result
data: {"type":"tool_result","tool":"query_assets","result":"..."}

event: tool_confirm
data: {"type":"tool_confirm","tool":"execute_command","description":"...","pending_id":"..."}

event: done
data: {"type":"done","conversation_id":"..."}

event: error
data: {"type":"error","content":"错误信息"}
```

## 工具定义

保留现有 10 个工具，返回纯数据格式（LLM 自行决定输出格式）。

## 技术栈

- **后端**: FastAPI, SQLAlchemy, PyMySQL, SSE
- **前端**: Vue 3, Element Plus, marked, highlight.js, Pinia
- **LLM**: OpenAI 兼容 API（可配置 base_url/api_key/model）
