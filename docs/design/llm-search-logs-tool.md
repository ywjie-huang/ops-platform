# LLM `query_logs` 工具设计报告（阶段 3）

| 项目 | 内容 |
|---|---|
| 状态 | 待评审 |
| 日期 | 2026-08-11 |
| 依赖 | ELK 日志检索（已完成：`d8e8077` / `52a8004` / `a46083d` / `a2f560d`） |
| 涉及模块 | `backend/app/services/ai/tools.py`、`backend/app/services/elasticsearch.py` |

> **命名说明**：工具命名为 `query_logs`（而非 `search_logs`）。原因有二：(1) 项目所有只读工具遵循 `query_*` 命名规范（`query_assets` / `query_alerts` / `query_k8s` …）；(2) `services/elasticsearch.py` 中已有的 async 服务函数就叫 `search_logs()`，工具若同名则 handler 内部需 `from ... import search_logs as es_search_logs` 规避，可读性差。底层 `search_logs()` 服务函数保持原名，handler 内部调用它。

---

## 1. 背景与目标

AI 助手现有工具链：`query_assets` / `query_host_metrics` / `query_alerts` / `query_containers` / `query_k8s` / `query_tickets` / `get_patrol_reports`（只读）+ `execute_command` / `run_patrol` / `create_ticket`（写操作，需确认）。

诊断链缺最后一环：模型能看到"CPU 飙了""Pod 在 CrashLoop"，却**看不到任何日志证据**，只能泛泛建议"去查日志"。

**目标**：新增只读工具 `query_logs`，让模型在回答诊断类问题时能自助拉取 ES 日志作为证据，输出"有日志佐证的结论"。

**非目标**：

- 不让模型构造任意 ES 查询（安全边界不变，查询仍在后端白名单构造）
- 不替代日志检索页（人用的深度分析仍在 UI）

## 2. 现状盘点（为什么成本很低）

| 已有设施 | 复用点 |
|---|---|
| `services/elasticsearch.py` | `search_logs()`（async，kw-only：`keyword/namespace/pod/container/host/level/start/end/size/offset`）直接作为 handler 的数据源，返回 `{"total": int, "items": [{timestamp,message,namespace,pod,container,host,level,id,index}]}`；白名单查询构造（`build_query`）不变 |
| `TOOL_DEFINITIONS`（`list[dict]`） | 追加一个 `{"type":"function","function":{...}}` schema |
| `READONLY_TOOLS`（`set[str]`） | 追加字符串 `"query_logs"` |
| `TOOL_PERMISSIONS`（`dict[str,str]`） | 追加 `"query_logs": "monitoring.view"` |
| `TOOL_HANDLERS`（`dict[str,str]`） | 追加 `"query_logs": "app.services.ai.tools.handle_query_logs"` |
| dispatcher 权限校验 | `query_logs → monitoring.view`，与 `api/logs.py:36`（`api_permission_required("monitoring.view")`）及前端 `routes.ts:115`（`meta.permission: 'monitoring.view'`）**同源**，复用业务权限，无需新增权限码；无权限用户问日志自动被拒绝（防 RBAC 绕过） |
| readonly 标记 | dispatcher 对 `query_logs` 返回 `readonly: True`；免确认直接执行的决策在上层对话循环 `services/ai/conversations.py`（dispatcher 本身不区分读写自动执行，只回传标记） |
| handler 返回 str 约定 | 格式化文本喂给模型，与 `handle_query_alerts` 同构；ES 异常路径单独处理（见下） |

**ES 异常路径**：`elasticsearch.py` 通过抛 `ElasticsearchError(detail)` 统一信号——`_conn()` 在 ES URL 为空时抛「Elasticsearch 未配置，请先到「系统管理 → 集成中心」填写服务地址」；所有传输错误（`httpx.TimeoutException`/`ConnectError`/`HTTPStatusError`）在 `_search_with` 统一捕获并 `raise ElasticsearchError(_explain_http_error(exc))`。handler 应 `except ElasticsearchError as e: return e.detail` 直接转述中文提示——否则异常冒泡到 dispatcher 会被套上「工具执行失败:」前缀，提示变差。

前端**零改动**（工具调用过程前端已有展示）。

## 3. 工具 Schema 设计

```json
{
  "type": "function",
  "function": {
    "name": "query_logs",
    "description": "检索 Elasticsearch 中的历史日志（K8s Pod / 容器 / 主机系统日志）。用于故障诊断时获取日志证据：可按关键字、命名空间、Pod、容器、主机、级别过滤，默认查最近 30 分钟。排查告警或容器异常时，建议先用 query_alerts/query_k8s 定位对象，再用本工具查其 error 日志。",
    "parameters": {
      "type": "object",
      "properties": {
        "keyword":   { "type": "string",  "description": "日志内容关键字（短语匹配），如 OutOfMemory、超时、订单号" },
        "namespace": { "type": "string",  "description": "K8s 命名空间（精确匹配）" },
        "pod":       { "type": "string",  "description": "Pod 名称（精确匹配，可含随机后缀）" },
        "container": { "type": "string",  "description": "容器名称（精确匹配）。一个 Pod 多容器时按容器名定位" },
        "host":      { "type": "string",  "description": "主机名（精确匹配）" },
        "level":     { "type": "string",  "description": "日志级别，如 error、warn。诊断异常时建议传 error" },
        "minutes":   { "type": "integer", "description": "向前回溯分钟数，默认 30，最大 1440。分析告警时传 60 覆盖告警滞后" },
        "limit":     { "type": "integer", "description": "返回条数，默认 10，最大 20" }
      }
    }
  }
}
```

**设计决策说明**：

- **`minutes` 相对时间而非 start/end**：模型对"现在几点"没有可靠感知，让它算绝对时间会频繁出错；相对窗口是最不容易犯错的参数形式。handler 内换算为 `end = now.isoformat()`、`start = (now - timedelta(minutes=minutes)).isoformat()`，传给底层 `search_logs(start=, end=)`
- **工具层用 `limit` 而非底层 `size` 命名**：遵循 `query_alerts`/`query_tickets` 等工具的命名习惯（都叫 `limit`）；handler 内 `size = min(int(args.get("limit", 10)), 20)` 后传给 `search_logs(size=...)`
- **`limit` 硬上限 20**：控制 token 预算。20 条 × 截断 300 字符 ≈ 6KB 文本，对上下文友好（底层 `MAX_SIZE=500`，工具层进一步收紧到 20）
- **description 内嵌用法指引**（"先定位对象再查日志""诊断传 error"）：这是 prompt engineering 的主战场，直接决定模型会不会乱调
- **不设 offset**：翻深页对诊断无意义，引导模型改条件而不是翻页

## 4. Handler 设计

`async def handle_query_logs(db, args) -> str`（异步，因底层 `search_logs` 是 async，dispatcher 会 `await`），输出为模型友好的纯文本：

```text
最近 30 分钟内共 1,283 条匹配日志，以下是最近 10 条（级别=error，pod=api-7d9f）：

[2026-08-11 14:23:01] ERROR prod/api-7d9f/server
java.lang.OutOfMemoryError: Java heap space
    at com.example.OrderService.batchInsert(OrderService.java:182)...
（消息已截断，完整内容请到「监控告警 → 日志检索」查看）

[2026-08-11 14:22:58] ERROR ...
```

**每条格式**：`[<timestamp 取年月日时分秒>] <LEVEL 大写> <namespace>/<pod>/<container 或 host>` 换行后跟 `message`（截断 300 字符，多行保留——堆栈对诊断至关重要）。字段全部取自 `search_logs()` 返回的 item（`timestamp/message/namespace/pod/container/host/level`）。

**关键规则**：

| 场景 | 输出策略 |
|---|---|
| 正常 | `总数 + N 条`；每条一行头（时间/级别/namespace/pod/container|host）+ 消息体（截断 300 字符，多行保留） |
| 总数 > limit | 末尾追加引导语：「仅显示最近 N 条。可缩小时间窗或增加过滤条件，或引导用户到日志检索页」 |
| 0 条 | 明确"无匹配"并给建议：「可尝试：扩大 minutes、去掉 level 过滤、检查 pod 名是否完整」——防止模型编造日志 |
| ES 异常 | `except ElasticsearchError as e: return e.detail`——直接转述中文友好提示（含"未配置"场景），不抛异常中断对话。否则异常冒泡到 dispatcher 会被套上「工具执行失败:」前缀，提示变差 |

> **注意**：ES「未配置」不是独立分支，而是 `ElasticsearchError` 的一个实例（`_conn()` 在 URL 为空时抛出），与传输错误走同一条 `except ElasticsearchError` 路径。无需 handler 单独判断 ES 是否配置。

**为什么截断 300 而不是更少**：Java 堆栈的关键信息（异常类 + 第一个 at 行）通常在前 200 字符内；截太短模型只能看到"有 error"而看不到"什么 error"。

**闭环设计**：handler 输出末尾追加日志检索页 URL，模型回答时天然会带上它——用户从 AI 结论一键跳回 UI 看全文。

> **URL 参数契约**（已核对 `LogSearchView.vue:386-402` 的 `initFromRoute()`）：页面读 `keyword/namespace/pod/container/host/level/start/end` 共 8 个 query key——**没有 `minutes`**，时间只能用 `start`/`end`（ISO 字符串）。因此 handler 拼 URL 时时间窗必须换算成 `start=<ISO>&end=<ISO>`，不能写 `&minutes=60`（页面不认）。示例：`/monitoring/logs?pod=api-7d9f&level=error&start=2026-08-11T13:23:00%2B08:00&end=2026-08-11T14:23:00%2B08:00`。

## 5. 权限与安全

- **权限码**：`monitoring.view`，与日志检索页及 `api/logs.py` 三个端点（`/logs/search`、`/logs/histogram`、`/logs/filter-options`）**同源**，复用业务权限，不新增权限码。无权限用户触发时 dispatcher 返回「没有执行该操作所需的权限 (monitoring.view)」，模型如实转述
- **只读**：加入 `READONLY_TOOLS`，免确认直接执行
- **注入面不变**：handler 只接受白名单参数，最终走 `build_query()`——模型无法注入任意 DSL，与 UI 路径同一条防线
- **留痕**：工具调用记录进 AI 会话历史（现有框架行为），可追溯"AI 查了哪些日志"
- **⚠️ 合规决策项（上线前需拍板）**：日志内容会被发送给 LLM 服务商（若使用外部 API）。若日志可能含敏感数据（手机号/身份证/凭据），需决策：
  - 方案 A：日志类诊断引导用户切内网模型 profile（多 profile 框架已支持）
  - 方案 B：handler 内做关键词级脱敏（手机号/邮箱/身份证正则打码，成本低但覆盖有限）
  - 方案 C：接受风险，仅在系统提示词声明

## 6. 端到端流程示例

用户：「`api-7d9f` 这个 Pod 为什么一直重启？」

```text
用户消息
  → 模型规划：需要看 Pod 状态 + 日志
  → tool_call: query_k8s          （确认 Pod 处于 CrashLoopBackOff，重启 14 次）
  → tool_call: query_logs         { pod: "api-7d9f", level: "error", minutes: 60, limit: 10 }
  → 模型综合：「该 Pod 60 分钟内重启 14 次。日志显示每次启动约 2 分钟后
     抛出 OutOfMemoryError（OrderService.java:182 批量插入），
     与内存 limit 512Mi 相关。建议：1) 临时调高 limit 至 1Gi 验证……
     完整日志：[日志检索链接]」
```

## 7. 测试计划

| 层 | 用例 |
|---|---|
| 单测（`test_ai_tools.py` 扩展，函数名 `test_query_logs_*`） | mock `app.services.ai.tools.search_logs`（在 tools 模块内 import 别名），断言 handler 返回子串。覆盖：正常（含截断 300、末尾 URL）、0 条话术、ES 未配置（mock 抛 `ElasticsearchError` 验证返回 `e.detail`）、limit 钳制（传 50 验证底层收到 `size=20`）、`minutes`→`start/end` 换算（断言底层收到的 start/end ISO 间隔正确） |
| 权限（`test_ai_dispatcher_permissions.py` 扩展） | 照搬现有第二个测试模式：`monkeypatch.setattr(dispatcher, "has_permission", fake)` 记录被询问的 code，`dispatch_tool(db=None, tool_name="query_logs", ...)`，断言 `asked["code"] == "monitoring.view"` |
| Mock ES | mock `_search`（或直接 mock tools 模块内导入的 `search_logs`）验证 handler 不依赖真实 ES（与现有测试风格一致） |
| 真实模型走查 | 5 个场景 prompt：Pod 崩溃诊断 / 主机告警关联 / 模糊提问（"最近有啥错误日志"）/ 无权限用户 / ES 未配置——人工评判断言模型行为 |

## 8. 实施步骤与工作量

1. `tools.py`：`TOOL_DEFINITIONS`（list）+1 schema、`READONLY_TOOLS`（set）+1、`TOOL_PERMISSIONS`（dict）+1、`TOOL_HANDLERS`（dict）+1、新增 `async def handle_query_logs`（调 `search_logs`，except `ElasticsearchError`）——**单文件，约 150 行**
2. 测试两个文件各加用例
3. 真实模型走查调 description 措辞（经验活，预留迭代空间）

**预估：半天**，不含模型走查迭代。

## 9. 风险与边界

| 风险 | 缓解 |
|---|---|
| 模型构造糟糕的过滤组合导致查不到 | description 内嵌用法示例；0 条输出自带调整建议 |
| ES 慢查询拖慢对话 | ES 客户端读超时 15s；limit ≤ 20；时间窗 ≤ 1440 分钟 |
| 日志内容撑爆上下文 | 300 字符截断 + 20 条上限 ≈ 6KB 上限 |
| 日志含敏感信息出域 | 见 §5 合规决策项 |
| 模型把"无日志"曲解为"无问题" | 0 条话术明确"仅表示该条件下无匹配"，并在系统提示词层声明（实施时评估是否需要） |

## 10. 后续扩展（本阶段不做，设计上已预留）

- **`log_error_patterns` 工具**：terms 聚合 message 指纹，回答"最近有哪些类型的错误"——聚合结果比原始日志更省 token
- **告警事件排障面板「AI 分析」按钮**：前端把 alert context 拼成预填问题发起对话，模型自动走 `query_alerts → search_logs` 链路
- **巡检报告关联**：`get_patrol_reports` 发现异常后自动带日志证据

