<template>
  <div>
    <!-- 页头 -->
    <div class="page-header appr-head">
      <div>
        <h2 class="page-title">审批中心</h2>
        <p class="appr-sub">需审批环境的部署在此审批，通过后自动触发 Jenkins 执行</p>
      </div>
      <div class="seg" role="tablist" aria-label="审批视图切换">
        <button type="button" role="tab" :aria-selected="view === 'pending'" :class="{ active: view === 'pending' }" @click="switchView('pending')">
          待审批<template v-if="pending.length"> · {{ pending.length }}</template>
        </button>
        <button type="button" role="tab" :aria-selected="view === 'resolved'" :class="{ active: view === 'resolved' }" @click="switchView('resolved')">
          已处理
        </button>
      </div>
    </div>

    <!-- 待审批：卡片队列 -->
    <div v-if="view === 'pending'" v-loading="loading">
      <div v-for="a in pending" :key="a.id" class="appr-card">
        <div class="appr-bar" aria-hidden="true"></div>
        <div class="appr-body">
          <div class="appr-info">
            <div class="appr-t1">
              <span class="name">{{ a.app_name }}</span>
              <span class="arrow muted">→</span>
              <span class="env">{{ a.env_name }}</span>
              <span class="approval-tag">需审批</span>
              <span class="muted appr-rec">部署单 #{{ a.record_id }}</span>
            </div>
            <div class="appr-t2">
              <span>触发人 <b>{{ a.trigger_user_name || '—' }}</b></span>
              <span>提交于 <b :title="formatFullDateTime(a.created_at)">{{ formatRelativeTime(a.created_at) }}</b></span>
              <span v-if="a.jenkins_job_name">Jenkins Job <b class="mono">{{ a.jenkins_job_name }}</b></span>
            </div>
            <div class="appr-diff">
              <span class="muted">版本变更：</span>
              <code class="mono v1">{{ a.current_version || '（首次部署）' }}</code>
              <el-icon class="muted"><ArrowRight /></el-icon>
              <code class="mono v2">{{ a.version }}</code>
            </div>
          </div>
          <div class="appr-side">
            <el-input
              v-model="comments[a.id]"
              type="textarea"
              :rows="2"
              placeholder="审批意见（拒绝时建议填写原因）"
              aria-label="审批意见"
            />
            <div class="appr-btns">
              <el-button type="primary" :loading="actingId === a.id" @click="handleApprove(a)">通过并触发部署</el-button>
              <el-button type="danger" plain :loading="actingId === a.id" @click="handleReject(a)">拒绝</el-button>
              <el-button text size="small" @click="$router.push('/deploy/records/' + a.record_id)">查看部署单</el-button>
            </div>
          </div>
        </div>
      </div>
      <el-empty v-if="!pending.length && !loading" description="太棒了，没有等待审批的发布" :image-size="90" />
    </div>

    <!-- 已处理：表格 -->
    <div v-else class="data-card table-card" v-loading="loading">
      <div class="table-wrapper">
        <el-table :data="resolved">
          <el-table-column label="ID" width="80">
            <template #default="{ row }"><span class="mono muted">#{{ row.id }}</span></template>
          </el-table-column>
          <el-table-column label="应用" min-width="130">
            <template #default="{ row }"><span class="app-name">{{ row.app_name }}</span></template>
          </el-table-column>
          <el-table-column label="环境" width="100">
            <template #default="{ row }"><span class="type-tag type-tag--approval">{{ row.env_name }}</span></template>
          </el-table-column>
          <el-table-column label="版本" min-width="130">
            <template #default="{ row }"><code class="mono ver-code">{{ row.version }}</code></template>
          </el-table-column>
          <el-table-column label="触发人" width="100" prop="trigger_user_name" />
          <el-table-column label="提交时间" width="120">
            <template #default="{ row }">
              <span class="muted" :title="formatFullDateTime(row.created_at)">{{ formatRelativeTime(row.created_at) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="结果" width="110">
            <template #default="{ row }">
              <span class="pill" :class="row.status === 'approved' ? 'pill--success' : 'pill--danger'">
                <i class="dot"></i>{{ row.status === 'approved' ? '已通过' : '已拒绝' }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="审批人" width="100">
            <template #default="{ row }">{{ row.approver_name || '—' }}</template>
          </el-table-column>
          <el-table-column label="意见" min-width="160">
            <template #default="{ row }"><span class="muted">{{ row.comment || '—' }}</span></template>
          </el-table-column>
          <el-table-column label="处理时间" width="120">
            <template #default="{ row }">
              <span class="muted" :title="formatFullDateTime(row.resolved_at)">{{ row.resolved_at ? formatRelativeTime(row.resolved_at) : '—' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="110" fixed="right">
            <template #default="{ row }">
              <el-button text type="primary" size="small" @click="$router.push('/deploy/records/' + row.record_id)">部署单</el-button>
            </template>
          </el-table-column>
          <template #empty><el-empty description="暂无已处理的审批" :image-size="80" /></template>
        </el-table>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref, reactive, onActivated, onDeactivated } from 'vue'
import { ElMessage } from 'element-plus'
import { ArrowRight } from '@element-plus/icons-vue'
import { getDeployApprovals, approveDeploy, rejectDeploy } from '@/api/deploy'
import { formatRelativeTime, formatFullDateTime } from '@/utils/time'

const view = ref<'pending' | 'resolved'>('pending')
const pending = ref<any[]>([])
const resolved = ref<any[]>([])
const loading = ref(false)
const comments = reactive<Record<number, string>>({})
const actingId = ref<number | null>(null)

async function fetchPending() {
  loading.value = true
  try {
    const res: any = await getDeployApprovals({ status: 'pending' })
    pending.value = res.data || []
  } finally {
    loading.value = false
  }
}

async function fetchResolved() {
  loading.value = true
  try {
    const res: any = await getDeployApprovals({ status: 'resolved' })
    resolved.value = res.data || []
  } finally {
    loading.value = false
  }
}

function switchView(v: 'pending' | 'resolved') {
  view.value = v
  if (v === 'pending') fetchPending()
  else fetchResolved()
}

// 待审批视图 15s 自动刷新
let refreshTimer: ReturnType<typeof setInterval> | null = null

onActivated(() => {
  fetchPending()
  refreshTimer = setInterval(() => {
    if (view.value === 'pending') fetchPending()
  }, 15000)
})

onDeactivated(() => {
  if (refreshTimer) { clearInterval(refreshTimer); refreshTimer = null }
})

async function handleApprove(a: any) {
  actingId.value = a.id
  try {
    await approveDeploy(a.id, (comments[a.id] || '').trim() || undefined)
    ElMessage.success('已通过，Jenkins 执行中')
    delete comments[a.id]
    await fetchPending()
  } finally {
    actingId.value = null
  }
}

async function handleReject(a: any) {
  actingId.value = a.id
  try {
    await rejectDeploy(a.id, (comments[a.id] || '').trim() || undefined)
    ElMessage.success('已拒绝')
    delete comments[a.id]
    await fetchPending()
  } finally {
    actingId.value = null
  }
}
</script>

<style scoped lang="scss">
.appr-head {
  flex-wrap: wrap;
  gap: 10px;
}

.appr-sub {
  font-size: 13px;
  color: var(--text-muted);
  margin-top: 4px;
}

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
    font-size: 12.5px;
    font-weight: 600;
    color: var(--text-secondary);
    padding: 6px 14px;
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

.mono { font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace; }
.muted { color: var(--text-muted); }

/* ── 待审批卡片 ── */
.appr-card {
  display: flex;
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  overflow: hidden;
  margin-bottom: 12px;
  transition: box-shadow .2s ease-out;

  &:hover {
    box-shadow: 0 2px 10px color-mix(in srgb, var(--warning-color) 12%, transparent);
  }
}

.appr-bar {
  width: 4px;
  flex: none;
  background: var(--warning-color);
}

.appr-body {
  flex: 1;
  min-width: 0;
  display: grid;
  grid-template-columns: 1fr 300px;
  gap: 18px;
  padding: 16px 20px;
}

.appr-info { min-width: 0; }

.appr-t1 {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;

  .name { font-size: 15px; font-weight: 750; }
  .env { font-size: 13px; font-weight: 700; color: var(--text-secondary); }
}

.appr-rec { font-size: 12px; }

.appr-t2 {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  font-size: 12.5px;
  color: var(--text-muted);
  margin-top: 8px;

  b { color: var(--text-secondary); font-weight: 600; }
}

.appr-diff {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  font-size: 12.5px;
  flex-wrap: wrap;

  .v1 {
    color: var(--text-muted);
    text-decoration: line-through;
    font-size: 12.5px;
  }

  .v2 {
    color: var(--text-primary);
    font-weight: 800;
    font-size: 13.5px;
  }
}

.appr-side {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.appr-btns {
  display: flex;
  gap: 8px;
  align-items: center;

  .el-button + .el-button { margin-left: 0; }
}

/* ── 已处理表格 ── */
.table-card { padding: 12px 16px 16px; }

.app-name { font-weight: 650; }
.ver-code { font-weight: 700; font-size: 12.5px; }

.pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;

  .dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }

  &--success { color: #15803d; background: color-mix(in srgb, var(--success-color) 12%, transparent); }
  &--danger { color: #b42318; background: color-mix(in srgb, var(--danger-color) 10%, transparent); }
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

@media (max-width: 900px) {
  .appr-body { grid-template-columns: 1fr; }
}
</style>
