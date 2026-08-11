<template>
  <div>
    <!-- Page Header -->
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">模型配置</h2>
        <span v-if="configured" class="status-tag success">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
          已配置
        </span>
        <span v-else class="status-tag info">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
          未配置
        </span>
        <span v-if="isDirty" class="status-tag info">未保存</span>
      </div>
      <div class="header-right">
        <button class="btn" :class="{ 'is-loading': testing }" :disabled="testing" @click="handleTest">
          <svg v-if="!testing" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>
          <div v-else class="spinner"></div>
          测试连接
        </button>
        <button class="btn btn-primary" :class="{ 'is-loading': saving }" :disabled="saving" @click="handleSave">
          <svg v-if="!saving" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>
          <div v-else class="spinner"></div>
          保存配置
        </button>
      </div>
    </div>

    <!-- 测试结果提示 -->
    <div v-if="testResult !== null" class="alert" :class="testResult ? 'alert-success' : 'alert-error'" style="margin-bottom: 16px;">
      <svg v-if="testResult" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
      <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
      <div>
        <strong>{{ testResult ? '连接成功' : '连接失败' }}</strong>
        <div v-if="testResultMsg">{{ testResultMsg }}</div>
      </div>
      <button class="btn-text" @click="testResult = null" style="margin-left: auto;">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      </button>
    </div>

    <!-- 主布局：左侧列表 + 右侧配置 -->
    <div class="main-layout">

      <!-- LEFT: 模型列表 -->
      <ProfileList
        :profiles="profiles"
        :active-profile-id="activeProfileId"
        :loading="loadingProfiles"
        :is-dirty="isDirty"
        :has-active="!!activeProfile"
        @select="selectProfile"
        @add="handleAddProfile"
        @clone="handleCloneProfile"
      />

      <!-- RIGHT: 配置面板 -->
      <div class="config-panel" v-if="activeProfile">
        <ProviderPresetGrid
          :profile="activeProfile"
          :providers="providers"
          @select="applyProvider"
          @api-mode-change="handleApiModeChange"
        />
        <ConnectionForm
          :profile="activeProfile"
          :form-errors="formErrors"
          :api-key-placeholder="apiKeyPlaceholder"
          :provider-changed="providerChanged"
          :loading-models="loadingModels"
          :model-options="modelOptions"
          :model-list-tip="modelListTip"
          @validate="validateField"
          @refresh-models="handleRefreshModels"
        />
        <ModelParamsForm
          :profile="activeProfile"
          :temperature-presets="temperaturePresets"
          :prompt-templates="promptTemplates"
          @apply-prompt="applyPromptTemplate"
        />
        <QuickTestPanel
          v-model="testInput"
          :messages="testMessages"
          :sending="testSending"
          :result="testChatResult"
          @send="handleTestChat"
        />

        <!-- 操作栏 -->
        <div class="action-bar">
          <div class="action-bar-left">
            <button class="btn" @click="handleCloneProfile">
              复制此配置
            </button>
            <button
              v-if="profiles.length > 1"
              class="btn btn-danger"
              @click="handleDeleteProfile"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
              删除此配置
            </button>
          </div>
          <div class="action-bar-right">
            <button
              v-if="!activeProfile.is_active"
              class="btn btn-success"
              @click="handleSetActive"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
              设为当前使用
            </button>
            <span v-else class="tag tag-active">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
              当前使用中
            </span>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-else class="card empty-panel">
        <svg class="empty-panel-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
        <p>请从左侧选择或新增一个模型配置</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getLLMProfiles,
  updateLLMProfiles,
  testLLMConnection,
  testLLMChat,
  listLLMModels,
  toLLMProfileWritePayload,
  formatLLMTestMessage,
  type LLMProfile,
} from '@/api/settings'
import {
  PROVIDER_PRESETS,
  SYSTEM_PROMPT_TEMPLATES,
  TEMPERATURE_PRESETS,
  resolveProviderDraft,
  snapshotProviderDraft,
} from './providerPreset'
import {
  serializeProfiles,
  normalizeLoadedProfiles,
  isLocalProvider,
} from './modelConfigState'
import ProfileList from './model-config/components/ProfileList.vue'
import ProviderPresetGrid from './model-config/components/ProviderPresetGrid.vue'
import ConnectionForm from './model-config/components/ConnectionForm.vue'
import ModelParamsForm from './model-config/components/ModelParamsForm.vue'
import QuickTestPanel from './model-config/components/QuickTestPanel.vue'

// ── 服务商预设 / 模板 ──
const providers = PROVIDER_PRESETS
const promptTemplates = SYSTEM_PROMPT_TEMPLATES
const temperaturePresets = TEMPERATURE_PRESETS

// ── 状态 ──
const loading = ref(false)
const loadingProfiles = ref(false)
const saving = ref(false)
const testing = ref(false)
const configured = ref(false)
const testResult = ref<boolean | null>(null)
const testResultMsg = ref('')
const savedSnapshot = ref('')
const loadingModels = ref(false)
const modelOptions = ref<Array<{ id: string; owned_by: string }>>([])
const modelListTip = ref('')

const profiles = ref<LLMProfile[]>([])
const activeProfileId = ref<string | null>(null)
const providerDrafts = reactive<Record<string, ReturnType<typeof snapshotProviderDraft>>>({})

const activeProfile = computed(() => profiles.value.find(p => p.id === activeProfileId.value) || null)
const isDirty = computed(() => serializeProfiles(profiles.value) !== savedSnapshot.value)

// 记录每个 profile 上次保存/加载时的 provider，用于检测「服务商是否被改过」。
// 切换服务商后旧 api_key 不再适用，UI 需提示用户重新填写。
const savedProviderById = reactive<Record<string, string>>({})
// 当前激活 profile 是否在加载/保存后又被改了服务商
const providerChanged = computed(() => {
  const p = activeProfile.value
  if (!p) return false
  const saved = savedProviderById[p.id]
  // 新建的 profile 没记录过，不算变更
  if (saved === undefined) return false
  return saved !== p.provider
})

const apiKeyPlaceholder = computed(() => {
  const p = activeProfile.value
  if (!p) return 'sk-xxxxxxxxxxxxxxxx'
  // 服务商变更后，旧 key 不再适用，提示重新填写
  if (providerChanged.value) return '服务商已变更，请填写新服务商的 API Key'
  if (p.has_api_key) {
    return p.api_key_masked
      ? `已配置 ${p.api_key_masked}，留空表示不修改`
      : '已配置，留空表示不修改'
  }
  return 'sk-xxxxxxxxxxxxxxxx'
})

// ── 表单验证 ──
const formErrors = reactive<Record<string, string>>({
  base_url: '',
  model: '',
})

function validateField(field: string) {
  if (field === 'base_url') {
    formErrors.base_url = activeProfile.value?.base_url.trim() ? '' : '请输入 API 地址'
  } else if (field === 'model') {
    formErrors.model = activeProfile.value?.model.trim() ? '' : '请输入模型名称'
  }
}

function validateForm(): boolean {
  validateField('base_url')
  validateField('model')
  return !formErrors.base_url && !formErrors.model
}

// ── 快速测试 ──
const testInput = ref('')
const testSending = ref(false)
const testMessages = ref<Array<{ role: string; content: string }>>([])
const testChatResult = ref<{ ok: boolean; msg: string } | null>(null)

// ── 工具函数 ──

function generateId(): string {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 6)
}

function markSaved() {
  savedSnapshot.value = serializeProfiles(profiles.value)
  // 同步每个 profile 的 provider 快照，用于 providerChanged 判定
  for (const p of profiles.value) {
    savedProviderById[p.id] = p.provider
  }
}

async function confirmDiscardIfDirty(actionLabel = '切换'): Promise<boolean> {
  if (!isDirty.value) return true
  try {
    await ElMessageBox.confirm(
      `当前配置尚未保存，确认${actionLabel}并丢弃修改？`,
      '未保存的更改',
      { type: 'warning', confirmButtonText: '丢弃修改', cancelButtonText: '继续编辑' },
    )
    return true
  } catch {
    return false
  }
}

function draftCredentialPayload(p: LLMProfile) {
  return {
    base_url: p.base_url.trim(),
    api_key: (p.api_key || '').trim(),
    model: p.model.trim(),
    api_mode: p.api_mode || 'chat_completions',
    reasoning_effort: (p.reasoning_effort || '') as '' | 'low' | 'medium' | 'high',
    provider: p.provider || '',
    profile_id: p.id,
  }
}

// ── 数据加载 ──
async function fetchProfiles() {
  loadingProfiles.value = true
  try {
    const res: any = await getLLMProfiles()
    profiles.value = normalizeLoadedProfiles(res.data?.items || [])

    // 默认选中激活的（legacy 迁移由后端 ensure_llm_profiles_migrated 处理）
    const active = profiles.value.find(p => p.is_active)
    activeProfileId.value = active?.id || profiles.value[0]?.id || null
    configured.value = !!active
    markSaved()
  } finally {
    loadingProfiles.value = false
  }
}



// ── 保存 profiles ──
async function saveProfiles() {
  saving.value = true
  try {
    const res: any = await updateLLMProfiles(toLLMProfileWritePayload(profiles.value))
    const items = res.data?.items
    if (Array.isArray(items) && items.length) {
      const selectedId = activeProfileId.value
      profiles.value = normalizeLoadedProfiles(items)
      activeProfileId.value =
        profiles.value.find(p => p.id === selectedId)?.id ||
        profiles.value.find(p => p.is_active)?.id ||
        profiles.value[0]?.id ||
        null
    } else {
      // 兼容旧响应：保存后本地清空输入的 key，并标记 has_api_key
      profiles.value = profiles.value.map((p) => ({
        ...p,
        has_api_key: !!(p.api_key || '').trim() || !!p.has_api_key,
        api_key: '',
        copy_api_key_from: undefined,
      }))
    }
    configured.value = profiles.value.some(p => p.is_active)
    markSaved()
    ElMessage.success('配置已保存')
  } finally {
    saving.value = false
  }
}

// ── 选择配置 ──
async function selectProfile(p: LLMProfile) {
  if (p.id === activeProfileId.value) return
  if (!(await confirmDiscardIfDirty('切换配置'))) return
  const targetId = p.id
  if (isDirty.value) {
    // 用户确认丢弃后，重新加载已保存状态
    await fetchProfiles()
  }
  activeProfileId.value =
    profiles.value.find(item => item.id === targetId)?.id ||
    profiles.value[0]?.id ||
    null
  testResult.value = null
  testMessages.value = []
  testChatResult.value = null
  formErrors.base_url = ''
  formErrors.model = ''
  modelOptions.value = []
  modelListTip.value = ''
}

// ── 新增配置 ──
function handleAddProfile() {
  const newProfile: LLMProfile = {
    id: generateId(),
    name: '新模型',
    provider: 'custom',
    icon: '⚡',
    base_url: '',
    api_key: '',
    has_api_key: false,
    model: '',
    temperature: 0.7,
    max_tokens: 4096,
    top_p: 1.0,
    system_prompt: '',
    is_active: false,
  }
  profiles.value.push(newProfile)
  activeProfileId.value = newProfile.id
  modelOptions.value = []
  modelListTip.value = ''
  testResult.value = null
  testMessages.value = []
  testChatResult.value = null
}

// ── 复制配置 ──
function handleCloneProfile() {
  if (!activeProfile.value) return
  const src = activeProfile.value
  const cloned: LLMProfile = {
    ...src,
    id: generateId(),
    name: `${src.name || '配置'} 副本`,
    api_key: '',
    is_active: false,
    // 保存时由后端从源 profile 拷贝真实密钥
    has_api_key: !!src.has_api_key,
    api_key_masked: src.api_key_masked || '',
    copy_api_key_from: src.has_api_key ? src.id : undefined,
  }
  profiles.value.push(cloned)
  activeProfileId.value = cloned.id
  modelOptions.value = []
  modelListTip.value = src.has_api_key
    ? '已复制配置；保存后将沿用源配置密钥'
    : '已复制配置'
  testResult.value = null
  testMessages.value = []
  testChatResult.value = null
  ElMessage.success('已复制为新配置（未保存）')
}

function applyPromptTemplate(content: string) {
  if (!activeProfile.value) return
  activeProfile.value.system_prompt = content
}

async function handleRefreshModels() {
  if (!activeProfile.value) return
  const p = activeProfile.value
  if (!p.base_url.trim()) {
    ElMessage.warning('请先填写 API 地址')
    return
  }
  if (!(p.api_key || '').trim() && !p.has_api_key && !isLocalProvider(p)) {
    ElMessage.warning('请先填写 API Key')
    return
  }
  loadingModels.value = true
  modelListTip.value = ''
  try {
    const res: any = await listLLMModels({
      base_url: p.base_url.trim(),
      api_key: (p.api_key || '').trim(),
      provider: p.provider || '',
      api_mode: p.api_mode || 'chat_completions',
      profile_id: p.id,
    })
    const items = res.data?.items || []
    modelOptions.value = items
    if (res.data?.ok && items.length) {
      modelListTip.value = `已拉取 ${items.length} 个模型，可输入筛选或点选`
      if (!p.model && items[0]?.id) {
        p.model = items[0].id
      }
    } else {
      modelOptions.value = []
      modelListTip.value = res.msg || '未能拉取模型列表，请手动输入模型名'
    }
  } catch (e: any) {
    modelOptions.value = []
    modelListTip.value = e?.message || '拉取模型失败，请手动输入'
  } finally {
    loadingModels.value = false
  }
}

// ── 删除配置 ──
async function handleDeleteProfile() {
  if (!activeProfile.value) return
  await ElMessageBox.confirm(`确定删除配置「${activeProfile.value.name}」？`, '确认删除', {
    type: 'warning',
  })
  const deleting = activeProfile.value
  const idx = profiles.value.findIndex(p => p.id === activeProfileId.value)
  profiles.value.splice(idx, 1)
  const next = profiles.value[Math.min(idx, profiles.value.length - 1)] || null
  activeProfileId.value = next?.id || null
  if (deleting.is_active && next && !next.is_active) {
    profiles.value.forEach(p => { p.is_active = p.id === next.id })
    ElMessage.info(`已自动将「${next.name}」设为当前使用`)
  }
  await saveProfiles()
}

// ── 设为当前使用 ──
async function handleSetActive() {
  if (!activeProfile.value) return
  if (isDirty.value) {
    // 激活前先保存当前草稿，避免激活的是旧值
    if (!validateForm()) return
    profiles.value.forEach(p => { p.is_active = p.id === activeProfileId.value })
    await saveProfiles()
    return
  }
  profiles.value.forEach(p => { p.is_active = p.id === activeProfileId.value })
  await saveProfiles()
}

// ── 应用服务商预设 ──
function applyProvider(p: typeof providers[number]) {
  if (!activeProfile.value) return
  if (activeProfile.value.provider) {
    providerDrafts[activeProfile.value.provider] = snapshotProviderDraft(activeProfile.value)
  }
  const draft = resolveProviderDraft({
    nextPreset: p,
    rememberedDraft: providerDrafts[p.id],
  })
  activeProfile.value.provider = p.id
  activeProfile.value.icon = p.icon
  // 仅默认名时跟随预设名，避免覆盖用户自定义名称
  if (!activeProfile.value.name || activeProfile.value.name === '新模型' || providers.some(x => x.name === activeProfile.value?.name)) {
    activeProfile.value.name = p.name
  }
  activeProfile.value.base_url = draft.base_url
  activeProfile.value.model = draft.model
  activeProfile.value.api_mode = draft.api_mode
  activeProfile.value.reasoning_effort = draft.reasoning_effort
  testResult.value = null
  formErrors.base_url = ''
  formErrors.model = ''
}

function handleApiModeChange() {
  if (!activeProfile.value) return
  if (activeProfile.value.api_mode === 'responses') {
    activeProfile.value.reasoning_effort = activeProfile.value.reasoning_effort || 'medium'
  } else {
    activeProfile.value.reasoning_effort = ''
  }
}

// ── 保存按钮 ──
async function handleSave() {
  if (!activeProfile.value) return
  if (!validateForm()) {
    // 校验失败时给出明确提示，避免「点保存没反应」
    const missing: string[] = []
    if (formErrors.base_url) missing.push('API 地址')
    if (formErrors.model) missing.push('模型名称')
    ElMessage.warning(`请填写必填项：${missing.join('、')}`)
    return
  }
  // 自动更新名称
  if (activeProfile.value.name === '新模型' && activeProfile.value.model) {
    activeProfile.value.name = activeProfile.value.model
  }
  await saveProfiles()
}

// ── 测试连接 ──
async function handleTest() {
  if (!activeProfile.value) return
  const p = activeProfile.value
  if (!p.base_url.trim() || !p.model.trim()) {
    ElMessage.warning('请至少填写 API 地址和模型名称')
    return
  }
  if (providerChanged.value && !(p.api_key || '').trim() && !isLocalProvider(p)) {
    ElMessage.warning('服务商已变更，请填写新服务商的 API Key')
    return
  }
  if (!(p.api_key || '').trim() && !p.has_api_key && !isLocalProvider(p)) {
    ElMessage.warning('请填写 API Key')
    return
  }
  testing.value = true
  testResult.value = null
  try {
    const res: any = await testLLMConnection(draftCredentialPayload(p))
    testResult.value = res.data?.ok ?? false
    if (res.data) {
      testResultMsg.value = formatLLMTestMessage(
        { ...res.data, msg: res.msg },
        res.msg || (testResult.value ? '连接成功' : '连接失败'),
      )
      if (!testResult.value && res.msg && !String(testResultMsg.value).includes(res.msg)) {
        testResultMsg.value = `${testResultMsg.value}${res.msg ? `（${res.msg}）` : ''}`
      }
    } else {
      testResultMsg.value = res.msg || ''
    }
  } catch {
    testResult.value = false
    testResultMsg.value = '请求失败，请检查网络或配置'
  } finally {
    testing.value = false
  }
}

// ── 快速测试聊天（草稿配置） ──
async function handleTestChat() {
  if (!testInput.value.trim() || testSending.value || !activeProfile.value) return
  const p = activeProfile.value
  if (!p.base_url.trim() || !p.model.trim()) {
    ElMessage.warning('请至少填写 API 地址和模型名称')
    return
  }
  if (providerChanged.value && !(p.api_key || '').trim() && !isLocalProvider(p)) {
    ElMessage.warning('服务商已变更，请填写新服务商的 API Key')
    return
  }
  if (!(p.api_key || '').trim() && !p.has_api_key && !isLocalProvider(p)) {
    ElMessage.warning('请填写 API Key')
    return
  }

  const msg = testInput.value.trim()
  testInput.value = ''
  testMessages.value.push({ role: 'user', content: msg })
  testSending.value = true
  testChatResult.value = null


  try {
    const res: any = await testLLMChat({
      ...draftCredentialPayload(p),
      temperature: p.temperature,
      max_tokens: Math.min(p.max_tokens || 256, 512),
      top_p: p.top_p,
      system_prompt: p.system_prompt || '',
      message: msg,
    })
    const ok = !!res.data?.ok
    const content = res.data?.content || ''
    const latency = res.data?.latency_ms
    const tags: string[] = []
    if (isDirty.value) tags.push('未保存草稿')
    if (!p.is_active) tags.push('未设为当前使用')
    if (ok && content) {
      testMessages.value.push({ role: 'assistant', content })
      testChatResult.value = {
        ok: true,
        msg: [
          '试聊成功',
          latency != null ? `${latency}ms` : null,
          `model=${p.model}`,
          ...tags,
        ].filter(Boolean).join(' · '),
      }
    } else {
      testChatResult.value = {
        ok: false,
        msg: formatLLMTestMessage(res.data, res.msg || '试聊失败') + (tags.length ? ` · ${tags.join(' · ')}` : ''),
      }
    }
  } catch (e: any) {
    testChatResult.value = { ok: false, msg: e?.message || '请求失败' }
  } finally {
    testSending.value = false

  }
}


onBeforeRouteLeave(async (_to, _from, next) => {
  if (!isDirty.value) {
    next()
    return
  }
  const ok = await confirmDiscardIfDirty('离开页面')
  next(ok)
})

onMounted(fetchProfiles)

</script>

<style scoped>
/* ── SVG Icon System ── */
.icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}

/* ── Page Header ── */
.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.header-right {
  display: flex;
  gap: 8px;
}

/* ── Status Tag ── */
.status-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}
.status-tag.success { background: var(--success-bg, #f0fdf4); color: var(--success-color, #16a34a); border: 1px solid var(--success-border, #bbf7d0); }
.status-tag.info { background: #f8fafc; color: #64748b; border: 1px solid #e2e8f0; }
.status-tag.error { background: var(--error-bg, #fef2f2); color: var(--error-color, #dc2626); border: 1px solid var(--error-border, #fecaca); }

/* ── Buttons ── */
.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid var(--border-color);
  background: var(--surface-color);
  color: var(--text-primary);
  transition: all 0.15s;
}
.btn:hover { border-color: #c0c4cc; }
.btn:focus-visible {
  outline: 2px solid var(--primary-color);
  outline-offset: 2px;
}
.btn-primary {
  background: var(--primary-color);
  color: white;
  border-color: var(--primary-color);
}
.btn-primary:hover { background: var(--primary-hover); }
.btn-danger {
  background: var(--error-bg, #fef2f2);
  color: var(--error-color, #dc2626);
  border-color: var(--error-border, #fecaca);
}
.btn-danger:hover { background: #fee2e2; }
.btn-success {
  background: var(--success-bg, #f0fdf4);
  color: var(--success-color, #16a34a);
  border-color: var(--success-border, #bbf7d0);
}
.btn-success:hover { background: #dcfce7; }
.btn-text { border: none; background: none; color: var(--primary-color); padding: 4px 8px; }
.btn-text:hover { background: var(--primary-bg); }
.btn-sm { padding: 4px 12px; font-size: 12px; }
.btn:disabled, .btn.is-loading {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ── Cards ── */
.card {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: 20px;
}

/* ── Main Layout ── */
.main-layout {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 16px;
  align-items: start;
}

/* ── Empty State ── */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px 16px;
  text-align: center;
  gap: 8px;
}
.empty-state-icon {
  width: 40px;
  height: 40px;
  color: var(--text-muted);
  opacity: 0.5;
}
.empty-state-text {
  font-size: 13px;
  color: var(--text-muted);
}
.empty-panel {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  gap: 12px;
}
.empty-panel-icon {
  width: 48px;
  height: 48px;
  color: #d9d9d9;
}
.empty-panel p { font-size: 14px; color: var(--text-muted); }

/* ── Config Panel ── */
.config-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ── Section Title ── */
.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 8px;
}
.section-title svg { color: var(--text-secondary); }

/* ── Card Content ── */
.card-content {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-top: 12px;
}

/* ── Form Styles ── */
.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.form-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 4px;
}
.form-label .required { color: var(--error-color, #dc2626); }
.form-input {
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  font-size: 13px;
  font-family: inherit;
  transition: border-color 0.15s, box-shadow 0.15s;
  background: var(--surface-color);
  color: var(--text-primary);
}
.form-input:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 0 2px rgba(94, 106, 210, 0.1);
}
.form-input:focus-visible {
  outline: 2px solid var(--primary-color);
  outline-offset: 1px;
}
.form-input::placeholder { color: var(--text-muted); }
.form-input.error {
  border-color: var(--error-color, #dc2626);
  box-shadow: 0 0 0 2px rgba(220, 38, 38, 0.1);
}
.form-tip {
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1.4;
}
.form-error {
  font-size: 12px;
  color: var(--error-color, #dc2626);
  line-height: 1.4;
  display: flex;
  align-items: center;
  gap: 4px;
}

/* ── Inline Tag ── */
.tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 0 8px;
  height: 22px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
}
.tag-default { background: #f5f5f5; color: var(--text-secondary); }
.tag-active { background: var(--primary-bg); color: var(--primary-color); }

/* ── Alert Banner ── */
.alert {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 10px 14px;
  border-radius: 6px;
  font-size: 13px;
  line-height: 1.4;
}
.alert svg { flex-shrink: 0; margin-top: 1px; }
.alert-success { background: var(--success-bg, #f0fdf4); color: var(--success-color, #16a34a); border: 1px solid var(--success-border, #bbf7d0); }
.alert-error { background: var(--error-bg, #fef2f2); color: var(--error-color, #dc2626); border: 1px solid var(--error-border, #fecaca); }

/* ── Loading Spinner ── */
.spinner {
  width: 14px;
  height: 14px;
  border: 2px solid var(--border-color);
  border-top-color: var(--primary-color);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ── Action Bar ── */
.action-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.action-bar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}


.profile-list-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}
.action-bar-left {
  display: flex;
  align-items: center;
  gap: 8px;
}
/* ── Responsive ── */
@media (max-width: 900px) {
  .main-layout { grid-template-columns: 1fr; }
  .form-row { grid-template-columns: 1fr; }
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #d9d9d9; border-radius: 3px; }

/* ── Reduced Motion ── */
@media (prefers-reduced-motion: reduce) {
  * {
    animation: none !important;
    transition: none !important;
  }
}
</style>
