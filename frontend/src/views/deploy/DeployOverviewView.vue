<template>
  <div>
    <!-- 页头 -->
    <div class="page-header ov-head">
      <div>
        <h2 class="page-title">发布总览</h2>
        <p class="ov-sub">所有应用 × 环境的当前版本与发布状态一览</p>
      </div>
      <div class="head-actions">
        <el-button @click="$router.push('/deploy/records')">部署记录</el-button>
        <el-button @click="$router.push('/deploy/approvals')">审批中心</el-button>
        <el-button v-if="canCreate" type="primary" @click="$router.push('/deploy/apps/create')">
          <el-icon><Plus /></el-icon>创建应用
        </el-button>
      </div>
    </div>

    <!-- KPI 条 -->
    <div class="kpi-strip" role="region" aria-label="发布指标" v-loading="loading && !data">
      <div class="kpi" role="button" tabindex="0" @click="goRecords('active')" @keyup.enter="goRecords('active')">
        <div class="kpi-ico kpi-ico--primary"><el-icon><Promotion /></el-icon></div>
        <div class="kpi-body">
          <div class="kpi-k">进行中部署</div>
          <div class="kpi-v kpi-v--primary">{{ kpi.running ?? 0 }}</div>
          <div class="kpi-sub">{{ runningSub || '当前没有进行中的部署' }}</div>
        </div>
      </div>
      <div class="kpi" role="button" tabindex="0" @click="goApprovals" @keyup.enter="goApprovals">
        <div class="kpi-ico kpi-ico--warning"><el-icon><Clock /></el-icon></div>
        <div class="kpi-body">
          <div class="kpi-k">待审批</div>
          <div class="kpi-v kpi-v--warning">{{ kpi.pending_approvals ?? 0 }}</div>
          <div class="kpi-sub">{{ (kpi.pending_approvals ?? 0) > 0 ? '点击前往审批中心处理' : '没有等待审批的发布' }}</div>
        </div>
      </div>
      <div class="kpi" role="button" tabindex="0" @click="goRecords()" @keyup.enter="goRecords()">
        <div class="kpi-ico kpi-ico--success"><el-icon><CircleCheck /></el-icon></div>
        <div class="kpi-body">
          <div class="kpi-k">今日部署</div>
          <div class="kpi-v">{{ kpi.today_total ?? 0 }}</div>
          <div class="kpi-sub">成功 {{ kpi.today_success ?? 0 }} · 失败 {{ kpi.today_failed ?? 0 }}</div>
        </div>
      </div>
      <div class="kpi" role="button" tabindex="0" @click="goRecords('failed')" @keyup.enter="goRecords('failed')">
        <div class="kpi-ico kpi-ico--danger"><el-icon><Warning /></el-icon></div>
        <div class="kpi-body">
          <div class="kpi-k">本周失败</div>
          <div class="kpi-v kpi-v--danger">{{ kpi.week_failed ?? 0 }}</div>
          <div class="kpi-sub">{{ weekFailedSub || '近 7 天没有失败记录' }}</div>
        </div>
      </div>
    </div>
    <!-- 状态矩阵 -->
    <div class="card">
      <div class="card-head">
        <span class="card-title">环境状态矩阵</span>
        <span class="card-hint">应用超过 10 个自动切换紧凑密度 · 异常优先排序</span>
        <span class="sp"></span>
        <span class="refresh-note" role="status">
          <span class="refresh-dot"></span>每 10 秒自动刷新<template v-if="updatedAt"> · 更新于 {{ updatedAt }}</template>
        </span>
      </div>
      <div class="mx-toolbar">
        <el-input
          v-model="mxSearch"
          placeholder="搜索应用名…"
          clearable
          class="mx-search"
          aria-label="搜索矩阵中的应用"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-select v-model="mxType" placeholder="全部类型" clearable class="mx-type" aria-label="按应用类型筛选">
          <el-option v-for="t in appTypes" :key="t.value" :label="t.label" :value="t.value" />
        </el-select>
        <el-button size="small" :type="mxOnlyAttention ? 'primary' : 'default'" :plain="!mxOnlyAttention" @click="mxOnlyAttention = !mxOnlyAttention">
          仅看需关注
        </el-button>
        <span class="sp"></span>
        <span class="card-hint mx-sort-hint">排序：进行中 → 失败 → 待审批 → 正常</span>
        <span class="card-hint">{{ visibleApps.length }} / {{ apps.length }} 个应用</span>
        <div class="seg" role="group" aria-label="矩阵密度">
          <button type="button" :class="{ active: density === 'cozy' }" @click="userDensity = 'cozy'">舒适</button>
          <button type="button" :class="{ active: density === 'compact' }" @click="userDensity = 'compact'">紧凑</button>
        </div>
      </div>
      <div class="matrix-wrap" v-loading="loading && !data">
        <div
          v-if="envs.length"
          class="matrix"
          :class="{ compact: density === 'compact' }"
          :style="{ gridTemplateColumns: matrixColumns }"
          role="table"
          aria-label="应用环境状态矩阵"
        >
          <div class="mx-head" role="columnheader">应用 / Jenkins Job</div>
          <div v-for="env in envs" :key="env.id" class="mx-head" role="columnheader">
            <span class="env-dot" :style="{ background: envColor(env.name) }"></span>
            {{ env.display_name || env.name }} {{ env.name }}
            <span v-if="env.approval_required" class="approval-tag">需审批</span>
          </div>

          <template v-for="app in visibleApps" :key="app.id">
            <div class="mx-app" role="rowheader">
              <span class="name" @click="goApp(app.name)">{{ app.name }}</span>
              <span class="row2"><span class="type-tag">{{ typeLabel(app.app_type) }}</span></span>
              <span class="job mono">{{ app.jenkins_job_name || '未配置 Job' }}</span>
            </div>
            <template v-for="env in envs" :key="env.id">
              <!-- 未配置该环境 -->
              <div v-if="!cellOf(app, env.id)" class="mx-cell mx-cell--na" role="cell">—</div>
              <!-- 已配置但无记录 / 已停用 -->
              <div v-else-if="!recordOf(app, env.id)" class="mx-cell empty" role="cell">
                {{ cellOf(app, env.id)!.enabled ? '未部署' : '未启用' }}
              </div>
              <!-- 有部署记录 -->
              <div
                v-else
                class="mx-cell"
                :class="{ running: isActiveStatus(recordOf(app, env.id)!.status) }"
                role="cell"
                tabindex="0"
                @click="cellClick(recordOf(app, env.id)!)"
                @keyup.enter="cellClick(recordOf(app, env.id)!)"
              >
                <span class="ver mono">{{ recordOf(app, env.id)!.version }}</span>
                <span class="pill" :class="pillClass(recordOf(app, env.id)!.status)">
                  <i class="dot" :class="{ 'dot--pulse': isActiveStatus(recordOf(app, env.id)!.status) }"></i>
                  {{ deployStatusLabel(recordOf(app, env.id)!.status) }}
                </span>
                <div v-if="isActiveStatus(recordOf(app, env.id)!.status)" class="mini-progress"><i></i></div>
                <span class="meta">
                  <template v-if="recordOf(app, env.id)!.status === 'pending'">提交于 </template>
                  {{ formatRelativeTime(recordOf(app, env.id)!.created_at || '') }} · {{ recordOf(app, env.id)!.trigger_user_name || '—' }}
                  <template v-if="recordOf(app, env.id)!.jenkins_build_number"> · 构建 #{{ recordOf(app, env.id)!.jenkins_build_number }}</template>
                  <template v-else-if="recordOf(app, env.id)!.status === 'failed'"> · 查看日志</template>
                </span>
              </div>
            </template>
          </template>
        </div>
        <el-empty v-if="!loading && !envs.length" description="暂无环境或应用数据" :image-size="80" />
        <el-empty v-else-if="envs.length && !visibleApps.length" description="没有符合筛选条件的应用" :image-size="80" />
      </div>
    </div>
    <!-- 下半区：动态 + 待审批 -->
    <div class="grid-2">
      <div class="card">
        <div class="card-head">
          <span class="card-title">最近动态</span>
          <span class="sp"></span>
          <el-button text size="small" @click="goRecords()">查看全部 →</el-button>
        </div>
        <div class="feed" v-loading="loading && !data">
          <div
            v-for="item in feed"
            :key="item.id"
            class="feed-item"
            role="button"
            tabindex="0"
            @click="goRecord(item.id)"
            @keyup.enter="goRecord(item.id)"
          >
            <div class="feed-ico" :class="feedIconClass(item.status)">
              <el-icon><component :is="feedIcon(item.status)" /></el-icon>
            </div>
            <div class="feed-main">
              <div class="feed-title">
                <b>{{ item.app_name }}</b> 发布到 <b>{{ item.env_name }}</b>{{ feedPhrase(item) }}
              </div>
              <div class="feed-meta">{{ formatRelativeTime(item.created_at) }} · 触发人 {{ item.trigger_user_name || '—' }}</div>
            </div>
            <code class="feed-ver mono">{{ item.version }}</code>
          </div>
          <el-empty v-if="!feed.length" description="暂无动态" :image-size="70" />
        </div>
      </div>

      <div class="card">
        <div class="card-head">
          <span class="card-title">待审批 <span v-if="approvals.length" class="approval-tag">{{ kpi.pending_approvals ?? approvals.length }}</span></span>
          <span class="sp"></span>
          <el-button text size="small" @click="goApprovals">审批中心 →</el-button>
        </div>
        <div v-loading="loading && !data">
          <div v-for="a in approvals" :key="a.id" class="appr-item">
            <div class="appr-line1">
              <span class="name">{{ a.app_name }}</span>
              <span class="muted">→</span>
              <span class="type-tag type-tag--approval">{{ a.env_name }}</span>
              <code class="mono appr-ver">{{ a.version }}</code>
            </div>
            <div class="appr-line2">
              {{ a.trigger_user_name || '—' }} 提交 · {{ formatRelativeTime(a.created_at) }}
              <template v-if="a.current_version"> · 当前线上 {{ a.current_version }}</template>
            </div>
            <div v-if="canApprove" class="appr-actions">
              <el-button size="small" type="primary" :loading="actingId === a.id" @click="quickApprove(a)">通过</el-button>
              <el-button size="small" type="danger" plain :loading="actingId === a.id" @click="quickReject(a)">拒绝</el-button>
            </div>
          </div>
          <el-empty v-if="!approvals.length" description="没有待审批的发布" :image-size="70" />
        </div>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref, computed, onActivated, onDeactivated } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Plus, Search, Promotion, Clock, CircleCheck, CircleClose, Warning, Remove,
} from '@element-plus/icons-vue'
import { getDeployOverview, approveDeploy, rejectDeploy } from '@/api/deploy'
import { useAuthStore } from '@/stores/modules/auth'
import { formatRelativeTime } from '@/utils/time'
import {
  deployStatusLabel, deployStatusType, isActiveStatus, statusSeverity,
  formatDeployDuration, envColor,
} from '@/utils/deployStatus'

interface MatrixRecord {
  id: number
  env_id: number
  env_name: string | null
  version: string
  status: string
  trigger_type: string
  trigger_user_name: string | null
  duration: number | null
  jenkins_build_url: string
  jenkins_build_number: number | null
  created_at: string | null
}

interface MatrixCell {
  enabled: boolean
  record: MatrixRecord | null
}

interface MatrixApp {
  id: number
  name: string
  display_name: string
  app_type: string
  jenkins_job_name: string
  envs: Record<string, MatrixCell>
}

interface EnvCol {
  id: number
  name: string
  display_name: string
  approval_required: boolean
}

const router = useRouter()
const authStore = useAuthStore()

const data = ref<any>(null)
const loading = ref(false)
const updatedAt = ref('')

const kpi = computed(() => data.value?.kpi || {})
const envs = computed<EnvCol[]>(() => data.value?.envs || [])
const apps = computed<MatrixApp[]>(() => data.value?.apps || [])
const feed = computed<any[]>(() => data.value?.feed || [])
const approvals = computed<any[]>(() => data.value?.approvals || [])

const canCreate = computed(() => authStore.hasPermission('deploy.create'))
const canApprove = computed(() => authStore.hasPermission('deploy.approve'))

const appTypes = [
  { label: 'Web 应用', value: 'web' },
  { label: 'API 服务', value: 'api' },
  { label: '后台任务', value: 'worker' },
  { label: '前端项目', value: 'frontend' },
  { label: '其他', value: 'other' },
]
const typeLabel = (v: string) => appTypes.find(t => t.value === v)?.label || v

// ── 数据加载 + 自动刷新 ──
async function fetchOverview() {
  loading.value = true
  try {
    const res: any = await getDeployOverview()
    data.value = res.data
    updatedAt.value = new Date().toLocaleTimeString('zh-CN', { hour12: false })
  } finally {
    loading.value = false
  }
}

let refreshTimer: ReturnType<typeof setInterval> | null = null

onActivated(() => {
  fetchOverview()
  refreshTimer = setInterval(fetchOverview, 10000)
})

onDeactivated(() => {
  if (refreshTimer) { clearInterval(refreshTimer); refreshTimer = null }
})

// ── 矩阵 ──
const mxSearch = ref('')
const mxType = ref('')
const mxOnlyAttention = ref(false)
const userDensity = ref<'cozy' | 'compact' | null>(null)

const density = computed<'cozy' | 'compact'>(() =>
  userDensity.value ?? (apps.value.length > 10 ? 'compact' : 'cozy'),
)

const matrixColumns = computed(() =>
  '230px repeat(' + envs.value.length + ', minmax(220px, 1fr))',
)

function cellOf(app: MatrixApp, envId: number): MatrixCell | undefined {
  return app.envs?.[String(envId)]
}

function recordOf(app: MatrixApp, envId: number): MatrixRecord | null {
  return cellOf(app, envId)?.record ?? null
}

function appSeverity(app: MatrixApp): number {
  let sev = 0
  for (const key of Object.keys(app.envs || {})) {
    sev = Math.max(sev, statusSeverity(app.envs[key]?.record?.status))
  }
  return sev
}

const visibleApps = computed(() => {
  const kw = mxSearch.value.trim().toLowerCase()
  return apps.value
    .filter(a => {
      if (kw && !a.name.toLowerCase().includes(kw) && !(a.display_name || '').toLowerCase().includes(kw)) return false
      if (mxType.value && a.app_type !== mxType.value) return false
      if (mxOnlyAttention.value && appSeverity(a) < 2) return false
      return true
    })
    .sort((a, b) => (appSeverity(b) - appSeverity(a)) || a.name.localeCompare(b.name))
})

const pillClass = (status: string) => 'pill--' + deployStatusType(status)

// ── KPI 副标题（从矩阵/动态推导） ──
const runningSub = computed(() => {
  for (const app of apps.value) {
    for (const key of Object.keys(app.envs || {})) {
      const r = app.envs[key]?.record
      if (r && isActiveStatus(r.status) && r.status !== 'pending') {
        let s = app.name + ' → ' + (r.env_name || '')
        if (r.jenkins_build_number) s += ' · 构建 #' + r.jenkins_build_number
        return s
      }
    }
  }
  return ''
})

const weekFailedSub = computed(() => {
  const failed = feed.value.find(f => f.status === 'failed')
  return failed ? failed.app_name + ' → ' + failed.env_name : ''
})

// ── 动态 ──
function feedIcon(status: string) {
  if (status === 'success') return CircleCheck
  if (status === 'failed') return CircleClose
  if (status === 'cancelled') return Remove
  if (status === 'pending') return Clock
  return Promotion
}

function feedIconClass(status: string) {
  if (status === 'success') return 'feed-ico--success'
  if (status === 'failed') return 'feed-ico--danger'
  if (status === 'pending') return 'feed-ico--warning'
  if (status === 'cancelled') return 'feed-ico--info'
  return 'feed-ico--primary'
}

function feedPhrase(item: any): string {
  switch (item.status) {
    case 'success': {
      const d = formatDeployDuration(item.duration)
      return ' 成功' + (d !== '—' ? '，耗时 ' + d : '')
    }
    case 'failed': {
      const reason = (item.error_message || '').split('\n')[0].slice(0, 40)
      return ' 失败' + (reason ? '：' + reason : '（详见构建日志）')
    }
    case 'pending':
      return ' 发布申请已提交，等待审批'
    case 'cancelled':
      return ' 已取消'
    default: {
      const b = item.jenkins_build_number ? '（构建 #' + item.jenkins_build_number + '）' : ''
      return '，Jenkins 执行中' + b
    }
  }
}

// ── 审批快捷操作 ──
const actingId = ref<number | null>(null)

async function quickApprove(a: any) {
  await ElMessageBox.confirm(
    '通过后平台将自动触发 Jenkins 执行部署（' + a.app_name + ' → ' + a.env_name + ' ' + a.version + '）。',
    '确认通过',
    { type: 'info', confirmButtonText: '通过并触发', cancelButtonText: '取消' },
  )
  actingId.value = a.id
  try {
    await approveDeploy(a.id)
    ElMessage.success('已通过，Jenkins 执行中')
    await fetchOverview()
  } finally {
    actingId.value = null
  }
}

async function quickReject(a: any) {
  const { value } = await ElMessageBox.prompt('请输入拒绝原因（可选）', '拒绝发布申请', {
    confirmButtonText: '确认拒绝',
    cancelButtonText: '取消',
    inputPlaceholder: '将记录到审批日志',
  })
  actingId.value = a.id
  try {
    await rejectDeploy(a.id, (value || '').trim() || undefined)
    ElMessage.success('已拒绝')
    await fetchOverview()
  } finally {
    actingId.value = null
  }
}

// ── 跳转 ──
function goRecords(filter?: string) {
  if (filter === 'failed') router.push({ path: '/deploy/records', query: { status: 'failed' } })
  else if (filter === 'active') router.push({ path: '/deploy/records', query: { status: 'active' } })
  else router.push('/deploy/records')
}

function goApprovals() {
  router.push('/deploy/approvals')
}

function goApp(name: string) {
  router.push('/deploy/apps/' + name)
}

function goRecord(id: number) {
  router.push('/deploy/records/' + id)
}

function cellClick(record: MatrixRecord) {
  if (record.status === 'pending') goApprovals()
  else goRecord(record.id)
}
</script>
<style scoped lang="scss">
.ov-head {
  flex-wrap: wrap;
  gap: 10px;
}

.ov-sub {
  font-size: 13px;
  color: var(--text-muted);
  margin-top: 4px;
}

.head-actions { display: flex; gap: 8px; flex-wrap: wrap; }
.sp { flex: 1; }
.mono { font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace; }
.muted { color: var(--text-muted); }

/* ── 卡片 ── */
.card {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  overflow: hidden;
}

.card-head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 18px;
  border-bottom: 1px solid var(--border-color);
  flex-wrap: wrap;
}

.card-title { font-size: 14.5px; font-weight: 700; }
.card-hint { font-size: 12px; color: var(--text-muted); }

/* ── KPI 条 ── */
.kpi-strip {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  margin-bottom: 18px;
}

.kpi {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: 16px 18px;
  display: flex;
  align-items: center;
  gap: 14px;
  cursor: pointer;
  transition: border-color .15s ease-out, box-shadow .15s ease-out;

  &:hover, &:focus-visible {
    border-color: var(--primary-color);
    box-shadow: 0 2px 10px color-mix(in srgb, var(--primary-color) 14%, transparent);
    outline: none;
  }
}

.kpi-ico {
  width: 42px;
  height: 42px;
  border-radius: 11px;
  display: grid;
  place-items: center;
  flex: none;
  font-size: 19px;

  &--primary { background: var(--primary-bg); color: var(--primary-color); }
  &--warning { background: color-mix(in srgb, var(--warning-color) 14%, transparent); color: #b45309; }
  &--success { background: color-mix(in srgb, var(--success-color) 12%, transparent); color: #15803d; }
  &--danger { background: color-mix(in srgb, var(--danger-color) 10%, transparent); color: #b42318; }
}

.kpi-body { min-width: 0; }
.kpi-k { font-size: 12px; color: var(--text-muted); font-weight: 600; }

.kpi-v {
  font-size: 24px;
  font-weight: 800;
  line-height: 1.25;
  font-variant-numeric: tabular-nums;

  &--primary { color: var(--primary-color); }
  &--warning { color: #b45309; }
  &--danger { color: #b42318; }
}

.kpi-sub {
  font-size: 11.5px;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ── 矩阵工具条 ── */
.mx-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 16px;
  flex-wrap: wrap;
  border-bottom: 1px solid var(--border-color);
}

.mx-search { width: 190px; }
.mx-type { width: 130px; }

.seg {
  display: inline-flex;
  background: color-mix(in srgb, var(--text-muted) 10%, transparent);
  border-radius: 8px;
  padding: 2px;
  gap: 2px;

  button {
    border: 0;
    background: transparent;
    font-family: inherit;
    font-size: 12px;
    font-weight: 600;
    color: var(--text-secondary);
    padding: 4px 11px;
    border-radius: 6px;
    cursor: pointer;
    transition: all .15s ease-out;

    &.active {
      background: var(--surface-color);
      color: var(--primary-color);
      box-shadow: 0 1px 3px rgba(0, 0, 0, .12);
    }
  }
}

.refresh-note {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 12px;
  color: var(--text-muted);
}

.refresh-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--success-color);
  animation: pulse 1.6s ease-in-out infinite;
}

/* ── 矩阵 ── */
.matrix-wrap { overflow-x: auto; }

.matrix {
  display: grid;
  gap: 1px;
  background: var(--border-color);
  min-width: 960px;
}

.mx-head {
  background: color-mix(in srgb, var(--text-muted) 7%, transparent);
  padding: 12px 16px;
  font-size: 12px;
  font-weight: 700;
  color: var(--text-muted);
  display: flex;
  align-items: center;
  gap: 8px;
  letter-spacing: .3px;
}

.env-dot { width: 8px; height: 8px; border-radius: 50%; flex: none; }

.mx-app {
  background: var(--surface-color);
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 4px;

  .name {
    font-size: 14px;
    font-weight: 700;
    color: var(--text-primary);
    cursor: pointer;

    &:hover { color: var(--primary-color); }
  }

  .job { font-size: 11.5px; color: var(--text-muted); }
  .row2 { display: flex; align-items: center; gap: 6px; margin-top: 2px; }
}

.mx-cell {
  background: var(--surface-color);
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  cursor: pointer;
  transition: background .15s;
  position: relative;

  &:hover, &:focus-visible { background: color-mix(in srgb, var(--primary-color) 5%, transparent); outline: none; }

  .ver { font-size: 14px; font-weight: 750; word-break: break-all; }

  .meta {
    font-size: 11.5px;
    color: var(--text-muted);
    display: flex;
    align-items: center;
    gap: 5px;
  }

  &.empty {
    align-items: center;
    justify-content: center;
    color: var(--text-muted);
    font-size: 12.5px;
    cursor: default;

    &:hover { background: var(--surface-color); }
  }

  &--na {
    align-items: center;
    justify-content: center;
    color: color-mix(in srgb, var(--text-muted) 55%, transparent);
    font-size: 12.5px;
    cursor: default;
    background: color-mix(in srgb, var(--text-muted) 3%, var(--surface-color));

    &:hover { background: color-mix(in srgb, var(--text-muted) 3%, var(--surface-color)); }
  }

  &.running {
    background: linear-gradient(135deg, color-mix(in srgb, var(--primary-color) 7%, transparent), color-mix(in srgb, var(--primary-color) 1%, transparent));
  }
}

.mini-progress {
  height: 4px;
  border-radius: 2px;
  background: var(--primary-bg);
  overflow: hidden;

  i {
    display: block;
    height: 100%;
    width: 40%;
    border-radius: 2px;
    background: var(--primary-color);
    animation: slide 1.6s ease-in-out infinite;
  }
}

@keyframes slide {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(260%); }
}

/* 紧凑密度：每行约 34px，一屏 25+ 应用 */
.matrix.compact {
  .mx-head { padding: 8px 16px; font-size: 11.5px; }

  .mx-app {
    padding: 7px 16px;
    flex-direction: row;
    align-items: center;
    gap: 8px;

    .name { font-size: 12.5px; }
    .row2, .job { display: none; }
  }

  .mx-cell {
    flex-direction: row;
    align-items: center;
    gap: 8px;
    padding: 7px 16px;

    .ver { font-size: 12px; font-weight: 650; order: 2; }
    .pill { order: 1; font-size: 11px; padding: 1px 8px 1px 6px; gap: 4px; }

    .meta {
      order: 3;
      font-size: 11px;
      margin-left: auto;
      max-width: 150px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .mini-progress { display: none; }

    &.empty, &--na { padding: 7px 16px; font-size: 11.5px; justify-content: flex-start; align-items: center; }
  }
}

/* ── 状态 pill / 标签 ── */
.pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
  width: fit-content;

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
}

/* ── 下半区 ── */
.grid-2 {
  display: grid;
  grid-template-columns: 1.4fr 1fr;
  gap: 14px;
  margin-top: 14px;
}

.feed { padding: 4px 0; }

.feed-item {
  display: flex;
  gap: 12px;
  padding: 11px 20px;
  border-bottom: 1px solid var(--border-color);
  align-items: flex-start;
  cursor: pointer;
  transition: background .15s;

  &:last-child { border-bottom: 0; }
  &:hover, &:focus-visible { background: color-mix(in srgb, var(--primary-color) 4%, transparent); outline: none; }
}

.feed-ico {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  display: grid;
  place-items: center;
  flex: none;
  margin-top: 1px;
  font-size: 15px;

  &--success { background: color-mix(in srgb, var(--success-color) 12%, transparent); color: #15803d; }
  &--danger { background: color-mix(in srgb, var(--danger-color) 10%, transparent); color: #b42318; }
  &--primary { background: var(--primary-bg); color: var(--primary-color); }
  &--warning { background: color-mix(in srgb, var(--warning-color) 14%, transparent); color: #b45309; }
  &--info { background: color-mix(in srgb, var(--text-muted) 12%, transparent); color: var(--text-secondary); }
}

.feed-main { flex: 1; min-width: 0; }

.feed-title {
  font-size: 13px;
  color: var(--text-primary);
  line-height: 1.5;

  b { font-weight: 700; }
}

.feed-meta { font-size: 11.5px; color: var(--text-muted); margin-top: 2px; }

.feed-ver {
  font-size: 12px;
  flex: none;
  margin-top: 3px;
  color: var(--text-secondary);
}

.appr-item {
  padding: 14px 20px;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  gap: 8px;

  &:last-child { border-bottom: 0; }
}

.appr-line1 {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;

  .name { font-weight: 700; font-size: 13.5px; }
}

.appr-ver { font-size: 12.5px; font-weight: 700; }
.appr-line2 { font-size: 12px; color: var(--text-muted); }
.appr-actions { display: flex; gap: 8px; margin-top: 2px; }

/* ── 响应式 ── */
@media (max-width: 1100px) {
  .kpi-strip { grid-template-columns: repeat(2, 1fr); }
  .grid-2 { grid-template-columns: 1fr; }
}

@media (max-width: 768px) {
  .kpi-strip { grid-template-columns: 1fr; }
  .mx-sort-hint { display: none; }
  .mx-search { width: 100%; }
}
</style>
