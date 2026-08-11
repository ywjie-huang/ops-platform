# LLM `search_logs` 工具设计报告（阶段 3）

| 项目 | 内容 |
|---|---|
| 状态 | 待评审 |
| 日期 | 2026-08-11 |
| 依赖 | ELK 日志检索（已完成：`d8e8077` / `52a8004` / `a46083d` / `a2f560d`） |
| 涉及模块 | `backend/app/services/ai/tools.py`、`backend/app/services/elasticsearch.py` |

---

## 1. 背景与目标

AI 助手现有工具链：`query_assets` / `query_host_metrics` / `query_alerts` / `query_containers` / `query_k8s` / `query_tickets` / `get_patrol_reports`（只读）+ `execute_command` / `run_patrol` / `create_ticket`（写操作，需确认）。

诊断链缺最后一环：模型能看到"CPU 飙了""Pod 在 CrashLoop"，却**看不到任何日志证据**，只能泛泛建议"去查日志"。

**目标**：新增只读工具 `search_logs`，让模型在回答诊断类问题时能自助拉取 ES 日志作为证据，输出"有日志佐证的结论"。

**非目标**：

- 不让模型构造任意 ES 查询（安全边界不变，查询仍在后端白名单构造）
- 不替代日志检索页（人用的深度分析仍在 UI）

## 2. 现状盘点（为什么成本很低）

| 已有设施 | 复用点 |
|---|---|
| `services/elasticsearch.py` | `search_logs()` 直接作为 handler 的数据源，白名单查询构造不变 |
| `TOOL_DEFINITIONS` / `TOOL_HANDLERS` / `READONLY_TOOLS` / `TOOL_PERMISSIONS` | 四张表各加一行即完成注册 |
| dispatcher 权限校验 | `search_logs → monitoring.view`，无权限用户问日志自动被拒绝（防 RBAC 绕过） |
| readonly 自动执行流 | 只读工具无需确认，SSE 直接流式返回 |
| handler 返回 str 约定 | 格式化文本喂给模型，与 `handle_query_alerts` 同构 |

前端**零改动**（工具调用过程前端已有展示）。

## 3. 工具 Schema 设计

```json
{
  "type": "function",
  "function": {
    "name": "search_logs",
    "description": "检索 Elasticsearch 中的历史日志（K8s Pod / 容器 / 主机系统日志）。用于故障诊断时获取日志证据：可按关键字、命名空间、Pod、主机、级别过滤，默认查最近 30 分钟。排查告警或容器异常时，建议先用 query_alerts/query_k8s 定位对象，再用本工具查其 error 日志。",
    "parameters": {
      "type": "object",
      "properties": {
        "keyword":   { "type": "string",  "description": "日志内容关键字（短语匹配），如 OutOfMemory、超时、订单号" },
        "namespace": { "type": "string",  "description": "K8s 命名空间（精确匹配）" },
        "pod":       { "type": "string",  "description": "Pod 名称（精确匹配，可含随机后缀）" },
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

- **`minutes` 相对时间而非 start/end**：模型对"现在几点"没有可靠感知，让它算绝对时间会频繁出错；相对窗口是最不容易犯错的参数形式。handler 内换算为 `[now-minutes, now]`
- **`limit` 硬上限 20**：控制 token 预算。20 条 × 截断 300 字符 ≈ 6KB 文本，对上下文友好
- **description 内嵌用法指引**（"先定位对象再查日志""诊断传 error"）：这是 prompt engineering 的主战场，直接决定模型会不会乱调
- **不设 offset**：翻深页对诊断无意义，引导模型改条件而不是翻页

## 4. Handler 设计

`handle_search_logs(db, args) -> str`（异步），输出为模型友好的纯文本：

```text
最近 30 分钟内共 1,283 条匹配日志，以下是最近 10 条（级别=error，pod=api-7d9f）：

[08-11 14:23:01] ERROR prod/api-7d9f/server
java.lang.OutOfMemoryError: Java heap space
    at com.example.OrderService.batchInsert(OrderService.java:182)...
（消息已截断，完整内容请到「监控告警 → 日志检索」查看）

[08-11 14:22:58] ERROR ...
```

**关键规则**：

| 场景 | 输出策略 |
|---|---|
| 正常 | `总数 + N 条`；每条一行头（时间/级别/来源）+ 消息体（截断 300 字符，多行保留——堆栈对诊断至关重要） |
| 总数 > limit | 末尾追加引导语：「仅显示最近 N 条。可缩小时间窗或增加过滤条件，或引导用户到日志检索页」 |
| 0 条 | 明确"无匹配"并给建议：「可尝试：扩大 minutes、去掉 level 过滤、检查 pod 名是否完整」——防止模型编造日志 |
| ES 未配置 | 固定话术：「日志服务未配置，请引导用户到系统管理 → 集成中心配置 Elasticsearch」 |
| ES 异常 | `ElasticsearchError.detail` 原文返回（已是中文友好提示），不抛异常中断对话 |

**为什么截断 300 而不是更少**：Java 堆栈的关键信息（异常类 + 第一个 at 行）通常在前 200 字符内；截太短模型只能看到"有 error"而看不到"什么 error"。

**闭环设计**：handler 输出附带检索页 URL 参数形式（`/monitoring/logs?pod=...&level=error`），模型回答时天然会带上它——用户从 AI 结论一键跳回 UI 看全文。

## 5. 权限与安全

- **权限码**：`monitoring.view`（与日志检索页一致）。无权限用户触发时 dispatcher 返回「没有执行该操作所需的权限」，模型如实转述
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
  → tool_call: search_logs        { pod: "api-7d9f", level: "error", minutes: 60, limit: 10 }
  → 模型综合：「该 Pod 60 分钟内重启 14 次。日志显示每次启动约 2 分钟后
     抛出 OutOfMemoryError（OrderService.java:182 批量插入），
     与内存 limit 512Mi 相关。建议：1) 临时调高 limit 至 1Gi 验证……
     完整日志：[日志检索链接]」
```

## 7. 测试计划

| 层 | 用例 |
|---|---|
| 单测（`test_ai_tools.py` 扩展） | 参数映射正确性；`minutes` 换算；消息截断；0 条话术；ES 未配置话术；limit 上限钳制 |
| 权限（`test_ai_dispatcher_permissions.py` 扩展） | 无 `monitoring.view` 用户调用被拒 |
| Mock ES | mock `_search` 验证 handler 不依赖真实 ES（与现有测试风格一致） |
| 真实模型走查 | 5 个场景 prompt：Pod 崩溃诊断 / 主机告警关联 / 模糊提问（"最近有啥错误日志"）/ 无权限用户 / ES 未配置——人工评判断言模型行为 |

## 8. 实施步骤与工作量

1. `tools.py`：`TOOL_DEFINITIONS` +1、`READONLY_TOOLS` +1、`TOOL_PERMISSIONS` +1、`TOOL_HANDLERS` +1、新增 `handle_search_logs`（异步，调 `search_logs`）——**单文件，约 150 行**
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

