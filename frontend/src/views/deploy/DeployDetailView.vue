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
          <div v-if="record.jenkins_build_url" class="meta-item">
            <span class="meta-label">Jenkins</span>
            <a class="meta-link" :href="record.jenkins_build_url" target="_blank" rel="noopener">
              构建 #{{ record.jenkins_build_number }} 日志 ↗
            </a>
          </div>
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

    <!-- 回滚对话框 -->
    <el-dialog v-model="rollbackDialogVisible" title="回滚部署" width="560px" top="5vh" aria-labelledby="rollback-dialog-title">
      <div v-loading="loadingTargets" class="rollback-content">
        <p class="rollback-hint">选择回滚目标：</p>
        <el-radio-group v-model="rollbackTarget" class="rollback-options">
          <el-radio value="last" class="rollback-radio">
            <div class="rollback-option">
              <div class="rollback-option-title">回滚到上一次成功部署</div>
              <div v-if="rollbackTargets.records.length > 0" class="rollback-option-desc">
                部署 #{{ rollbackTargets.records[0].id }} · 版本 {{ rollbackTargets.records[0].version || '—' }} · {{ formatTime(rollbackTargets.records[0].created_at) }}
              </div>
              <div v-else class="rollback-option-desc">无可用的历史部署记录</div>
            </div>
          </el-radio>

          <div class="rollback-divider">或者选择构建版本：</div>

          <el-radio
            v-for="build in rollbackTargets.builds"
            :key="build.build_number"
            :value="`build:${build.build_number}`"
            class="rollback-radio"
          >
            <div class="rollback-option">
              <div class="rollback-option-title">
                构建 #{{ build.build_number }}
                <el-tag v-if="build.tag" size="small" type="warning">{{ build.tag }}</el-tag>
              </div>
              <div class="rollback-option-desc">
                <span v-if="build.commit">Commit: {{ build.commit.substring(0, 7) }} · </span>
                <span v-if="build.branch">分支: {{ build.branch }} · </span>
                {{ formatTime(build.created_at) }}
              </div>
            </div>
          </el-radio>

          <el-empty v-if="!loadingTargets && rollbackTargets.builds.length === 0" description="暂无可用的构建版本" :image-size="60" />
        </el-radio-group>
      </div>
      <template #footer>
        <el-button @click="rollbackDialogVisible = false">取消</el-button>
        <el-button type="warning" @click="confirmRollback" :loading="rollingback" :disabled="rollbackTarget === 'last' && rollbackTargets.records.length === 0">
          <el-icon><Refresh /></el-icon>确认回滚
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onActivated, onDeactivated, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { getDeployRecord, cancelDeploy, rollbackDeploy, getRollbackTargets } from '@/api/deploy'

const route = useRoute()
const router = useRouter()
const recordId = ref(Number(route.params.id))
const loading = ref(true)
const cancelling = ref(false)
const rollingback = ref(false)
const record = ref<any>({})
const logContainer = ref<HTMLElement | null>(null)

// 回滚对话框
const rollbackDialogVisible = ref(false)
const rollbackTarget = ref('last')  // 'last' 或 'build:xxx'
const rollbackTargets = ref<{ records: any[]; builds: any[] }>({ records: [], builds: [] })
const loadingTargets = ref(false)

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

const canCancel = computed(() => ['pending', 'building', 'deploying', 'triggering'].includes(record.value.status))
const canRollback = computed(() => ['success', 'failed', 'cancelled'].includes(record.value.status))

const statusLabel = (v: string) => ({ pending: '待执行', building: '构建中', deploying: '部署中', triggering: 'Jenkins执行中', success: '成功', failed: '失败', cancelled: '已取消' }[v] || v)
const statusType = (v: string) => ({ pending: 'info', building: 'warning', deploying: 'warning', triggering: 'warning', success: 'success', failed: 'danger', cancelled: 'info' }[v] || '') as any
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

let pollTimer: ReturnType<typeof setInterval> | null = null
let lastLogLen = 0

function startSSE() {
  lastLogLen = record.value.log?.length || 0

  pollTimer = setInterval(async () => {
    try {
      const res: any = await getDeployRecord(recordId.value)
      const newLog = res.data.log || ''
      if (newLog.length > lastLogLen) {
        record.value.log = newLog
        lastLogLen = newLog.length
        scrollToBottom()
      }
      if (res.data.status) record.value.status = res.data.status
      if (['success', 'failed', 'cancelled'].includes(res.data.status)) {
        stopSSE()
        fetchRecord() // 刷新完整记录（含 duration 等字段）
      }
    } catch { /* ignore */ }
  }, 1000)
}

function stopSSE() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
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
  // 打开回滚对话框
  rollbackTarget.value = 'last'
  rollbackDialogVisible.value = true
  loadingTargets.value = true
  try {
    const res: any = await getRollbackTargets(recordId.value)
    rollbackTargets.value = res.data
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '获取回滚目标失败')
  } finally {
    loadingTargets.value = false
  }
}

async function confirmRollback() {
  rollingback.value = true
  try {
    let buildNumber: string | undefined
    if (rollbackTarget.value.startsWith('build:')) {
      buildNumber = rollbackTarget.value.substring(6)
    }
    const res: any = await rollbackDeploy(recordId.value, buildNumber)
    ElMessage.success('回滚已触发')
    rollbackDialogVisible.value = false
    router.push(`/deploy/records/${res.data.id}`)
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '回滚失败')
  } finally {
    rollingback.value = false
  }
}

onActivated(() => {
  stopSSE()
  recordId.value = Number(route.params.id)
  fetchRecord().then(() => {
    // 如果还在执行中（含模式 B 的 triggering），启动轮询
    if (['pending', 'building', 'deploying', 'triggering'].includes(record.value.status)) {
      startSSE()
    }
  })
})

onDeactivated(() => {
  stopSSE()
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

/* ── 回滚对话框 ── */
.rollback-content {
  min-height: 200px;
}

.rollback-hint {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 16px;
}

.rollback-options {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
}

.rollback-radio {
  width: 100%;
  margin-right: 0;
  padding: 12px;
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  background: var(--surface-color);
}

.rollback-radio:hover {
  border-color: var(--primary-color);
}

.rollback-option {
  margin-left: 8px;
}

.rollback-option-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 8px;
}

.rollback-option-desc {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 4px;
}

.rollback-divider {
  font-size: 13px;
  color: var(--text-muted);
  padding: 8px 0;
}
</style>
