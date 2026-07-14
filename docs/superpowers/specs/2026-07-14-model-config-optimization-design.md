# 模型配置页优化设计

## 背景

当前智能中心已提供「模型配置」页（`frontend/src/views/ai/ModelConfigView.vue`），支持：

- 多套 LLM Profile 管理
- OpenAI / DeepSeek / 通义千问 / Ollama 预设
- Chat Completions / Responses 双模式
- 连接测试与页面内快速试聊
- 激活配置同步回写 `llm.*` 兼容字段

整体骨架可用，但在正确性、安全与运维配置体验上仍有明显短板，影响用户对配置是否生效的判断，也存在密钥明文暴露风险。

## 目标

在不打断现有 AI 助手主流程的前提下，把模型配置页做成：

1. **测得准**：测试/试聊验证的是当前编辑中的配置，而不是碰巧激活的那套。
2. **存得稳**：未保存变更可感知、可拦截，避免误切换丢失。
3. **密钥可控**：API Key 不在读接口明文回显，写回时支持不修改密钥。
4. **配得快**：服务商预设、模型发现、错误分类降低首次配置失败率。
5. **结构可演进**：短期止血，中期体验，长期资源化与组件拆分。

## 非目标

- 不在本轮重做 AI 聊天主界面。
- 不引入完整计费/配额系统。
- 不强制迁移到外部 KMS（可预留接口）。
- 不在本轮支持非 OpenAI 兼容协议（如原生 Anthropic / Gemini），仅保留扩展点。

## 现状结论

| 维度 | 现状 | 问题 |
| --- | --- | --- |
| 试聊 | 调用正式 `sendAiMessageStream` | 实际测的是后端激活配置，不是当前编辑 draft |
| API Key | `GET /settings/llm/profiles` 明文返回 | 权限用户可见全部密钥；审计/抓包风险高 |
| 连接测试 | 强制要求 `api_key` | 与 Ollama 可留空文案冲突 |
| 切换保护 | 无 dirty 检查 | 切换 Profile / 套用预设可能丢未保存修改 |
| 预设 | 4 家固定 | 中转站、Azure、国产云覆盖不足 |
| 模型名 | 纯手填 | 易填错；无 `/models` 发现 |
| 存储 | `llm.profiles` JSON 全量替换 + 激活项双写 `llm.*` | 前端仍承担 legacy 迁移；并发覆盖风险 |
| 页面结构 | 单文件约 1300 行 | 逻辑、样式、交互耦合，难测难迭代 |

## 设计原则

1. **草稿优先**：编辑区是 source of truth；保存前任何测试都应对草稿生效。
2. **激活显式**：只有“设为当前使用 / 保存并激活”才影响 AI 正式对话。
3. **密钥最小暴露**：读掩码、写可选覆盖、日志不落明文。
4. **失败可诊断**：连接错误要分类，而不是只回一段截断文本。
5. **渐进增强**：先修正确性与安全，再补体验，最后做结构升级。
6. **兼容运行时**：AI 助手继续通过 `get_llm_config()` 读取激活配置，短期不改主对话链路。

## 推荐方案总览

采用三阶段演进：

```text
Phase 1 止血
  - 草稿试聊 / 连接测试
  - API Key 掩码
  - Ollama 空 key
  - dirty 未保存保护

Phase 2 体验
  - Profile 重命名/复制
  - 模型列表发现
  - 错误分类与延迟指标
  - 预设扩展 + prompt 模板 + 参数快捷档

Phase 3 结构
  - profiles 资源化 API
  - 后端统一 active 解析与 legacy 迁移
  - 页面组件拆分
  - 健康状态 / 场景绑定 / 导入导出
```

## Phase 1：止血（正确性 / 安全）

### 1.1 草稿级连接测试与试聊

#### 问题

页面顶部「测试连接」虽传当前表单，但「快速测试」走 AI 正式聊天接口，后端使用已激活配置。用户编辑未激活 Profile 时，试聊结果会误导。

#### 方案

面向“当前草稿”的后端能力：

| 接口 | 作用 |
| --- | --- |
| `POST /api/v1/settings/test-connection/llm` | 已有；修正空 key 规则与返回结构 |
| `POST /api/v1/settings/llm/test-chat` | 新增；对草稿配置发一条短消息并返回 |

前端规则：

- 快速试聊**禁止**再调用 `sendAiMessageStream`
- 试聊 payload 直接取当前 `activeProfile` 表单值
- 若配置未保存，结果区标注「基于未保存草稿」
- 若测试的不是激活项，标注「未设为当前使用」

`test-chat` 请求体建议：

```json
{
  "base_url": "https://api.deepseek.com/v1",
  "api_key": "sk-xxx 或空或 __UNCHANGED__",
  "model": "deepseek-chat",
  "api_mode": "chat_completions",
  "reasoning_effort": "",
  "temperature": 0.7,
  "max_tokens": 256,
  "top_p": 1.0,
  "system_prompt": "",
  "message": "请用一句话介绍你自己",
  "profile_id": "optional-for-key-resolve"
}
```

说明：

- `api_key` 为空且 `profile_id` 存在时，后端可回查已存密钥（配合掩码方案）。
- 试聊默认限制 `max_tokens` 上限，避免误用大输出浪费额度。

### 1.2 API Key 掩码与不覆盖写入

#### 读

`GET /settings/llm/profiles` 不再返回明文 key，改为：

```json
{
  "id": "abc",
  "name": "DeepSeek",
  "api_key_masked": "sk-****xyz",
  "has_api_key": true,
  "api_key": ""
}
```

兼容策略：

- 前端统一使用 `has_api_key` + 展示 `api_key_masked`
- 输入框 placeholder 在已有 key 时显示「已配置，留空表示不修改」

#### 写

`PUT /settings/llm/profiles` 约定：

| 前端提交的 `api_key` | 后端行为 |
| --- | --- |
| 非空新值 | 更新为新密钥 |
| 空字符串 / 省略 / `__UNCHANGED__` | 保留原密钥 |
| 显式清除标记（可选后续） | 清空密钥 |

实现要点：

- 后端按 `profile.id` 合并旧 key，禁止“全量明文回写”造成误清空
- 通用 settings 列表中的 `llm.api_key` 同样掩码
- 审计日志只记录“是否变更密钥”，不记录密钥内容

### 1.3 Ollama / 本地模型空 Key

连接测试校验改为：

```text
必填：base_url、model
api_key：
  - provider in {ollama} 或 base_url 指向本地常见地址时允许为空
  - 其他 provider 默认必填
```

前端：

- Ollama 预设继续提示可留空
- 非本地 provider 在保存/测试前校验 key（新建且 `has_api_key=false` 时）

### 1.4 Dirty 状态与切换保护

状态模型：

```ts
const savedSnapshot = ref<string>('')
const isDirty = computed(() => serialize(profiles.value) !== savedSnapshot.value)
```

交互：

- 切换左侧 Profile、应用服务商预设、路由离开前：若当前草稿 dirty，弹确认
- 左侧列表对未保存项显示「未保存」角标
- 新增 Profile 后立即进入编辑态，并标记 dirty
- 保存成功后刷新 snapshot

删除保护：

- 不允许删到 0 个激活配置后静默失效
- 若删除的是激活项，要求先指定新激活项，或自动激活相邻项并明确提示

## Phase 2：体验增强

### 2.1 Profile 管理补齐

| 能力 | 行为 |
| --- | --- |
| 重命名 | 列表双击或右侧标题可编辑；不再只靠模型名自动覆盖 |
| 复制 | 「复制为新配置」：复制除 id/is_active 外字段，key 默认复用 |
| 排序 | 可选拖拽；第一版可用上移/下移 |
| 空状态 | 无配置时引导选择服务商，一键创建首个 Profile |

名称规则：

- 新增默认名：`新模型`
- 仅当名称仍是默认名且用户填写了 model 时，保存可自动改为 model
- 用户手动改名后不再自动覆盖

### 2.2 服务商预设扩展

保留现有 4 家，新增：

- OpenAI 兼容 / 中转站（通用）
- Azure OpenAI（预留 endpoint / deployment / api-version 字段）
- Moonshot / 智谱 / 硅基流动 等常见国产兼容站（按产品需要裁剪）

预设行为：

- 点击预设：填充推荐 `base_url`、默认 `model`、`api_mode`
- 继续使用现有 `providerDrafts` 记忆，避免来回切换丢失手工修改
- 明确「自定义」卡片，provider=`custom`

### 2.3 模型发现

新增：

```http
POST /api/v1/settings/llm/models
{
  "base_url": "...",
  "api_key": "... 或 __UNCHANGED__",
  "profile_id": "optional"
}
```

后端代理请求 `{base_url}/models`，返回简化列表：

```json
{
  "items": [
    { "id": "deepseek-chat", "owned_by": "deepseek" }
  ]
}
```

前端：

- 模型名字段改为「可搜索下拉 + 允许自定义输入」
- 拉取失败时静默降级为纯输入，不阻断保存
- 缓存按 `base_url + has_api_key` 短时记忆，避免频繁请求

### 2.4 连接测试结构化结果

统一返回：

```json
{
  "ok": true,
  "latency_ms": 842,
  "status_code": 200,
  "model": "deepseek-chat",
  "error_code": null,
  "message": "LLM 连接成功"
}
```

失败时 `error_code` 枚举：

| code | 含义 | 前端引导 |
| --- | --- | --- |
| `validation` | 参数不完整 | 补全必填项 |
| `auth` | 401/403 | 检查 API Key |
| `model_not_found` | 模型不存在 | 检查模型名 / 拉取模型列表 |
| `timeout` | 超时 | 检查网络/代理/地址 |
| `connect` | DNS/连接失败 | 检查 base_url 可达性 |
| `protocol` | 非预期响应 | 检查接口模式 / 兼容性 |
| `unknown` | 其他 | 展示截断详情 |

页面展示：

- 成功：连接成功 · 842ms · model=xxx
- 失败：分类标题 + 可展开原始详情

### 2.5 参数与提示词体验

- Temperature 快捷档：`精确 0.2` / `均衡 0.5` / `发散 0.8`
- Max Tokens 支持输入框精确编辑；滑条保留
- Top P 默认收进「高级参数」折叠区
- 系统提示词提供模板：
  - 通用运维助手
  - 故障排查
  - 巡检报告解读
  - 工单撰写

### 2.6 测试区信息架构

| 动作 | 目的 | 位置 |
| --- | --- | --- |
| 测试连接 | 鉴权 + 协议可达 | 页头主按钮 |
| 快速试聊 | 体感质量 / 延迟 | 底部测试卡片 |

试聊结果至少展示：

- 是否成功
- 总耗时
- 首 token 耗时（若流式）
- 使用的 model
- 是否草稿 / 是否激活配置

## Phase 3：结构升级

### 3.1 后端配置模型收口

短期兼容：

```text
llm.profiles = [ {...}, {...} ]
active profile 同步到 llm.base_url / llm.api_key / ...
get_llm_config() 继续读平铺字段
```

中期目标：

```text
get_llm_config(db):
  profiles = get_llm_profiles(db)
  active = first is_active or None
  if active: return normalize(active)
  fallback to legacy llm.* fields
  optional: auto-migrate legacy -> profiles
```

原则：

- legacy 迁移逻辑从**前端**移到**后端**
- 前端不再调用 `getSettings()` 做 profile 拼装
- AI 运行时始终只认“激活配置”

长期可选：

- 独立表 `llm_profiles`
- 字段：`id, name, provider, base_url, api_key_encrypted, model, api_mode, reasoning_effort, temperature, max_tokens, top_p, system_prompt, is_active, last_tested_at, last_test_ok, latency_ms, created_at, updated_at`

### 3.2 API 资源化

在全量 PUT 稳定后，逐步提供：

```http
GET    /settings/llm/profiles
POST   /settings/llm/profiles
GET    /settings/llm/profiles/{id}
PUT    /settings/llm/profiles/{id}
DELETE /settings/llm/profiles/{id}
POST   /settings/llm/profiles/{id}/activate
POST   /settings/llm/test-connection
POST   /settings/llm/test-chat
POST   /settings/llm/models
```

权限：

- 读：`settings.view`（或后续 `ai.config.view`）
- 写/激活：`settings.update`（或后续 `ai.config.manage`）

### 3.3 前端拆分

建议目录：

```text
frontend/src/views/ai/model-config/
  ModelConfigView.vue
  components/
    ProfileList.vue
    ProviderPresetGrid.vue
    ConnectionForm.vue
    ModelParamsForm.vue
    QuickTestPanel.vue
  composables/
    useModelConfig.ts
    useProfileDirty.ts
  types.ts
```

`useModelConfig.ts` 负责：

- 加载 / 保存 / 激活 / 删除 / 复制
- 连接测试 / 试聊
- 模型列表
- dirty 与 snapshot

### 3.4 可选产品能力

按需开启，不阻塞前两阶段：

1. **健康状态**：记录 `last_tested_at / last_ok / latency_ms`，列表用状态点展示
2. **场景绑定**：`usage: default | title | tool`，标题生成与主对话可分模型
3. **导入导出**：导出不含 key 的 JSON；导入后单独补 key
4. **代理与自定义 Header**：适配内网中转与特殊网关鉴权
5. **调用统计**：近 7 日成功率 / 次数（依赖 AI 调用日志）

## 关键交互流程

### 新建并激活一套模型

```text
进入模型配置
  -> 点击新增 或 选择服务商预设
  -> 填 base_url / key / model
  -> 测试连接（草稿）
  -> 可选快速试聊（草稿）
  -> 保存配置
  -> 设为当前使用
  -> 页头状态变为“已配置”
```

### 编辑已有配置但不切换激活

```text
选择非激活 Profile
  -> 修改参数
  -> 测试连接 / 试聊（明确基于草稿/该 Profile）
  -> 保存
  -> AI 正式对话仍使用原激活项，直到用户点击“设为当前使用”
```

### 密钥更新

```text
打开已有 Profile
  -> key 输入框为空，placeholder 显示已配置掩码
  -> 若用户不改 key，保存时提交空/__UNCHANGED__
  -> 后端保留原 key
  -> 若用户输入新 key，则覆盖
```

## 数据契约

### Profile 对外字段（读）

```ts
interface LLMProfileView {
  id: string
  name: string
  provider: string
  icon: string
  base_url: string
  api_key_masked: string
  has_api_key: boolean
  model: string
  api_mode: 'chat_completions' | 'responses'
  reasoning_effort: '' | 'low' | 'medium' | 'high'
  temperature: number
  max_tokens: number
  top_p: number
  system_prompt: string
  is_active: boolean
  // Phase 3 optional
  last_tested_at?: string | null
  last_test_ok?: boolean | null
  latency_ms?: number | null
}
```

### Profile 写入字段

```ts
interface LLMProfileWrite {
  id: string
  name: string
  provider: string
  icon: string
  base_url: string
  api_key?: string // 空/__UNCHANGED__ 表示不修改
  model: string
  api_mode?: 'chat_completions' | 'responses'
  reasoning_effort?: '' | 'low' | 'medium' | 'high'
  temperature: number
  max_tokens: number
  top_p: number
  system_prompt: string
  is_active: boolean
}
```

## 前端状态机（简版）

```text
idle
  -> loading profiles
  -> ready
      -> editing (dirty=true)
          -> saving
              -> ready / error
          -> testing
              -> ready + testResult
          -> chatting
              -> ready + chatResult
      -> activating
          -> ready
```

约束：

- `saving/testing/chatting` 期间禁用冲突操作
- `dirty=true` 时切换需确认
- 激活成功后刷新 `configured` 与列表状态点

## 安全与审计

1. 任何 GET 配置接口不返回完整 API Key
2. 更新接口支持密钥不覆盖语义，防止前端用掩码/空值洗白密钥
3. 审计日志记录：
   - 操作者
   - profile id / name
   - 动作：create/update/delete/activate/test
   - 是否修改了 api_key
   - 不记录 key 明文、不记录完整试聊内容（可记截断 message）
4. `test-chat` / `test-connection` 需登录且具备 settings 权限
5. 服务端对 `base_url` 做基础校验（http/https）；内网地址是否允许按现网策略决定

## 兼容性

| 场景 | 处理 |
| --- | --- |
| 旧数据只有 `llm.*` 平铺字段 | 后端迁移为单条 active profile（从前端迁移逻辑上收） |
| 旧前端仍提交明文 api_key | 后端继续接受；有值则更新 |
| AI 主对话 | 继续读激活配置，不依赖 profiles 列表接口 |
| Ollama 无 key | 测试与运行时都允许空 key |

## 测试计划

### 后端

- profiles 读取返回掩码，不含明文 key
- 更新时空 key 不覆盖旧 key
- 更新时新 key 可覆盖
- Ollama / 本地地址允许空 key 测试成功路径
- 非本地 provider 缺 key 时返回 `validation` / 明确错误
- `test-connection` 错误码分类
- `test-chat` 使用请求体配置，而非当前激活配置
- 激活项同步到 `llm.*` 字段
- legacy 平铺配置可被迁移/读取

### 前端

- 切换 dirty profile 弹出确认
- 试聊不调用正式 AI chat API
- 已有 key 时输入框展示“已配置，留空不修改”
- 保存后 dirty 清除
- 删除激活项时的保护/自动激活逻辑
- 模型列表失败时降级为手填
- provider 预设切换保留手工 draft（沿用 `providerPreset` 测试）

### 手工验收

1. 配 DeepSeek：测试连接成功，试聊返回内容，设为当前使用后 AI 页可用
2. 配 Ollama 无 key：测试连接与试聊可用
3. 编辑未激活配置并试聊：结果对应该草稿模型，不影响当前 AI 会话所用模型
4. 不改 key 只改 temperature 后保存：key 仍有效
5. 未保存切换 profile：有确认，取消则留在原处

## 落地节奏与验收

### Phase 1（优先，1–2 天）

验收：

- [ ] 快速试聊验证的是当前草稿配置
- [ ] API Key 读接口掩码，写接口可保留旧值
- [ ] Ollama 空 key 可测试
- [ ] 未保存切换有保护
- [ ] 相关单测/接口测通过

### Phase 2（3–5 天）

验收：

- [ ] 支持重命名、复制
- [ ] 模型发现可用且可降级
- [ ] 连接测试展示延迟与错误分类
- [ ] 预设/模板/参数快捷档提升配置效率

### Phase 3（按需）

验收：

- [ ] profiles API 资源化或后端统一 active 解析完成
- [ ] 前端迁移逻辑移除
- [ ] 页面完成组件拆分
- [ ] 可选能力按开关/需求交付

## 建议实施顺序（执行清单）

1. **修试聊与测试语义**：草稿配置专用 test-chat；页面文案区分草稿/激活
2. **密钥掩码合并写入**：后端读掩码 + 写时 merge；前端 placeholder 与空值语义
3. **Ollama 空 key**：前后端校验对齐
4. **dirty 保护**：snapshot + 离开/切换确认
5. **连接结果结构化**：latency + error_code
6. **模型发现与 Profile 复制/重命名**
7. **预设与参数体验**
8. **后端收口 legacy + 前端拆分**

## 风险与缓解

| 风险 | 影响 | 缓解 |
| --- | --- | --- |
| 掩码改造导致旧前端保存时清空 key | 生产 AI 不可用 | 后端 merge 旧 key；加回归测试 |
| 试聊接口被滥用刷模型额度 | 成本上升 | 权限控制、短 max_tokens、频率限制（可后续） |
| `/models` 兼容性差 | 体验回退 | 失败降级手填，不阻断主流程 |
| 全量 PUT 并发覆盖 | 多人同时改配置互相覆盖 | Phase 3 资源化；短期可接受单管理员场景 |
| base_url 指向内网被 SSRF | 安全风险 | 沿用现网策略；必要时加 allowlist/blocklist |

## 成功标准

优化完成后，模型配置页应满足：

1. 用户能确信“我测过的配置，就是我即将启用的配置”
2. 管理员打开页面不会在网络响应里看到完整 API Key
3. 本地 Ollama 与云端 API 都能按预期完成测试
4. 误切换/误关闭不再轻易丢失未保存修改
5. 新增服务商或拆分组件时，不必继续堆进单文件巨型页面

## 涉及文件（预期）

### 前端

- `frontend/src/views/ai/ModelConfigView.vue`
- `frontend/src/views/ai/providerPreset.ts`
- `frontend/src/api/settings.ts`
- 后续拆分目录 `frontend/src/views/ai/model-config/*`
- 测试：`frontend/tests/providerPreset.test.mjs` 及新增 model-config 相关测试

### 后端

- `backend/app/api/settings.py`
- `backend/app/core/settings.py`
- 可选：`backend/app/services/ai/llm_client.py`（复用连接/试聊）
- 新增/补充 tests：settings llm profiles / test-connection / test-chat

### 文档

- 本设计：`docs/superpowers/specs/2026-07-14-model-config-optimization-design.md`
- 若进入开发，再补 plan：`docs/superpowers/plans/2026-07-14-model-config-optimization.md`
