<template>
  <div>
    <div class="page-header">
      <h2 class="page-title">部署详情 #{{ record.id || '—' }}</h2>
      <div class="header-actions">
        <el-button v-if="canRollback" type="warning" @click="handleRollback" :loading="rollingback">
          <el-icon><Refresh /></el-icon>回滚
        </el-button>
        <el-button v-if="canCancel" type="danger" @click="handleCancel" :loading="cancelling">取消部署</el-button>
        <el-button @click="$router.back()">返回</el-button>
      </div>
    </div>

    <div v-loading="loading" class="detail-layout">
      <!-- 左侧：日志 -->
      <div class="detail-main">
        <!-- 状态进度条 -->
        <div class="status-bar">
          <div
            v-for="(step, idx) in steps"
            :key="step.key"
            class="status-step"
            :class="stepClass(step.key, idx)"
          >
            <div class="step-dot" />
            <span class="step-label">{{ step.label }}</span>
          </div>
        </div>

        <!-- 日志终端 -->
        <div class="log-terminal" ref="logContainer">
          <pre class="log-content">{{ record.log || '等待日志输出…' }}</pre>
        </div>
      </div>

      <!-- 右侧：元信息 -->
      <div class="detail-sidebar">
        <div class="meta-card">
          <h4 class="meta-title">部署信息</h4>
          <div class="meta-item"><span class="meta-label">应用</span><span class="meta-value">{{ record.app_name || '—' }}</span></div>
          <div class="meta-item"><span class="meta-label">环境</span><span class="meta-value">{{ record.env_name || '—' }}</span></div>
          <div class="meta-item"><span class="meta-label">版本</span><code class="meta-code">{{ record.version || '—' }}</code></div>
          <div class="meta-item">
            <span class="meta-label">状态</span>
            <el-tag :type="statusType(record.status)" size="small">{{ statusLabel(record.status) }}</el-tag>
          </div>
          <div class="meta-item"><span class="meta-label">触发方式</span><span class="meta-value">{{ triggerLabel(record.trigger_type) }}</span></div>
          <div class="meta-item"><span class="meta-label">触发人</span><span class="meta-value">{{ record.trigger_user_name || '—' }}</span></div>
          <div class="meta-item"><span class="meta-label">耗时</span><span class="meta-value">{{ record.duration != null ? formatDuration(record.duration) : '—' }}</span></div>
          <div class="meta-item"><span class="meta-label">开始时间</span><span class="meta-value">{{ formatTime(record.started_at) }}</span></div>
          <div class="meta-item"><span class="meta-label">结束时间</span><span class="meta-value">{{ formatTime(record.finished_at) }}</span></div>
          <div v-if="record.error_message" class="meta-item">
            <span class="meta-label">错误</span>
            <span class="meta-error">{{ record.error_message }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { getDeployRecord, cancelDeploy, rollbackDeploy } from '@/api/deploy'

const route = useRoute()
const router = useRouter()
const recordId = ref(Number(route.params.id))
const loading = ref(true)
const cancelling = ref(false)
const rollingback = ref(false)
const record = ref<any>({})
const logContainer = ref<HTMLElement | null>(null)
let eventSource: EventSource | null = null

const steps = [
  { key: 'pending', label: '待执行' },
  { key: 'building', label: '构建' },
  { key: 'deploying', label: '部署' },
  { key: 'success', label: '完成' },
]

const stepOrder = ['pending', 'building', 'deploying', 'success']

function stepClass(stepKey: string, idx: number) {
  const currentIdx = stepOrder.indexOf(record.value.status || 'pending')
  // failed/cancelled 视为在当前阶段失败
  if (record.value.status === 'failed' || record.value.status === 'cancelled') {
    if (idx <= currentIdx) return idx < currentIdx ? 'step-done' : 'step-failed'
    return ''
  }
  if (idx < currentIdx) return 'step-done'
  if (idx === currentIdx) return 'step-active'
  return ''
}

const canCancel = computed(() => ['pending', 'building', 'deploying'].includes(record.value.status))
const canRollback = computed(() => ['success', 'failed', 'cancelled'].includes(record.value.status))

const statusLabel = (v: string) => ({ pending: '待执行', building: '构建中', deploying: '部署中', success: '成功', failed: '失败', cancelled: '已取消' }[v] || v)
const statusType = (v: string) => ({ pending: 'info', building: 'warning', deploying: 'warning', success: 'success', failed: 'danger', cancelled: 'info' }[v] || '') as any
const triggerLabel = (v: string) => ({ manual: '手动', rollback: '回滚', webhook: 'Webhook' }[v] || v)

function formatDuration(sec: number) {
  if (sec < 60) return `${Math.round(sec)}s`
  const m = Math.floor(sec / 60)
  const s = Math.round(sec % 60)
  return `${m}m ${s}s`
}

function formatTime(iso: string) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('zh-CN')
}

function scrollToBottom() {
  nextTick(() => {
    if (logContainer.value) {
      logContainer.value.scrollTop = logContainer.value.scrollHeight
    }
  })
}

async function fetchRecord() {
  try {
    const res: any = await getDeployRecord(recordId.value)
    record.value = res.data
    scrollToBottom()
  } finally {
    loading.value = false
  }
}

function startSSE() {
  const token = localStorage.getItem('token') || ''
  const base = import.meta.env.VITE_API_BASE_URL || '/api/v1'
  const url = `${base}/deploy/records/${recordId.value}/log`

  eventSource = new EventSource(url)
  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      if (data.log) {
        record.value.log = (record.value.log || '') + data.log
        scrollToBottom()
      }
      if (data.status) {
        record.value.status = data.status
      }
      if (data.done) {
        eventSource?.close()
        eventSource = null
        // 最终刷新一次完整记录
        fetchRecord()
      }
    } catch {
      // ignore parse errors
    }
  }
  eventSource.onerror = () => {
    // SSE 连接断开，轮询兜底
    eventSource?.close()
    eventSource = null
    if (['pending', 'building', 'deploying'].includes(record.value.status)) {
      setTimeout(fetchRecord, 3000)
    }
  }
}

async function handleCancel() {
  cancelling.value = true
  try {
    await cancelDeploy(recordId.value)
    ElMessage.success('已取消')
    fetchRecord()
  } finally {
    cancelling.value = false
  }
}

async function handleRollback() {
  rollingback.value = true
  try {
    const res: any = await rollbackDeploy(recordId.value)
    ElMessage.success('回滚已触发')
    router.push(`/deploy/records/${res.data.id}`)
  } finally {
    rollingback.value = false
  }
}

onMounted(() => {
  fetchRecord().then(() => {
    // 如果还在执行中，启动 SSE
    if (['pending', 'building', 'deploying'].includes(record.value.status)) {
      startSSE()
    }
  })
})

onBeforeUnmount(() => {
  eventSource?.close()
})
</script>

<style scoped>
.header-actions {
  display: flex;
  gap: 8px;
}

.detail-layout {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}

.detail-main {
  flex: 1;
  min-width: 0;
}

.detail-sidebar {
  width: 280px;
  flex-shrink: 0;
}

/* ── 状态进度条 ── */
.status-bar {
  display: flex;
  align-items: center;
  gap: 0;
  padding: 16px 20px;
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  margin-bottom: 16px;
}

.status-step {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  position: relative;
}

.status-step:not(:last-child)::after {
  content: '';
  flex: 1;
  height: 2px;
  background: var(--border-color);
  margin: 0 12px;
}

.step-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--border-color);
  border: 2px solid var(--border-color);
  flex-shrink: 0;
  transition: all 0.3s ease;
}

.step-label {
  font-size: 13px;
  color: var(--text-muted);
  white-space: nowrap;
}

.step-active .step-dot {
  background: var(--primary-color);
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px var(--primary-bg);
}

.step-active .step-label {
  color: var(--primary-color);
  font-weight: 600;
}

.step-active:not(:last-child)::after {
  background: var(--primary-color);
}

.step-done .step-dot {
  background: var(--success-color);
  border-color: var(--success-color);
}

.step-done .step-label {
  color: var(--success-color);
}

.step-done:not(:last-child)::after {
  background: var(--success-color);
}

.step-failed .step-dot {
  background: var(--danger-color);
  border-color: var(--danger-color);
}

.step-failed .step-label {
  color: var(--danger-color);
  font-weight: 600;
}

/* ── 日志终端 ── */
.log-terminal {
  background: #1a1a2e;
  border: 1px solid #2a2a4a;
  border-radius: var(--border-radius);
  padding: 16px;
  height: 520px;
  overflow-y: auto;
  font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
}

.log-content {
  margin: 0;
  font-size: 13px;
  line-height: 1.7;
  color: #e0e0e0;
  white-space: pre-wrap;
  word-break: break-all;
}

/* ── 元信息卡片 ── */
.meta-card {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: 20px;
}

.meta-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 16px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border-color);
}

.meta-item {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
  font-size: 13px;
}

.meta-item:last-child {
  margin-bottom: 0;
}

.meta-label {
  color: var(--text-muted);
  flex-shrink: 0;
  margin-right: 12px;
}

.meta-value {
  color: var(--text-primary);
  text-align: right;
  word-break: break-all;
}

.meta-code {
  background: var(--bg-color);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
  color: var(--text-primary);
}

.meta-error {
  color: var(--danger-color);
  text-align: right;
  font-size: 12px;
  word-break: break-all;
}

@media (max-width: 768px) {
  .detail-layout {
    flex-direction: column;
  }
  .detail-sidebar {
    width: 100%;
  }
}
</style>
