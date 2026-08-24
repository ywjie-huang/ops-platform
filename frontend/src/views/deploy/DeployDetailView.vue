<template>
  <div v-loading="loading && !record">
    <template v-if="record">
      <!-- 面包屑 -->
      <nav class="crumb" aria-label="面包屑">
        <router-link to="/deploy/records">部署记录</router-link>
        <span class="sep">/</span>
        <span>#{{ record.id }}</span>
      </nav>

      <!-- 英雄区 -->
      <div class="hero">
        <span class="h-title mono">#{{ record.id }}</span>
        <span class="pill" :class="'pill--' + deployStatusType(record.status)">
          <i class="dot" :class="{ 'dot--pulse': active }"></i>{{ deployStatusLabel(record.status) }}
        </span>
        <span class="type-tag">
          <router-link :to="'/deploy/apps/' + record.app_name" class="app-link">{{ record.app_name }}</router-link>
          → {{ record.env_name }}
        </span>
        <code class="mono hero-ver">{{ record.version }}</code>
        <span v-if="record.trigger_type === 'rollback'" class="type-tag type-tag--approval">回滚单</span>
        <span class="sp"></span>
        <el-button v-if="active && canExecute" type="danger" plain @click="handleCancel">取消部署</el-button>
        <template v-if="!active">
          <el-button v-if="canRollback" @click="openRollback">
            <el-icon><RefreshLeft /></el-icon>回滚
          </el-button>
          <el-button v-if="record.status === 'failed' && canExecute" @click="handleRedeploy">重新部署</el-button>
        </template>
        <el-button v-if="record.jenkins_build_url" type="primary" @click="openJenkins">
          {{ active ? '在 Jenkins 中查看 #' + record.jenkins_build_number : '查看 Jenkins 日志 #' + record.jenkins_build_number }}
          <el-icon><TopRight /></el-icon>
        </el-button>
      </div>

      <!-- 步骤条 -->
      <div class="steps" role="list" aria-label="部署阶段">
        <template v-for="(s, idx) in steps" :key="s.key">
          <div v-if="idx > 0" class="step-line" :class="lineClass(idx)"></div>
          <div class="step" :class="s.state" role="listitem">
            <div class="step-dot">
              <el-icon v-if="s.state === 'done'"><Check /></el-icon>
              <el-icon v-else-if="s.state === 'fail'"><Close /></el-icon>
              <template v-else>{{ idx + 1 }}</template>
            </div>
            <div class="step-txt">
              <span class="step-label">{{ s.label }}</span>
              <span class="step-sub">{{ s.sub || '—' }}</span>
            </div>
          </div>
        </template>
      </div>

      <!-- Jenkins 横幅（执行中） -->
      <div v-if="active && record.status !== 'pending'" class="jenkins-banner" role="status">
        <div class="jb-ico"><el-icon><Setting /></el-icon></div>
        <div class="jb-body">
          <div class="jb-title">
            {{ record.jenkins_build_number ? 'Jenkins 构建 #' + record.jenkins_build_number + ' 执行中' : 'Jenkins 任务排队触发中' }}
            <span v-if="jenkinsJobName" class="jb-job">（{{ jenkinsJobName }}）</span>
          </div>
          <div class="jb-sub">平台已将 8 个参数（APP_NAME / ENV / VERSION / RECORD_ID / CALLBACK_TOKEN …）下发给 Job，构建结束后 Jenkins 将携带一次性 Token 回调本平台更新状态</div>
        </div>
        <span class="sp"></span>
        <el-button v-if="record.jenkins_build_url" @click="openJenkins">在 Jenkins 中查看</el-button>
      </div>

      <!-- 待审批横幅 -->
      <div v-else-if="record.status === 'pending'" class="jenkins-banner jenkins-banner--wait" role="status">
        <div class="jb-ico jb-ico--wait"><el-icon><Clock /></el-icon></div>
        <div class="jb-body">
          <div class="jb-title">等待审批</div>
          <div class="jb-sub">该环境需要审批：审批通过后平台自动触发 Jenkins 执行。可前往审批中心查看，或取消本次部署。</div>
        </div>
        <span class="sp"></span>
        <el-button @click="$router.push('/deploy/approvals')">前往审批中心</el-button>
      </div>

      <!-- 错误横幅 -->
      <div v-if="record.status === 'failed'" class="err-banner" role="alert">
        <el-icon class="e-ico"><CircleClose /></el-icon>
        <div>
          <div class="err-title">{{ record.jenkins_build_number ? 'Jenkins 构建 #' + record.jenkins_build_number + ' 失败' : '部署失败' }}</div>
          <div class="err-body">{{ record.error_message || '失败原因来自 Jenkins 回调 message，完整堆栈请查看 Jenkins 构建日志。修复后可直接「重新部署」，或「回滚」到上一成功版本。' }}</div>
        </div>
      </div>
      <!-- 日志 + 侧栏 -->
      <div class="detail-layout">
        <div class="term">
          <div class="term-head">
            <div class="term-dots" aria-hidden="true"><i class="td td--r"></i><i class="td td--y"></i><i class="td td--g"></i></div>
            <span class="term-title">部署日志 · {{ active ? '实时轮询中' : '已结束' }}</span>
            <span class="sp"></span>
            <button v-if="active" type="button" class="term-btn" :class="{ on: followLog }" @click="followLog = !followLog">跟随滚动</button>
            <button type="button" class="term-btn" @click="copyLog">复制</button>
            <button type="button" class="term-btn" @click="downloadLog">下载</button>
          </div>
          <div ref="termBodyRef" class="term-body" role="log" aria-live="polite">
            <div v-for="(line, i) in logLines" :key="i" class="term-line">
              <span v-if="line.time" class="lt">[{{ line.time }}]</span>
              <span :class="line.cls">{{ line.text }} </span>
            </div>
            <div v-if="active" class="term-line"><span class="cursor-blink"></span></div>
            <div v-if="!logLines.length && !active" class="term-line"><span class="lt">暂无日志</span></div>
          </div>
        </div>

        <aside>
          <div class="meta-card">
            <div class="meta-title">部署信息</div>
            <div class="meta-item"><span class="meta-k">应用</span><span class="meta-v">{{ record.app_name }}</span></div>
            <div class="meta-item">
              <span class="meta-k">环境</span>
              <span class="meta-v">{{ record.env_name }}<span v-if="record.approval" class="approval-tag">需审批</span></span>
            </div>
            <div class="meta-item"><span class="meta-k">版本</span><span class="meta-v"><code class="mono">{{ record.version }}</code></span></div>
            <div class="meta-item"><span class="meta-k">触发方式</span><span class="meta-v">{{ triggerTypeLabel(record.trigger_type) }}</span></div>
            <div class="meta-item"><span class="meta-k">触发人</span><span class="meta-v">{{ record.trigger_user_name || '—' }}</span></div>
            <div v-if="record.approval" class="meta-item">
              <span class="meta-k">审批</span>
              <span class="meta-v">{{ approvalText }}</span>
            </div>
            <div v-if="record.rollback_from" class="meta-item">
              <span class="meta-k">回滚来源</span>
              <span class="meta-v"><router-link class="meta-link" :to="'/deploy/records/' + record.rollback_from">部署单 #{{ record.rollback_from }}</router-link></span>
            </div>
            <div class="meta-item">
              <span class="meta-k">Jenkins</span>
              <span class="meta-v">
                <a v-if="record.jenkins_build_url" class="meta-link mono" :href="record.jenkins_build_url" target="_blank" rel="noopener noreferrer">构建 #{{ record.jenkins_build_number }} ↗</a>
                <span v-else class="muted">—</span>
              </span>
            </div>
            <div class="meta-item"><span class="meta-k">开始时间</span><span class="meta-v">{{ timeText(record.started_at || record.created_at) }}</span></div>
            <div v-if="record.finished_at" class="meta-item"><span class="meta-k">结束时间</span><span class="meta-v">{{ timeText(record.finished_at) }}</span></div>
            <div class="meta-item">
              <span class="meta-k">{{ active ? '已耗时' : '耗时' }}</span>
              <span class="meta-v" :class="{ 'elapsed-live': active }">{{ active ? elapsedText : formatDeployDuration(record.duration) }}</span>
            </div>
            <div v-if="record.error_message" class="meta-item">
              <span class="meta-k">错误</span>
              <span class="meta-v meta-v--err">{{ record.error_message }}</span>
            </div>
          </div>
          <div class="side-actions">
            <el-button v-if="active && canExecute" type="danger" plain class="side-btn" @click="handleCancel">取消部署</el-button>
            <el-button v-if="!active && canRollback" class="side-btn" @click="openRollback">
              <el-icon><RefreshLeft /></el-icon>回滚到历史版本
            </el-button>
            <el-button v-if="!active && record.status === 'failed' && canExecute" class="side-btn" @click="handleRedeploy">重新部署</el-button>
          </div>
        </aside>
      </div>

      <!-- 回滚弹窗 -->
      <el-dialog v-model="rollbackVisible" title="回滚部署" width="540px" :close-on-click-modal="false">
        <p class="rb-note">
          选择要回滚到的历史成功版本。回滚将以 <code class="mono rb-code">RELEASE_MODE=rollback</code>
          重触发同一 Jenkins Job（跳过构建，直接部署旧产物），并生成一条新的部署记录。
        </p>
        <div v-loading="rollbackLoading">
          <div v-if="rollbackTargets.length" class="radio-list" role="radiogroup" aria-label="选择回滚目标版本">
            <div
              v-for="(t, i) in rollbackTargets"
              :key="t.id"
              class="radio-item"
              :class="{ sel: rollbackTargetId === t.id }"
              role="radio"
              :aria-checked="rollbackTargetId === t.id"
              tabindex="0"
              @click="rollbackTargetId = t.id"
              @keyup.enter="rollbackTargetId = t.id"
            >
              <span class="radio-dot"></span>
              <div class="radio-main">
                <div class="radio-t1">
                  <code class="mono">{{ t.version }}</code>
                  <span v-if="i === 0" class="rec-tag">推荐 · 上一次成功</span>
                </div>
                <div class="radio-t2">
                  部署单 #{{ t.id }} · {{ t.trigger_user_name || '—' }}<template v-if="t.trigger_type === 'rollback'">（回滚）</template>
                  · {{ formatRelativeTime(t.created_at) }}<template v-if="t.duration != null"> · 耗时 {{ formatDeployDuration(t.duration) }}</template>
                </div>
              </div>
            </div>
          </div>
          <el-empty v-else description="没有可回滚的历史成功版本" :image-size="70" />
        </div>
        <template #footer>
          <el-button @click="rollbackVisible = false">取消</el-button>
          <el-button type="danger" :disabled="!rollbackTargetId" :loading="rollbacking" @click="confirmRollback">
            <el-icon><RefreshLeft /></el-icon>{{ rollbackConfirmText }}
          </el-button>
        </template>
      </el-dialog>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onActivated, onDeactivated } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Check, Close, Clock, CircleClose, RefreshLeft, Setting, TopRight,
} from '@element-plus/icons-vue'
import {
  getDeployRecord, cancelDeploy, rollbackDeploy, getRollbackTargets, executeDeploy,
} from '@/api/deploy'
import { useAuthStore } from '@/stores/modules/auth'
import { formatRelativeTime } from '@/utils/time'
import {
  deployStatusLabel, deployStatusType, isActiveStatus, triggerTypeLabel, formatDeployDuration,
} from '@/utils/deployStatus'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const record = ref<any>(null)
const loading = ref(false)
const followLog = ref(true)
const termBodyRef = ref<HTMLElement | null>(null)

const canExecute = computed(() => authStore.hasPermission('deploy.execute'))
const canRollback = computed(() => authStore.hasPermission('deploy.rollback'))

const active = computed(() => record.value && isActiveStatus(record.value.status))

const recordId = () => Number(route.params.id)

// ── 数据加载 + 轮询 ──
async function fetchRecord() {
  loading.value = true
  try {
    const res: any = await getDeployRecord(recordId())
    record.value = res.data
  } finally {
    loading.value = false
  }
}

let tickTimer: ReturnType<typeof setInterval> | null = null
let tickCount = 0
const nowTs = ref(Date.now())

function startTicker() {
  stopTicker()
  tickTimer = setInterval(async () => {
    nowTs.value = Date.now()
    tickCount += 1
    // 每 3s 轮询一次记录状态与日志
    if (tickCount % 3 === 0) {
      await fetchRecord()
      if (!active.value) stopTicker()
    }
  }, 1000)
}

function stopTicker() {
  if (tickTimer) { clearInterval(tickTimer); tickTimer = null }
}

onActivated(async () => {
  await fetchRecord()
  if (active.value) startTicker()
  // 记录列表「回滚」操作带 ?rollback=1 深链直达
  if (route.query.rollback === '1' && !active.value && canRollback.value) {
    openRollback()
  }
})

onDeactivated(stopTicker)

// keep-alive 下切换到另一条记录时重新加载
watch(() => route.params.id, async (n, o) => {
  if (n && n !== o) {
    stopTicker()
    record.value = null
    await fetchRecord()
    if (active.value) startTicker()
  }
})

// ── 耗时 ──
const elapsedText = computed(() => {
  if (!record.value?.created_at) return '—'
  const start = new Date(record.value.created_at).getTime()
  const sec = Math.max(0, (nowTs.value - start) / 1000)
  return formatDeployDuration(sec) + '…'
})

// ── 步骤条 ──
interface StepItem { key: string; label: string; state: 'done' | 'active' | 'fail' | 'idle'; sub: string }

const timeText = (iso: string | null | undefined) => {
  if (!iso) return '—'
  return new Date(iso).toLocaleTimeString('zh-CN', { hour12: false })
}

const steps = computed<StepItem[]>(() => {
  const r = record.value
  if (!r) return []
  const list: StepItem[] = [
    { key: 'submit', label: '已提交', state: 'done', sub: timeText(r.created_at) + ' · ' + (r.trigger_user_name || '—') },
  ]
  const a = r.approval
  if (a) {
    if (a.status === 'approved') {
      list.push({ key: 'approval', label: '审批通过', state: 'done', sub: timeText(a.resolved_at) + ' · ' + (a.approver_name || '—') })
    } else if (a.status === 'rejected') {
      list.push({ key: 'approval', label: '审批被拒绝', state: 'fail', sub: a.comment || (a.approver_name || '—') })
    } else {
      list.push({ key: 'approval', label: '等待审批', state: r.status === 'cancelled' ? 'fail' : 'active', sub: timeText(a.created_at) + ' 提交' })
    }
  } else if (r.status !== 'pending') {
    list.push({ key: 'trigger', label: '触发 Jenkins', state: 'done', sub: timeText(r.started_at || r.created_at) })
  }

  const st = r.status as string
  if (st === 'success') {
    list.push({ key: 'jenkins', label: 'Jenkins 执行', state: 'done', sub: r.jenkins_build_number ? '构建 #' + r.jenkins_build_number : '' })
  } else if (st === 'failed') {
    list.push({ key: 'jenkins', label: 'Jenkins 执行', state: 'fail', sub: r.jenkins_build_number ? '构建 #' + r.jenkins_build_number + ' 失败' : '执行失败' })
  } else if (st === 'cancelled') {
    list.push({ key: 'jenkins', label: 'Jenkins 执行', state: 'idle', sub: '已取消' })
  } else if (st === 'pending') {
    list.push({ key: 'jenkins', label: 'Jenkins 执行', state: 'idle', sub: '审批通过后触发' })
  } else {
    list.push({ key: 'jenkins', label: 'Jenkins 执行', state: 'active', sub: r.jenkins_build_number ? '构建 #' + r.jenkins_build_number + ' · 等待回调' : '排队触发中' })
  }

  if (st === 'success') {
    list.push({ key: 'done', label: '完成', state: 'done', sub: '耗时 ' + formatDeployDuration(r.duration) })
  } else if (st === 'failed') {
    list.push({ key: 'done', label: '完成', state: 'fail', sub: '—' })
  } else if (st === 'cancelled') {
    list.push({ key: 'done', label: '已取消', state: 'idle', sub: '—' })
  } else {
    list.push({ key: 'done', label: '完成', state: 'idle', sub: '—' })
  }
  return list
})

function lineClass(idx: number) {
  const prev = steps.value[idx - 1]
  if (!prev) return ''
  if (prev.state === 'done') return 'done'
  if (prev.state === 'fail') return 'fail'
  return ''
}

const approvalText = computed(() => {
  const a = record.value?.approval
  if (!a) return ''
  if (a.status === 'approved') return (a.approver_name || '—') + ' · ' + timeText(a.resolved_at) + ' 通过'
  if (a.status === 'rejected') return (a.approver_name || '—') + ' 拒绝' + (a.comment ? '：' + a.comment : '')
  return '等待审批中…'
})

const jenkinsJobName = computed(() => record.value?.approval?.jenkins_job_name || '')

// ── 日志解析 ──
interface LogLine { time: string; text: string; cls: string }

const logLines = computed<LogLine[]>(() => {
  const raw: string = record.value?.log || ''
  return raw.split('\n').filter(l => l.trim()).map(l => {
    const m = l.match(/^\[(\d{2}:\d{2}:\d{2})\]\s?(.*)$/)
    const time = m ? m[1] : ''
    const text = m ? m[2] : l
    let cls = ''
    if (/失败|错误|error|exception|取消/i.test(text)) cls = 'le'
    else if (/成功|审批通过/.test(text)) cls = 'lo'
    else if (/需要审批|等待/.test(text)) cls = 'lw'
    else if (/\[模式B\]|Jenkins|构建|审批/.test(text)) cls = 'li'
    return { time, text, cls }
  })
})

// 跟随滚动
watch(logLines, async () => {
  if (!followLog.value) return
  await nextTick()
  const el = termBodyRef.value
  if (el) el.scrollTop = el.scrollHeight
})

async function copyLog() {
  try {
    await navigator.clipboard.writeText(record.value?.log || '')
    ElMessage.success('日志已复制')
  } catch {
    ElMessage.warning('复制失败，请手动选择复制')
  }
}

function downloadLog() {
  const blob = new Blob([record.value?.log || ''], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'deploy-' + record.value?.id + '.log'
  a.click()
  URL.revokeObjectURL(url)
}

// ── 操作 ──
function openJenkins() {
  window.open(record.value?.jenkins_build_url, '_blank', 'noopener')
}

async function handleCancel() {
  await ElMessageBox.confirm('确定取消部署单 #' + record.value.id + '（' + record.value.version + '）吗？', '取消部署', {
    type: 'warning',
    confirmButtonText: '确定取消',
    cancelButtonText: '再想想',
  })
  await cancelDeploy(record.value.id)
  ElMessage.success('已取消')
  stopTicker()
  await fetchRecord()
}

async function handleRedeploy() {
  await ElMessageBox.confirm(
    '将以相同版本（' + record.value.version + '）重新触发部署到 ' + record.value.env_name + '。',
    '重新部署',
    { type: 'info', confirmButtonText: '确认部署', cancelButtonText: '取消' },
  )
  const res: any = await executeDeploy({
    app_name: record.value.app_name,
    env_id: record.value.env_id,
    version: record.value.version,
  })
  ElMessage.success(res.msg || '已提交')
  if (res.data?.id) router.push('/deploy/records/' + res.data.id)
}

// ── 回滚 ──
const rollbackVisible = ref(false)
const rollbackLoading = ref(false)
const rollbackTargets = ref<any[]>([])
const rollbackTargetId = ref<number | null>(null)
const rollbacking = ref(false)

const rollbackConfirmText = computed(() => {
  const t = rollbackTargets.value.find(x => x.id === rollbackTargetId.value)
  return t ? '确认回滚到 ' + t.version : '确认回滚'
})

async function openRollback() {
  rollbackVisible.value = true
  rollbackLoading.value = true
  rollbackTargetId.value = null
  try {
    const res: any = await getRollbackTargets(record.value.id)
    rollbackTargets.value = res.data?.records || []
    rollbackTargetId.value = rollbackTargets.value[0]?.id ?? null
  } finally {
    rollbackLoading.value = false
  }
}

async function confirmRollback() {
  if (!rollbackTargetId.value) return
  rollbacking.value = true
  try {
    const res: any = await rollbackDeploy(record.value.id, rollbackTargetId.value)
    ElMessage.success(res.msg || '回滚已触发')
    rollbackVisible.value = false
    if (res.data?.id) router.push('/deploy/records/' + res.data.id)
  } finally {
    rollbacking.value = false
  }
}
</script>
<style scoped lang="scss">
.crumb {
  font-size: 13px;
  color: var(--text-muted);
  margin-bottom: 10px;

  a { color: var(--text-secondary); transition: color .15s; }
  a:hover { color: var(--primary-color); }
  .sep { margin: 0 6px; }
}

.sp { flex: 1; }
.mono { font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace; }
.muted { color: var(--text-muted); }

/* ── 英雄区 ── */
.hero {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: 18px 20px;
  margin-bottom: 14px;
}

.h-title { font-size: 22px; font-weight: 800; }
.hero-ver { font-weight: 700; font-size: 14px; }
.app-link { color: inherit; }
.app-link:hover { color: var(--primary-color); }

/* ── 状态 pill ── */
.pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;

  .dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; flex: none; }
  .dot--pulse { animation: pulse 1.6s ease-in-out infinite; }

  &--success { color: #15803d; background: color-mix(in srgb, var(--success-color) 12%, transparent); }
  &--danger { color: #b42318; background: color-mix(in srgb, var(--danger-color) 10%, transparent); }
  &--warning { color: #b45309; background: color-mix(in srgb, var(--warning-color) 14%, transparent); }
  &--primary { color: var(--primary-color); background: var(--primary-bg); }
  &--info { color: var(--text-secondary); background: color-mix(in srgb, var(--text-muted) 14%, transparent); }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: .35; }
}

.type-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: 6px;
  font-size: 11.5px;
  font-weight: 600;
  color: var(--text-secondary);
  background: color-mix(in srgb, var(--text-muted) 12%, transparent);

  &--approval { color: #b45309; background: color-mix(in srgb, var(--warning-color) 16%, transparent); }
}

.approval-tag {
  display: inline-flex;
  align-items: center;
  padding: 1px 7px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 700;
  color: #b45309;
  background: color-mix(in srgb, var(--warning-color) 16%, transparent);
  margin-left: 6px;
}

/* ── 步骤条 ── */
.steps {
  display: flex;
  align-items: flex-start;
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: 20px 24px;
  margin-bottom: 14px;
  overflow-x: auto;
}

.step {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: none;
}

.step-dot {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-size: 12.5px;
  font-weight: 700;
  background: color-mix(in srgb, var(--text-muted) 10%, transparent);
  border: 1.5px solid var(--border-color);
  color: var(--text-muted);
  flex: none;
}

.step.done .step-dot { background: var(--success-color); border-color: var(--success-color); color: #fff; }
.step.active .step-dot {
  background: var(--primary-color);
  border-color: var(--primary-color);
  color: #fff;
  box-shadow: 0 0 0 5px var(--primary-bg);
}
.step.fail .step-dot {
  background: var(--danger-color);
  border-color: var(--danger-color);
  color: #fff;
  box-shadow: 0 0 0 5px color-mix(in srgb, var(--danger-color) 12%, transparent);
}

.step-txt { display: flex; flex-direction: column; gap: 1px; }
.step-label { font-size: 13px; font-weight: 700; color: var(--text-secondary); white-space: nowrap; }
.step.active .step-label { color: var(--primary-color); }
.step.done .step-label { color: #15803d; }
.step.fail .step-label { color: #b42318; }
.step-sub { font-size: 11px; color: var(--text-muted); white-space: nowrap; }

.step-line {
  flex: 1;
  height: 2px;
  background: var(--border-color);
  margin: 14px 14px 0;
  min-width: 24px;

  &.done { background: var(--success-color); }
  &.fail { background: var(--danger-color); }
}

/* ── Jenkins / 错误横幅 ── */
.jenkins-banner {
  display: flex;
  gap: 14px;
  align-items: center;
  background: var(--surface-color);
  border: 1px solid color-mix(in srgb, var(--primary-color) 30%, transparent);
  border-radius: var(--border-radius);
  padding: 14px 18px;
  margin-bottom: 14px;

  &--wait { border-color: color-mix(in srgb, var(--warning-color) 35%, transparent); }
}

.jb-ico {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  background: var(--primary-bg);
  color: var(--primary-color);
  display: grid;
  place-items: center;
  flex: none;
  font-size: 18px;

  &--wait {
    background: color-mix(in srgb, var(--warning-color) 14%, transparent);
    color: #b45309;
  }
}

.jb-body { min-width: 0; }
.jb-title { font-size: 13.5px; font-weight: 700; }
.jb-job { color: var(--text-muted); font-weight: 500; }
.jb-sub { font-size: 12px; color: var(--text-muted); margin-top: 3px; line-height: 1.5; }

.err-banner {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  background: color-mix(in srgb, var(--danger-color) 8%, transparent);
  border: 1px solid color-mix(in srgb, var(--danger-color) 30%, transparent);
  border-radius: var(--border-radius);
  padding: 14px 18px;
  margin-bottom: 14px;
}

.e-ico { color: #b42318; font-size: 18px; margin-top: 2px; flex: none; }
.err-title { font-size: 13.5px; font-weight: 700; color: #b42318; }
.err-body { font-size: 12.5px; color: var(--text-secondary); margin-top: 3px; line-height: 1.6; }

/* ── 布局 ── */
.detail-layout {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 14px;
  align-items: start;
}

/* ── 终端 ── */
.term {
  background: #17172b;
  border-radius: var(--border-radius);
  overflow: hidden;
  border: 1px solid #26263e;
}

.term-head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-bottom: 1px solid #26263e;
}

.term-dots { display: flex; gap: 6px; }

.td {
  width: 10px;
  height: 10px;
  border-radius: 50%;

  &--r { background: #f87171; }
  &--y { background: #fbbf24; }
  &--g { background: #4ade80; }
}

.term-title { font-size: 12px; color: #8b8ba7; font-weight: 600; }

.term-btn {
  border: 1px solid #343452;
  background: transparent;
  color: #a6a6c4;
  font-family: inherit;
  font-size: 11.5px;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: 6px;
  cursor: pointer;
  transition: all .15s ease-out;

  &:hover { color: #fff; border-color: #4a4a70; }

  &.on {
    background: color-mix(in srgb, var(--primary-color) 25%, transparent);
    border-color: var(--primary-color);
    color: #cdd3ff;
  }
}

.term-body {
  padding: 14px 16px;
  font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
  font-size: 12.5px;
  line-height: 1.75;
  color: #d6d6e8;
  height: 380px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-all;
}

.term-line { min-height: 1em; }
.lt { color: #6b6b8a; margin-right: 6px; }
.le { color: #f87171; }
.lo { color: #4ade80; }
.li { color: #8ea2ff; }
.lw { color: #fbbf24; }

.cursor-blink {
  display: inline-block;
  width: 8px;
  height: 14px;
  background: #8ea2ff;
  vertical-align: middle;
  animation: blink 1s step-end infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

/* ── 侧栏 ── */
.meta-card {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: 16px 18px;
}

.meta-title { font-size: 14px; font-weight: 700; margin-bottom: 12px; }

.meta-item {
  display: flex;
  gap: 12px;
  padding: 7px 0;
  font-size: 13px;
  border-bottom: 1px dashed var(--border-color);

  &:last-child { border-bottom: 0; }
}

.meta-k { width: 64px; flex: none; color: var(--text-muted); font-size: 12px; padding-top: 1px; }
.meta-v { font-weight: 600; color: var(--text-primary); word-break: break-all; display: flex; align-items: center; flex-wrap: wrap; gap: 4px; }

.meta-v--err {
  color: #b42318;
  font-size: 12px;
  font-weight: 500;
}

.elapsed-live { color: var(--primary-color); }

.meta-link {
  color: var(--primary-color);
  font-size: 12.5px;

  &:hover { text-decoration: underline; }
}

.side-actions {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.side-btn {
  width: 100%;
  margin-left: 0 !important;
  justify-content: center;
}

/* ── 回滚弹窗 ── */
.rb-note {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 14px;
  line-height: 1.6;
}

.rb-code {
  background: color-mix(in srgb, var(--text-muted) 10%, transparent);
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 12px;
}

.radio-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 320px;
  overflow-y: auto;
}

.radio-item {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: 12px 14px;
  cursor: pointer;
  transition: border-color .15s ease-out, background .15s ease-out;

  &:hover, &:focus-visible { border-color: color-mix(in srgb, var(--primary-color) 45%, transparent); outline: none; }

  &.sel {
    border-color: var(--primary-color);
    background: var(--primary-bg);
  }
}

.radio-dot {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 1.5px solid var(--border-color);
  flex: none;
  margin-top: 2px;
  position: relative;
  transition: border-color .15s;

  .sel & {
    border-color: var(--primary-color);

    &::after {
      content: '';
      position: absolute;
      inset: 3px;
      border-radius: 50%;
      background: var(--primary-color);
    }
  }
}

.radio-main { min-width: 0; }

.radio-t1 {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 700;
}

.rec-tag {
  font-size: 11px;
  font-weight: 700;
  color: #15803d;
  background: color-mix(in srgb, var(--success-color) 12%, transparent);
  padding: 1px 7px;
  border-radius: 6px;
}

.radio-t2 {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 3px;
}

/* ── 响应式 ── */
@media (max-width: 1000px) {
  .detail-layout { grid-template-columns: 1fr; }
}

@media (max-width: 768px) {
  .steps { padding: 14px 16px; }
  .step-sub { display: none; }
  .term-body { height: 280px; }
}
</style>
