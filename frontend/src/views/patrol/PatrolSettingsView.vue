<template>
  <div>
    <div class="page-header">
      <div style="display:flex;align-items:center;gap:12px">
        <el-button text @click="$router.push('/patrol')"><el-icon><ArrowLeft /></el-icon> 返回</el-button>
        <h2 class="page-title" style="margin:0">巡检阈值配置</h2>
      </div>
      <div style="display:flex;gap:8px">
        <el-button @click="handleReset">恢复默认</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">
          <el-icon><Check /></el-icon> 保存配置
        </el-button>
      </div>
    </div>

    <div class="threshold-grid" v-loading="loading">
      <div v-for="group in groups" :key="group.key" class="threshold-card">
        <div class="card-header" :style="{ background: group.bg }">
          <span class="card-icon">{{ group.icon }}</span>
          <span class="card-title">{{ group.title }}</span>
          <span class="card-unit">{{ group.unit }}</span>
        </div>
        <div class="card-body">
          <!-- 警告阈值 -->
          <div class="slider-row">
            <div class="slider-label">
              <span class="dot warning"></span>
              <span>警告阈值</span>
              <span class="slider-value">{{ thresholds[group.warnKey] }}{{ group.unit }}</span>
            </div>
            <el-slider
              v-model="thresholds[group.warnKey]"
              :min="group.min"
              :max="group.max"
              :step="group.step"
              :marks="group.marks"
              :format-tooltip="(v: number) => `${v}${group.unit}`"
              class="threshold-slider warning-slider"
              @change="onSliderChange"
            />
          </div>
          <!-- 严重阈值 -->
          <div class="slider-row">
            <div class="slider-label">
              <span class="dot critical"></span>
              <span>严重阈值</span>
              <span class="slider-value">{{ thresholds[group.critKey] }}{{ group.unit }}</span>
            </div>
            <el-slider
              v-model="thresholds[group.critKey]"
              :min="group.min"
              :max="group.max"
              :step="group.step"
              :marks="group.marks"
              :format-tooltip="(v: number) => `${v}${group.unit}`"
              class="threshold-slider critical-slider"
              @change="onSliderChange"
            />
          </div>
          <!-- 预览条 -->
          <div class="preview-bar">
            <div class="preview-zone safe" :style="{ width: thresholds[group.warnKey] + '%' }">
              <span v-if="thresholds[group.warnKey] > 15">正常</span>
            </div>
            <div class="preview-zone warn" :style="{ width: (thresholds[group.critKey] - thresholds[group.warnKey]) + '%' }">
              <span v-if="thresholds[group.critKey] - thresholds[group.warnKey] > 10">警告</span>
            </div>
            <div class="preview-zone crit" :style="{ width: (100 - thresholds[group.critKey]) + '%' }">
              <span v-if="100 - thresholds[group.critKey] > 10">严重</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 快捷预设 -->
    <div class="data-card" style="margin-top:16px">
      <div style="display:flex;align-items:center;gap:16px">
        <span style="font-weight:600;font-size:14px">快捷预设</span>
        <el-button-group>
          <el-button size="small" :type="activePreset === 'strict' ? 'primary' : 'default'" @click="applyPreset('strict')">严格</el-button>
          <el-button size="small" :type="activePreset === 'normal' ? 'primary' : 'default'" @click="applyPreset('normal')">标准</el-button>
          <el-button size="small" :type="activePreset === 'relaxed' ? 'primary' : 'default'" @click="applyPreset('relaxed')">宽松</el-button>
        </el-button-group>
        <el-alert type="info" :closable="false" :show-icon="true" style="flex:1;padding:6px 12px">
          <template #title>修改后下次巡检生效，已有报告不受影响</template>
        </el-alert>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Check } from '@element-plus/icons-vue'
import { getPatrolThresholds, updatePatrolThresholdsBulk } from '@/api/patrol'

const router = useRouter()
const loading = ref(false)
const saving = ref(false)
const activePreset = ref<string>('normal')

const DEFAULTS = {
  'patrol.cpu_warning': 80, 'patrol.cpu_critical': 95,
  'patrol.memory_warning': 85, 'patrol.memory_critical': 95,
  'patrol.disk_warning': 85, 'patrol.disk_critical': 95,
  'patrol.load_warning': 5, 'patrol.load_critical': 10,
}

const thresholds = reactive<Record<string, number>>({ ...DEFAULTS })

const groups = [
  {
    key: 'cpu', icon: '🖥️', title: 'CPU 使用率', unit: '%',
    warnKey: 'patrol.cpu_warning', critKey: 'patrol.cpu_critical',
    min: 0, max: 100, step: 5,
    marks: { 0: '0', 50: '50', 100: '100' },
    bg: 'linear-gradient(135deg, #667eea22, #764ba222)',
  },
  {
    key: 'mem', icon: '📊', title: '内存使用率', unit: '%',
    warnKey: 'patrol.memory_warning', critKey: 'patrol.memory_critical',
    min: 0, max: 100, step: 5,
    marks: { 0: '0', 50: '50', 100: '100' },
    bg: 'linear-gradient(135deg, #f093fb22, #f5576c22)',
  },
  {
    key: 'disk', icon: '💾', title: '磁盘使用率', unit: '%',
    warnKey: 'patrol.disk_warning', critKey: 'patrol.disk_critical',
    min: 0, max: 100, step: 5,
    marks: { 0: '0', 50: '50', 100: '100' },
    bg: 'linear-gradient(135deg, #4facfe22, #00f2fe22)',
  },
  {
    key: 'load', icon: '⚡', title: '系统负载', unit: '',
    warnKey: 'patrol.load_warning', critKey: 'patrol.load_critical',
    min: 0, max: 30, step: 1,
    marks: { 0: '0', 10: '10', 20: '20', 30: '30' },
    bg: 'linear-gradient(135deg, #43e97b22, #38f9d722)',
  },
]

const PRESETS: Record<string, Record<string, number>> = {
  strict:  { 'patrol.cpu_warning': 70, 'patrol.cpu_critical': 90, 'patrol.memory_warning': 75, 'patrol.memory_critical': 90, 'patrol.disk_warning': 75, 'patrol.disk_critical': 90, 'patrol.load_warning': 3, 'patrol.load_critical': 8 },
  normal:  { ...DEFAULTS },
  relaxed: { 'patrol.cpu_warning': 90, 'patrol.cpu_critical': 98, 'patrol.memory_warning': 90, 'patrol.memory_critical': 98, 'patrol.disk_warning': 90, 'patrol.disk_critical': 98, 'patrol.load_warning': 8, 'patrol.load_critical': 15 },
}

function applyPreset(name: string) {
  const p = PRESETS[name]
  if (!p) return
  Object.assign(thresholds, p)
  activePreset.value = name
  ElMessage.success(`已应用「${name === 'strict' ? '严格' : name === 'normal' ? '标准' : '宽松'}」预设`)
}

function onSliderChange() {
  // 手动拖滑块时取消预设高亮
  activePreset.value = ''
}

async function fetchThresholds() {
  loading.value = true
  try {
    const res: any = await getPatrolThresholds()
    for (const item of res.data.items) {
      const num = parseFloat(item.value)
      if (!isNaN(num)) thresholds[item.key] = num
    }
  } finally { loading.value = false }
}

function handleReset() {
  Object.assign(thresholds, DEFAULTS)
  activePreset.value = ''
  ElMessage.success('已恢复默认值（未保存）')
}

async function handleSave() {
  // 校验
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
    for (const [k, v] of Object.entries(thresholds)) data[k] = String(v)
    await updatePatrolThresholdsBulk(data)
    ElMessage.success('巡检阈值保存成功')
  } finally { saving.value = false }
}

onMounted(fetchThresholds)
</script>

<style scoped>
.threshold-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.threshold-card {
  border: 1px solid var(--border-color);
  border-radius: 12px;
  overflow: hidden;
  background: #fff;
  transition: box-shadow 0.2s;
}
.threshold-card:hover {
  box-shadow: 0 4px 16px rgba(0,0,0,0.06);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 20px;
}
.card-icon { font-size: 22px; }
.card-title { font-size: 15px; font-weight: 600; }
.card-unit {
  margin-left: auto;
  font-size: 12px;
  color: var(--text-muted);
  background: var(--el-fill-color-lighter);
  padding: 2px 8px;
  border-radius: 4px;
}

.card-body {
  padding: 16px 20px 20px;
}

.slider-row {
  margin-bottom: 16px;
}
.slider-label {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
  font-size: 13px;
  color: var(--text-muted);
}
.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.dot.warning { background: var(--el-color-warning); }
.dot.critical { background: var(--el-color-danger); }
.slider-value {
  margin-left: auto;
  font-weight: 700;
  font-size: 18px;
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
}

.threshold-slider {
  margin-left: 4px;
}
.warning-slider :deep(.el-slider__bar) {
  background: var(--el-color-warning);
}
.warning-slider :deep(.el-slider__button) {
  border-color: var(--el-color-warning);
}
.critical-slider :deep(.el-slider__bar) {
  background: var(--el-color-danger);
}
.critical-slider :deep(.el-slider__button) {
  border-color: var(--el-color-danger);
}

/* 预览条 */
.preview-bar {
  display: flex;
  height: 28px;
  border-radius: 6px;
  overflow: hidden;
  margin-top: 4px;
  font-size: 11px;
  font-weight: 600;
}
.preview-zone {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  transition: width 0.3s;
  min-width: 0;
}
.preview-zone.safe { background: var(--el-color-success); }
.preview-zone.warn { background: var(--el-color-warning); }
.preview-zone.crit { background: var(--el-color-danger); }

/* 响应式 */
@media (max-width: 900px) {
  .threshold-grid {
    grid-template-columns: 1fr;
  }
}
</style>
