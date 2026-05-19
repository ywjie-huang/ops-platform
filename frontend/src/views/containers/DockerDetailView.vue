<template>
  <div>
    <div class="page-header">
      <div style="display:flex;align-items:center;gap:12px">
        <el-button text @click="$router.push('/assets/docker')"><el-icon><ArrowLeft /></el-icon> 返回</el-button>
        <h2 class="page-title" style="margin:0">{{ host.name || '主机详情' }}</h2>
        <el-tag :type="host.online ? 'success' : 'danger'" size="small">
          {{ host.online ? '在线' : '离线' }}
        </el-tag>
        <el-tag v-if="host.docker_version" type="info" size="small">Docker {{ host.docker_version }}</el-tag>
      </div>
      <div style="display:flex;gap:8px">
        <el-button :loading="refreshing" @click="handleRefresh"><el-icon><Refresh /></el-icon> 刷新</el-button>
        <el-button type="danger" plain @click="handleDelete">删除主机</el-button>
      </div>
    </div>

    <!-- 主机信息卡片 -->
    <el-row :gutter="16" style="margin-bottom:16px">
      <el-col :span="4" v-for="item in hostInfoCards" :key="item.label">
        <div class="stat-card">
          <div class="stat-label">{{ item.label }}</div>
          <div class="stat-value" :style="{ color: item.color }">{{ item.value }}</div>
        </div>
      </el-col>
    </el-row>

    <!-- 主机系统指标 -->
    <el-row :gutter="16" style="margin-bottom:16px">
      <el-col :span="4" v-for="item in metricCards" :key="item.label">
        <div class="stat-card metric-card">
          <div class="stat-label">{{ item.label }}</div>
          <div class="metric-value">
            <span class="stat-value" :style="{ color: item.color }">{{ item.value }}</span>
            <el-progress
              v-if="item.percent != null"
              :percentage="Math.min(item.percent, 100)"
              :stroke-width="4"
              :show-text="false"
              :color="item.percent > 85 ? '#f56c6c' : item.percent > 70 ? '#e6a23c' : '#409eff'"
              style="margin-top:6px"
            />
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 容器列表 -->
    <div class="data-card">
      <div class="filter-bar">
        <el-input v-model="keyword" placeholder="搜索容器名称或镜像…" clearable style="width:260px" @keyup.enter="fetchContainers" />
        <el-select v-model="statusFilter" placeholder="状态" clearable style="width:130px">
          <el-option label="运行中" value="running" />
          <el-option label="已停止" value="exited" />
          <el-option label="暂停" value="paused" />
        </el-select>
        <span style="margin-left:auto;color:var(--text-muted);font-size:13px">
          共 {{ filteredContainers.length }} 个容器
        </span>
      </div>

      <el-table :data="pagedContainers" stripe v-loading="loading">
        <el-table-column prop="name" label="容器名称" min-width="180" show-overflow-tooltip>
          <template #default="{row}">
            <strong>{{ row.name }}</strong>
          </template>
        </el-table-column>
        <el-table-column prop="container_id" label="容器 ID" width="130">
          <template #default="{row}"><code class="mono">{{ row.container_id }}</code></template>
        </el-table-column>
        <el-table-column prop="image" label="镜像" min-width="240" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{row}">
            <el-tag :type="containerStatusType(row.status)" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="CPU" width="100" align="center">
          <template #default="{row}">
            <span :style="{ color: row.cpu_percent > 80 ? 'var(--el-color-danger)' : '' }">
              {{ row.cpu_percent.toFixed(1) }}%
            </span>
          </template>
        </el-table-column>
        <el-table-column label="内存" width="180">
          <template #default="{row}">
            <div style="display:flex;align-items:center;gap:8px">
              <el-progress
                :percentage="Math.min(row.memory_percent, 100)"
                :stroke-width="6"
                :show-text="false"
                :color="row.memory_percent > 80 ? '#f56c6c' : row.memory_percent > 60 ? '#e6a23c' : '#409eff'"
                style="flex:1"
              />
              <span class="mono" style="font-size:12px;white-space:nowrap">{{ formatBytes(row.memory_usage) }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="网络 I/O" width="170">
          <template #default="{row}">
            <span class="mono" style="font-size:12px">↓{{ formatBytes(row.net_rx_bytes) }} ↑{{ formatBytes(row.net_tx_bytes) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="磁盘 I/O" width="170">
          <template #default="{row}">
            <span class="mono" style="font-size:12px">R{{ formatBytes(row.block_read) }} W{{ formatBytes(row.block_write) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="restart_count" label="重启" width="70" align="center">
          <template #default="{row}">
            <span :style="{ color: row.restart_count > 3 ? 'var(--el-color-danger)' : '' }">{{ row.restart_count }}</span>
          </template>
        </el-table-column>
        <el-table-column label="端口映射" min-width="220" show-overflow-tooltip>
          <template #default="{row}">{{ formatPorts(row.ports) }}</template>
        </el-table-column>
        <el-table-column prop="updated_at" label="更新时间" width="170">
          <template #default="{row}">{{ formatTime(row.updated_at) }}</template>
        </el-table-column>
      </el-table>
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
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Refresh } from '@element-plus/icons-vue'
import { getDockerHost, deleteDockerHost, refreshDockerHost, getHostContainers } from '@/api/containers'

const route = useRoute()
const router = useRouter()
const hostId = Number(route.params.id)

const host = ref<any>({})
const containers = ref<any[]>([])
const loading = ref(false)
const refreshing = ref(false)
const keyword = ref('')
const statusFilter = ref('')
const page = ref(1)
const pageSize = ref(20)

let refreshTimer: ReturnType<typeof setInterval> | null = null

// ─── 计算属性 ──────────────────────────────────────────────

const hostInfoCards = computed(() => {
  const h = host.value
  return [
    { label: '主机 IP', value: h.host_ip || '-', color: '' },
    { label: 'Agent 地址', value: h.endpoint || '-', color: '' },
    { label: '操作系统', value: h.host_os || '-', color: '' },
    { label: 'Docker 版本', value: h.docker_version || '-', color: '' },
    { label: '最后同步', value: h.last_heartbeat ? formatTime(h.last_heartbeat) : '从未', color: '' },
    { label: '说明', value: h.description || '-', color: '' },
  ]
})

const metricCards = computed(() => {
  const m = host.value.metrics || {}
  return [
    { label: 'CPU 核心', value: m.cpu_count ?? '-', color: '', percent: null },
    { label: 'CPU 使用率', value: m.cpu_percent != null ? m.cpu_percent.toFixed(1) + '%' : '-', color: m.cpu_percent > 80 ? 'var(--el-color-danger)' : '', percent: m.cpu_percent ?? null },
    { label: '内存使用率', value: m.memory_percent != null ? m.memory_percent.toFixed(1) + '%' : '-', color: m.memory_percent > 80 ? 'var(--el-color-danger)' : '', percent: m.memory_percent ?? null },
    { label: '磁盘使用率', value: m.disk_usage?.percent != null ? m.disk_usage.percent.toFixed(1) + '%' : '-', color: (m.disk_usage?.percent || 0) > 85 ? 'var(--el-color-danger)' : '', percent: m.disk_usage?.percent ?? null },
    { label: '容器总数', value: containers.value.length, color: '', percent: null },
    { label: '运行中', value: containers.value.filter(c => c.status === 'running').length, color: 'var(--el-color-success)', percent: null },
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

// ─── 工具函数 ──────────────────────────────────────────────

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

// ─── 数据获取 ──────────────────────────────────────────────

async function fetchHost() {
  try {
    const res: any = await getDockerHost(hostId)
    host.value = res.data
  } catch {
    ElMessage.error('主机不存在')
    router.push('/assets/docker')
  }
}

async function fetchContainers() {
  loading.value = true
  try {
    const res: any = await getHostContainers(hostId)
    containers.value = res.data
  } finally { loading.value = false }
}

async function handleRefresh() {
  refreshing.value = true
  try {
    await refreshDockerHost(hostId)
    await fetchHost()
    await fetchContainers()
    ElMessage.success('刷新成功')
  } catch {
    ElMessage.error('Agent 连接失败')
  } finally { refreshing.value = false }
}

async function handleDelete() {
  await ElMessageBox.confirm(`确定删除主机「${host.value.name}」？所有容器数据将被清除。`, '删除确认', { type: 'warning' })
  await deleteDockerHost(hostId)
  ElMessage.success('删除成功')
  router.push('/assets/docker')
}

// ─── 自动刷新 ──────────────────────────────────────────────

function startAutoRefresh() {
  refreshTimer = setInterval(() => {
    fetchHost()
    fetchContainers()
  }, 15000)
}

onMounted(() => {
  fetchHost()
  fetchContainers()
  startAutoRefresh()
})

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer)
})
</script>

<style scoped>
.stat-card {
  background: #fff;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 12px 16px;
  overflow: hidden;
}
.stat-label { font-size: 12px; color: var(--text-muted); margin-bottom: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.stat-value { font-size: 15px; font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; display: block; }
.metric-card { min-height: 72px; }
.metric-value { min-height: 36px; }
.mono { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }
.pagination-wrap { display: flex; justify-content: flex-end; margin-top: 16px; }
</style>
