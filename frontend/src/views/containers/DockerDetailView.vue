<template>
  <div>
    <div class="page-header">
      <div class="header-left">
        <el-button text aria-label="返回 Docker 监控列表" @click="$router.push('/assets/docker')"><el-icon><ArrowLeft /></el-icon> 返回</el-button>
        <h2 class="page-title">{{ host.name || '主机详情' }}</h2>
        <el-tag :type="host.online ? 'success' : 'danger'" size="small">
          {{ host.online ? '在线' : '离线' }}
        </el-tag>
        <el-tag v-if="host.docker_version" type="info" size="small">Docker {{ host.docker_version }}</el-tag>
      </div>
      <div class="header-right">
        <el-tooltip :content="autoRefresh ? '关闭自动刷新' : '开启后每 15s 自动刷新数据'" placement="bottom">
          <el-button :type="autoRefresh ? 'primary' : 'default'" size="small" @click="toggleAutoRefresh">
            <el-icon><Refresh /></el-icon>
            {{ autoRefresh ? '自动刷新中' : '自动刷新' }}
          </el-button>
        </el-tooltip>
        <el-button :loading="refreshing" size="small" aria-label="立即刷新数据" @click="handleRefresh"><el-icon><Refresh /></el-icon> 刷新</el-button>
        <el-button type="danger" plain size="small" :aria-label="`删除主机 ${host.name}`" @click="handleDelete">删除主机</el-button>
      </div>
    </div>

    <!-- 概览指标 -->
    <div class="overview-grid" role="region" aria-label="主机指标概览">
      <div v-for="item in overviewCards" :key="item.label" class="stat-card">
        <div class="stat-label">{{ item.label }}</div>
        <div class="stat-value" :style="item.color ? { color: item.color } : undefined">{{ item.value }}</div>
        <el-progress
          v-if="item.percent != null"
          :percentage="Math.min(item.percent, 100)"
          :stroke-width="4"
          :show-text="false"
          :color="progressColor(item.percent)"
          class="stat-progress"
        />
      </div>
    </div>

    <!-- 容器列表 -->
    <div class="data-card">
      <div class="filter-bar">
        <el-input v-model="keyword" placeholder="搜索容器名称或镜像…" clearable class="search-input" aria-label="搜索容器" @keyup.enter="fetchContainers" />
        <el-select v-model="statusFilter" placeholder="状态" clearable class="status-select" aria-label="容器状态筛选">
          <el-option label="运行中" value="running" />
          <el-option label="已停止" value="exited" />
          <el-option label="暂停" value="paused" />
        </el-select>
        <span class="container-count">
          共 {{ filteredContainers.length }} 个容器
        </span>
      </div>

      <div class="table-wrapper">
      <el-table :data="pagedContainers" stripe v-loading="loading">
        <el-table-column prop="name" label="容器名称" min-width="180" show-overflow-tooltip>
          <template #default="{row}">
            <strong>{{ row.name }}</strong>
          </template>
        </el-table-column>
        <el-table-column prop="image" label="镜像" min-width="240" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{row}">
            <el-tag :type="containerStatusType(row.status)" size="small">{{ containerStatusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="CPU" width="100" align="center">
          <template #default="{row}">
            <span :class="{ 'value-danger': row.cpu_percent > THRESHOLD_WARN }">
              {{ row.cpu_percent.toFixed(1) }}%
            </span>
          </template>
        </el-table-column>
        <el-table-column label="内存" width="180">
          <template #default="{row}">
            <div class="memory-cell">
              <el-progress
                :percentage="Math.min(row.memory_percent, 100)"
                :stroke-width="6"
                :show-text="false"
                :color="progressColor(row.memory_percent)"
                class="memory-progress"
              />
              <span class="mono memory-text">{{ formatBytes(row.memory_usage) }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="网络 I/O" width="170">
          <template #default="{row}">
            <span class="mono io-text">↓{{ formatBytes(row.net_rx_bytes) }} ↑{{ formatBytes(row.net_tx_bytes) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="restart_count" label="重启" width="70" align="center">
          <template #default="{row}">
            <span :class="{ 'value-danger': row.restart_count > 3 }">{{ row.restart_count }}</span>
          </template>
        </el-table-column>
        <el-table-column label="端口映射" min-width="220" show-overflow-tooltip>
          <template #default="{row}">{{ formatPorts(row.ports) }}</template>
        </el-table-column>
        <el-table-column type="expand" width="40">
          <template #default="{row}">
            <div class="expand-detail">
              <span class="expand-item"><strong>容器 ID:</strong> <code class="mono">{{ row.container_id }}</code></span>
              <span class="expand-item"><strong>磁盘 I/O:</strong> <span class="mono">R {{ formatBytes(row.block_read) }} / W {{ formatBytes(row.block_write) }}</span></span>
              <span class="expand-item"><strong>更新时间:</strong> {{ formatTime(row.updated_at) }}</span>
            </div>
          </template>
        </el-table-column>
      </el-table>
      </div>

      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="filteredContainers.length"
          layout="total, sizes, prev, pager, next"
          small
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onActivated, onDeactivated } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Refresh } from '@element-plus/icons-vue'
import { getDockerHost, deleteDockerHost, refreshDockerHost, getHostContainers } from '@/api/containers'

// ─── 阈值常量 ──────────────────────────────────────────────

const THRESHOLD_WARN = 70
const THRESHOLD_DANGER = 85

const route = useRoute()
const router = useRouter()
const hostId = computed(() => Number(route.params.id))

const host = ref<any>({})
const containers = ref<any[]>([])
const loading = ref(false)
const refreshing = ref(false)
const keyword = ref('')
const statusFilter = ref('')
const page = ref(1)
const pageSize = ref(20)
const autoRefresh = ref(false)

let refreshTimer: ReturnType<typeof setInterval> | null = null

// ─── 工具函数 ──────────────────────────────────────────────

function progressColor(percent: number): string {
  if (percent > THRESHOLD_DANGER) return 'var(--danger-color)'
  if (percent > THRESHOLD_WARN) return 'var(--warning-color)'
  return 'var(--primary-color)'
}

function formatTime(ts: string) {
  if (!ts) return '-'
  try { return new Date(ts).toLocaleString('zh-CN') } catch { return ts }
}

function formatBytes(bytes: number): string {
  if (!bytes || bytes === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  return (bytes / Math.pow(1024, i)).toFixed(i > 0 ? 1 : 0) + ' ' + units[i]
}

function formatPorts(portsJson: string): string {
  if (!portsJson || portsJson === '{}') return '-'
  try {
    const ports = JSON.parse(portsJson)
    const mappings: string[] = []
    for (const [containerPort, bindings] of Object.entries(ports)) {
      if (Array.isArray(bindings) && bindings.length > 0) {
        for (const b of bindings) {
          mappings.push(`${b.HostIp || '0.0.0.0'}:${b.HostPort}→${containerPort}`)
        }
      } else {
        mappings.push(containerPort)
      }
    }
    return mappings.join(', ') || '-'
  } catch { return portsJson }
}

function containerStatusType(s: string) {
  if (s === 'running') return 'success'
  if (s === 'exited') return 'danger'
  if (s === 'paused') return 'warning'
  return 'info'
}

function containerStatusLabel(s: string) {
  if (s === 'running') return '运行中'
  if (s === 'exited') return '已停止'
  if (s === 'paused') return '暂停'
  return s
}

// ─── 计算属性 ──────────────────────────────────────────────

const overviewCards = computed(() => {
  const h = host.value
  const m = h.metrics || {}
  return [
    { label: 'CPU 使用率', value: m.cpu_percent != null ? m.cpu_percent.toFixed(1) + '%' : '-', color: m.cpu_percent != null ? progressColor(m.cpu_percent) : '', percent: m.cpu_percent ?? null },
    { label: '内存使用率', value: m.memory_percent != null ? m.memory_percent.toFixed(1) + '%' : '-', color: m.memory_percent != null ? progressColor(m.memory_percent) : '', percent: m.memory_percent ?? null },
    { label: '磁盘使用率', value: m.disk_usage?.percent != null ? m.disk_usage.percent.toFixed(1) + '%' : '-', color: m.disk_usage?.percent != null ? progressColor(m.disk_usage.percent) : '', percent: m.disk_usage?.percent ?? null },
    { label: '容器总数', value: containers.value.length, color: '', percent: null },
    { label: '运行中', value: containers.value.filter(c => c.status === 'running').length, color: 'var(--success-color)', percent: null },
    { label: '主机 IP', value: h.host_ip || '-', color: '', percent: null },
  ]
})

const filteredContainers = computed(() => {
  let list = containers.value
  if (keyword.value) {
    const kw = keyword.value.toLowerCase()
    list = list.filter(c => c.name.toLowerCase().includes(kw) || c.image.toLowerCase().includes(kw))
  }
  if (statusFilter.value) {
    list = list.filter(c => c.status === statusFilter.value)
  }
  return list
})

const pagedContainers = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return filteredContainers.value.slice(start, start + pageSize.value)
})

watch(keyword, () => { page.value = 1 })
watch(statusFilter, () => { page.value = 1 })

// ─── 数据获取 ──────────────────────────────────────────────

async function fetchHost() {
  if (!hostId.value || isNaN(hostId.value)) return
  try {
    const res: any = await getDockerHost(hostId.value)
    host.value = res.data
  } catch {
    ElMessage.error('主机不存在')
  }
}

async function fetchContainers() {
  if (!hostId.value || isNaN(hostId.value)) return
  loading.value = true
  try {
    const res: any = await getHostContainers(hostId.value)
    containers.value = res.data
  } finally { loading.value = false }
}

async function handleRefresh() {
  refreshing.value = true
  try {
    await refreshDockerHost(hostId.value)
    await fetchHost()
    await fetchContainers()
    ElMessage.success('刷新成功')
  } catch {
    ElMessage.error('Agent 连接失败')
  } finally { refreshing.value = false }
}

async function handleDelete() {
  await ElMessageBox.confirm(`确定删除主机「${host.value.name}」？所有容器数据将被清除。`, '删除确认', { type: 'warning' })
  await deleteDockerHost(hostId.value)
  ElMessage.success('删除成功')
  router.push('/assets/docker')
}

// ─── 自动刷新 ──────────────────────────────────────────────

function toggleAutoRefresh() {
  autoRefresh.value = !autoRefresh.value
  if (autoRefresh.value) {
    refreshTimer = setInterval(() => {
      fetchHost()
      fetchContainers()
    }, 15000)
  } else {
    stopAutoRefresh()
  }
}

function stopAutoRefresh() {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
}

onActivated(() => {
  fetchHost()
  fetchContainers()
})

onDeactivated(stopAutoRefresh)
</script>

<style scoped>
.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.header-right {
  display: flex;
  gap: 8px;
  align-items: center;
}

/* 概览指标 */
.overview-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}
.stat-card {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 12px 16px;
  overflow: hidden;
}
.stat-label {
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.stat-value {
  font-size: 15px;
  font-weight: 700;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: block;
}
.stat-progress {
  margin-top: 6px;
}

/* 筛选栏 */
.search-input {
  width: 260px;
}
.status-select {
  width: 130px;
}
.container-count {
  margin-left: auto;
  color: var(--text-secondary);
  font-size: 13px;
}

/* 表格 */
.memory-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}
.memory-progress {
  flex: 1;
}
.memory-text {
  font-size: 12px;
  white-space: nowrap;
}
.io-text {
  font-size: 12px;
}
.value-danger {
  color: var(--danger-color);
}
.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

/* 展开行 */
.expand-detail {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  padding: 8px 16px;
  font-size: 13px;
}
.expand-item {
  color: var(--text-secondary);
}
.expand-item strong {
  color: var(--text-primary);
}

/* 分页 */
.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

/* 响应式 */
@media (max-width: 1200px) {
  .overview-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}
@media (max-width: 768px) {
  .overview-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .search-input {
    width: 100%;
  }
}
</style>
