<template>
  <div class="card">
    <div class="section-title">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
      模型参数
    </div>
    <div class="card-content">
      <div class="params-grid">
        <div class="param-card">
          <div class="param-header">
            <span class="param-label">Temperature</span>
            <span class="param-value">{{ profile.temperature.toFixed(1) }}</span>
          </div>
          <div class="chip-row">
            <button
              v-for="item in temperaturePresets"
              :key="item.id"
              type="button"
              class="chip"
              :class="{ active: Math.abs(profile.temperature - item.value) < 0.05 }"
              @click="profile.temperature = item.value"
            >
              {{ item.label }} {{ item.value }}
            </button>
          </div>
          <input
            type="range"
            class="param-slider"
            v-model.number="profile.temperature"
            min="0"
            max="2"
            step="0.1"
            aria-label="Temperature 值"
          />
          <div class="param-range"><span>0 (精确)</span><span>2 (随机)</span></div>
        </div>
        <div class="param-card">
          <div class="param-header">
            <span class="param-label">Max Tokens</span>
            <input
              class="param-number"
              type="number"
              min="256"
              max="128000"
              step="1"
              v-model.number="profile.max_tokens"
              aria-label="Max Tokens 精确值"
            />
          </div>
          <input
            type="range"
            class="param-slider"
            v-model.number="profile.max_tokens"
            min="256"
            max="32768"
            step="256"
            aria-label="Max Tokens 值"
          />
          <div class="param-range"><span>256</span><span>32768</span></div>
        </div>
      </div>

      <details class="advanced-block">
        <summary>高级参数</summary>
        <div class="param-card" style="margin-top: 12px;">
          <div class="param-header">
            <span class="param-label">Top P</span>
            <span class="param-value">{{ profile.top_p.toFixed(2) }}</span>
          </div>
          <input
            type="range"
            class="param-slider"
            v-model.number="profile.top_p"
            min="0"
            max="1"
            step="0.05"
            aria-label="Top P 值"
          />
          <div class="param-range"><span>0</span><span>1</span></div>
        </div>
      </details>

      <div class="form-group">
        <label class="form-label">系统提示词 <span class="tag tag-default">可选</span></label>
        <div class="chip-row" style="margin-bottom: 8px;">
          <button
            v-for="tpl in promptTemplates"
            :key="tpl.id"
            type="button"
            class="chip"
            @click="$emit('apply-prompt', tpl.content)"
          >
            {{ tpl.name }}
          </button>
        </div>
        <textarea
          class="form-input"
          v-model="profile.system_prompt"
          rows="3"
          placeholder="你是一个专业的运维助手，擅长 Linux 系统管理、Docker 容器编排和 Kubernetes 运维..."
          style="resize: vertical; min-height: 72px;"
        ></textarea>
        <span class="form-tip">自定义 AI 助手的角色和行为。留空使用默认提示词。</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { LLMProfile } from '@/api/settings'

defineProps<{
  profile: LLMProfile
  temperaturePresets: ReadonlyArray<{ id: string; label: string; value: number }>
  promptTemplates: Array<{ id: string; name: string; content: string }>
}>()

defineEmits<{
  (e: 'apply-prompt', content: string): void
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
.params-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}
.param-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 14px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  background: var(--bg-color);
}
.param-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.param-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
}
.param-value {
  font-size: 13px;
  font-weight: 700;
  color: var(--primary-color);
  font-family: 'SF Mono', 'Consolas', monospace;
}
.param-number {
  width: 96px;
  padding: 4px 8px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  font-size: 13px;
  font-family: 'SF Mono', 'Consolas', monospace;
  color: var(--primary-color);
  font-weight: 700;
  text-align: right;
  background: var(--surface-color);
}
.param-slider {
  width: 100%;
  height: 4px;
  -webkit-appearance: none;
  appearance: none;
  background: #e8e8e8;
  border-radius: 2px;
  outline: none;
}
.param-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: var(--primary-color);
  cursor: pointer;
}
.param-range {
  display: flex;
  justify-content: space-between;
  font-size: 10px;
  color: var(--text-muted);
}
.chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.chip {
  border: 1px solid var(--border-color);
  background: var(--surface-color);
  color: var(--text-secondary);
  border-radius: 999px;
  padding: 2px 10px;
  font-size: 12px;
  cursor: pointer;
}
.chip.active {
  border-color: var(--primary-color);
  background: var(--primary-bg);
  color: var(--primary-color);
}
.advanced-block {
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 10px 12px;
  background: var(--bg-color);
}
.advanced-block summary {
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
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
.form-input {
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  font-size: 13px;
  font-family: inherit;
  background: var(--surface-color);
  color: var(--text-primary);
}
.form-tip {
  font-size: 12px;
  color: var(--text-muted);
}
.tag {
  display: inline-flex;
  align-items: center;
  padding: 0 8px;
  height: 22px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
}
.tag-default {
  background: #f5f5f5;
  color: var(--text-secondary);
}
@media (max-width: 900px) {
  .params-grid { grid-template-columns: 1fr; }
}
</style>
