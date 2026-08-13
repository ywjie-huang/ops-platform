<template>
  <div class="card conn-card">
    <div class="sec-title">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>
      连接配置
    </div>
    <div class="card-content">
      <div class="f-group">
        <label class="f-label">配置名称</label>
        <input class="f-input" v-model="profile.name" placeholder="例如：DeepSeek 生产" />
        <span class="f-tip">用于左侧列表识别；仅当名称为“新模型”时保存会自动用模型名填充</span>
      </div>
      <div class="f-group">
        <label class="f-label"><span class="req">*</span> API 地址</label>
        <input
          class="f-input"
          :class="{ error: formErrors.base_url }"
          v-model="profile.base_url"
          placeholder="https://api.openai.com/v1"
          @blur="$emit('validate', 'base_url')"
        />
        <span v-if="formErrors.base_url" class="f-error">{{ formErrors.base_url }}</span>
        <span v-else class="f-tip">OpenAI 兼容接口地址，支持 OpenAI / DeepSeek / 通义千问 / Ollama / 中转站等</span>
      </div>
      <div class="f-row">
        <div class="f-group">
          <label class="f-label">API Key</label>
          <div class="pw">
            <input
              class="f-input"
              :type="showPassword ? 'text' : 'password'"
              v-model="profile.api_key"
              :placeholder="apiKeyPlaceholder"
            />
            <span class="eye" @click="showPassword = !showPassword">
              <svg v-if="!showPassword" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
              <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
            </span>
          </div>
          <span class="f-tip" :class="{ 'f-tip-warn': providerChanged && profile.has_api_key }">
            <template v-if="providerChanged && profile.has_api_key">服务商已变更，当前密钥为原服务商所有，请填写新服务商的 API Key</template>
            <template v-else-if="providerChanged">服务商已变更，请填写新服务商的 API Key</template>
            <template v-else-if="profile.has_api_key">已配置密钥，留空表示不修改</template>
            <template v-else>部分本地模型（如 Ollama）可留空</template>
          </span>
        </div>
        <div class="f-group">
          <label class="f-label"><span class="req">*</span> 模型名称</label>
          <div class="model-input-row">
            <el-select
              v-model="profile.model"
              class="model-select"
              :class="{ 'is-error': formErrors.model }"
              filterable
              allow-create
              default-first-option
              fit-input-width
              clearable
              placeholder="输入或选择模型"
              popper-class="model-select-popper"
              aria-label="模型名称"
              @change="$emit('validate', 'model')"
              @blur="$emit('validate', 'model')"
            >
              <template #empty>
                <div class="model-select-empty">暂无可选模型，可直接输入模型名称</div>
              </template>
              <el-option
                v-for="model in modelOptions"
                :key="model.id"
                :label="model.id"
                :value="model.id"
              >
                <div class="model-option" :title="model.owned_by ? `${model.id} · ${model.owned_by}` : model.id">
                  <span class="model-option__id">{{ model.id }}</span>
                  <span v-if="model.owned_by" class="model-option__owner">{{ model.owned_by }}</span>
                </div>
              </el-option>
            </el-select>
            <button
              class="btn btn-sm"
              type="button"
              :class="{ 'is-loading': loadingModels }"
              :disabled="loadingModels"
              @click="$emit('refresh-models')"
            >
              <span v-if="loadingModels" class="spinner"></span>
              {{ loadingModels ? '拉取中' : '刷新模型' }}
            </button>
          </div>
          <span v-if="formErrors.model" class="f-error">{{ formErrors.model }}</span>
          <span v-else class="f-tip">{{ modelListTip || '可手动输入，或点击“刷新模型”从服务商拉取' }}</span>
        </div>
      </div>
      <div class="f-row">
        <div class="f-group">
          <label class="f-label">接口模式</label>
          <select class="f-input f-select" v-model="profile.api_mode" @change="$emit('api-mode-change')">
            <option value="chat_completions">Chat Completions</option>
            <option value="responses">Responses</option>
            <option value="anthropic">Anthropic Messages</option>
          </select>
          <span class="f-tip">智谱 Coding Plan / Claude 官方选 Anthropic；中转站支持 Responses 时可切换</span>
        </div>
        <div class="f-group">
          <label class="f-label">推理强度</label>
          <select
            class="f-input f-select"
            v-model="profile.reasoning_effort"
            :disabled="profile.api_mode !== 'responses'"
          >
            <option value="" disabled>仅 Responses 模式生效</option>
            <option value="low">low</option>
            <option value="medium">medium</option>
            <option value="high">high</option>
          </select>
          <span class="f-tip">仅 Responses 模式生效，控制思考深度</span>
        </div>
      </div>
    </div>
    <!-- 测试连接：就近展示结果 -->
    <div class="conn-foot">
      <button class="btn" type="button" :disabled="testing" @click="$emit('test')">
        <svg v-if="!testing" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>
        <span v-else class="spinner"></span>
        {{ testing ? '测试中…' : '测试连接' }}
      </button>
      <span v-if="hasResult" class="conn-result" :class="testResult ? 'ok' : 'fail'">
        <svg v-if="testResult" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
        <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
        <span class="conn-result-msg">{{ testResultMsg || (testResult ? '连接成功' : '连接失败') }}</span>
        <i class="x" title="关闭" @click="$emit('close-result')">✕</i>
      </span>
      <span class="f-tip conn-foot-tip">用当前草稿测试，无需先保存</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { LLMProfile } from '@/api/settings'

const props = defineProps<{
  profile: LLMProfile
  formErrors: Record<string, string>
  apiKeyPlaceholder: string
  providerChanged?: boolean
  loadingModels?: boolean
  modelOptions: Array<{ id: string; owned_by: string }>
  modelListTip?: string
  testing?: boolean
  testResult?: boolean | null
  testResultMsg?: string
}>()

defineEmits<{
  (e: 'validate', field: string): void
  (e: 'refresh-models'): void
  (e: 'api-mode-change'): void
  (e: 'test'): void
  (e: 'close-result'): void
}>()

const showPassword = ref(false)
const hasResult = computed(() => props.testResult === true || props.testResult === false)
</script>

<style scoped>
.card {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--radius, 10px);
  padding: 16px 18px;
  position: relative;
  flex: none;
  box-shadow: 0 1px 2px rgba(17, 17, 17, 0.035);
}
.sec-title { font-size: 13.5px; font-weight: 700; display: flex; align-items: center; gap: 8px; color: var(--text-primary); }
.sec-title svg { width: 15px; height: 15px; color: var(--text-secondary); }
.card-content { display: flex; flex-direction: column; gap: 13px; margin-top: 13px; }

/* ── 表单 ── */
.f-row { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.f-group { display: flex; flex-direction: column; gap: 5px; }
.f-label { font-size: 12.5px; font-weight: 600; color: var(--text-primary); display: flex; gap: 4px; align-items: center; }
.req { color: var(--danger-color); }
.f-input {
  padding: 8px 11px; border: 1px solid var(--border-strong, #e2e2e6); border-radius: 7px; font-size: 13px;
  background: var(--surface-color); color: var(--text-primary); font-family: inherit; width: 100%;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.f-input:focus { outline: none; border-color: var(--primary-color); box-shadow: 0 0 0 2px rgba(94, 106, 210, 0.12); }
.f-input:disabled { opacity: 0.55; background: var(--surface-2, #f6f6f8); cursor: not-allowed; }
.f-input::placeholder { color: var(--text-muted); }
.f-input.error { border-color: var(--danger-color); box-shadow: 0 0 0 2px rgba(229, 72, 77, 0.1); }
.f-select {
  appearance: none; -webkit-appearance: none; padding-right: 30px; cursor: pointer;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M1 1l4 4 4-4' stroke='%238c8c8c' fill='none' stroke-width='1.6' stroke-linecap='round'/%3E%3C/svg%3E");
  background-repeat: no-repeat; background-position: right 11px center;
}
.f-select:disabled { cursor: not-allowed; }
.f-tip { font-size: 11.5px; color: var(--text-muted); line-height: 1.45; }
.f-tip-warn { color: var(--warning-color); }
.f-error { font-size: 11.5px; color: var(--danger-color); line-height: 1.45; }

/* ── 密码显隐 ── */
.pw { position: relative; }
.pw .f-input { padding-right: 34px; }
.eye { position: absolute; right: 9px; top: 50%; transform: translateY(-50%); cursor: pointer; color: var(--text-muted); display: flex; }
.eye svg { width: 15px; height: 15px; }
.eye:hover { color: var(--text-primary); }

/* ── 模型选择行 ── */
.model-input-row { display: flex; gap: 8px; align-items: center; }
.model-select { flex: 1; min-width: 0; }
.model-select :deep(.el-select__wrapper) {
  min-height: 34px;
  border-radius: 7px;
  background: var(--surface-color);
  box-shadow: 0 0 0 1px var(--border-strong, #e2e2e6) inset;
  transition: box-shadow 180ms ease-out;
}
.model-select:hover :deep(.el-select__wrapper) { box-shadow: 0 0 0 1px var(--text-muted) inset; }
.model-select :deep(.el-select__wrapper.is-focused) {
  box-shadow: 0 0 0 1px var(--primary-color) inset, 0 0 0 2px rgba(94, 106, 210, 0.12);
}
.model-select.is-error :deep(.el-select__wrapper) { box-shadow: 0 0 0 1px var(--danger-color) inset; }
.model-select.is-error :deep(.el-select__wrapper.is-focused) {
  box-shadow: 0 0 0 1px var(--danger-color) inset, 0 0 0 2px rgba(229, 72, 77, 0.12);
}
.model-option { display: flex; align-items: center; justify-content: space-between; gap: 16px; min-width: 0; }
.model-option__id { overflow: hidden; color: var(--text-primary); text-overflow: ellipsis; white-space: nowrap; }
.model-option__owner { flex: none; max-width: 38%; overflow: hidden; color: var(--text-muted); font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }
.model-select-empty { padding: 10px 12px; color: var(--text-secondary); font-size: 12px; line-height: 1.5; text-align: center; }
:global(.model-select-popper .el-select-dropdown__wrap) { max-height: 280px; }
:global(.model-select-popper .el-select-dropdown__item) { padding: 0 12px; }
:global(.model-select-popper .el-select-dropdown__item.is-selected) { color: var(--primary-color); background: var(--primary-bg); }

/* ── 测试连接底栏 ── */
.conn-foot {
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
  margin-top: 14px; padding-top: 13px; border-top: 1px solid var(--border-color); position: relative;
}
.conn-result {
  display: inline-flex; align-items: center; gap: 7px; padding: 6px 11px;
  border-radius: 7px; font-size: 12px; font-weight: 600; max-width: 100%;
}
.conn-result.ok { color: #15803d; background: var(--success-bg, rgba(34, 197, 94, 0.11)); border: 1px solid rgba(34, 197, 94, 0.25); }
.conn-result.fail { color: #b42318; background: var(--danger-bg, rgba(229, 72, 77, 0.1)); border: 1px solid rgba(229, 72, 77, 0.25); }
.conn-result svg { width: 13px; height: 13px; flex: none; }
.conn-result-msg { overflow: hidden; text-overflow: ellipsis; }
.conn-result .x { cursor: pointer; opacity: 0.6; margin-left: 2px; font-style: normal; flex: none; }
.conn-result .x:hover { opacity: 1; }
.conn-foot-tip { margin-left: auto; }
@keyframes fadeUp { from { opacity: 0; transform: translateY(7px); } }
.conn-result { animation: fadeUp 0.25s ease; }

/* ── 按钮 / spinner ── */
.btn {
  display: inline-flex; align-items: center; gap: 6px; padding: 7px 14px; border-radius: 7px;
  font-size: 12.5px; font-weight: 600; cursor: pointer; border: 1px solid var(--border-strong, #e2e2e6);
  background: var(--surface-color); color: var(--text-primary); transition: all 0.15s; font-family: inherit;
}
.btn:hover { border-color: #c9c9cf; transform: translateY(-1px); box-shadow: 0 3px 8px rgba(17, 17, 17, 0.07); }
.btn:active { transform: none; box-shadow: none; }
.btn:disabled, .btn.is-loading { opacity: 0.55; cursor: not-allowed; transform: none; box-shadow: none; }
.btn:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 2px; }
.btn-sm { padding: 5px 11px; font-size: 12px; }
.btn svg { width: 13px; height: 13px; }
.spinner {
  width: 13px; height: 13px; border: 2px solid var(--border-strong, #e2e2e6);
  border-top-color: var(--primary-color); border-radius: 50%; animation: spin 0.6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

@media (max-width: 900px) {
  .f-row { grid-template-columns: 1fr; }
}
@media (max-width: 600px) {
  .model-input-row { flex-direction: column; align-items: stretch; }
  .model-input-row .btn { min-height: 44px; }
}
@media (prefers-reduced-motion: reduce) {
  .model-select :deep(.el-select__wrapper) { transition: none; }
  * { animation: none !important; transition: none !important; }
}
</style>
