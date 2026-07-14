<template>
  <div class="card">
    <div class="section-title">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>
      快速选择服务商
    </div>
    <div class="card-content">
      <div class="provider-presets">
        <div
          v-for="p in providers"
          :key="p.id"
          class="provider-card"
          :class="{ selected: profile.provider === p.id }"
          role="radio"
          :aria-checked="profile.provider === p.id"
          :aria-label="`${p.name}: ${p.hint}`"
          tabindex="0"
          @click="$emit('select', p)"
          @keydown.enter.space.prevent="$emit('select', p)"
        >
          <div class="provider-logo">{{ p.icon }}</div>
          <div class="provider-name">{{ p.name }}</div>
          <div class="provider-desc">{{ p.hint }}</div>
        </div>
      </div>
      <div class="form-row">
        <div class="form-group">
          <label class="form-label">接口模式</label>
          <select class="form-input" v-model="profile.api_mode" @change="$emit('api-mode-change')">
            <option value="chat_completions">Chat Completions</option>
            <option value="responses">Responses</option>
          </select>
          <span class="form-tip">中转站支持 Responses 时可切换到新接口</span>
        </div>
        <div class="form-group" v-if="profile.api_mode === 'responses'">
          <label class="form-label">推理强度</label>
          <select class="form-input" v-model="profile.reasoning_effort">
            <option value="low">low</option>
            <option value="medium">medium</option>
            <option value="high">high</option>
          </select>
          <span class="form-tip">仅 Responses 模式生效</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { LLMProfile } from '@/api/settings'
import type { ProviderPreset } from '../../providerPreset'

defineProps<{
  profile: LLMProfile
  providers: ProviderPreset[]
}>()

defineEmits<{
  (e: 'select', provider: ProviderPreset): void
  (e: 'api-mode-change'): void
}>()
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
.provider-presets {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 10px;
}
.provider-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 14px 10px;
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  cursor: pointer;
  transition: all 0.15s;
  background: var(--surface-color);
}
.provider-card:hover {
  border-color: #c0c4cc;
  background: #fafafa;
}
.provider-card:focus-visible {
  outline: 2px solid var(--primary-color);
  outline-offset: 2px;
}
.provider-card.selected {
  border-color: var(--primary-color);
  background: var(--primary-bg);
  box-shadow: 0 0 0 1px var(--primary-color);
}
.provider-logo {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f5f5;
  font-size: 13px;
  font-weight: 700;
  color: var(--text-secondary);
}
.provider-card.selected .provider-logo {
  background: rgba(94, 106, 210, 0.12);
  color: var(--primary-color);
}
.provider-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}
.provider-desc {
  font-size: 11px;
  color: var(--text-muted);
  text-align: center;
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
}
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
.form-tip {
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1.4;
}
@media (max-width: 900px) {
  .provider-presets { grid-template-columns: repeat(2, 1fr); }
  .form-row { grid-template-columns: 1fr; }
}
</style>
