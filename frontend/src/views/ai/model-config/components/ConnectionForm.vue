<template>
  <div class="card">
    <div class="section-title">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"/><polyline points="16 6 12 2 8 6"/><line x1="12" y1="2" x2="12" y2="15"/></svg>
      连接配置
    </div>
    <div class="card-content">
      <div class="form-group">
        <label class="form-label">配置名称</label>
        <input class="form-input" v-model="profile.name" placeholder="例如：DeepSeek 生产" />
        <span class="form-tip">用于左侧列表识别；仅当名称为“新模型”时保存会自动用模型名填充</span>
      </div>
      <div class="form-group">
        <label class="form-label"><span class="required">*</span> API 地址</label>
        <input
          class="form-input"
          :class="{ error: formErrors.base_url }"
          v-model="profile.base_url"
          placeholder="https://api.openai.com/v1"
          @blur="$emit('validate', 'base_url')"
        />
        <span v-if="formErrors.base_url" class="form-error">{{ formErrors.base_url }}</span>
        <span v-else class="form-tip">OpenAI 兼容接口地址，支持 OpenAI / DeepSeek / 通义千问 / Ollama / 中转站等</span>
      </div>
      <div class="form-row">
        <div class="form-group">
          <label class="form-label">API Key</label>
          <div class="form-input-password">
            <input
              class="form-input"
              :type="showPassword ? 'text' : 'password'"
              v-model="profile.api_key"
              :placeholder="apiKeyPlaceholder"
            />
            <span class="eye-icon" @click="showPassword = !showPassword">
              <svg v-if="!showPassword" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
              <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
            </span>
          </div>
          <span class="form-tip">
            {{ profile.has_api_key ? '已配置密钥，留空表示不修改' : '部分本地模型（如 Ollama）可留空' }}
          </span>
        </div>
        <div class="form-group">
          <label class="form-label"><span class="required">*</span> 模型名称</label>
          <div class="model-input-row">
            <input
              class="form-input"
              list="llm-model-options"
              :class="{ error: formErrors.model }"
              v-model="profile.model"
              placeholder="gpt-4o"
              @blur="$emit('validate', 'model')"
            />
            <button
              class="btn btn-sm"
              type="button"
              :class="{ 'is-loading': loadingModels }"
              :disabled="loadingModels"
              @click="$emit('refresh-models')"
            >
              {{ loadingModels ? '拉取中' : '刷新模型' }}
            </button>
          </div>
          <datalist id="llm-model-options">
            <option v-for="m in modelOptions" :key="m.id" :value="m.id">
              {{ m.owned_by ? `${m.id} · ${m.owned_by}` : m.id }}
            </option>
          </datalist>
          <span v-if="formErrors.model" class="form-error">{{ formErrors.model }}</span>
          <span v-else class="form-tip">
            {{ modelListTip || '可手动输入，或点击“刷新模型”从服务商拉取' }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { LLMProfile } from '@/api/settings'

defineProps<{
  profile: LLMProfile
  formErrors: Record<string, string>
  apiKeyPlaceholder: string
  loadingModels?: boolean
  modelOptions: Array<{ id: string; owned_by: string }>
  modelListTip?: string
}>()

defineEmits<{
  (e: 'validate', field: string): void
  (e: 'refresh-models'): void
}>()

const showPassword = ref(false)
</script>

<style scoped>
.card {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: 20px;
}
.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 8px;
}
.section-title svg { color: var(--text-secondary); }
.card-content {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-top: 12px;
}
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
  background: var(--surface-color);
  color: var(--text-primary);
}
.form-input:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 0 2px rgba(94, 106, 210, 0.1);
}
.form-input.error {
  border-color: var(--error-color, #dc2626);
}
.form-input-password {
  position: relative;
}
.form-input-password .form-input {
  padding-right: 36px;
  width: 100%;
}
.form-input-password .eye-icon {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  cursor: pointer;
  color: var(--text-muted);
  display: flex;
  align-items: center;
}
.model-input-row {
  display: flex;
  gap: 8px;
  align-items: center;
}
.model-input-row .form-input { flex: 1; }
.form-tip {
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1.4;
}
.form-error {
  font-size: 12px;
  color: var(--error-color, #dc2626);
}
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
}
.btn-sm { padding: 4px 12px; font-size: 12px; }
.btn:disabled, .btn.is-loading {
  opacity: 0.5;
  cursor: not-allowed;
}
@media (max-width: 900px) {
  .form-row { grid-template-columns: 1fr; }
}
</style>
