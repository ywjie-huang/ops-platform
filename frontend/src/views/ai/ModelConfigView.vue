<template>
  <div class="mc-root">
    <!-- 页头：只留标题 + 脏状态 -->
    <div class="mc-head">
      <h1 class="mc-title">模型配置</h1>
      <span v-if="isDirty" class="tag warn"><span class="dot"></span>未保存更改</span>
    </div>

    <div class="layout">
      <!-- 左：配置列表 -->
      <ProfileList
        :profiles="profiles"
        :active-profile-id="activeProfileId"
        :dirty-ids="dirtyIds"
        :loading="loadingProfiles"
        @select="selectProfile"
        @add="handleAddProfile"
        @clone="handleCloneProfile"
        @remove="handleDeleteProfile"
      />

      <!-- 中：配置列（独立滚动） -->
      <div class="config-col" v-if="activeProfile">
        <ProviderPresetGrid
          :profile="activeProfile"
          :providers="providers"
          @select="applyProvider"
        />
        <ConnectionForm
          :profile="activeProfile"
          :form-errors="formErrors"
          :api-key-placeholder="apiKeyPlaceholder"
          :provider-changed="providerChanged"
          :loading-models="loadingModels"
          :model-options="modelOptions"
          :model-list-tip="modelListTip"
          :testing="testing"
          :test-result="testResult"
          :test-result-msg="testResultMsg"
          @validate="validateField"
          @refresh-models="handleRefreshModels"
          @api-mode-change="handleApiModeChange"
          @test="handleTest"
          @close-result="testResult = null"
        />
        <ModelParamsForm
          :profile="activeProfile"
          :temperature-presets="temperaturePresets"
          :prompt-templates="promptTemplates"
          @apply-prompt="applyPromptTemplate"
        />

        <!-- 粘性操作底栏 -->
        <div class="action-bar">
          <div class="ab-left">
            <button v-if="profiles.length > 1" class="btn btn-danger" type="button" @click="handleDeleteProfile()">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
              删除此配置
            </button>
            <button class="btn" type="button" @click="handleCloneProfile()">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
              复制
            </button>
            <span v-if="isDirty" class="ab-dirty"><span class="dot"></span>{{ dirtyIds.length }} 项未保存</span>
          </div>
          <div class="ab-right">
            <button v-if="!activeProfile.is_active" class="btn btn-success" type="button" @click="handleSetActive">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
              设为当前使用
            </button>
            <span v-else class="using-chip">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
              当前使用中
            </span>
            <button class="btn btn-primary" type="button" :disabled="saving" @click="handleSave">
              <svg v-if="!saving" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>
              <span v-else class="spinner"></span>
              保存配置 <span class="kbd">Ctrl S</span>
            </button>
          </div>
        </div>
      </div>

      <!-- 空态向导 -->
      <div class="config-col" v-else-if="!loadingProfiles">
        <div class="card wiz-card">
          <div class="wiz-hero">
            <div class="wiz-title">从选择一个服务商开始</div>
            <div class="wiz-sub">选择预设会自动填入推荐地址与模型，你只需粘贴 API Key</div>
          </div>
          <div class="wiz-steps">
            <div class="step"><div class="n">1</div><b>选择服务商</b><span>预设覆盖国际 / 国内主流与本地部署</span></div>
            <div class="step"><div class="n">2</div><b>填写密钥</b><span>粘贴 API Key；本地 Ollama 可留空</span></div>
            <div class="step"><div class="n">3</div><b>测试并保存</b><span>一键测试连接，成功后保存并设为使用中</span></div>
          </div>
          <div class="pv-tiles">
            <button
              v-for="p in providers"
              :key="p.id"
              type="button"
              class="pv-tile"
              @click="handleWizardSelect(p)"
            >
              <span class="pv-logo" :class="{ 'has-img': !!logoOf(p.id) }">
                <img v-if="logoOf(p.id)" :src="logoOf(p.id)" :alt="p.name" />
                <template v-else>{{ p.icon }}</template>
              </span>
              <span class="pv-t-text">
                <span class="pv-t-name">{{ p.name }}</span>
                <span class="pv-t-hint">{{ p.hint }}</span>
              </span>
            </button>
          </div>
        </div>
      </div>

      <!-- 右：常驻快速测试栏 -->
      <QuickTestPanel
        v-if="activeProfile"
        class="test-col"
        v-model="testInput"
        :messages="testMessages"
        :sending="testSending"
        :result="testChatResult"
        :subtitle="activeProfile.name + ' · ' + (dirtyIds.includes(activeProfile.id) ? '草稿' : '已保存')"
        @send="handleTestChat"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onActivated, onDeactivated, onBeforeUnmount } from 'vue'
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
import { providerLogoOf } from './providerLogos'
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
const logoOf = providerLogoOf

// ── 状态 ──
const loadingProfiles = ref(false)
const saving = ref(false)
const testing = ref(false)
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

// 逐项脏标记：每个 profile 与上次保存/加载时的序列化对比（新增未保存的也算脏）
const savedSnapshotById = reactive<Record<string, string>>({})
const dirtyIds = computed(() =>
  profiles.value
    .filter(p => savedSnapshotById[p.id] !== serializeProfiles([p]))
    .map(p => p.id),
)

// 记录每个 profile 上次保存/加载时的 provider，用于检测「服务商是否被改过」。
// 切换服务商后旧 api_key 不再适用，UI 需提示用户重新填写。
const savedProviderById = reactive<Record<string, string>>({})
const providerChanged = computed(() => {
  const p = activeProfile.value
  if (!p) return false
  const saved = savedProviderById[p.id]
  if (saved === undefined) return false
  return saved !== p.provider
})

const apiKeyPlaceholder = computed(() => {
  const p = activeProfile.value
  if (!p) return 'sk-xxxxxxxxxxxxxxxx'
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
    formErrors.base_url = (activeProfile.value?.base_url || '').trim() ? '' : '请输入 API 地址'
  } else if (field === 'model') {
    formErrors.model = (activeProfile.value?.model || '').trim() ? '' : '请输入模型名称'
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
  for (const p of profiles.value) {
    savedSnapshotById[p.id] = serializeProfiles([p])
    savedProviderById[p.id] = p.provider
  }
  // 已删除的 id 不再保留快照
  for (const id of Object.keys(savedSnapshotById)) {
    if (!profiles.value.some(p => p.id === id)) delete savedSnapshotById[id]
  }
  for (const id of Object.keys(savedProviderById)) {
    if (!profiles.value.some(p => p.id === id)) delete savedProviderById[id]
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
    base_url: (p.base_url || '').trim(),
    api_key: (p.api_key || '').trim(),
    model: (p.model || '').trim(),
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

// ── 新增配置（第一个配置自动设为使用中） ──
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
    is_active: profiles.value.length === 0,
  }
  profiles.value.push(newProfile)
  activeProfileId.value = newProfile.id
  modelOptions.value = []
  modelListTip.value = ''
  testResult.value = null
  testMessages.value = []
  testChatResult.value = null
}

// ── 空态向导：选服务商 = 新增 + 应用预设 ──
function handleWizardSelect(preset: typeof providers[number]) {
  handleAddProfile()
  applyProvider(preset)
}

// ── 复制配置（可指定源，默认当前激活项） ──
function handleCloneProfile(source?: LLMProfile) {
  const src = source || activeProfile.value
  if (!src) return
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
  if (!(p.base_url || '').trim()) {
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
      base_url: (p.base_url || '').trim(),
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

// ── 删除配置（可指定目标，默认当前激活项；删除使用中配置时自动顺延） ──
async function handleDeleteProfile(target?: LLMProfile) {
  const victim = target || activeProfile.value
  if (!victim || profiles.value.length <= 1) return
  try {
    await ElMessageBox.confirm(`确定删除配置「${victim.name}」？`, '确认删除', { type: 'warning' })
  } catch {
    return
  }
  const idx = profiles.value.findIndex(p => p.id === victim.id)
  profiles.value.splice(idx, 1)
  const next = profiles.value[Math.min(idx, profiles.value.length - 1)] || null
  if (victim.is_active && next) {
    profiles.value.forEach(p => { p.is_active = p.id === next.id })
    ElMessage.info(`已自动将「${next.name}」设为当前使用`)
  }
  if (activeProfileId.value === victim.id) {
    activeProfileId.value = next?.id || null
  }
  await saveProfiles()
}

// ── 设为当前使用 ──
async function handleSetActive() {
  if (!activeProfile.value) return
  if (isDirty.value && !validateForm()) return
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
  if (!activeProfile.value || saving.value) return
  if (!validateForm()) {
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
  if (!(p.base_url || '').trim() || !(p.model || '').trim()) {
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
  if (!(p.base_url || '').trim() || !(p.model || '').trim()) {
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

// ── Ctrl+S 快捷保存（keep-alive 下随激活状态挂载/卸载） ──
function onKeydown(e: KeyboardEvent) {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
    e.preventDefault()
    handleSave()
  }
}
onActivated(() => window.addEventListener('keydown', onKeydown))
onDeactivated(() => window.removeEventListener('keydown', onKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))

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
/* ── mockup 设计令牌（局部覆盖，不影响其他页面） ── */
.mc-root {
  --surface-2: #f6f6f8;
  --border-strong: #e2e2e6;
  --radius: 10px;
  --success-bg: rgba(34, 197, 94, 0.11);
  --warning-bg: rgba(245, 166, 35, 0.13);
  --danger-bg: rgba(229, 72, 77, 0.1);

  height: calc(100vh - var(--header-height) - 40px);
  display: flex;
  flex-direction: column;
  gap: 14px;
}

/* ── 页头 ── */
.mc-head { flex: none; display: flex; align-items: center; gap: 10px; }
.mc-title { font-size: 17px; font-weight: 750; color: var(--text-primary); }
.tag {
  display: inline-flex; align-items: center; gap: 5px; padding: 3px 11px;
  border-radius: 999px; font-size: 12px; font-weight: 600;
}
.tag.warn { color: #b45309; background: var(--warning-bg); border: 1px solid rgba(245, 166, 35, 0.32); }
.tag .dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }

/* ── 三栏布局 ── */
.layout {
  flex: 1; min-height: 0; display: grid;
  grid-template-columns: 268px minmax(0, 1fr) 330px; gap: 16px;
  width: 100%; max-width: 1760px; margin: 0 auto;
}
.config-col {
  min-height: 0; overflow-y: auto; display: flex; flex-direction: column;
  gap: 14px; padding: 2px 6px 2px 2px;
}

/* ── 粘性操作底栏 ── */
.action-bar {
  position: sticky; bottom: 10px; z-index: 15;
  display: flex; align-items: center; justify-content: space-between; gap: 10px;
  background: rgba(255, 255, 255, 0.94); backdrop-filter: blur(8px);
  border: 1px solid var(--border-strong); border-radius: 11px; padding: 10px 12px;
  box-shadow: 0 10px 28px -14px rgba(17, 17, 17, 0.28); flex: none;
}
.ab-left, .ab-right { display: flex; align-items: center; gap: 8px; position: relative; }
.using-chip {
  display: inline-flex; align-items: center; gap: 5px; font-size: 12px; font-weight: 700;
  color: #15803d; background: var(--success-bg); border: 1px solid rgba(34, 197, 94, 0.25);
  padding: 6px 11px; border-radius: 7px;
}
.using-chip svg { width: 12px; height: 12px; }
.ab-dirty {
  font-size: 11.5px; color: #b45309; font-weight: 600;
  display: inline-flex; align-items: center; gap: 5px; margin-left: 4px;
}
.ab-dirty .dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
.kbd {
  font: 700 10px ui-monospace, Menlo, Consolas, monospace; padding: 2px 5px; border-radius: 4px;
  border: 1px solid rgba(255, 255, 255, 0.4); background: rgba(255, 255, 255, 0.16);
  color: #fff; letter-spacing: 0.02em;
}

/* ── 按钮 ── */
.btn {
  display: inline-flex; align-items: center; gap: 6px; padding: 7px 14px; border-radius: 7px;
  font-size: 12.5px; font-weight: 600; cursor: pointer; border: 1px solid var(--border-strong);
  background: var(--surface-color); color: var(--text-primary); transition: all 0.15s; font-family: inherit;
}
.btn:hover { border-color: #c9c9cf; transform: translateY(-1px); box-shadow: 0 3px 8px rgba(17, 17, 17, 0.07); }
.btn:active { transform: none; box-shadow: none; }
.btn:disabled { opacity: 0.55; cursor: not-allowed; transform: none; box-shadow: none; }
.btn:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 2px; }
.btn svg { width: 13px; height: 13px; }
.btn-primary { background: var(--primary-color); border-color: var(--primary-color); color: #fff; }
.btn-primary:hover:not(:disabled) { background: var(--primary-hover); }
.btn-danger { color: #b42318; background: var(--danger-bg); border-color: rgba(229, 72, 77, 0.25); }
.btn-danger:hover { background: rgba(229, 72, 77, 0.16); border-color: rgba(229, 72, 77, 0.35); }
.btn-success { color: #15803d; background: var(--success-bg); border-color: rgba(34, 197, 94, 0.3); }
.btn-success:hover { background: rgba(34, 197, 94, 0.18); }
.spinner {
  width: 13px; height: 13px; border: 2px solid rgba(255, 255, 255, 0.4);
  border-top-color: #fff; border-radius: 50%; animation: spin 0.6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ── 空态向导 ── */
.card {
  background: var(--surface-color); border: 1px solid var(--border-color);
  border-radius: var(--radius); padding: 16px 18px; position: relative; flex: none;
  box-shadow: 0 1px 2px rgba(17, 17, 17, 0.035);
}
.wiz-card { display: flex; flex-direction: column; gap: 16px; padding: 22px; }
.wiz-hero { text-align: center; padding: 10px 0 2px; }
.wiz-title { font-size: 17px; font-weight: 800; }
.wiz-sub { font-size: 12.5px; color: var(--text-muted); margin-top: 5px; }
.wiz-steps { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
.step { border: 1px solid var(--border-color); border-radius: 9px; padding: 12px; background: var(--surface-2); }
.step .n {
  width: 20px; height: 20px; border-radius: 50%; background: var(--primary-color); color: #fff;
  font-size: 11px; font-weight: 800; display: grid; place-items: center; margin-bottom: 8px;
}
.step b { font-size: 12.5px; display: block; margin-bottom: 3px; }
.step span { font-size: 11.5px; color: var(--text-muted); line-height: 1.45; }

/* ── 向导服务商瓷砖（与 ProviderPresetGrid 同款） ── */
.pv-tiles { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 8px; }
.pv-tile {
  display: flex; flex-direction: column; align-items: center; gap: 8px;
  padding: 14px 10px 12px; border: 1px solid var(--border-color); border-radius: 10px;
  cursor: pointer; background: var(--surface-color); transition: all 0.13s;
  text-align: center; font-family: inherit;
}
.pv-tile:hover { border-color: #c9c9cf; background: var(--surface-2); transform: translateY(-1px); box-shadow: 0 3px 8px rgba(17, 17, 17, 0.06); }
.pv-tile:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 2px; }
.pv-logo {
  width: 46px; height: 46px; border-radius: 12px; display: grid; place-items: center;
  background: #f5f5f5; color: var(--text-secondary); font-size: 13px; font-weight: 800; flex: none;
}
.pv-logo.has-img { background: #fff; border: 1px solid var(--border-strong); box-shadow: 0 1px 2px rgba(17, 17, 17, 0.06); }
.pv-logo.has-img img { width: 62%; height: 62%; object-fit: contain; display: block; }
.pv-t-text { display: flex; flex-direction: column; align-items: center; gap: 2px; }
.pv-t-name { font-size: 12.5px; font-weight: 600; color: var(--text-primary); }
.pv-t-hint { font-size: 10.5px; color: var(--text-muted); margin-top: 1px; }

/* ── 入场动画（错落） ── */
@keyframes fadeUp { from { opacity: 0; transform: translateY(7px); } }
.config-col > * { animation: fadeUp 0.34s cubic-bezier(0.2, 0.7, 0.2, 1) both; }
.config-col > :nth-child(2) { animation-delay: 0.05s; }
.config-col > :nth-child(3) { animation-delay: 0.1s; }
.config-col > :nth-child(4) { animation-delay: 0.15s; }
.config-col > :nth-child(5) { animation-delay: 0.2s; }

/* ── 滚动条 ── */
.config-col::-webkit-scrollbar { width: 8px; }
.config-col::-webkit-scrollbar-thumb { background: #d8d8dd; border-radius: 5px; border: 2px solid transparent; background-clip: content-box; }

/* ── 响应式：窄屏降为两栏 / 单栏，测试栏移到底部 ── */
@media (max-width: 1500px) {
  .layout { grid-template-columns: 250px minmax(0, 1fr) 300px; }
}
@media (max-width: 1280px) {
  .layout { grid-template-columns: 240px minmax(0, 1fr); }
  .layout > .test-col { grid-column: 1 / -1; height: 400px; }
}
@media (max-width: 860px) {
  .mc-root { height: auto; }
  .layout { grid-template-columns: 1fr; }
  .layout > .plist { max-height: 320px; }
  .config-col { overflow: visible; }
  .layout > .test-col { height: 420px; }
  .action-bar { position: static; }
}

@media (prefers-reduced-motion: reduce) {
  * { animation: none !important; transition: none !important; }
}
</style>
