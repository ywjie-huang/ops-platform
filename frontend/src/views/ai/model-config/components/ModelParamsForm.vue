<template>
  <div class="card">
    <div class="sec-title">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/><line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/><line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/><line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/><line x1="17" y1="16" x2="23" y2="16"/></svg>
      模型参数
    </div>
    <div class="card-content">
      <div class="params-grid">
        <div class="param-card">
          <div class="param-head">
            <span class="param-label">Temperature</span>
            <span class="param-val">{{ profile.temperature.toFixed(1) }}</span>
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
            class="slider"
            v-model.number="profile.temperature"
            min="0"
            max="2"
            step="0.1"
            :style="sliderFill(profile.temperature, 0, 2)"
            aria-label="Temperature"
          />
          <div class="param-range"><span>0（精确）</span><span>2（随机）</span></div>
        </div>
        <div class="param-card">
          <div class="param-head">
            <span class="param-label">Max Tokens</span>
            <input
              class="param-num"
              type="number"
              min="256"
              max="32768"
              step="256"
              v-model.number="profile.max_tokens"
              aria-label="Max Tokens 精确值"
            />
          </div>
          <input
            type="range"
            class="slider"
            v-model.number="profile.max_tokens"
            min="256"
            max="32768"
            step="256"
            :style="sliderFill(profile.max_tokens, 256, 32768)"
            aria-label="Max Tokens"
          />
          <div class="param-range"><span>256</span><span>32768</span></div>
        </div>
      </div>
      <details class="adv">
        <summary>高级参数</summary>
        <div class="param-card adv-card">
          <div class="param-head">
            <span class="param-label">Top P</span>
            <span class="param-val">{{ profile.top_p.toFixed(2) }}</span>
          </div>
          <input
            type="range"
            class="slider"
            v-model.number="profile.top_p"
            min="0"
            max="1"
            step="0.05"
            :style="sliderFill(profile.top_p, 0, 1)"
            aria-label="Top P"
          />
          <div class="param-range"><span>0</span><span>1</span></div>
        </div>
      </details>
      <div class="f-group">
        <label class="f-label">系统提示词 <span class="f-tip">（可选）</span></label>
        <div class="chip-row">
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
          class="f-input"
          v-model="profile.system_prompt"
          placeholder="你是一个专业的运维助手，擅长 Linux 系统管理、Docker 容器编排和 Kubernetes 运维..."
        ></textarea>
        <span class="f-tip">自定义 AI 助手的角色和行为，留空使用默认提示词</span>
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

/** 滑杆轨道随值填充（对齐 mockup 的 paintSlider） */
function sliderFill(value: number, min: number, max: number) {
  const p = Math.min(100, Math.max(0, ((Number(value) - min) / (max - min)) * 100))
  return { background: `linear-gradient(90deg, var(--primary-color) ${p}%, #e4e4e8 ${p}%)` }
}
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

/* ── 参数卡片 ── */
.params-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.param-card {
  border: 1px solid var(--border-color); border-radius: 9px; background: var(--surface-2, #f6f6f8);
  padding: 12px 13px; display: flex; flex-direction: column; gap: 9px; position: relative;
}
.param-head { display: flex; justify-content: space-between; align-items: center; }
.param-label { font-size: 12px; font-weight: 700; color: var(--text-secondary); }
.param-val {
  font-size: 13px; font-weight: 800; color: var(--primary-color);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}
.param-num {
  width: 92px; padding: 4px 8px; border: 1px solid var(--border-strong, #e2e2e6); border-radius: 6px;
  font-size: 12.5px; text-align: right; font-family: ui-monospace, Menlo, Consolas, monospace;
  color: var(--primary-color); font-weight: 700; background: var(--surface-color);
}
.param-num:focus { outline: none; border-color: var(--primary-color); box-shadow: 0 0 0 2px rgba(94, 106, 210, 0.12); }
.param-range { display: flex; justify-content: space-between; font-size: 10.5px; color: var(--text-muted); }

/* ── 滑杆（轨道随值填充，见 script sliderFill） ── */
.slider { width: 100%; height: 4px; -webkit-appearance: none; appearance: none; background: #e4e4e8; border-radius: 2px; outline: none; }
.slider::-webkit-slider-thumb {
  -webkit-appearance: none; width: 14px; height: 14px; border-radius: 50%;
  background: var(--primary-color); cursor: pointer; border: 2.5px solid #fff; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.25);
}
.slider::-moz-range-thumb {
  width: 14px; height: 14px; border-radius: 50%; background: var(--primary-color);
  cursor: pointer; border: 2.5px solid #fff; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.25);
}

/* ── 快捷值 / 模板 chips ── */
.chip-row { display: flex; gap: 6px; flex-wrap: wrap; }
.chip {
  border: 1px solid var(--border-strong, #e2e2e6); background: var(--surface-color); color: var(--text-secondary);
  border-radius: 999px; padding: 3px 11px; font-size: 11.5px; cursor: pointer; font-weight: 600;
  font-family: inherit; transition: all 0.15s;
}
.chip:hover { border-color: var(--primary-color); color: var(--primary-color); }
.chip.active { border-color: var(--primary-color); background: var(--primary-bg); color: var(--primary-color); }
.chip:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 2px; }

/* ── 高级参数 ── */
details.adv { border: 1px solid var(--border-color); border-radius: 9px; background: var(--surface-2, #f6f6f8); padding: 10px 13px; }
details.adv summary { cursor: pointer; font-size: 12.5px; font-weight: 700; color: var(--text-secondary); }
.adv-card { margin-top: 11px; background: var(--surface-color); }

/* ── 系统提示词 ── */
.f-group { display: flex; flex-direction: column; gap: 5px; }
.f-label { font-size: 12.5px; font-weight: 600; color: var(--text-primary); display: flex; gap: 4px; align-items: center; }
.f-input {
  padding: 8px 11px; border: 1px solid var(--border-strong, #e2e2e6); border-radius: 7px; font-size: 13px;
  background: var(--surface-color); color: var(--text-primary); font-family: inherit; width: 100%;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.f-input:focus { outline: none; border-color: var(--primary-color); box-shadow: 0 0 0 2px rgba(94, 106, 210, 0.12); }
textarea.f-input { resize: vertical; min-height: 68px; line-height: 1.55; }
.f-tip { font-size: 11.5px; color: var(--text-muted); line-height: 1.45; font-weight: 400; }

@media (max-width: 900px) {
  .params-grid { grid-template-columns: 1fr; }
}
@media (prefers-reduced-motion: reduce) {
  * { animation: none !important; transition: none !important; }
}
</style>
