<template>
  <div>
    <!-- 页头 -->
    <div class="page-header">
      <div>
        <h2 class="page-title">部署记录</h2>
        <p class="rec-sub">全部应用的发布台账 · 进行中的记录自动刷新</p>
      </div>
    </div>

    <!-- 筛选栏 -->
    <div class="filter-bar" role="search">
      <el-select v-model="filters.app_name" placeholder="全部应用" clearable filterable class="f-app" aria-label="按应用筛选" @change="applyFilters">
        <el-option v-for="a in appOptions" :key="a" :label="a" :value="a" />
      </el-select>
      <el-select v-model="filters.env_id" placeholder="全部环境" clearable class="f-env" aria-label="按环境筛选" @change="applyFilters">
        <el-option v-for="e in envOptions" :key="e.id" :label="e.display_name || e.name" :value="e.id" />
      </el-select>
      <el-select v-model="filters.status" placeholder="全部状态" clearable class="f-status" aria-label="按状态筛选" @change="applyFilters">
        <el-option label="进行中" value="active" />
        <el-option label="待审批" value="pending" />
        <el-option label="Jenkins 执行中" value="triggering" />
        <el-option label="成功" value="success" />
        <el-option label="失败" value="failed" />
        <el-option label="已取消" value="cancelled" />
      </el-select>
      <el-select v-model="filters.trigger_type" placeholder="触发方式" clearable class="f-trigger" aria-label="按触发方式筛选" @change="applyFilters">
        <el-option label="手动" value="manual" />
        <el-option label="回滚" value="rollback" />
        <el-option label="Webhook" value="webhook" />
      </el-select>
      <el-input
        v-model="filters.version_kw"
        placeholder="搜索版本号…"
        clearable
        class="f-version"
        aria-label="搜索版本号"
        @input="handleVersionInput"
        @keyup.enter="applyFilters"
        @clear="applyFilters"
      />
      <el-button text @click="resetFilters">重置</el-button>
      <span class="sp"></span>
      <span v-if="hasActiveRows" class="refresh-note" role="status"><span class="refresh-dot"></span>有进行中部署 · 每 3s 刷新</span>
    </div>

    <!-- 表格 -->
    <div class="data-card table-card">
      <div class="table-wrapper">
        <el-table :data="items" v-loading="loading" @row-click="(row: any) => goDetail(row)" row-class-name="row-clickable">
          <el-table-column label="ID" width="80">
            <template #default="{ row }"><span class="mono muted">#{{ row.id }}</span></template>
          </el-table-column>
          <el-table-column label="应用" min-width="130">
            <template #default="{ row }"><span class="app-name">{{ row.app_name }}</span></template>
          </el-table-column>
          <el-table-column label="环境" width="100">
            <template #default="{ row }"><span class="type-tag">{{ row.env_name }}</span></template>
          </el-table-column>
          <el-table-column label="版本" min-width="140">
            <template #default="{ row }"><code class="mono ver-code">{{ row.version }}</code></template>
          </el-table-column>
          <el-table-column label="状态" width="140">
            <template #default="{ row }">
              <span class="pill" :class="'pill--' + deployStatusType(row.status)">
                <i class="dot" :class="{ 'dot--pulse': isActiveStatus(row.status) }"></i>{{ deployStatusLabel(row.status) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="触发" width="80">
            <template #default="{ row }">
              <span :class="{ 'trigger-rollback': row.trigger_type === 'rollback' }">{{ triggerTypeLabel(row.trigger_type) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="触发人" width="100">
            <template #default="{ row }">{{ row.trigger_user_name || '—' }}</template>
          </el-table-column>
          <el-table-column label="耗时" width="90">
            <template #default="{ row }"><span class="muted">{{ formatDeployDuration(row.duration) }}</span></template>
          </el-table-column>
          <el-table-column label="时间" width="130">
            <template #default="{ row }">
              <span class="muted" :title="formatFullDateTime(row.created_at)">{{ formatRelativeTime(row.created_at) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="Jenkins" width="100">
            <template #default="{ row }">
              <a
                v-if="row.jenkins_build_url"
                class="meta-link mono"
                :href="row.jenkins_build_url"
                target="_blank"
                rel="noopener noreferrer"
                @click.stop
              >#{{ row.jenkins_build_number }} ↗</a>
              <span v-else class="muted">—</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="150" fixed="right">
            <template #default="{ row }">
              <div @click.stop>
                <el-button v-if="row.status === 'pending' && canApprove" text type="primary" size="small" @click="$router.push('/deploy/approvals')">去审批</el-button>
                <template v-else>
                  <el-button text type="primary" size="small" @click="goDetail(row)">详情</el-button>
                  <el-button v-if="isActiveStatus(row.status) && canExecute" text type="danger" size="small" @click="handleCancel(row)">取消</el-button>
                  <el-button v-else-if="isFinalStatus(row.status) && canRollback && row.status !== 'cancelled'" text size="small" @click="goDetail(row, true)">回滚</el-button>
                </template>
              </div>
            </template>
          </el-table-column>
          <template #empty><el-empty description="暂无部署记录" :image-size="80" /></template>
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
  </div>
</template>
<script setup lang="ts">
import { ref, reactive, computed, onActivated, onDeactivated } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getDeployRecords, getDeployApps, getDeployEnvs, cancelDeploy } from '@/api/deploy'
import { usePagination } from '@/hooks/usePagination'
import { useAuthStore } from '@/stores/modules/auth'
import { formatRelativeTime, formatFullDateTime } from '@/utils/time'
import {
  deployStatusLabel, deployStatusType, isActiveStatus, isFinalStatus,
  triggerTypeLabel, formatDeployDuration,
} from '@/utils/deployStatus'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const items = ref<any[]>([])
const loading = ref(false)
const appOptions = ref<string[]>([])
const envOptions = ref<any[]>([])

// 支持从其他页面带 query 深链（app_name / env_id / status）
const filters = reactive({
  app_name: String(route.query.app_name || ''),
  env_id: route.query.env_id ? Number(route.query.env_id) : null as number | null,
  status: String(route.query.status || ''),
  trigger_type: '',
  version_kw: '',
})

const canExecute = computed(() => authStore.hasPermission('deploy.execute'))
const canRollback = computed(() => authStore.hasPermission('deploy.rollback'))
const canApprove = computed(() => authStore.hasPermission('deploy.approve'))

const hasActiveRows = computed(() => items.value.some(r => isActiveStatus(r.status)))

async function fetchData(extra?: any) {
  loading.value = true
  try {
    const res: any = await getDeployRecords({
      app_name: filters.app_name || undefined,
      env_id: filters.env_id || undefined,
      status: filters.status || undefined,
      trigger_type: filters.trigger_type || undefined,
      version_kw: filters.version_kw || undefined,
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

async function fetchOptions() {
  try {
    const [appsRes, envsRes]: any[] = await Promise.all([getDeployApps({ page_size: 200 }), getDeployEnvs()])
    appOptions.value = (appsRes.data.items || []).map((a: any) => a.name)
    envOptions.value = envsRes.data || []
  } catch {
    // 筛选项加载失败不影响列表
  }
}

// 有进行中记录时每 3s 刷新
let refreshTimer: ReturnType<typeof setInterval> | null = null

onActivated(() => {
  fetchData()
  fetchOptions()
  refreshTimer = setInterval(() => {
    if (hasActiveRows.value) fetchData()
  }, 3000)
})

onDeactivated(() => {
  if (refreshTimer) { clearInterval(refreshTimer); refreshTimer = null }
})

let versionTimer: ReturnType<typeof setTimeout> | null = null

function handleVersionInput() {
  if (versionTimer) clearTimeout(versionTimer)
  versionTimer = setTimeout(applyFilters, 300)
}

function applyFilters() {
  resetPagination()
  fetchData()
}

function resetFilters() {
  Object.assign(filters, { app_name: '', env_id: null, status: '', trigger_type: '', version_kw: '' })
  applyFilters()
}

function goDetail(row: any, rollback = false) {
  router.push({ path: '/deploy/records/' + row.id, query: rollback ? { rollback: '1' } : {} })
}

async function handleCancel(row: any) {
  await ElMessageBox.confirm('确定取消部署单 #' + row.id + '（' + row.version + '）吗？', '取消部署', {
    type: 'warning',
    confirmButtonText: '确定取消',
    cancelButtonText: '再想想',
  })
  await cancelDeploy(row.id)
  ElMessage.success('已取消')
  fetchData()
}
</script>

<style scoped lang="scss">
.rec-sub {
  font-size: 13px;
  color: var(--text-muted);
  margin-top: 4px;
}

.f-app { width: 170px; }
.f-env { width: 130px; }
.f-status { width: 150px; }
.f-trigger { width: 110px; }
.f-version { width: 180px; }

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

.app-name { font-weight: 650; }
.ver-code { font-weight: 700; font-size: 12.5px; }

.trigger-rollback { color: var(--primary-color); font-weight: 600; }

.meta-link {
  color: var(--primary-color);
  font-size: 12px;

  &:hover { text-decoration: underline; }
}

:deep(.row-clickable) { cursor: pointer; }

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

@media (max-width: 900px) {
  .f-app, .f-env, .f-status, .f-trigger, .f-version { width: 100%; }
  .refresh-note { display: none; }
}
</style>
