# Model Config Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让模型配置页“测得准、存得稳、密钥可控”，优先修草稿试聊、API Key 掩码、Ollama 空 key、未保存保护；再补体验与结构升级。

**Architecture:** 后端继续以 `llm.profiles` JSON + 激活项双写 `llm.*` 兼容 AI 运行时；本轮先在 settings API 层补齐掩码合并、草稿测试与错误分类。前端 `ModelConfigView` 改为草稿优先：测试/试聊只打草稿接口，保存前用 snapshot 做 dirty 保护。Phase 3 再考虑资源化 API 与页面拆分。

**Tech Stack:** FastAPI, SQLAlchemy, httpx, pytest, Vue 3, TypeScript, Element Plus, Node test runner

**Spec:** `docs/superpowers/specs/2026-07-14-model-config-optimization-design.md`

**Progress (2026-07-14):** Phase 1 done (commit 1e0400c). Phase 2 Tasks 8–10 implemented (rename/clone, model discovery, presets/templates/param UX). Remaining: Phase 3 optional.

---

## 范围分层

| 阶段 | 目标 | 是否本 plan 必做 |
| --- | --- | --- |
| Phase 1 | 正确性 / 安全止血 | 是 |
| Phase 2 | 配置体验增强 | 是，接在 Phase 1 后 |
| Phase 3 | 结构升级 | 可选，单独开干前再确认 |

---

## 文件结构（预期）

### 后端

- Modify: `backend/app/core/settings.py`
- Modify: `backend/app/api/settings.py`
- Create/Modify: `backend/tests/test_llm_profiles.py`（或等价 settings 测试文件）

### 前端

- Modify: `frontend/src/api/settings.ts`
- Modify: `frontend/src/views/ai/ModelConfigView.vue`
- Modify: `frontend/src/views/ai/providerPreset.ts`（如需扩展预设）
- Create: `frontend/tests/modelConfig*.test.mjs` / `frontend/src/views/ai/*.test.mjs`

### 文档

- Spec: `docs/superpowers/specs/2026-07-14-model-config-optimization-design.md`
- Plan: `docs/superpowers/plans/2026-07-14-model-config-optimization.md`

---

## Phase 1 — 止血

### Task 1: 后端 API Key 掩码与合并写入

**Files:**
- Modify: `backend/app/core/settings.py`
- Modify: `backend/app/api/settings.py`
- Create: `backend/tests/test_llm_profiles.py`

- [ ] **Step 1: 写失败测试**

覆盖：

1. `GET /settings/llm/profiles` 返回 `has_api_key` + `api_key_masked`，不返回完整 key
2. `PUT /settings/llm/profiles` 提交空 `api_key` 时保留旧 key
3. `PUT` 提交新 key 时可覆盖
4. 激活项同步到 `llm.api_key` 时写入真实 key，但通用 settings 列表读取需掩码（若本轮一并处理）

示例断言方向：

```python
# 读
assert "sk-secret" not in str(resp.json())
assert item["has_api_key"] is True
assert item["api_key_masked"].startswith("sk-")
assert item.get("api_key") in ("", None)

# 写空 key 不覆盖
# 先写入 profile(api_key="sk-old")
# 再 PUT api_key="" / "__UNCHANGED__"
# DB 中 profiles JSON 与 llm.api_key 仍为 sk-old
```

- [ ] **Step 2: 实现掩码工具**

在 `backend/app/core/settings.py` 或 `backend/app/api/settings.py` 增加：

```python
UNCHANGED_SECRET = "__UNCHANGED__"

def mask_api_key(api_key: str) -> str:
    key = (api_key or "").strip()
    if not key:
        return ""
    if len(key) <= 8:
        return "*" * len(key)
    return f"{key[:3]}****{key[-4:]}"

def merge_profile_secrets(old_profiles: list[dict], new_profiles: list[dict]) -> list[dict]:
    old_by_id = {p.get("id"): p for p in old_profiles if p.get("id")}
    merged = []
    for p in new_profiles:
        item = dict(p)
        incoming = (item.get("api_key") or "").strip()
        if incoming in ("", UNCHANGED_SECRET):
            prev = old_by_id.get(item.get("id")) or {}
            item["api_key"] = prev.get("api_key") or ""
        merged.append(item)
    return merged

def public_profile(profile: dict) -> dict:
    raw_key = profile.get("api_key") or ""
    data = dict(profile)
    data["api_key"] = ""
    data["has_api_key"] = bool(str(raw_key).strip())
    data["api_key_masked"] = mask_api_key(raw_key)
    return data
```

- [ ] **Step 3: 改 GET/PUT profiles**

`api_get_llm_profiles`:

- 读原始 profiles
- map `public_profile`

`api_update_llm_profiles`:

- 先 `get_llm_profiles`
- `merge_profile_secrets`
- `set_llm_profiles`
- 再按 active 同步 `llm.*`
- 审计日志只写“是否修改 api_key”，不写明文

- [ ] **Step 4: 跑测试通过**

```bash
cd backend && python -m pytest tests/test_llm_profiles.py -q
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/settings.py backend/app/api/settings.py backend/tests/test_llm_profiles.py
git commit -m "$(cat <<'EOF'
fix(settings): mask LLM API keys and preserve secrets on update

EOF
)"
```

---

### Task 2: 连接测试支持 Ollama 空 key + 结构化错误

**Files:**
- Modify: `backend/app/api/settings.py`
- Modify: `backend/tests/test_llm_profiles.py`

- [ ] **Step 1: 写失败测试**

覆盖：

1. 本地/Ollama 地址允许空 `api_key`
2. 云端 provider 缺 key 返回 `error_code=validation`
3. 超时 / 连接失败 / 401 映射到对应 `error_code`
4. 成功时返回 `ok/latency_ms/status_code/model`

建议辅助函数：

```python
def is_local_llm(base_url: str, provider: str = "") -> bool:
    u = (base_url or "").lower()
    p = (provider or "").lower()
    return p == "ollama" or "localhost" in u or "127.0.0.1" in u or ":11434" in u
```

- [ ] **Step 2: 改造 `api_test_llm_connection`**

返回统一结构：

```json
{
  "code": 0,
  "msg": "LLM 连接成功",
  "data": {
    "ok": true,
    "latency_ms": 842,
    "status_code": 200,
    "model": "deepseek-chat",
    "error_code": null
  }
}
```

错误码：

- `validation`
- `auth`
- `model_not_found`
- `timeout`
- `connect`
- `protocol`
- `unknown`

规则：

- 必填：`base_url`、`model`
- `api_key`：非本地默认必填；本地/Ollama 可空
- 请求头：有 key 才带 `Authorization`

- [ ] **Step 3: 跑测试**

```bash
cd backend && python -m pytest tests/test_llm_profiles.py -q
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/settings.py backend/tests/test_llm_profiles.py
git commit -m "$(cat <<'EOF'
fix(settings): harden LLM connection test for local models

EOF
)"
```

---

### Task 3: 新增草稿试聊接口 `POST /settings/llm/test-chat`

**Files:**
- Modify: `backend/app/api/settings.py`
- Modify: `backend/tests/test_llm_profiles.py`
- Optional reuse: `backend/app/services/ai/llm_client.py`

- [ ] **Step 1: 写失败测试**

覆盖：

1. 请求体里的 model/base_url 生效，不读取当前激活配置
2. `api_key` 为空且带 `profile_id` 时，可回查已存 key
3. 缺必填字段返回明确错误
4. 成功返回 assistant 文本与耗时；失败返回 error_code

- [ ] **Step 2: 定义请求体**

```python
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
    profile_id: str | None = None
```

约束：

- `message` 去空后必填
- `max_tokens` 服务端 clamp，例如 `min(max_tokens, 512)`
- 不写会话、不落 AI messages 表

- [ ] **Step 3: 实现接口**

推荐路径：

1. resolve key（incoming / unchanged / profile 回查）
2. 用 httpx 直接打 chat/completions 或 responses
3. 返回：

```json
{
  "code": 0,
  "msg": "ok",
  "data": {
    "ok": true,
    "content": "我是运维助手...",
    "latency_ms": 1234,
    "model": "deepseek-chat",
    "error_code": null
  }
}
```

第一版可用非流式，降低复杂度；前端仍可做成“发送中”体验。

- [ ] **Step 4: 权限**

- 与连接测试一致：至少 `settings.view`
- 若后续要更严，可改 `settings.update`

- [ ] **Step 5: 跑测试并 Commit**

```bash
cd backend && python -m pytest tests/test_llm_profiles.py -q
git add backend/app/api/settings.py backend/tests/test_llm_profiles.py
git commit -m "$(cat <<'EOF'
feat(settings): add draft LLM test-chat endpoint

EOF
)"
```

---

### Task 4: 前端 settings API 与类型适配

**Files:**
- Modify: `frontend/src/api/settings.ts`
- Create: `frontend/tests/settingsLlmApi.test.mjs`（可选，若项目惯用纯函数测试则可把序列化辅助抽出来测）

- [ ] **Step 1: 扩展 `LLMProfile` 类型**

```ts
export interface LLMProfile {
  id: string
  name: string
  provider: string
  icon: string
  base_url: string
  api_key: string
  api_key_masked?: string
  has_api_key?: boolean
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

- [ ] **Step 2: 增加 API 方法**

```ts
export function testLLMChat(data: {
  base_url: string
  api_key?: string
  model: string
  api_mode?: 'chat_completions' | 'responses'
  reasoning_effort?: '' | 'low' | 'medium' | 'high'
  temperature?: number
  max_tokens?: number
  top_p?: number
  system_prompt?: string
  message: string
  profile_id?: string
}) {
  return request.post('/settings/llm/test-chat', data)
}
```

- [ ] **Step 3: 保存时规范化 payload**

约定前端保存逻辑：

- 用户未改 key：提交 `api_key: ''` 或 `'__UNCHANGED__'`
- 用户输入新 key：提交新值
- 不把 `api_key_masked` 当作真实 key 回写

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/settings.ts
git commit -m "$(cat <<'EOF'
feat(frontend): extend LLM settings API for masked keys and test-chat

EOF
)"
```

---

### Task 5: ModelConfigView 草稿试聊 + Key 展示语义

**Files:**
- Modify: `frontend/src/views/ai/ModelConfigView.vue`

- [ ] **Step 1: 去掉正式 AI chat 依赖**

删除/停用：

```ts
import { sendAiMessageStream } from '@/api/ai'
```

快速测试改为 `testLLMChat(...)`。

- [ ] **Step 2: Key 输入语义**

- 加载后：`api_key` 置空字符串
- placeholder：
  - `has_api_key`：`已配置 ${api_key_masked}，留空表示不修改`
  - 否则：`sk-xxxxxxxxxxxxxxxx`
- 保存/测试时：
  - 输入为空：传 `''` 或 `__UNCHANGED__`，并带 `profile_id`
  - 输入非空：传新 key

- [ ] **Step 3: 试聊结果文案**

展示：

- 成功/失败
- 耗时
- model
- 若 `isDirty`：标注「基于未保存草稿」
- 若当前 profile 非 active：标注「未设为当前使用」

- [ ] **Step 4: 连接测试结果适配结构化 data**

兼容旧 `msg`，优先展示：

- `连接成功 · 842ms · model=xxx`
- 失败时展示 `error_code` 对应中文引导

- [ ] **Step 5: 手工/自动验证点**

- 编辑未激活 profile 试聊，结果对应该 draft model
- 不改 key 只改 temperature 后保存，后续测试仍可用
- Ollama 空 key 可点测试连接

- [ ] **Step 6: Commit**

```bash
git add frontend/src/views/ai/ModelConfigView.vue frontend/src/api/settings.ts
git commit -m "$(cat <<'EOF'
fix(ai): make model config test against draft profile

EOF
)"
```

---

### Task 6: Dirty 状态与切换保护

**Files:**
- Modify: `frontend/src/views/ai/ModelConfigView.vue`
- Create: `frontend/src/views/ai/modelConfigDirty.test.mjs`（或抽 `serializeProfiles` 纯函数后测）

- [ ] **Step 1: 抽序列化与 dirty 判断（便于测试）**

建议新建小工具，或同文件导出纯函数：

```ts
export function serializeProfiles(profiles: LLMProfile[]): string {
  // 稳定字段顺序；忽略纯展示字段
  return JSON.stringify(profiles.map(p => ({
    id: p.id,
    name: p.name,
    provider: p.provider,
    icon: p.icon,
    base_url: p.base_url,
    api_key: p.api_key || '',
    model: p.model,
    api_mode: p.api_mode || 'chat_completions',
    reasoning_effort: p.reasoning_effort || '',
    temperature: p.temperature,
    max_tokens: p.max_tokens,
    top_p: p.top_p,
    system_prompt: p.system_prompt || '',
    is_active: !!p.is_active,
  })))
}
```

- [ ] **Step 2: 接 snapshot**

```ts
const savedSnapshot = ref('')
const isDirty = computed(() => serializeProfiles(profiles.value) !== savedSnapshot.value)

function markSaved() {
  savedSnapshot.value = serializeProfiles(profiles.value)
}
```

在 `fetchProfiles` 成功、`saveProfiles` 成功后调用 `markSaved()`。

- [ ] **Step 3: 切换/预设/离开拦截**

- `selectProfile`：若 dirty，先 `ElMessageBox.confirm`
- `applyProvider`：同上，或把预设视为对当前 draft 的编辑（不切换 profile 时可直接改，不必确认）
- 路由离开：`onBeforeRouteLeave` 拦截
- 列表项显示「未保存」角标（仅当前 dirty 时对 active 项或整体 header 提示均可，优先简单：页头/当前项）

- [ ] **Step 4: 删除保护**

- 删除激活项时：自动激活相邻项，并 toast 说明
- 至少一个 profile 时才允许删（保持现逻辑）
- 删除后立刻保存或保持 dirty 需统一：建议删除仍调用现有 `saveProfiles()`，成功后 `markSaved()`

- [ ] **Step 5: 测试**

```bash
cd frontend && node --test src/views/ai/modelConfigDirty.test.mjs
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/views/ai/ModelConfigView.vue frontend/src/views/ai/modelConfigDirty.test.mjs
git commit -m "$(cat <<'EOF'
feat(ai): guard unsaved model config changes

EOF
)"
```

---

### Task 7: Phase 1 回归与收口

**Files:**
- 本阶段所有改动文件

- [ ] **Step 1: 后端测试**

```bash
cd backend && python -m pytest tests/test_llm_profiles.py -q
```

- [ ] **Step 2: 前端相关测试**

```bash
cd frontend && node --test tests/providerPreset.test.mjs src/views/ai/modelConfigDirty.test.mjs
```

- [ ] **Step 3: 类型/构建（记录预存失败）**

```bash
cd frontend && npm run build
```

- [ ] **Step 4: 手工验收清单**

1. DeepSeek：填 key → 测试连接成功 → 试聊成功 → 设为当前使用 → AI 页可用
2. Ollama：空 key → 测试连接/试聊可用
3. 编辑未激活配置试聊：不改变 AI 页实际激活模型
4. 不改 key 只改参数保存：key 仍有效
5. 未保存切换 profile：有确认，取消留在原处
6. 网络面板中 profiles GET 无完整 key

- [ ] **Step 5: 如有遗漏，补测后 Commit**

```bash
git add -A
git status
# 仅提交本需求相关文件
```

---

## Phase 2 — 体验

### Task 8: Profile 重命名与复制

**Files:**
- Modify: `frontend/src/views/ai/ModelConfigView.vue`

- [ ] 右侧标题或列表支持直接改 `name`
- [ ] 仅当 name 仍为「新模型」时，保存才自动用 model 覆盖
- [ ] 增加「复制为新配置」：
  - 新 id
  - `is_active=false`
  - `api_key` 输入为空，但 `has_api_key` 继承（保存时靠后端 merge 不够，因为新 id）
  - **注意：** 复制时如果要复用 key，前端需在复制保存时显式带上旧 key，或后端支持 `clone_from`
  - 推荐第一版：复制时前端暂存 `source_profile_id`，保存 payload 带 `api_key: ''` 不够；改为复制时请求后端仍拿不到明文 key
  - **落地决策（本 plan 采用）：** 复制配置时，后端新增可选字段不必要；前端复制后要求用户重填 key，或提供“复制并沿用密钥”时在保存接口增加 `copy_api_key_from: oldId`
- [ ] 实现最小可用方案：

```ts
// 保存单条时可扩展，但当前是全量 PUT
// 约定：复制出的 profile 带字段 copy_api_key_from?: string
// 后端 merge 时若 api_key 空且存在 copy_api_key_from，则从源 profile 拷贝 key
```

- [ ] 补后端 merge 逻辑与测试
- [ ] Commit：`feat(ai): support rename and clone model profiles`

---

### Task 9: 模型列表发现

**Files:**
- Modify: `backend/app/api/settings.py`
- Modify: `frontend/src/api/settings.ts`
- Modify: `frontend/src/views/ai/ModelConfigView.vue`
- Modify: `backend/tests/test_llm_profiles.py`

- [ ] 新增 `POST /settings/llm/models`
- [ ] 代理 `{base_url}/models`
- [ ] 失败返回空列表 + 错误信息，不 500 打断前端
- [ ] 前端模型名改为可搜索下拉 + 自定义输入
- [ ] 拉取按钮：「刷新模型」
- [ ] Commit：`feat(settings): discover LLM models from provider`

---

### Task 10: 预设扩展与参数体验

**Files:**
- Modify: `frontend/src/views/ai/ModelConfigView.vue`
- Modify: `frontend/src/views/ai/providerPreset.ts`
- Modify: `frontend/tests/providerPreset.test.mjs`

- [ ] 增加「OpenAI 兼容 / 中转站」「自定义」预设
- [ ] 可选增加 1~2 个国产兼容站（按产品点名再加，避免无依据堆砌）
- [ ] Temperature 快捷档：0.2 / 0.5 / 0.8
- [ ] Top P 收进高级折叠
- [ ] 系统提示词模板 4 个运维场景
- [ ] 保持 `providerDrafts` 切换记忆
- [ ] Commit：`feat(ai): improve model config presets and parameter UX`

---

## Phase 3 — 结构（可选）

> 进入前先确认：Phase 1/2 已合入且线上无 key 回写事故。

### Task 11: 后端统一 active 解析，移除前端 legacy 迁移

**Files:**
- Modify: `backend/app/core/settings.py`
- Modify: `backend/app/api/settings.py`
- Modify: `frontend/src/views/ai/ModelConfigView.vue`
- Tests: backend settings / ai info

- [ ] `get_llm_config()` 优先从 active profile 读
- [ ] 无 profiles 时 fallback `llm.*`，并可 auto-migrate 成单 profile
- [ ] 删除前端 `migrateFromLegacy()`
- [ ] 回归 AI chat / titles 仍可用
- [ ] Commit：`refactor(settings): resolve active LLM profile on backend`

---

### Task 12: 页面拆分

**Files:**
- Create: `frontend/src/views/ai/model-config/**`
- Modify: router 仍指向聚合页，或改 re-export

- [ ] 拆 `ProfileList` / `ProviderPresetGrid` / `ConnectionForm` / `ModelParamsForm` / `QuickTestPanel`
- [ ] 抽 `useModelConfig.ts`
- [ ] 行为无回归：保存、测试、试聊、激活、dirty
- [ ] Commit：`refactor(ai): split model config view into components`

---

### Task 13: API 资源化（更后）

**Files:**
- Modify: `backend/app/api/settings.py`
- Modify: frontend api + view

- [ ] `POST/PUT/DELETE /settings/llm/profiles/{id}`
- [ ] `POST /settings/llm/profiles/{id}/activate`
- [ ] 前端逐步从全量 PUT 迁移
- [ ] 保留旧全量 PUT 一段时间做兼容
- [ ] Commit：`feat(settings): resourceful LLM profile APIs`

---

## 执行顺序（给执行 agent）

严格按此顺序，避免 key 回写事故：

1. Task 1 掩码与 merge  
2. Task 2 连接测试  
3. Task 3 test-chat  
4. Task 4 前端 API 类型  
5. Task 5 页面试聊/Key 语义  
6. Task 6 dirty 保护  
7. Task 7 Phase 1 回归  
8. Task 8~10 Phase 2  
9. Task 11~13 仅在明确需要时做  

---

## 风险检查清单（每阶段结束都过一遍）

- [ ] GET profiles 响应中搜索不到真实 key 片段
- [ ] 空 key 保存不会把 DB 里的 key 洗成空
- [ ] 试聊不再调用 `/ai/chat`
- [ ] AI 正式对话仍只认激活配置
- [ ] Ollama 空 key 路径前后端文案一致
- [ ] 不相关工作区改动不要塞进本需求 commit

---

## 完成定义（DoD）

### Phase 1 Done

- 草稿试聊与连接测试语义正确
- API Key 掩码 + 不覆盖写入
- Ollama 空 key 可用
- dirty 切换保护可用
- 对应测试通过，手工 6 条验收通过

### Phase 2 Done

- 可重命名/复制
- 模型发现可降级
- 预设与参数体验可用

### Phase 3 Done

- 后端统一 active 解析
- 前端无 legacy 迁移
- 页面已拆分或 API 已资源化（按实际选择项）
