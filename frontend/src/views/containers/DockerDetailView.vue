<template>
  <div>
    <div class="detail-header">
      <div>
        <div class="detail-title-row">
          <el-button text aria-label="返回 Docker 监控列表" @click="$router.push('/assets/docker')">
            <el-icon><ArrowLeft /></el-icon>
            返回
          </el-button>
          <h2 class="page-title">{{ host.name || '主机详情' }}</h2>
          <el-tag :type="host.online ? 'success' : 'danger'" size="small">
            <span class="tag-dot" :class="host.online ? 'dot-success' : 'dot-danger'" aria-hidden="true"></span>
            {{ host.online ? '在线' : '离线' }}
          </el-tag>
          <el-tag v-if="containerSummary.abnormal > 0" type="warning" size="small">
            {{ containerSummary.abnormal }} 个异常容器
          </el-tag>
        </div>
        <div class="detail-fields">
          <div>
            <div class="field-label">Agent 地址</div>
            <div class="field-value mono">{{ host.endpoint || '-' }}</div>
          </div>
          <div>
            <div class="field-label">主机 IP</div>
            <div class="field-value mono">{{ host.host_ip || endpointHost(host.endpoint) || '-' }}</div>
          </div>
          <div>
            <div class="field-label">Docker 版本</div>
            <div class="field-value">{{ host.docker_version || '-' }}</div>
          </div>
          <div>
            <div class="field-label">最后同步</div>
            <div class="field-value" :class="syncValueClass">{{ relativeSyncTime }}</div>
          </div>
        </div>
      </div>
      <div class="header-actions">
        <el-tooltip :content="autoRefresh ? '关闭自动刷新' : '开启后每 15s 自动刷新数据'" placement="bottom">
          <el-button :type="autoRefresh ? 'primary' : 'default'" size="small" @click="toggleAutoRefresh">
            <el-icon><Refresh /></el-icon>
            {{ autoRefresh ? '自动刷新中' : '自动刷新' }}
          </el-button>
        </el-tooltip>
        <el-button :loading="refreshing" type="primary" size="small" aria-label="立即刷新 Docker 主机数据" @click="handleRefresh">
          <el-icon><Refresh /></el-icon>
          立即刷新
        </el-button>
        <el-button type="danger" plain size="small" :aria-label="`删除主机 ${host.name}`" @click="handleDelete">删除主机</el-button>
      </div>
    </div>

    <div class="sync-notice" :class="syncNoticeClass">
      <span class="status-dot" :class="syncDotClass" aria-hidden="true"></span>
      <span>{{ syncNoticeText }}</span>
    </div>

    <div class="summary-grid" role="region" aria-label="主机指标概览">
      <div v-for="item in overviewCards" :key="item.label" class="metric-card">
        <div class="metric-label">{{ item.label }}</div>
        <div class="metric-value" :class="item.valueClass">{{ item.value }}</div>
        <el-progress
          v-if="item.percent != null"
          :percentage="Math.min(item.percent, 100)"
          :stroke-width="4"
          :show-text="false"
          :color="progressColor(item.percent)"
          class="stat-progress"
        />
        <div class="metric-foot">{{ item.foot }}</div>
      </div>
    </div>

    <div class="detail-grid">
      <div class="panel">
        <div class="panel-head">
          <div>
            <h3 class="panel-title">容器列表</h3>
            <p class="panel-subtitle">异常和重启次数较高的容器优先展示。</p>
          </div>
          <div class="container-tools">
            <el-input v-model="keyword" placeholder="搜索容器名或镜像" clearable class="search-input" aria-label="搜索容器" />
            <el-button size="small" :loading="loading" @click="fetchContainers">刷新列表</el-button>
          </div>
        </div>

        <div class="status-tabs" role="tablist" aria-label="容器状态筛选">
          <button
            v-for="tab in statusTabs"
            :key="tab.value"
            type="button"
            class="status-tab"
            :class="{ active: statusFilter === tab.value }"
            @click="statusFilter = tab.value"
          >
            {{ tab.label }} {{ tab.count }}
          </button>
        </div>

        <div class="table-wrapper">
          <el-table :data="pagedContainers" stripe v-loading="loading">
            <el-table-column prop="name" label="容器" min-width="210" show-overflow-tooltip>
              <template #default="{ row }">
                <div class="container-name">
                  <strong>{{ row.name }}</strong>
                  <span class="mono">{{ row.image }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="120">
              <template #default="{ row }">
                <el-tag :type="containerStatusType(row.status)" size="small">
                  <span class="tag-dot" :class="containerDotClass(row.status)" aria-hidden="true"></span>
                  {{ containerStatusLabel(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="CPU" width="100" align="center">
              <template #default="{ row }">
                <span :class="{ 'text-warning': row.cpu_percent > THRESHOLD_WARN, 'text-danger': row.cpu_percent > THRESHOLD_DANGER }">
                  {{ Number(row.cpu_percent || 0).toFixed(1) }}%
                </span>
              </template>
            </el-table-column>
            <el-table-column label="内存" width="170">
              <template #default="{ row }">
                <div class="memory-cell">
                  <el-progress
                    :percentage="Math.min(row.memory_percent || 0, 100)"
                    :stroke-width="6"
                    :show-text="false"
                    :color="progressColor(row.memory_percent || 0)"
                    class="memory-progress"
                  />
                  <span class="mono memory-text">{{ formatBytes(row.memory_usage) }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="端口" min-width="190" show-overflow-tooltip>
              <template #default="{ row }">{{ formatPorts(row.ports) }}</template>
            </el-table-column>
            <el-table-column prop="restart_count" label="重启" width="80" align="center">
              <template #default="{ row }">
                <span :class="{ 'text-warning': row.restart_count > 3, 'text-danger': row.restart_count > 10 }">{{ row.restart_count }}</span>
              </template>
            </el-table-column>
            <el-table-column label="更新时间" width="150">
              <template #default="{ row }">{{ formatTime(row.updated_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="250" fixed="right" align="right">
              <template #default="{ row }">
                <div class="action-cell">
                  <el-button
                    size="small"
                    type="info"
                    link
                    :aria-label="`查看容器 ${row.name} 日志`"
                    @click.stop="openContainerLogs(row)"
                  >日志</el-button>
                  <el-button
                    v-if="row.status !== 'running'"
                    size="small"
                    type="success"
                    link
                    :aria-label="`启动容器 ${row.name}`"
                    @click.stop="handleContainerAction(row, 'start')"
                  >启动</el-button>
                  <el-button
                    v-if="row.status === 'running'"
                    size="small"
                    type="primary"
                    link
                    :aria-label="`重启容器 ${row.name}`"
                    @click.stop="handleContainerAction(row, 'restart')"
                  >重启</el-button>
                  <el-button
                    v-if="row.status === 'running'"
                    size="small"
                    type="warning"
                    link
                    :aria-label="`停止容器 ${row.name}`"
                    @click.stop="handleContainerAction(row, 'stop')"
                  >停止</el-button>
                  <el-button
                    size="small"
                    type="danger"
                    link
                    :aria-label="`删除容器 ${row.name}`"
                    @click.stop="handleContainerAction(row, 'delete')"
                  >删除</el-button>
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

      <aside class="panel health-panel">
        <div class="panel-head compact">
          <h3 class="panel-title">主机健康</h3>
          <el-tag :type="healthTagType" size="small">{{ healthLabel }}</el-tag>
        </div>
        <div class="health-list">
          <div v-for="item in healthItems" :key="item.label" class="health-item">
            <div class="health-row">
              <span>{{ item.label }}</span>
              <strong>{{ item.value }}</strong>
            </div>
            <div class="health-bar" aria-hidden="true">
              <span :class="item.barClass" :style="{ width: item.percent + '%' }"></span>
            </div>
          </div>
        </div>
        <div class="event-list">
          <div class="event-item">
            <strong>异常容器</strong>
            <span>{{ containerSummary.abnormal > 0 ? `发现 ${containerSummary.abnormal} 个异常容器` : '未发现异常容器' }}</span>
          </div>
          <div class="event-item">
            <strong>同步状态</strong>
            <span>{{ syncHintText }}</span>
          </div>
          <div class="event-item">
            <strong>建议动作</strong>
            <span>{{ actionSuggestion }}</span>
          </div>
        </div>
      </aside>
    </div>

    <el-drawer v-model="logsDrawerVisible" size="720px" :with-header="false" destroy-on-close>
      <div class="drawer-head">
        <div class="drawer-head-copy">
          <h3>{{ selectedContainer?.name || '容器' }}</h3>
          <div class="drawer-sub">{{ selectedContainer?.image || '-' }} · {{ selectedContainer ? containerStatusLabel(selectedContainer.status) : '' }}</div>
        </div>
        <div class="drawer-actions">
          <el-button size="small" :loading="logsLoading" @click="fetchSelectedContainerLogs">刷新</el-button>
          <el-button size="small" :disabled="!containerLogs" @click="copyLogs">复制</el-button>
          <el-button size="small" :disabled="!containerLogs" @click="downloadLogs">下载</el-button>
        </div>
      </div>
      <div class="drawer-body">
        <div class="log-toolbar">
          <span>最近</span>
          <el-select v-model="logTailLines" size="small" class="log-tail-select" @change="fetchSelectedContainerLogs">
            <el-option :value="100" label="100 行" />
            <el-option :value="300" label="300 行" />
            <el-option :value="500" label="500 行" />
            <el-option :value="1000" label="1000 行" />
          </el-select>
        </div>
        <div v-loading="logsLoading">
          <pre class="log-box" tabindex="0" role="log" aria-label="Docker 容器日志">{{ containerLogs || '暂无日志' }}</pre>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onActivated, onDeactivated } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Refresh } from '@element-plus/icons-vue'
import {
  getDockerHost,
  deleteDockerHost,
  refreshDockerHost,
  getHostContainers,
  getDockerContainerLogs,
  startDockerContainer,
  stopDockerContainer,
  restartDockerContainer,
  deleteDockerContainer,
} from '@/api/containers'
import { getHostSyncState, secondsSince, sortContainersByRisk, summarizeContainers } from '@/utils/dockerMonitor'

const THRESHOLD_WARN = 70
const THRESHOLD_DANGER = 85

const route = useRoute()
const router = useRouter()
const hostName = computed(() => (
  route.name === 'DockerDetail' ? String(route.params.name ?? '') : ''
))

const host = ref<any>({})
const containers = ref<any[]>([])
const loading = ref(false)
const refreshing = ref(false)
const keyword = ref('')
const statusFilter = ref('all')
const page = ref(1)
const pageSize = ref(20)
const autoRefresh = ref(false)
const selectedContainer = ref<any | null>(null)
const logsDrawerVisible = ref(false)
const logsLoading = ref(false)
const containerLogs = ref('')
const logTailLines = ref(300)

let refreshTimer: ReturnType<typeof setInterval> | null = null

const containerSummary = computed(() => summarizeContainers(containers.value))
const syncState = computed(() => getHostSyncState(host.value))
const relativeSyncTime = computed(() => formatRelativeTime(host.value.last_heartbeat))

const syncValueClass = computed(() => {
  if (syncState.value === 'fresh') return ''
  if (syncState.value === 'stale') return 'text-warning'
  return 'text-danger'
})

const syncNoticeClass = computed(() => syncState.value === 'fresh' ? 'notice-info' : syncState.value === 'stale' ? 'notice-warning' : 'notice-danger')
const syncDotClass = computed(() => syncState.value === 'fresh' ? 'dot-info' : syncState.value === 'stale' ? 'dot-warning' : 'dot-danger')
const syncHintText = computed(() => {
  if (syncState.value === 'fresh') return 'Agent 同步正常'
  if (syncState.value === 'stale') return '数据可能过期'
  if (syncState.value === 'offline') return host.value.status_message || 'Agent 连接失败'
  return '等待首次同步'
})
const syncNoticeText = computed(() => {
  if (syncState.value === 'fresh') return '当前容器数据来自平台最近一次 Agent 同步。需要现场确认时，请点击“立即刷新”。'
  if (syncState.value === 'stale') return '当前数据超过 60 秒未同步，建议立即刷新后再执行容器操作。'
  return '当前主机未正常同步，列表可能不是最新状态，请检查 Agent 地址和网络连通性。'
})

const statusTabs = computed(() => [
  { label: '全部', value: 'all', count: containers.value.length },
  { label: '运行中', value: 'running', count: containers.value.filter((item) => item.status === 'running').length },
  { label: '已停止', value: 'exited', count: containers.value.filter((item) => item.status === 'exited').length },
  { label: '异常', value: 'abnormal', count: containerSummary.value.abnormal },
])

const filteredContainers = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  let list = containers.value
  if (kw) {
    list = list.filter((item) => item.name.toLowerCase().includes(kw) || item.image.toLowerCase().includes(kw))
  }
  if (statusFilter.value === 'abnormal') {
    list = list.filter((item) => ['exited', 'dead', 'restarting', 'removing'].includes(item.status))
  } else if (statusFilter.value !== 'all') {
    list = list.filter((item) => item.status === statusFilter.value)
  }
  return sortContainersByRisk(list)
})

const pagedContainers = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return filteredContainers.value.slice(start, start + pageSize.value)
})

const overviewCards = computed(() => {
  const m = host.value.metrics || {}
  const diskPercent = m.disk_usage?.percent ?? null
  return [
    { label: 'CPU 使用率', value: m.cpu_percent != null ? m.cpu_percent.toFixed(1) + '%' : '-', percent: m.cpu_percent ?? null, valueClass: metricValueClass(m.cpu_percent), foot: `${m.cpu_count ?? '-'} 核` },
    { label: '内存使用率', value: m.memory_percent != null ? m.memory_percent.toFixed(1) + '%' : '-', percent: m.memory_percent ?? null, valueClass: metricValueClass(m.memory_percent), foot: m.memory_total ? formatBytes(m.memory_total) : '内存总量未知' },
    { label: '磁盘使用率', value: diskPercent != null ? diskPercent.toFixed(1) + '%' : '-', percent: diskPercent, valueClass: metricValueClass(diskPercent), foot: '主要数据分区' },
    { label: '容器总数', value: containerSummary.value.total, percent: null, valueClass: '', foot: `运行中 ${containerSummary.value.running}` },
    { label: '异常容器', value: containerSummary.value.abnormal, percent: null, valueClass: containerSummary.value.abnormal ? 'text-danger' : '', foot: `${containerSummary.value.exited} exited` },
    { label: '重启风险', value: containerSummary.value.restartRisk, percent: null, valueClass: containerSummary.value.restartRisk ? 'text-warning' : '', foot: '重启次数 > 3' },
  ]
})

const healthItems = computed(() => {
  const m = host.value.metrics || {}
  const diskPercent = m.disk_usage?.percent ?? 0
  return [
    { label: 'CPU', value: m.cpu_percent != null ? m.cpu_percent.toFixed(1) + '%' : '-', percent: Math.min(m.cpu_percent ?? 0, 100), barClass: healthBarClass(m.cpu_percent ?? 0) },
    { label: '内存', value: m.memory_percent != null ? m.memory_percent.toFixed(1) + '%' : '-', percent: Math.min(m.memory_percent ?? 0, 100), barClass: healthBarClass(m.memory_percent ?? 0) },
    { label: '磁盘', value: diskPercent ? diskPercent.toFixed(1) + '%' : '-', percent: Math.min(diskPercent, 100), barClass: healthBarClass(diskPercent) },
  ]
})

const healthTagType = computed(() => containerSummary.value.abnormal > 0 || healthItems.value.some((item) => item.percent > THRESHOLD_WARN) ? 'warning' : 'success')
const healthLabel = computed(() => healthTagType.value === 'warning' ? '关注' : '正常')
const actionSuggestion = computed(() => {
  if (containerSummary.value.abnormal > 0) return '优先查看异常容器日志，再执行重启或停止。'
  if (syncState.value !== 'fresh') return '先立即刷新，确认数据新鲜度。'
  return '主机状态平稳，保持自动同步即可。'
})

watch(keyword, () => { page.value = 1 })
watch(statusFilter, () => { page.value = 1 })

function progressColor(percent: number): string {
  if (percent > THRESHOLD_DANGER) return 'var(--danger-color)'
  if (percent > THRESHOLD_WARN) return 'var(--warning-color)'
  return 'var(--primary-color)'
}

function metricValueClass(percent?: number | null) {
  if (percent == null) return ''
  if (percent > THRESHOLD_DANGER) return 'text-danger'
  if (percent > THRESHOLD_WARN) return 'text-warning'
  return ''
}

function healthBarClass(percent: number) {
  if (percent > THRESHOLD_DANGER) return 'danger'
  if (percent > THRESHOLD_WARN) return 'warning'
  return ''
}

function endpointHost(endpoint = '') {
  const value = endpoint.replace(/^https?:\/\//, '')
  return value.split(':')[0]
}

function formatRelativeTime(ts?: string | null) {
  const seconds = secondsSince(ts)
  if (seconds == null) return '从未同步'
  if (seconds < 60) return `${seconds} 秒前`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes} 分钟前`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours} 小时前`
  return `${Math.floor(hours / 24)} 天前`
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
          mappings.push(`${b.HostIp || '0.0.0.0'}:${b.HostPort}->${containerPort}`)
        }
      } else {
        mappings.push(containerPort)
      }
    }
    return mappings.join(', ') || '-'
  } catch {
    return portsJson
  }
}

function containerStatusType(s: string) {
  if (s === 'running') return 'success'
  if (s === 'exited' || s === 'dead') return 'danger'
  if (s === 'paused' || s === 'restarting') return 'warning'
  return 'info'
}

function containerDotClass(s: string) {
  if (s === 'running') return 'dot-success'
  if (s === 'exited' || s === 'dead') return 'dot-danger'
  if (s === 'paused' || s === 'restarting') return 'dot-warning'
  return 'dot-info'
}

function containerStatusLabel(s: string) {
  if (s === 'running') return '运行中'
  if (s === 'exited') return '已停止'
  if (s === 'paused') return '暂停'
  if (s === 'restarting') return '重启中'
  return s
}

async function openContainerLogs(row: any) {
  selectedContainer.value = row
  containerLogs.value = ''
  logsDrawerVisible.value = true
  await fetchSelectedContainerLogs()
}

async function fetchSelectedContainerLogs() {
  if (!selectedContainer.value) return
  logsLoading.value = true
  try {
    const res: any = await getDockerContainerLogs(hostName.value, selectedContainer.value.container_id, { tail_lines: logTailLines.value })
    containerLogs.value = res.data?.logs || ''
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '加载日志失败')
  } finally {
    logsLoading.value = false
  }
}

function copyLogs() {
  if (!containerLogs.value) return
  navigator.clipboard.writeText(containerLogs.value).then(
    () => ElMessage.success('已复制到剪贴板'),
    () => ElMessage.error('复制失败'),
  )
}

function downloadLogs() {
  if (!containerLogs.value || !selectedContainer.value) return
  const blob = new Blob([containerLogs.value], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = `${selectedContainer.value.name || selectedContainer.value.container_id}.log`
  anchor.click()
  URL.revokeObjectURL(url)
}

async function handleContainerAction(row: any, action: 'start' | 'stop' | 'restart' | 'delete') {
  const labels = { start: '启动', stop: '停止', restart: '重启', delete: '删除' }

  if (action === 'delete') {
    try {
      await ElMessageBox.confirm(`确定删除容器「${row.name}」？此操作不可恢复。`, '删除确认', { type: 'warning' })
    } catch { return }
  }

  try {
    const apiMap = { start: startDockerContainer, stop: stopDockerContainer, restart: restartDockerContainer, delete: deleteDockerContainer }
    await apiMap[action](hostName.value, row.container_id)
    ElMessage.success(`${labels[action]}成功`)
    fetchContainers()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || `${labels[action]}失败`)
  }
}

async function fetchHost() {
  if (!hostName.value) return false
  try {
    const res: any = await getDockerHost(hostName.value)
    host.value = res.data
    return true
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '主机不存在')
    return false
  }
}

async function fetchContainers() {
  if (!hostName.value) return
  loading.value = true
  try {
    const res: any = await getHostContainers(hostName.value)
    containers.value = res.data
  } finally {
    loading.value = false
  }
}

async function loadHostDetail() {
  const routeRef = hostName.value
  if (!routeRef || activeLoadRef === routeRef) return
  activeLoadRef = routeRef
  if (host.value.name && host.value.name !== routeRef) {
    host.value = {}
    containers.value = []
  }
  try {
    if (await fetchHost()) await fetchContainers()
  } finally {
    if (activeLoadRef === routeRef) activeLoadRef = ''
  }
}

async function handleRefresh() {
  refreshing.value = true
  try {
    await refreshDockerHost(hostName.value)
    await fetchHost()
    await fetchContainers()
    ElMessage.success('刷新成功')
  } catch {
    ElMessage.error('Agent 连接失败')
  } finally {
    refreshing.value = false
  }
}

async function handleDelete() {
  await ElMessageBox.confirm(`确定删除主机「${host.value.name}」？所有容器数据将被清除。`, '删除确认', { type: 'warning' })
  await deleteDockerHost(hostName.value)
  ElMessage.success('删除成功')
  router.push('/assets/docker')
}

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

let activeLoadRef = ''
watch(hostName, loadHostDetail)

onActivated(loadHostDetail)

onDeactivated(stopAutoRefresh)
</script>

<style scoped>
.detail-header {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  padding: 14px;
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  background: var(--surface-color);
  margin-bottom: 12px;
}
.detail-title-row {
  display: flex;
  align-items: center;
  gap: 9px;
  flex-wrap: wrap;
}
.detail-fields {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin-top: 12px;
}
.field-label {
  color: var(--text-muted);
  font-size: 12px;
  margin-bottom: 2px;
}
.field-value {
  color: var(--text-primary);
  font-weight: 650;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.header-actions {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}
.sync-notice {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 11px;
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  margin-bottom: 12px;
  font-size: 13px;
}
.notice-info {
  background: var(--primary-bg);
  border-color: color-mix(in srgb, var(--primary-color), white 72%);
  color: var(--primary-color);
}
.notice-warning {
  background: color-mix(in srgb, var(--warning-color), white 91%);
  border-color: color-mix(in srgb, var(--warning-color), white 65%);
  color: #7a5100;
}
.notice-danger {
  background: color-mix(in srgb, var(--danger-color), white 93%);
  border-color: color-mix(in srgb, var(--danger-color), white 68%);
  color: #9f2227;
}
.summary-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 12px;
}
.metric-card {
  min-width: 0;
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: 12px 14px;
  overflow: hidden;
}
.metric-label {
  color: var(--text-secondary);
  font-size: 12px;
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.metric-value {
  color: var(--text-primary);
  font-size: 15px;
  font-weight: 750;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.metric-foot {
  margin-top: 5px;
  color: var(--text-muted);
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.stat-progress {
  margin-top: 6px;
}
.detail-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 280px;
  gap: 12px;
}
.panel {
  min-width: 0;
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  overflow: hidden;
}
.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px;
  border-bottom: 1px solid var(--border-color);
}
.panel-head.compact {
  align-items: center;
}
.panel-title {
  margin: 0;
  font-size: 14px;
  font-weight: 700;
}
.panel-subtitle {
  margin: 3px 0 0;
  color: var(--text-secondary);
  font-size: 12px;
}
.container-tools {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}
.search-input {
  width: 240px;
}
.status-tabs {
  display: flex;
  gap: 4px;
  padding: 10px 12px 0;
}
.status-tab {
  height: 32px;
  padding: 0 10px;
  border: 0;
  border-radius: 7px;
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
}
.status-tab.active {
  background: var(--primary-bg);
  color: var(--primary-color);
  font-weight: 650;
}
.container-name {
  display: grid;
  gap: 2px;
  min-width: 0;
}
.container-name strong,
.container-name span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.container-name span {
  color: var(--text-muted);
}
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
.action-cell {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 4px;
}
.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  padding: 11px 12px;
  border-top: 1px solid var(--border-color);
}
.health-list {
  display: grid;
  gap: 10px;
  padding: 12px;
}
.health-item {
  display: grid;
  gap: 6px;
}
.health-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: var(--text-secondary);
  font-size: 12px;
}
.health-row strong {
  color: var(--text-primary);
}
.health-bar {
  height: 6px;
  overflow: hidden;
  border-radius: 999px;
  background: #eef0f4;
}
.health-bar span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--primary-color);
}
.health-bar span.warning {
  background: var(--warning-color);
}
.health-bar span.danger {
  background: var(--danger-color);
}
.event-list {
  padding: 0 12px 12px;
}
.event-item {
  display: grid;
  gap: 3px;
  padding: 10px 0;
  border-top: 1px solid var(--border-color);
}
.event-item strong {
  font-size: 13px;
}
.event-item span {
  color: var(--text-muted);
  font-size: 12px;
}
.status-dot,
.tag-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--text-muted);
  flex: none;
}
.tag-dot {
  display: inline-block;
  margin-right: 5px;
}
.dot-success { background: var(--success-color); }
.dot-warning { background: var(--warning-color); }
.dot-danger { background: var(--danger-color); }
.dot-info { background: var(--primary-color); }
.text-warning { color: var(--warning-color); }
.text-danger { color: var(--danger-color); }
.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
}
.drawer-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  padding: 16px 18px 12px;
  border-bottom: 1px solid var(--border-color);
}
.drawer-head-copy {
  min-width: 0;
}
.drawer-head-copy h3 {
  margin: 0;
  font-size: 15px;
  word-break: break-all;
}
.drawer-sub {
  margin-top: 4px;
  color: var(--text-muted);
  font-size: 12px;
}
.drawer-actions {
  display: flex;
  gap: 6px;
  flex: none;
}
.drawer-body {
  padding: 14px 18px;
}
.log-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
  color: var(--text-secondary);
  font-size: 13px;
}
.log-tail-select {
  width: 110px;
}
.log-box {
  min-height: 320px;
  max-height: 560px;
  margin: 0;
  padding: 14px;
  overflow: auto;
  color: #d1d5db;
  background: #111827;
  border-radius: var(--border-radius);
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  outline: none;
}
.log-box:focus-visible {
  box-shadow: 0 0 0 2px var(--primary-color);
}
@media (max-width: 1200px) {
  .summary-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
  .detail-grid {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 768px) {
  .detail-header,
  .panel-head {
    grid-template-columns: 1fr;
    align-items: stretch;
  }
  .detail-fields {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .header-actions,
  .container-tools,
  .search-input {
    width: 100%;
  }
  .header-actions,
  .container-tools {
    flex-wrap: wrap;
  }
}
</style>
