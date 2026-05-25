<template>
  <div>
    <div class="page-header">
      <h2 class="page-title">主机监控</h2>
      <div class="header-actions">
        <el-tooltip :content="autoRefresh ? '关闭自动刷新' : '开启后每 60s 自动刷新数据'" placement="bottom">
          <el-button :type="autoRefresh ? 'primary' : 'default'" @click="toggleAutoRefresh">
            <el-icon><Refresh /></el-icon>
            {{ autoRefresh ? '自动刷新中' : '自动刷新' }}
          </el-button>
        </el-tooltip>
      </div>
    </div>

    <!-- 概览统计 -->
    <div class="stat-bar">
      <div class="stat-item">
        <div class="stat-value">{{ items.length }}</div>
        <div class="stat-label">主机总数</div>
      </div>
      <div class="stat-item">
        <div class="stat-value text-success">{{ onlineCount }}</div>
        <div class="stat-label">在线</div>
      </div>
      <div class="stat-item">
        <div class="stat-value text-muted">{{ offlineCount }}</div>
        <div class="stat-label">离线</div>
      </div>
      <div class="stat-item">
        <div class="stat-value text-danger">{{ dangerCount }}</div>
        <div class="stat-label">高负载</div>
      </div>
    </div>

    <!-- 搜索与筛选 -->
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
      </el-select>
      <el-select v-model="sortBy" placeholder="排序" style="width: 140px">
        <el-option label="按 CPU 降序" value="cpu_desc" />
        <el-option label="按内存降序" value="mem_desc" />
        <el-option label="按磁盘降序" value="disk_desc" />
        <el-option label="按主机名" value="name" />
      </el-select>
      <div class="filter-spacer" />
      <el-radio-group v-model="viewMode" size="small">
        <el-radio-button value="card">
          <el-icon><Grid /></el-icon>
        </el-radio-button>
        <el-radio-button value="table">
          <el-icon><List /></el-icon>
        </el-radio-button>
      </el-radio-group>
    </div>

    <!-- 卡片视图 -->
    <div v-if="viewMode === 'card'" v-loading="loading" class="host-grid">
      <div
        v-for="row in filteredItems"
        :key="row.id"
        class="host-card"
        @click="$router.push(`/monitoring/hosts/${row.id}`)"
      >
        <div class="host-card-header">
          <div class="host-info">
            <span :class="['status-dot', row.prometheus_ok ? 'dot-green' : 'dot-grey']" />
            <div>
              <div class="host-name">{{ row.name }}</div>
              <div class="host-ip">{{ row.ip_address }}</div>
            </div>
          </div>
          <div class="host-actions" @click.stop>
            <el-button size="small" text type="primary" @click="$router.push(`/monitoring/hosts/${row.id}`)">详情</el-button>
          </div>
        </div>

        <div class="host-metrics">
          <div class="metric-ring">
            <el-progress type="circle" :percentage="row.cpu || 0" :color="metricColor(row.cpu)" :width="64" :stroke-width="6" />
            <span class="metric-label">CPU</span>
          </div>
          <div class="metric-ring">
            <el-progress type="circle" :percentage="row.memory || 0" :color="metricColor(row.memory)" :width="64" :stroke-width="6" />
            <span class="metric-label">内存</span>
          </div>
          <div class="metric-ring">
            <el-progress type="circle" :percentage="row.disk || 0" :color="metricColor(row.disk)" :width="64" :stroke-width="6" />
            <span class="metric-label">磁盘</span>
          </div>
        </div>

        <div class="host-footer">
          <span class="footer-item">
            <el-icon><Upload /></el-icon> {{ row.network_in ?? '-' }} Mbps
          </span>
          <span class="footer-item">
            <el-icon><Download /></el-icon> {{ row.network_out ?? '-' }} Mbps
          </span>
          <span class="footer-item">负载 {{ row.load ?? '-' }}</span>
        </div>
      </div>

      <div v-if="!loading && filteredItems.length === 0" class="empty-state">
        <el-empty description="没有匹配的主机" />
      </div>
    </div>

    <!-- 表格视图 -->
    <div v-else class="data-card">
      <el-table :data="filteredItems" stripe v-loading="loading">
        <el-table-column label="主机" width="200">
          <template #default="{row}">
            <div style="display:flex;align-items:center;gap:8px">
              <span :class="['status-dot', row.prometheus_ok ? 'dot-green' : 'dot-grey']" />
              <div>
                <strong>{{ row.name }}</strong>
                <br><span style="color:var(--text-muted);font-size:12px">{{ row.ip_address }}</span>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="CPU" min-width="140">
          <template #default="{row}">
            <span v-if="!row.prometheus_ok" class="no-data">-</span>
            <el-progress v-else :percentage="row.cpu" :color="metricColor(row.cpu)" :stroke-width="10" />
          </template>
        </el-table-column>
        <el-table-column label="内存" min-width="140">
          <template #default="{row}">
            <span v-if="!row.prometheus_ok" class="no-data">-</span>
            <el-progress v-else :percentage="row.memory" :color="metricColor(row.memory)" :stroke-width="10" />
          </template>
        </el-table-column>
        <el-table-column label="磁盘" min-width="140">
          <template #default="{row}">
            <span v-if="!row.prometheus_ok" class="no-data">-</span>
            <el-progress v-else :percentage="row.disk" :color="metricColor(row.disk)" :stroke-width="10" />
          </template>
        </el-table-column>
        <el-table-column label="入站" width="90">
          <template #default="{row}">
            <span v-if="!row.prometheus_ok" class="no-data">-</span>
            <span v-else>{{ row.network_in }} Mbps</span>
          </template>
        </el-table-column>
        <el-table-column label="出站" width="90">
          <template #default="{row}">
            <span v-if="!row.prometheus_ok" class="no-data">-</span>
            <span v-else>{{ row.network_out }} Mbps</span>
          </template>
        </el-table-column>
        <el-table-column label="负载" width="70">
          <template #default="{row}">
            <span v-if="!row.prometheus_ok" class="no-data">-</span>
            <span v-else>{{ row.load }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="owner" label="负责人" width="80" />
        <el-table-column label="操作" width="70" fixed="right">
          <template #default="{row}">
            <el-button size="small" text type="primary" @click="$router.push(`/monitoring/hosts/${row.id}`)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onActivated, onDeactivated } from 'vue'
import { getHosts } from '@/api/monitoring'
import { Refresh, Grid, List, Upload, Download, Search } from '@element-plus/icons-vue'

const loading = ref(false)
const items = ref<any[]>([])
const autoRefresh = ref(false)
const keyword = ref('')
const statusFilter = ref('')
const sortBy = ref('cpu_desc')
const viewMode = ref<'card' | 'table'>('card')
let refreshTimer: ReturnType<typeof setInterval> | null = null

const onlineCount = computed(() => items.value.filter(r => r.prometheus_ok).length)
const offlineCount = computed(() => items.value.filter(r => !r.prometheus_ok).length)
const dangerCount = computed(() => items.value.filter(r => (r.cpu > 90 || r.memory > 90 || r.disk > 90)).length)

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

const metricColor = (v: number) => v > 90 ? '#ef4444' : v > 70 ? '#f59e0b' : '#22c55e'

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
.header-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

/* 概览统计栏 */
.stat-bar {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
}

.stat-item {
  flex: 1;
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: 16px 20px;
  text-align: center;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1;
}

.stat-value.text-success { color: var(--success-color); }
.stat-value.text-muted { color: var(--text-muted); }
.stat-value.text-danger { color: var(--danger-color); }

.stat-label {
  font-size: 13px;
  color: var(--text-secondary);
  margin-top: 6px;
}

/* 筛选栏 */
.filter-spacer { flex: 1; }

/* 卡片网格 */
.host-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
  min-height: 200px;
}

.host-card {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 16px 20px;
  cursor: pointer;
  transition: box-shadow 0.2s, border-color 0.2s;
}

.host-card:hover {
  border-color: var(--primary-color);
  box-shadow: 0 4px 16px rgba(59, 130, 246, 0.1);
}

.host-card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 16px;
}

.host-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.host-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.host-ip {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 2px;
}

.host-actions {
  display: flex;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.2s;
}

.host-card:hover .host-actions {
  opacity: 1;
}

/* 指标环形图 */
.host-metrics {
  display: flex;
  justify-content: space-around;
  padding: 8px 0 12px;
}

.metric-ring {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.metric-label {
  font-size: 12px;
  color: var(--text-secondary);
  font-weight: 500;
}

/* 底部网络信息 */
.host-footer {
  display: flex;
  justify-content: space-between;
  padding-top: 12px;
  border-top: 1px solid var(--border-color);
}

.footer-item {
  font-size: 12px;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  gap: 4px;
}

/* 状态指示灯 */
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.dot-green {
  background: #22c55e;
  box-shadow: 0 0 6px rgba(34, 197, 94, 0.4);
}
.dot-grey { background: #94a3b8; }

.no-data {
  color: var(--text-muted);
  font-size: 13px;
}

.empty-state {
  grid-column: 1 / -1;
  padding: 60px 0;
}

/* 响应式 */
@media (max-width: 768px) {
  .stat-bar { flex-wrap: wrap; }
  .stat-item { min-width: calc(50% - 8px); }
  .host-grid { grid-template-columns: 1fr; }
  .host-actions { opacity: 1; }
}
</style>
