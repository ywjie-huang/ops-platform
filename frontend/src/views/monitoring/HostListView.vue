<template>
  <div class="host-list">
    <header class="page-header workbench-header">
      <div>
        <h2 class="page-title">主机监控</h2>
        <p class="page-subtitle">按风险优先展示主机，支持快速筛查、详情定位与 SSH 进入处理。</p>
      </div>
      <div class="header-actions">
        <span v-if="lastRefreshTime" class="last-refresh">最近刷新 {{ lastRefreshTime }}</span>
        <span class="refresh-pill">{{ refreshStatusText }}</span>
        <span class="health-pill" :class="loadError ? 'is-danger' : 'is-success'">
          {{ dataHealthText }}
          <template v-if="partialFailureCount"> · {{ partialFailureCount }} 台采集失败</template>
        </span>
        <el-tooltip :content="autoRefresh ? '关闭自动刷新' : '开启后每 15s 自动刷新数据'" placement="bottom">
          <el-button :type="autoRefresh ? 'primary' : 'default'" @click="toggleAutoRefresh">
            <el-icon><Refresh /></el-icon>
            {{ autoRefresh ? '自动刷新中' : '自动刷新' }}
          </el-button>
        </el-tooltip>
        <el-button :loading="loading" @click="fetchData">
          <el-icon><Refresh /></el-icon>
          立即刷新
        </el-button>
      </div>
    </header>

    <section class="risk-summary" aria-label="主机风险摘要">
      <div v-for="card in overviewCards" :key="card.key" class="summary-card" :class="`tone-${card.tone}`">
        <span class="summary-label">{{ card.label }}</span>
        <strong class="summary-value">{{ card.value }}</strong>
      </div>
    </section>

    <section class="priority-strip" aria-label="优先处理主机">
      <div class="strip-header">
        <h3>优先处理</h3>
        <span>当前最值得先看的 {{ Math.min(priorityHosts.length, 5) }} 台主机</span>
      </div>
      <div class="priority-list">
        <button
          v-for="host in priorityHosts"
          :key="host.id"
          type="button"
          class="priority-item"
          :class="`tone-${host.tone}`"
          @click="goDetail(host)"
        >
          <span class="priority-name">{{ host.name }}</span>
          <span class="priority-summary">{{ host.headline }}</span>
          <span class="priority-owner">{{ host.owner || '未分配负责人' }}</span>
        </button>
      </div>
    </section>

    <!-- 错误状态 -->
    <div v-if="loadError" class="error-state">
      <el-icon :size="40" class="error-icon"><WarningFilled /></el-icon>
      <p class="error-text">{{ loadError }}</p>
      <el-button type="primary" @click="fetchData">重新加载</el-button>
    </div>

    <!-- 工作列表工具栏 -->
    <div class="filter-bar worklist-toolbar">
      <el-input
        v-model="keyword"
        placeholder="搜索主机名或 IP"
        clearable
        :prefix-icon="Search"
        class="filter-search"
      />
      <el-select v-model="statusFilter" placeholder="状态" clearable class="filter-status">
        <el-option label="在线" value="online" />
        <el-option label="离线" value="offline" />
        <el-option label="高危" value="danger" />
      </el-select>
      <el-input v-model="ownerFilter" placeholder="负责人" clearable class="filter-owner" />
      <el-select v-model="sortBy" placeholder="排序" class="filter-sort">
        <el-option label="风险优先" value="risk" />
        <el-option label="按 CPU 降序" value="cpu_desc" />
        <el-option label="按内存降序" value="mem_desc" />
        <el-option label="按磁盘降序" value="disk_desc" />
        <el-option label="按主机名" value="name" />
      </el-select>
    </div>

    <!-- 表格 -->
    <div class="data-card">
      <div class="table-wrapper">
        <el-table
          :data="paginatedItems"
          stripe
          v-loading="loading"
          row-class-name="host-row"
          show-overflow-tooltip
          @row-click="goDetail"
        >
          <el-table-column label="主机" min-width="220">
            <template #default="{row}">
              <div class="host-primary">
                <span class="host-name">{{ row.name }}</span>
                <span class="host-meta">{{ row.ip_address }} · {{ row.owner || '未分配负责人' }}</span>
              </div>
            </template>
          </el-table-column>

          <el-table-column label="状态" min-width="100" align="center">
            <template #default="{row}">
              <span class="status-chip" :class="`tone-${getHostStateMeta(row).tone}`">
                {{ getHostStateMeta(row).label }}
              </span>
            </template>
          </el-table-column>

          <el-table-column label="CPU" min-width="130" sortable prop="cpu">
            <template #default="{row}">
              <template v-if="row.prometheus_ok">
                <div class="metric-cell">
                  <div class="metric-bar-track">
                    <div class="metric-bar-fill" :style="{ transform: `scaleX(${row.cpu / 100})`, background: metricColor(row.cpu) }" />
                  </div>
                  <span class="metric-value">{{ row.cpu }}%</span>
                </div>
              </template>
              <span v-else class="no-data">-</span>
            </template>
          </el-table-column>

          <el-table-column label="内存" min-width="130" sortable prop="memory">
            <template #default="{row}">
              <template v-if="row.prometheus_ok">
                <div class="metric-cell">
                  <div class="metric-bar-track">
                    <div class="metric-bar-fill" :style="{ transform: `scaleX(${row.memory / 100})`, background: metricColor(row.memory) }" />
                  </div>
                  <span class="metric-value">{{ row.memory }}%</span>
                </div>
              </template>
              <span v-else class="no-data">-</span>
            </template>
          </el-table-column>

          <el-table-column label="磁盘" min-width="130" sortable prop="disk" class-name="hide-tablet">
            <template #default="{row}">
              <template v-if="row.prometheus_ok">
                <div class="metric-cell">
                  <div class="metric-bar-track">
                    <div class="metric-bar-fill" :style="{ transform: `scaleX(${row.disk / 100})`, background: metricColor(row.disk) }" />
                  </div>
                  <span class="metric-value">{{ row.disk }}%</span>
                </div>
              </template>
              <span v-else class="no-data">-</span>
            </template>
          </el-table-column>

          <el-table-column prop="owner" label="负责人" min-width="110" class-name="hide-desktop">
            <template #default="{row}">
              <span class="owner-value">{{ row.owner || '未分配' }}</span>
            </template>
          </el-table-column>

          <el-table-column label="采集状态" min-width="180">
            <template #default="{row}">
              <span class="collection-state">{{ getHostStateMeta(row).summary }}</span>
            </template>
          </el-table-column>

          <el-table-column label="动作" min-width="90" fixed="right" align="center">
            <template #default="{row}">
              <div class="row-actions">
                <el-button size="small" text type="primary" @click.stop="goDetail(row)">详情</el-button>
                <el-button
                  size="small"
                  text
                  type="primary"
                  @click.stop="$router.push(`/monitoring/hosts/${row.id}/ssh`)"
                >SSH</el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 空状态 -->
      <div v-if="!loading && !loadError && filteredItems.length === 0" class="empty-state">
        <el-empty :description="emptyDescription">
          <el-button v-if="keyword || statusFilter || ownerFilter" type="primary" @click="clearFilters">清除筛选</el-button>
        </el-empty>
      </div>
    </div>

    <!-- 分页 -->
    <div v-if="filteredItems.length > 0" class="pagination-wrap">
      <span class="pagination-total">共 {{ filteredItems.length }} 台</span>
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[20, 50, 100]"
        :total="filteredItems.length"
        layout="sizes, prev, pager, next"
        @current-change="currentPage = $event"
        @size-change="(s: number) => { pageSize = s; currentPage = 1 }"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onActivated, onDeactivated } from 'vue'
import { useRouter } from 'vue-router'
import { getHosts, type HostListItem } from '@/api/monitoring'
import { Refresh, Search, WarningFilled } from '@element-plus/icons-vue'
import { createAutoRefreshController } from '@/utils/autoRefresh'
import {
  buildHostOverview,
  buildPriorityHosts,
  getHostStateMeta,
  sortHostsByRisk,
} from '@/utils/hostMonitor'

const AUTO_REFRESH_INTERVAL_MS = 15000

const router = useRouter()
const loading = ref(false)
const loadError = ref('')
const items = ref<HostListItem[]>([])
const autoRefresh = ref(false)
const lastRefreshTime = ref('')
const keyword = ref('')
const statusFilter = ref('')
const ownerFilter = ref('')
const sortBy = ref('risk')
const autoRefreshController = createAutoRefreshController(fetchData, AUTO_REFRESH_INTERVAL_MS)

const currentPage = ref(1)
const pageSize = ref(20)

const overviewCards = computed(() => buildHostOverview(items.value))
const priorityHosts = computed(() => buildPriorityHosts(items.value))
const refreshStatusText = computed(() => autoRefresh.value ? '自动刷新中' : '手动刷新')
const dataHealthText = computed(() => loadError.value ? '采集异常' : '数据正常')
const partialFailureCount = computed(() => items.value.filter((item) => !item.prometheus_ok).length)

const filteredItems = computed(() => {
  let result = [...items.value]

  if (keyword.value) {
    const kw = keyword.value.toLowerCase()
    result = result.filter(r =>
      r.name?.toLowerCase().includes(kw) || r.ip_address?.toLowerCase().includes(kw)
    )
  }

  if (statusFilter.value === 'online') {
    result = result.filter(r => r.prometheus_ok && getHostStateMeta(r).key !== 'critical')
  } else if (statusFilter.value === 'offline') {
    result = result.filter(r => getHostStateMeta(r).key === 'offline')
  } else if (statusFilter.value === 'danger') {
    result = result.filter(r => getHostStateMeta(r).key === 'critical')
  }

  if (ownerFilter.value) {
    const owner = ownerFilter.value.toLowerCase()
    result = result.filter((item) => String(item.owner || '').toLowerCase().includes(owner))
  }

  const sorters: Record<string, (a: HostListItem, b: HostListItem) => number> = {
    cpu_desc: (a, b) => (b.cpu || 0) - (a.cpu || 0),
    mem_desc: (a, b) => (b.memory || 0) - (a.memory || 0),
    disk_desc: (a, b) => (b.disk || 0) - (a.disk || 0),
    name: (a, b) => (a.name || '').localeCompare(b.name || ''),
  }
  if (sortBy.value === 'risk') {
    result = sortHostsByRisk(result)
  } else {
    result.sort(sorters[sortBy.value] || sorters.cpu_desc)
  }

  return result
})

const paginatedItems = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return filteredItems.value.slice(start, start + pageSize.value)
})

const emptyDescription = computed(() => {
  if (keyword.value || statusFilter.value || ownerFilter.value) return '当前筛选条件下没有匹配的主机'
  return '当前没有可展示的主机监控数据'
})

watch([keyword, statusFilter, sortBy, ownerFilter], () => { currentPage.value = 1 })

function metricColor(v: number) {
  return v > 90 ? 'var(--danger-color)' : v > 70 ? 'var(--warning-color)' : 'var(--success-color)'
}

function goDetail(row: HostListItem) {
  router.push(`/monitoring/hosts/${row.id}`)
}

function clearFilters() {
  keyword.value = ''
  statusFilter.value = ''
  ownerFilter.value = ''
}

function formatTime(date: Date) {
  return `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}:${date.getSeconds().toString().padStart(2, '0')}`
}

async function fetchData() {
  loading.value = true
  loadError.value = ''
  try {
    const res: any = await getHosts()
    items.value = res.data
    lastRefreshTime.value = formatTime(new Date())
  } catch (e: any) {
    loadError.value = e?.message || '加载主机列表失败，请检查网络或稍后重试'
  } finally {
    loading.value = false
  }
}

function toggleAutoRefresh() {
  autoRefresh.value = !autoRefresh.value
  if (autoRefresh.value) {
    autoRefreshController.start()
  } else {
    autoRefreshController.stop()
  }
}

function stopAutoRefresh() {
  autoRefreshController.stop()
}

onActivated(() => {
  fetchData()
  if (autoRefresh.value) {
    autoRefreshController.start()
  }
})
onDeactivated(stopAutoRefresh)
</script>

<style scoped>
.host-list {
  min-height: 100%;
  display: flex;
  flex-direction: column;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.workbench-header {
  align-items: flex-start;
  gap: 16px;
}

.workbench-header > div:first-child {
  min-width: 240px;
}

.page-subtitle {
  margin: 5px 0 0;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.5;
}

.header-actions {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
  justify-content: flex-end;
  max-width: 680px;
}

.last-refresh {
  font-size: 12px;
  color: var(--text-muted);
  white-space: nowrap;
}

.refresh-pill,
.health-pill {
  display: inline-flex;
  align-items: center;
  flex-shrink: 0;
  min-height: 26px;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
}

.health-pill.is-success {
  color: color-mix(in srgb, var(--success-color) 78%, black);
  background: color-mix(in srgb, var(--success-color) 9%, var(--surface-color));
  border-color: color-mix(in srgb, var(--success-color) 22%, var(--border-color));
}

.health-pill.is-danger {
  color: color-mix(in srgb, var(--danger-color) 82%, black);
  background: color-mix(in srgb, var(--danger-color) 9%, var(--surface-color));
  border-color: color-mix(in srgb, var(--danger-color) 24%, var(--border-color));
}

.risk-summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 12px;
}

.summary-card {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: 11px 14px;
  display: grid;
  gap: 4px;
  min-width: 0;
}

.summary-label {
  font-size: 12px;
  color: var(--text-secondary);
}

.summary-value {
  font-size: 20px;
  line-height: 1;
  color: var(--text-primary);
}

.summary-card.tone-danger {
  border-color: color-mix(in srgb, var(--danger-color) 22%, var(--border-color));
}

.summary-card.tone-warning {
  border-color: color-mix(in srgb, var(--warning-color) 24%, var(--border-color));
}

.summary-card.tone-success {
  border-color: color-mix(in srgb, var(--success-color) 20%, var(--border-color));
}

.summary-card.tone-danger .summary-value {
  color: var(--danger-color);
}

.summary-card.tone-warning .summary-value {
  color: color-mix(in srgb, var(--warning-color) 86%, black);
}

.summary-card.tone-success .summary-value {
  color: color-mix(in srgb, var(--success-color) 78%, black);
}

.summary-card.tone-muted .summary-value {
  color: var(--text-secondary);
}

.priority-strip {
  margin-bottom: 12px;
  padding: 11px 14px;
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
}

.strip-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.strip-header h3 {
  margin: 0;
  font-size: 14px;
  color: var(--text-primary);
}

.strip-header span {
  font-size: 12px;
  color: var(--text-muted);
}

.priority-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 8px;
}

.priority-item {
  display: grid;
  gap: 4px;
  text-align: left;
  padding: 9px 10px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--surface-color);
  color: inherit;
  cursor: pointer;
  min-width: 0;
  transition: border-color 180ms ease-out, background-color 180ms ease-out;
}

.priority-item:hover {
  border-color: var(--primary-color);
  background: color-mix(in srgb, var(--primary-color) 4%, var(--surface-color));
}

.priority-item:focus-visible {
  border-color: var(--primary-color);
}

.priority-name,
.host-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.priority-summary,
.priority-owner,
.host-meta,
.collection-state,
.owner-value {
  font-size: 12px;
  color: var(--text-secondary);
}

.priority-owner {
  color: var(--text-muted);
}

/* ── Error State ── */
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  text-align: center;
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  margin-bottom: 12px;
}

.error-icon {
  color: var(--danger-color);
  margin-bottom: 12px;
}

.error-text {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 16px;
  max-width: 400px;
}

/* ── Filter Bar ── */
.filter-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.worklist-toolbar {
  margin-bottom: 12px;
}

.filter-search {
  width: min(320px, 100%);
}

.filter-status {
  width: 120px;
}

.filter-owner {
  width: 150px;
}

.filter-sort {
  width: 150px;
}

/* ── Data Card ── */
.data-card {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  overflow: hidden;
  flex: 1 1 auto;
}

.table-wrapper {
  overflow-x: auto;
}

:deep(.table-wrapper .el-table) {
  min-width: 1080px;
}

:deep(.data-card .el-table__header th) {
  background: color-mix(in srgb, var(--surface-color) 60%, var(--bg-color));
}

:deep(.data-card .el-table__body td) {
  vertical-align: middle;
}

.host-primary {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.host-name,
.host-meta,
.collection-state,
.owner-value {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status-chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 56px;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  line-height: 1.2;
}

.status-chip.tone-success,
.priority-item.tone-success {
  color: color-mix(in srgb, var(--success-color) 80%, black);
  background: color-mix(in srgb, var(--success-color) 8%, var(--surface-color));
  border-color: color-mix(in srgb, var(--success-color) 18%, var(--border-color));
}

.status-chip.tone-muted,
.priority-item.tone-muted {
  color: var(--text-secondary);
  background: color-mix(in srgb, var(--text-muted) 8%, var(--surface-color));
  border-color: color-mix(in srgb, var(--text-muted) 16%, var(--border-color));
}

.status-chip.tone-danger,
.priority-item.tone-danger {
  color: color-mix(in srgb, var(--danger-color) 80%, black);
  background: color-mix(in srgb, var(--danger-color) 8%, var(--surface-color));
  border-color: color-mix(in srgb, var(--danger-color) 20%, var(--border-color));
}

.status-chip.tone-warning,
.priority-item.tone-warning {
  color: color-mix(in srgb, var(--warning-color) 72%, black);
  background: color-mix(in srgb, var(--warning-color) 10%, var(--surface-color));
  border-color: color-mix(in srgb, var(--warning-color) 22%, var(--border-color));
}

/* ── Metric Cell ── */
.metric-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.metric-bar-track {
  width: 48px;
  height: 6px;
  background: color-mix(in srgb, var(--border-color) 80%, var(--bg-color));
  border-radius: 3px;
  overflow: hidden;
  flex-shrink: 0;
}

.metric-bar-fill {
  height: 100%;
  width: 100%;
  border-radius: 3px;
  transform-origin: left;
  transition: transform 0.3s ease-out;
}

.metric-value {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
  min-width: 36px;
  text-align: right;
}

/* ── Row Actions ── */
.row-actions {
  display: flex;
  gap: 2px;
  justify-content: center;
  white-space: nowrap;
}

/* ── No Data ── */
.no-data {
  color: var(--text-muted);
  font-size: 13px;
}

/* ── Empty State ── */
.empty-state {
  padding: 48px 0;
  text-align: center;
}

/* ── Pagination ── */
.pagination-wrap {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 12px;
  padding: 0 12px 12px;
}

.pagination-total {
  font-size: 13px;
  color: var(--text-secondary);
}

/* ── Keyboard Focus ── */
:focus-visible {
  outline: 2px solid var(--primary-color);
  outline-offset: 2px;
  border-radius: 4px;
}

/* ── Reduced Motion ── */
@media (prefers-reduced-motion: reduce) {
  .metric-bar-fill,
  .priority-item {
    transition: none;
  }
}

/* ── Responsive ── */
@media (max-width: 1100px) {
  :deep(.hide-tablet) {
    display: none;
  }
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
  }

  .risk-summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .header-actions {
    max-width: none;
    width: 100%;
    justify-content: flex-start;
  }

  .strip-header {
    align-items: flex-start;
    flex-direction: column;
    gap: 4px;
  }

  .priority-list {
    grid-template-columns: 1fr;
  }

  .filter-bar {
    padding: 10px;
  }

  :deep(.table-wrapper .el-table) {
    min-width: 920px;
  }

  .filter-search,
  .filter-status,
  .filter-owner,
  .filter-sort {
    width: 100%;
  }

  :deep(.hide-desktop) {
    display: none;
  }
}

@media (max-width: 520px) {
  .risk-summary {
    grid-template-columns: 1fr;
  }

  .summary-card {
    grid-template-columns: 1fr auto;
    align-items: center;
  }

  .pagination-wrap {
    align-items: flex-start;
    flex-direction: column;
    gap: 10px;
  }
}
</style>
