<template>
  <Teleport to="body">
    <Transition name="threshold-fade">
      <div
        v-if="modelValue"
        class="threshold-scrim"
        @click="close"
      />
    </Transition>

    <Transition name="threshold-slide">
      <aside
        v-if="modelValue"
        class="threshold-drawer"
        aria-label="阈值校准舱"
        role="dialog"
        aria-modal="true"
      >
        <div class="drawer-head">
          <div>
            <div class="eyebrow">Threshold Bay</div>
            <h3>校准阈值</h3>
            <p>只影响下一次巡检判定。当前报告、历史批次保持原样。</p>
          </div>
          <button class="icon-btn" type="button" aria-label="关闭" @click="close">×</button>
        </div>

        <div class="drawer-body" v-loading="loading">
          <div class="preset-rail">
            <button
              v-for="preset in presetOptions"
              :key="preset.key"
              class="preset"
              :class="{ active: activePreset === preset.key }"
              type="button"
              @click="applyPreset(preset.key)"
            >
              <span class="kicker">{{ preset.kicker }}</span>
              <strong>{{ preset.title }}</strong>
              <span>{{ preset.desc }}</span>
            </button>
          </div>

          <div class="metric-stack">
            <section v-for="group in groups" :key="group.key" class="metric">
              <div class="metric-top">
                <div class="metric-identity">
                  <div class="glyph" v-html="group.icon" />
                  <div>
                    <h4>{{ group.title }}</h4>
                    <small>{{ group.desc }}</small>
                  </div>
                </div>
                <span class="unit-pill">{{ group.kind === 'percent' ? '0–100%' : '绝对值' }}</span>
              </div>

              <div
                class="range-map"
                :style="rangeStyle(group)"
              >
                <div class="z-safe" />
                <div class="z-warn" />
                <div class="z-crit" />
              </div>
              <div class="range-labels">
                <span>{{ group.min }}{{ group.unit }}</span>
                <span>warn {{ thresholds[group.warnKey] }}{{ group.unit }}</span>
                <span>crit {{ thresholds[group.critKey] }}{{ group.unit }}</span>
                <span>{{ group.max }}{{ group.unit }}</span>
              </div>

              <div class="dual-controls">
                <label class="control warn">
                  <div class="control-label">
                    <span>警告线</span>
                    <em>{{ thresholds[group.warnKey] }}{{ group.unit }}</em>
                  </div>
                  <input
                    type="range"
                    :min="group.min"
                    :max="group.max"
                    :step="group.step"
                    :value="thresholds[group.warnKey]"
                    @input="onSlide(group.warnKey, group.critKey, 'warn', $event)"
                  />
                </label>
                <label class="control crit">
                  <div class="control-label">
                    <span>严重线</span>
                    <em>{{ thresholds[group.critKey] }}{{ group.unit }}</em>
                  </div>
                  <input
                    type="range"
                    :min="group.min"
                    :max="group.max"
                    :step="group.step"
                    :value="thresholds[group.critKey]"
                    @input="onSlide(group.critKey, group.warnKey, 'crit', $event)"
                  />
                </label>
              </div>

              <div v-if="group.kind === 'absolute'" class="load-note">
                负载按绝对值判定，色带仅用于相对位置示意，不代表百分比占用。
              </div>
            </section>
          </div>
        </div>

        <div class="drawer-foot">
          <div class="foot-hint">保存后立即写入配置；已生成的巡检报告不会被回溯修改。</div>
          <div class="foot-actions">
            <button class="btn" type="button" @click="handleReset">恢复默认</button>
            <button class="btn primary" type="button" :disabled="saving" @click="handleSave">
              {{ saving ? '保存中…' : '保存校准' }}
            </button>
          </div>
        </div>
      </aside>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { getPatrolThresholds, updatePatrolThresholdsBulk } from '@/api/patrol'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ (e: 'update:modelValue', value: boolean): void }>()

const loading = ref(false)
const saving = ref(false)
const activePreset = ref<string>('normal')

const DEFAULTS: Record<string, number> = {
  'patrol.cpu_warning': 80,
  'patrol.cpu_critical': 95,
  'patrol.memory_warning': 85,
  'patrol.memory_critical': 95,
  'patrol.disk_warning': 85,
  'patrol.disk_critical': 95,
  'patrol.load_warning': 5,
  'patrol.load_critical': 10,
}

const PRESETS: Record<string, Record<string, number>> = {
  strict: {
    'patrol.cpu_warning': 70, 'patrol.cpu_critical': 90,
    'patrol.memory_warning': 75, 'patrol.memory_critical': 90,
    'patrol.disk_warning': 75, 'patrol.disk_critical': 90,
    'patrol.load_warning': 3, 'patrol.load_critical': 8,
  },
  normal: { ...DEFAULTS },
  relaxed: {
    'patrol.cpu_warning': 90, 'patrol.cpu_critical': 98,
    'patrol.memory_warning': 90, 'patrol.memory_critical': 98,
    'patrol.disk_warning': 90, 'patrol.disk_critical': 98,
    'patrol.load_warning': 8, 'patrol.load_critical': 15,
  },
}

const thresholds = reactive<Record<string, number>>({ ...DEFAULTS })

const presetOptions = [
  { key: 'strict', kicker: 'Strict', title: '严格', desc: '更早告警，适合核心业务窗口' },
  { key: 'normal', kicker: 'Standard', title: '标准', desc: '默认平衡，大多数环境可直接用' },
  { key: 'relaxed', kicker: 'Relaxed', title: '宽松', desc: '降低噪声，适合压测/扩容期' },
]

const groups = [
  {
    key: 'cpu',
    title: 'CPU 使用率',
    desc: '主机 / 节点算力占用',
    unit: '%',
    warnKey: 'patrol.cpu_warning',
    critKey: 'patrol.cpu_critical',
    min: 0,
    max: 100,
    step: 1,
    kind: 'percent' as const,
    icon: '<svg viewBox="0 0 24 24"><rect x="5" y="5" width="14" height="14" rx="2"/><path d="M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3"/></svg>',
  },
  {
    key: 'mem',
    title: '内存使用率',
    desc: '可用内存压力',
    unit: '%',
    warnKey: 'patrol.memory_warning',
    critKey: 'patrol.memory_critical',
    min: 0,
    max: 100,
    step: 1,
    kind: 'percent' as const,
    icon: '<svg viewBox="0 0 24 24"><path d="M4 7h16v10H4z"/><path d="M8 7V5M12 7V5M16 7V5M8 19v-2M12 19v-2M16 19v-2"/></svg>',
  },
  {
    key: 'disk',
    title: '磁盘使用率',
    desc: '容量越线优先',
    unit: '%',
    warnKey: 'patrol.disk_warning',
    critKey: 'patrol.disk_critical',
    min: 0,
    max: 100,
    step: 1,
    kind: 'percent' as const,
    icon: '<svg viewBox="0 0 24 24"><ellipse cx="12" cy="6" rx="8" ry="3"/><path d="M4 6v6c0 1.7 3.6 3 8 3s8-1.3 8-3V6"/><path d="M4 12v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"/></svg>',
  },
  {
    key: 'load',
    title: '系统负载',
    desc: '按绝对值判定，不是百分比',
    unit: '',
    warnKey: 'patrol.load_warning',
    critKey: 'patrol.load_critical',
    min: 0,
    max: 30,
    step: 0.5,
    kind: 'absolute' as const,
    icon: '<svg viewBox="0 0 24 24"><path d="M4 18V6"/><path d="M4 18h16"/><path d="M7 14l3-4 3 2 4-6"/></svg>',
  },
]

function close() {
  emit('update:modelValue', false)
}

function rangeStyle(group: (typeof groups)[number]) {
  const warn = thresholds[group.warnKey]
  const crit = thresholds[group.critKey]
  if (group.kind === 'percent') {
    return {
      '--safe': `${Math.max(warn, 0)}%`,
      '--warnw': `${Math.max(crit - warn, 0)}%`,
      '--critw': `${Math.max(100 - crit, 0)}%`,
    }
  }
  const max = group.max
  return {
    '--safe': `${(warn / max) * 100}%`,
    '--warnw': `${Math.max(((crit - warn) / max) * 100, 0)}%`,
    '--critw': `${Math.max(((max - crit) / max) * 100, 0)}%`,
  }
}

function onSlide(field: string, pair: string, role: 'warn' | 'crit', event: Event) {
  const input = event.target as HTMLInputElement
  let value = parseFloat(input.value)
  if (Number.isNaN(value)) return
  if (role === 'warn' && value > thresholds[pair]) value = thresholds[pair]
  if (role === 'crit' && value < thresholds[pair]) value = thresholds[pair]
  thresholds[field] = value
  activePreset.value = ''
}

function applyPreset(name: string) {
  const preset = PRESETS[name]
  if (!preset) return
  Object.assign(thresholds, preset)
  activePreset.value = name
}

async function fetchThresholds() {
  loading.value = true
  try {
    const res: any = await getPatrolThresholds()
    for (const item of res.data.items || []) {
      const num = parseFloat(item.value)
      if (!Number.isNaN(num) && item.key in thresholds) {
        thresholds[item.key] = num
      }
    }
    activePreset.value = detectPreset()
  } catch {
    ElMessage.error('加载巡检阈值失败')
  } finally {
    loading.value = false
  }
}

function detectPreset() {
  for (const [name, preset] of Object.entries(PRESETS)) {
    const matched = Object.entries(preset).every(([key, value]) => thresholds[key] === value)
    if (matched) return name
  }
  return ''
}

function handleReset() {
  Object.assign(thresholds, DEFAULTS)
  activePreset.value = 'normal'
  ElMessage.success('已恢复标准默认值（尚未保存）')
}

async function handleSave() {
  const pairs = [
    ['patrol.cpu_warning', 'patrol.cpu_critical'],
    ['patrol.memory_warning', 'patrol.memory_critical'],
    ['patrol.disk_warning', 'patrol.disk_critical'],
    ['patrol.load_warning', 'patrol.load_critical'],
  ]
  for (const [warn, crit] of pairs) {
    if (thresholds[crit] < thresholds[warn]) {
      ElMessage.error('严重阈值不能小于警告阈值')
      return
    }
  }

  saving.value = true
  try {
    const data: Record<string, string> = {}
    for (const [key, value] of Object.entries(thresholds)) data[key] = String(value)
    await updatePatrolThresholdsBulk(data)
    ElMessage.success('阈值已保存，将在下次巡检生效')
    close()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '保存巡检阈值失败')
  } finally {
    saving.value = false
  }
}

watch(
  () => props.modelValue,
  (open) => {
    if (open) fetchThresholds()
  },
)
</script>

<style scoped>
.threshold-scrim {
  position: fixed;
  inset: 0;
  z-index: 3000;
  background: rgba(18, 20, 26, 0.28);
  backdrop-filter: blur(3px);
}

.threshold-drawer {
  position: fixed;
  top: 14px;
  right: 14px;
  bottom: 14px;
  width: min(520px, calc(100vw - 28px));
  z-index: 3001;
  display: grid;
  grid-template-rows: auto 1fr auto;
  border-radius: 24px;
  background: linear-gradient(180deg, rgba(252, 251, 248, 0.98), rgba(244, 241, 234, 0.98));
  border: 1px solid rgba(255, 255, 255, 0.7);
  box-shadow: 0 24px 60px rgba(18, 20, 26, 0.18);
  color: #12141a;
  overflow: hidden;
}

.drawer-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  padding: 22px 22px 16px;
  border-bottom: 1px solid rgba(18, 20, 26, 0.08);
}

.eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
  color: #0f766e;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.eyebrow::before {
  content: '';
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #0f766e;
  box-shadow: 0 0 0 4px rgba(15, 118, 110, 0.12);
}

.drawer-head h3 {
  margin: 0;
  font-size: 22px;
  letter-spacing: -0.04em;
}

.drawer-head p {
  margin: 6px 0 0;
  color: #6b7280;
  font-size: 13px;
  line-height: 1.5;
}

.icon-btn {
  width: 36px;
  height: 36px;
  border-radius: 12px;
  border: 1px solid rgba(18, 20, 26, 0.14);
  background: rgba(255, 255, 255, 0.7);
  cursor: pointer;
  font-size: 18px;
  line-height: 1;
  color: #2a2f3a;
}

.drawer-body {
  overflow: auto;
  padding: 18px 22px 8px;
}

.preset-rail {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin-bottom: 18px;
}

.preset {
  padding: 14px 12px;
  border-radius: 16px;
  border: 1px solid rgba(18, 20, 26, 0.08);
  background: rgba(255, 255, 255, 0.65);
  cursor: pointer;
  text-align: left;
  transition: 160ms ease;
  font: inherit;
  color: inherit;
}

.preset:hover {
  border-color: rgba(15, 118, 110, 0.24);
}

.preset.active {
  background: linear-gradient(180deg, rgba(15, 118, 110, 0.12), rgba(255, 255, 255, 0.8));
  border-color: rgba(15, 118, 110, 0.3);
  box-shadow: inset 0 0 0 1px rgba(15, 118, 110, 0.08);
}

.preset .kicker {
  display: block;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #9aa3b2;
  margin-bottom: 6px;
}

.preset strong {
  display: block;
  font-size: 15px;
  margin-bottom: 4px;
}

.preset span {
  display: block;
  color: #6b7280;
  font-size: 12px;
  line-height: 1.4;
}

.metric-stack {
  display: grid;
  gap: 12px;
}

.metric {
  border-radius: 18px;
  border: 1px solid rgba(18, 20, 26, 0.08);
  background: rgba(255, 255, 255, 0.72);
  padding: 16px;
}

.metric-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
}

.metric-identity {
  display: flex;
  align-items: center;
  gap: 12px;
}

.glyph {
  width: 40px;
  height: 40px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  background: #ebe6db;
  color: #2a2f3a;
  flex-shrink: 0;
}

.glyph :deep(svg) {
  width: 20px;
  height: 20px;
  stroke: currentColor;
  fill: none;
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.metric-identity h4 {
  margin: 0;
  font-size: 15px;
  letter-spacing: -0.02em;
}

.metric-identity small {
  display: block;
  margin-top: 2px;
  color: #6b7280;
  font-size: 12px;
}

.unit-pill {
  padding: 4px 8px;
  border-radius: 999px;
  background: #ebe6db;
  color: #6b7280;
  font-size: 11px;
  font-weight: 700;
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
  white-space: nowrap;
}

.range-map {
  height: 14px;
  border-radius: 999px;
  overflow: hidden;
  display: grid;
  grid-template-columns: var(--safe) var(--warnw) var(--critw);
  margin-bottom: 16px;
  background: #dfe5dc;
}

.range-map .z-safe { background: linear-gradient(90deg, #6f9d78, #4f8a5d); }
.range-map .z-warn { background: linear-gradient(90deg, #e0a24a, #c47b16); }
.range-map .z-crit { background: linear-gradient(90deg, #e06a3b, #c2410c); }

.range-labels {
  display: flex;
  justify-content: space-between;
  margin-top: -10px;
  margin-bottom: 14px;
  font-size: 11px;
  color: #9aa3b2;
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
  gap: 6px;
}

.dual-controls {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.control {
  padding: 12px;
  border-radius: 14px;
  background: rgba(244, 241, 234, 0.7);
}

.control.warn { background: rgba(196, 123, 22, 0.14); }
.control.crit { background: rgba(194, 65, 12, 0.12); }

.control-label {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-size: 12px;
  font-weight: 700;
  color: #2a2f3a;
}

.control-label em {
  font-style: normal;
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
  font-size: 16px;
  letter-spacing: -0.03em;
}

input[type='range'] {
  -webkit-appearance: none;
  appearance: none;
  width: 100%;
  height: 4px;
  border-radius: 999px;
  background: rgba(18, 20, 26, 0.12);
  outline: none;
}

input[type='range']::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #181b22;
  border: 2px solid #fff;
  box-shadow: 0 2px 8px rgba(18, 20, 26, 0.2);
  cursor: pointer;
}

input[type='range']::-moz-range-thumb {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #181b22;
  border: 2px solid #fff;
  box-shadow: 0 2px 8px rgba(18, 20, 26, 0.2);
  cursor: pointer;
}

.load-note {
  margin-top: 10px;
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(18, 20, 26, 0.04);
  color: #6b7280;
  font-size: 12px;
  line-height: 1.5;
}

.drawer-foot {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 16px 22px 20px;
  border-top: 1px solid rgba(18, 20, 26, 0.08);
  background: rgba(252, 251, 248, 0.9);
}

.foot-hint {
  color: #6b7280;
  font-size: 12px;
  line-height: 1.5;
  max-width: 240px;
}

.foot-actions {
  display: flex;
  gap: 8px;
}

.btn {
  appearance: none;
  border: 1px solid rgba(18, 20, 26, 0.14);
  background: rgba(255, 255, 255, 0.72);
  color: #2a2f3a;
  border-radius: 999px;
  padding: 11px 16px;
  font: inherit;
  font-size: 13px;
  font-weight: 650;
  cursor: pointer;
  transition: 160ms ease;
}

.btn:hover {
  transform: translateY(-1px);
  border-color: rgba(15, 118, 110, 0.28);
  box-shadow: 0 10px 24px rgba(18, 20, 26, 0.06);
}

.btn.primary {
  background: #181b22;
  border-color: #181b22;
  color: #f7f4ee;
}

.btn:disabled {
  opacity: 0.65;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.threshold-fade-enter-active,
.threshold-fade-leave-active {
  transition: opacity 0.22s ease;
}
.threshold-fade-enter-from,
.threshold-fade-leave-to {
  opacity: 0;
}

.threshold-slide-enter-active,
.threshold-slide-leave-active {
  transition: transform 0.24s cubic-bezier(.2, .8, .2, 1), opacity 0.24s ease;
}
.threshold-slide-enter-from,
.threshold-slide-leave-to {
  transform: translateX(24px);
  opacity: 0;
}

@media (max-width: 720px) {
  .threshold-drawer {
    width: calc(100vw - 20px);
    right: 10px;
    top: 10px;
    bottom: 10px;
  }
  .preset-rail,
  .dual-controls {
    grid-template-columns: 1fr;
  }
  .drawer-foot {
    flex-direction: column;
    align-items: stretch;
  }
  .foot-hint {
    max-width: none;
  }
  .foot-actions {
    justify-content: flex-end;
  }
}
</style>
