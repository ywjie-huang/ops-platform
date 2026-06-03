<template>
  <div class="host-list">
    <header class="page-header">
      <h2 class="page-title">主机监控</h2>
      <div class="header-actions">
        <el-tooltip :content="autoRefresh ? '关闭自动刷新' : '开启后每 60s 自动刷新数据'" placement="bottom">
          <el-button :type="autoRefresh ? 'primary' : 'default'" @click="toggleAutoRefresh">
            <el-icon><Refresh /></el-icon>
            {{ autoRefresh ? '自动刷新中' : '自动刷新' }}
          </el-button>
        </el-tooltip>
      </div>
    </header>

    <!-- 概览统计 pills -->
    <div class="stat-pills" role="group" aria-label="主机统计概览">
      <div class="stat-pill">
        <span class="pill-value">{{ items.length }}</span>
        <span class="pill-label">主机总数</span>
      </div>
      <div class="stat-pill">
        <span class="pill-value pill-success">{{ onlineCount }}</span>
        <span class="pill-label">在线</span>
      </div>
      <div class="stat-pill">
        <span class="pill-value pill-muted">{{ offlineCount }}</span>
        <span class="pill-label">离线</span>
      </div>
      <div class="stat-pill">
        <span class="pill-value pill-danger">{{ dangerCount }}</span>
        <span class="pill-label">高负载</span>
      </div>
    </div>

    <!-- 筛选栏 -->
    <div class="filter-bar">
      <el-input
        v-model="keyword"
        placeholder="搜索主机名或 IP"
        clearable
        :prefix-icon="Search"
        style="width: 240px"
      />
      <el-select v-model="statusFilter" placeholder="状态" clearable style="width: 120px">
        <el-option label="在线" value="online" />
        <el-option label="离线" value="offline" />
        <el-option label="高负载" value="danger" />
      </el-select>
      <el-select v-model="sortBy" placeholder="排序" style="width: 140px">
        <el-option label="按 CPU 降序" value="cpu_desc" />
        <el-option label="按内存降序" value="mem_desc" />
        <el-option label="按磁盘降序" value="disk_desc" />
        <el-option label="按主机名" value="name" />
      </el-select>
    </div>

    <!-- 表格 -->
    <div class="data-card">
      <el-table
        :data="paginatedItems"
        stripe
        v-loading="loading"
        row-class-name="host-row"
        @row-click="goDetail"
      >
        <el-table-column type="selection" width="40" />

        <el-table-column label="主机" min-width="200" sortable>
          <template #default="{row}">
            <div class="host-cell">
              <span :class="['status-dot', statusDotClass(row)]" />
              <div class="host-cell-text">
                <span class="host-cell-name">{{ row.name }}</span>
                <span class="host-cell-ip">{{ row.ip_address }}</span>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="状态" width="80" sortable>
          <template #default="{row}">
            <span :class="['status-tag', statusTagClass(row)]">{{ statusText(row) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="CPU" min-width="140" sortable prop="cpu">
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

        <el-table-column label="内存" min-width="140" sortable prop="memory">
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

        <el-table-column label="磁盘" min-width="140" sortable prop="disk">
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

        <el-table-column label="入站" width="90" sortable prop="network_in">
          <template #default="{row}">
            <span v-if="!row.prometheus_ok" class="no-data">-</span>
            <span v-else class="network-value">{{ row.network_in }} <small>Mbps</small></span>
          </template>
        </el-table-column>

        <el-table-column label="出站" width="90" sortable prop="network_out">
          <template #default="{row}">
            <span v-if="!row.prometheus_ok" class="no-data">-</span>
            <span v-else class="network-value">{{ row.network_out }} <small>Mbps</small></span>
          </template>
        </el-table-column>

        <el-table-column label="负载" width="70" sortable prop="load">
          <template #default="{row}">
            <span v-if="!row.prometheus_ok" class="no-data">-</span>
            <span v-else>{{ row.load }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="owner" label="负责人" width="80" />

        <el-table-column label="操作" width="80" fixed="right">
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

      <!-- 空状态 -->
      <div v-if="!loading && filteredItems.length === 0" class="empty-state">
        <el-empty :description="emptyDescription">
          <el-button v-if="keyword || statusFilter" type="primary" @click="clearFilters">清除筛选</el-button>
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
import { getHosts } from '@/api/monitoring'
import { Refresh, Search } from '@element-plus/icons-vue'

const router = useRouter()
const loading = ref(false)
const items = ref<any[]>([])
const autoRefresh = ref(false)
const keyword = ref('')
const statusFilter = ref('')
const sortBy = ref('cpu_desc')
let refreshTimer: ReturnType<typeof setInterval> | null = null

const currentPage = ref(1)
const pageSize = ref(20)

const onlineCount = computed(() => items.value.filter(r => r.prometheus_ok).length)
const offlineCount = computed(() => items.value.filter(r => !r.prometheus_ok).length)
const dangerCount = computed(() => items.value.filter(r => r.prometheus_ok && (r.cpu > 90 || r.memory > 90 || r.disk > 90)).length)

const filteredItems = computed(() => {
  let result = [...items.value]

  if (keyword.value) {
    const kw = keyword.value.toLowerCase()
    result = result.filter(r =>
      r.name?.toLowerCase().includes(kw) || r.ip_address?.toLowerCase().includes(kw)
    )
  }

  if (statusFilter.value === 'online') {
    result = result.filter(r => r.prometheus_ok)
  } else if (statusFilter.value === 'offline') {
    result = result.filter(r => !r.prometheus_ok)
  } else if (statusFilter.value === 'danger') {
    result = result.filter(r => r.prometheus_ok && (r.cpu > 90 || r.memory > 90 || r.disk > 90))
  }

  const sorters: Record<string, (a: any, b: any) => number> = {
    cpu_desc: (a, b) => (b.cpu || 0) - (a.cpu || 0),
    mem_desc: (a, b) => (b.memory || 0) - (a.memory || 0),
    disk_desc: (a, b) => (b.disk || 0) - (a.disk || 0),
    name: (a, b) => (a.name || '').localeCompare(b.name || ''),
  }
  result.sort(sorters[sortBy.value] || sorters.cpu_desc)

  return result
})

const paginatedItems = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return filteredItems.value.slice(start, start + pageSize.value)
})

const emptyDescription = computed(() => {
  if (keyword.value || statusFilter.value) return '没有匹配的主机'
  return '暂无主机数据'
})

watch([keyword, statusFilter, sortBy], () => { currentPage.value = 1 })

function metricColor(v: number) {
  return v > 90 ? 'var(--danger-color)' : v > 70 ? 'var(--warning-color)' : 'var(--success-color)'
}

function statusDotClass(row: any) {
  if (!row.prometheus_ok) return 'dot-grey'
  if (row.cpu > 90 || row.memory > 90 || row.disk > 90) return 'dot-red'
  return 'dot-green'
}

function statusTagClass(row: any) {
  if (!row.prometheus_ok) return 'tag-offline'
  if (row.cpu > 90 || row.memory > 90 || row.disk > 90) return 'tag-danger'
  return 'tag-online'
}

function statusText(row: any) {
  if (!row.prometheus_ok) return '离线'
  if (row.cpu > 90 || row.memory > 90 || row.disk > 90) return '告警'
  return '在线'
}

function goDetail(row: any) {
  router.push(`/monitoring/hosts/${row.id}`)
}

function clearFilters() {
  keyword.value = ''
  statusFilter.value = ''
}

async function fetchData() {
  loading.value = true
  try {
    const res: any = await getHosts()
    items.value = res.data
  } finally {
    loading.value = false
  }
}

function toggleAutoRefresh() {
  autoRefresh.value = !autoRefresh.value
  if (autoRefresh.value) {
    refreshTimer = setInterval(fetchData, 60000)
  } else if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
}

function stopAutoRefresh() {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
}

onActivated(() => {
  fetchData()
  if (autoRefresh.value) {
    refreshTimer = setInterval(fetchData, 60000)
  }
})
onDeactivated(stopAutoRefresh)
</script>

<style scoped>
.host-list {
  min-height: 100%;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.header-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

/* ── Stat Pills ── */
.stat-pills {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.stat-pill {
  display: flex;
  align-items: baseline;
  gap: 6px;
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  padding: 8px 14px;
}

.pill-value {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1;
}

.pill-success { color: var(--success-color); }
.pill-muted { color: var(--text-muted); }
.pill-danger { color: var(--danger-color); }

.pill-label {
  font-size: 12px;
  color: var(--text-secondary);
}

/* ── Filter Bar ── */
.filter-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  margin-bottom: 12px;
  flex-wrap: wrap;
}

/* ── Data Card ── */
.data-card {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  overflow: hidden;
}

/* ── Host Cell ── */
.host-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.host-cell-text {
  display: flex;
  flex-direction: column;
}

.host-cell-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.3;
}

.host-cell-ip {
  font-size: 11px;
  color: var(--text-muted);
  line-height: 1.3;
}

/* ── Status Dot ── */
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.dot-green {
  background: var(--success-color);
  box-shadow: 0 0 6px rgba(34, 197, 94, 0.4);
}

.dot-grey {
  background: var(--text-muted);
}

.dot-red {
  background: var(--danger-color);
  box-shadow: 0 0 6px rgba(229, 72, 77, 0.4);
}

/* ── Status Tag ── */
.status-tag {
  font-size: 12px;
  font-weight: 500;
  padding: 2px 8px;
  border-radius: 4px;
}

.tag-online {
  color: #16a34a;
  background: rgba(34, 197, 94, 0.1);
}

.tag-offline {
  color: var(--text-muted);
  background: rgba(148, 163, 184, 0.1);
}

.tag-danger {
  color: #dc2626;
  background: rgba(229, 72, 77, 0.1);
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
  background: var(--border-color);
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

/* ── Network Value ── */
.network-value {
  font-size: 12px;
  color: var(--text-primary);
}

.network-value small {
  font-size: 11px;
  color: var(--text-muted);
  font-weight: 400;
}

/* ── Row Actions ── */
.row-actions {
  display: flex;
  gap: 2px;
  opacity: 0;
  transition: opacity 0.15s;
}

.host-row:hover .row-actions {
  opacity: 1;
}

/* ── No Data ── */
.no-data {
  color: var(--text-muted);
  font-size: 13px;
}

/* ── Empty State ── */
.empty-state {
  padding: 60px 0;
  text-align: center;
}

/* ── Pagination ── */
.pagination-wrap {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 12px;
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
  .metric-bar-fill {
    transition: none;
  }
  .row-actions {
    transition: none;
  }
}

/* ── Responsive ── */
@media (max-width: 768px) {
  .stat-pills {
    flex-wrap: wrap;
  }
  .stat-pill {
    min-width: calc(50% - 4px);
  }
  .row-actions {
    opacity: 1;
  }
}
</style>
