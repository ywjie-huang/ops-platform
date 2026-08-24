<template>
  <div>
    <!-- 页头 -->
    <div class="page-header list-head">
      <div>
        <h2 class="page-title">应用管理</h2>
        <p class="list-sub">应用 = 一个可发布单元，绑定一个 Jenkins Job 执行构建与部署</p>
      </div>
      <el-button v-if="canCreate" type="primary" @click="$router.push('/deploy/apps/create')">
        <el-icon><Plus /></el-icon>创建应用
      </el-button>
    </div>

    <!-- 筛选栏 -->
    <div class="filter-bar" role="search">
      <el-input
        v-model="filters.keyword"
        placeholder="搜索应用名称 / Jenkins Job…"
        clearable
        class="filter-input"
        aria-label="搜索应用"
        @input="handleSearchInput"
        @keyup.enter="fetchData()"
        @clear="handleSearchClear"
      >
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <el-select v-model="filters.app_type" placeholder="全部类型" clearable class="filter-select" aria-label="应用类型筛选" @change="fetchData()">
        <el-option v-for="t in appTypes" :key="t.value" :label="t.label" :value="t.value" />
      </el-select>
      <el-select v-model="filters.status" placeholder="全部状态" clearable class="filter-select--sm" aria-label="状态筛选" @change="fetchData()">
        <el-option label="活跃" value="active" />
        <el-option label="已归档" value="archived" />
      </el-select>
      <el-select v-model="envFilter" placeholder="全部环境状态" clearable class="filter-select" aria-label="环境状态筛选">
        <el-option label="有进行中部署" value="active" />
        <el-option label="有失败" value="failed" />
        <el-option label="有待审批" value="pending" />
      </el-select>
      <el-button text @click="resetFilters">重置</el-button>
      <span class="sp"></span>
      <span class="refresh-note" role="status"><span class="refresh-dot"></span>每 10s 自动刷新</span>
    </div>

    <!-- 表格 -->
    <div class="data-card table-card">
      <div class="table-wrapper">
        <el-table :data="visibleItems" v-loading="loading" @row-click="(row: any) => goDetail(row.name)" row-class-name="row-clickable">
          <el-table-column label="应用" min-width="180">
            <template #default="{ row }">
              <div class="app-name">{{ row.name }}</div>
              <div class="app-desc">{{ row.description || row.display_name || '—' }}</div>
            </template>
          </el-table-column>
          <el-table-column label="类型" width="110">
            <template #default="{ row }">
              <span class="type-tag">{{ typeLabel(row.app_type) }}</span>
              <div v-if="row.status === 'archived'" class="archived-note">已归档</div>
            </template>
          </el-table-column>
          <el-table-column label="Jenkins Job" min-width="170">
            <template #default="{ row }">
              <code v-if="row.jenkins_job_name" class="mono job-code">{{ row.jenkins_job_name }}</code>
              <span v-else class="muted">未配置</span>
            </template>
          </el-table-column>
          <el-table-column label="环境状态" min-width="230">
            <template #default="{ row }">
              <div v-if="row.env_status?.length" class="env-chips">
                <span
                  v-for="e in row.env_status"
                  :key="e.env_id"
                  class="echip"
                  :class="echipClass(e)"
                  :title="echipTitle(e)"
                >
                  <span class="echip-env">{{ e.env_name }}</span>
                  <span class="st">{{ echipMark(e) }}</span>
                </span>
              </div>
              <span v-else class="muted">未配置环境</span>
            </template>
          </el-table-column>
          <el-table-column label="最近部署" min-width="170">
            <template #default="{ row }">
              <template v-if="row.last_record">
                <span class="pill" :class="'pill--' + deployStatusType(row.last_record.status)">
                  <i class="dot" :class="{ 'dot--pulse': isActiveStatus(row.last_record.status) }"></i>
                  {{ deployStatusLabel(row.last_record.status) }}
                </span>
                <div class="last-meta">
                  {{ formatRelativeTime(row.last_record.created_at || '') }} · {{ row.last_record.trigger_user_name || '—' }}
                  <template v-if="row.last_record.version"> · <code class="mono">{{ row.last_record.version }}</code></template>
                </div>
              </template>
              <span v-else class="muted">从未部署</span>
            </template>
          </el-table-column>
          <el-table-column label="更新时间" width="110">
            <template #default="{ row }">
              <span class="muted" :title="formatFullDateTime(row.updated_at)">{{ formatRelativeTime(row.updated_at) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="210" fixed="right">
            <template #default="{ row }">
              <div @click.stop>
                <el-button text type="primary" size="small" @click="goDetail(row.name)">详情</el-button>
                <el-button v-if="canExecute" text type="primary" size="small" :disabled="row.status !== 'active' || !row.env_status?.some((e: any) => e.enabled)" @click="openDeploy(row)">部署</el-button>
                <el-button v-if="canUpdate" text size="small" @click="$router.push('/deploy/apps/' + row.name + '/edit')">编辑</el-button>
                <el-button v-if="canDelete" text type="danger" size="small" @click="handleDelete(row)">删除</el-button>
              </div>
            </template>
          </el-table-column>
          <template #empty><el-empty description="暂无应用，点击右上角「创建应用」开始" :image-size="80" /></template>
        </el-table>
      </div>

      <el-pagination
        v-if="total > 0"
        class="pager"
        background
        :layout="paginationLayout"
        :total="total"
        :current-page="currentPage"
        :page-size="pageSize"
        :page-sizes="[10, 20, 50]"
        @current-change="handleCurrentChange"
        @size-change="handleSizeChange"
      />
    </div>

    <!-- 部署弹窗 -->
    <el-dialog v-model="deployDialogVisible" title="确认部署" width="500px" :close-on-click-modal="false">
      <div v-if="deployTarget" class="dlg-body">
        <div class="sum-box">
          <div class="sum-row"><span class="sum-k">应用</span><span class="sum-v">{{ deployTarget.name }}</span></div>
          <div class="sum-row"><span class="sum-k">Jenkins Job</span><span class="sum-v mono">{{ deployTarget.jenkins_job_name || '未配置' }}</span></div>
        </div>
        <div class="field">
          <label for="listDeployEnv">目标环境</label>
          <el-select id="listDeployEnv" v-model="deployEnvId" style="width: 100%" aria-label="选择目标环境">
            <el-option
              v-for="e in enabledEnvs(deployTarget)"
              :key="e.env_id"
              :label="e.env_name"
              :value="e.env_id"
            />
          </el-select>
        </div>
        <div class="field">
          <label for="listDeployVersion">版本号</label>
          <el-input id="listDeployVersion" v-model="deployVersion" placeholder="v3.1.9 / commit hash / tag" />
          <div class="hint">留空将自动使用「分支名 + 时间戳」兜底；需审批的环境提交后进入待审批</div>
        </div>
      </div>
      <template #footer>
        <el-button @click="deployDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="deploying" @click="confirmDeploy">
          <el-icon><Promotion /></el-icon>确认部署
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>
<script setup lang="ts">
import { ref, reactive, computed, onActivated, onDeactivated } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Promotion } from '@element-plus/icons-vue'
import { getDeployApps, deleteDeployApp, executeDeploy } from '@/api/deploy'
import { usePagination } from '@/hooks/usePagination'
import { useAuthStore } from '@/stores/modules/auth'
import { formatRelativeTime, formatFullDateTime } from '@/utils/time'
import { deployStatusLabel, deployStatusType, isActiveStatus } from '@/utils/deployStatus'

const router = useRouter()
const authStore = useAuthStore()

const items = ref<any[]>([])
const loading = ref(false)
const filters = reactive({ keyword: '', app_type: '', status: '' })
const envFilter = ref('')

const canCreate = computed(() => authStore.hasPermission('deploy.create'))
const canExecute = computed(() => authStore.hasPermission('deploy.execute'))
const canUpdate = computed(() => authStore.hasPermission('deploy.update'))
const canDelete = computed(() => authStore.hasPermission('deploy.delete'))

const appTypes = [
  { label: 'Web 应用', value: 'web' },
  { label: 'API 服务', value: 'api' },
  { label: '后台任务', value: 'worker' },
  { label: '前端项目', value: 'frontend' },
  { label: '其他', value: 'other' },
]
const typeLabel = (v: string) => appTypes.find(t => t.value === v)?.label || v

// ── 数据加载 ──
async function fetchData(extra?: any) {
  loading.value = true
  try {
    const res: any = await getDeployApps({
      ...filters,
      page: extra?.page || currentPage.value,
      page_size: extra?.page_size || pageSize.value,
    })
    items.value = res.data.items
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}

const { currentPage, pageSize, total, paginationLayout, handleCurrentChange, handleSizeChange, resetPagination } = usePagination(fetchData)

// 环境状态筛选（作用于当前页数据）
const visibleItems = computed(() => {
  if (!envFilter.value) return items.value
  return items.value.filter(row =>
    (row.env_status || []).some((e: any) => {
      if (envFilter.value === 'active') return isActiveStatus(e.status) && e.status !== 'pending'
      if (envFilter.value === 'failed') return e.status === 'failed'
      if (envFilter.value === 'pending') return e.status === 'pending'
      return true
    }),
  )
})

// ── 自动刷新 ──
let refreshTimer: ReturnType<typeof setInterval> | null = null

onActivated(() => {
  fetchData()
  refreshTimer = setInterval(() => fetchData(), 10000)
})

onDeactivated(() => {
  if (refreshTimer) { clearInterval(refreshTimer); refreshTimer = null }
})

// ── 筛选 ──
let searchTimer: ReturnType<typeof setTimeout> | null = null

function handleSearchInput() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => { resetPagination(); fetchData() }, 300)
}

function handleSearchClear() {
  if (searchTimer) clearTimeout(searchTimer)
  resetPagination()
  fetchData()
}

function resetFilters() {
  Object.assign(filters, { keyword: '', app_type: '', status: '' })
  envFilter.value = ''
  resetPagination()
  fetchData()
}

// ── 环境 chips ──
function echipClass(e: any) {
  if (!e.enabled) return 'echip--off'
  if (!e.status) return ''
  if (e.status === 'success') return 'echip--ok'
  if (e.status === 'failed') return 'echip--bad'
  if (e.status === 'pending') return 'echip--wait'
  if (isActiveStatus(e.status)) return 'echip--run'
  return ''
}

function echipMark(e: any) {
  if (!e.enabled) return '停'
  if (!e.status) return '–'
  if (e.status === 'success') return '✓'
  if (e.status === 'failed') return '✗'
  if (e.status === 'pending') return '待审批'
  if (isActiveStatus(e.status)) return '执行中'
  return '–'
}

function echipTitle(e: any) {
  const label = e.status ? deployStatusLabel(e.status) : '未部署'
  return e.env_name + '：' + (e.enabled ? label : '未启用')
}

// ── 操作 ──
function goDetail(name: string) {
  router.push('/deploy/apps/' + name)
}

async function handleDelete(row: any) {
  await ElMessageBox.confirm(
    '将级联删除该应用的环境配置、部署记录与配置项，且不可恢复。确定删除「' + row.name + '」吗？',
    '删除应用',
    { type: 'error', confirmButtonText: '删除', cancelButtonText: '取消' },
  )
  await deleteDeployApp(row.name)
  ElMessage.success('删除成功')
  fetchData()
}

// ── 部署 ──
const deployDialogVisible = ref(false)
const deployTarget = ref<any>(null)
const deployEnvId = ref<number | null>(null)
const deployVersion = ref('')
const deploying = ref(false)

const enabledEnvs = (row: any) => (row.env_status || []).filter((e: any) => e.enabled)

function openDeploy(row: any) {
  deployTarget.value = row
  deployEnvId.value = enabledEnvs(row)[0]?.env_id ?? null
  deployVersion.value = ''
  deployDialogVisible.value = true
}

async function confirmDeploy() {
  if (!deployTarget.value || !deployEnvId.value) {
    ElMessage.warning('请选择目标环境')
    return
  }
  deploying.value = true
  try {
    const res: any = await executeDeploy({
      app_name: deployTarget.value.name,
      env_id: deployEnvId.value,
      version: deployVersion.value.trim() || undefined,
    })
    ElMessage.success(res.msg || '已提交')
    deployDialogVisible.value = false
    if (res.data?.id) router.push('/deploy/records/' + res.data.id)
  } finally {
    deploying.value = false
  }
}
</script>
<style scoped lang="scss">
.list-head {
  flex-wrap: wrap;
  gap: 10px;
}

.list-sub {
  font-size: 13px;
  color: var(--text-muted);
  margin-top: 4px;
}

.filter-input { width: 260px; }
.filter-select { width: 140px; }
.filter-select--sm { width: 110px; }

.sp { flex: 1; }
.mono { font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace; }
.muted { color: var(--text-muted); }

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

.table-card { padding: 12px 16px 16px; }

.app-name { font-weight: 700; color: var(--text-primary); }

.app-desc {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 2px;
  max-width: 240px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.archived-note {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 3px;
}

.job-code { font-size: 12px; }

.last-meta {
  font-size: 11.5px;
  color: var(--text-muted);
  margin-top: 3px;
}

:deep(.row-clickable) {
  cursor: pointer;
}

/* ── 环境状态 chips ── */
.env-chips {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.echip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 9px;
  border-radius: 6px;
  font-size: 11.5px;
  font-weight: 600;
  border: 1px solid var(--border-color);
  background: color-mix(in srgb, var(--text-muted) 8%, transparent);
  color: var(--text-secondary);

  .st { font-weight: 800; }

  &--ok {
    color: #15803d;
    background: color-mix(in srgb, var(--success-color) 12%, transparent);
    border-color: transparent;
  }

  &--bad {
    color: #b42318;
    background: color-mix(in srgb, var(--danger-color) 10%, transparent);
    border-color: transparent;
  }

  &--run {
    color: var(--primary-color);
    background: var(--primary-bg);
    border-color: transparent;
  }

  &--wait {
    color: #b45309;
    background: color-mix(in srgb, var(--warning-color) 14%, transparent);
    border-color: transparent;
  }

  &--off {
    opacity: .55;
  }
}

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
  padding: 2px 8px;
  border-radius: 6px;
  font-size: 11.5px;
  font-weight: 600;
  color: var(--text-secondary);
  background: color-mix(in srgb, var(--text-muted) 12%, transparent);
}

.pager {
  margin-top: 14px;
  justify-content: flex-end;
}

/* ── 部署弹窗 ── */
.dlg-body { display: flex; flex-direction: column; gap: 14px; }

.sum-box {
  background: color-mix(in srgb, var(--text-muted) 7%, transparent);
  border-radius: var(--border-radius);
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sum-row {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 13px;
}

.sum-k {
  width: 88px;
  flex: none;
  color: var(--text-muted);
  font-size: 12px;
}

.sum-v {
  font-weight: 600;
  color: var(--text-primary);
  word-break: break-all;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;

  label {
    font-size: 13px;
    font-weight: 600;
    color: var(--text-secondary);
  }
}

.hint {
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1.5;
}

@media (max-width: 768px) {
  .filter-input, .filter-select { width: 100%; }
  .refresh-note { display: none; }
}
</style>
