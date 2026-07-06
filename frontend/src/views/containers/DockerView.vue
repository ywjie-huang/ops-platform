<template>
  <div>
    <div class="page-header docker-header">
      <div>
        <h2 class="page-title">Docker 监控</h2>
        <p class="page-subtitle">按风险优先展示 Docker 主机，数据来自平台最近一次 Agent 同步。</p>
      </div>
      <div class="header-actions">
        <el-tooltip :content="autoRefresh ? '关闭自动刷新' : '开启后每 15s 自动刷新数据'" placement="bottom">
          <el-button :type="autoRefresh ? 'primary' : 'default'" size="small" @click="toggleAutoRefresh">
            <el-icon><Refresh /></el-icon>
            {{ autoRefresh ? '自动刷新中' : '自动刷新' }}
          </el-button>
        </el-tooltip>
        <el-button size="small" :loading="loading" aria-label="刷新 Docker 主机列表" @click="refreshAll">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
        <el-button type="primary" size="small" @click="handleCreate">注册主机</el-button>
      </div>
    </div>

    <div class="summary-grid" role="region" aria-label="Docker 总览">
      <div v-for="item in overviewCards" :key="item.label" class="metric-card">
        <div class="metric-label">
          <span>{{ item.label }}</span>
          <span class="status-dot" :class="item.dotClass" aria-hidden="true"></span>
        </div>
        <div class="metric-value" :class="item.valueClass">{{ item.value }}</div>
        <div class="metric-foot">{{ item.foot }}</div>
      </div>
    </div>

    <div class="docker-toolbar">
      <div class="toolbar-left">
        <el-input
          v-model="hostKeyword"
          placeholder="搜索主机名、Agent 地址、主机 IP"
          clearable
          class="search-input"
          aria-label="搜索 Docker 主机"
        />
        <el-select v-model="statusFilter" class="status-select" aria-label="主机状态筛选">
          <el-option label="全部状态" value="all" />
          <el-option label="离线" value="offline" />
          <el-option label="同步过期" value="stale" />
          <el-option label="在线" value="online" />
          <el-option label="有异常容器" value="abnormal" />
        </el-select>
        <el-select v-model="sortMode" class="sort-select" aria-label="主机排序">
          <el-option label="风险优先" value="risk" />
          <el-option label="最近同步" value="heartbeat" />
          <el-option label="主机名" value="name" />
          <el-option label="容器数量" value="containers" />
        </el-select>
      </div>
      <div class="toolbar-right">
        <span class="refresh-meta">最近刷新：{{ lastRefreshText }}</span>
      </div>
    </div>

    <div class="table-card">
      <div class="table-meta">
        <span>已筛选出 {{ filteredHosts.length }} 台主机，默认展示风险最高的主机。</span>
        <span>共 {{ hosts.length }} 台主机</span>
      </div>
      <div class="table-wrapper">
        <el-table :data="pagedHosts" v-loading="loading" stripe class="host-table" @row-click="goDetail">
          <el-table-column label="主机" min-width="190" fixed>
            <template #default="{ row }">
              <div class="host-cell">
                <span class="risk-rail" :class="riskRailClass(row)" aria-hidden="true"></span>
                <div class="host-copy">
                  <strong>{{ row.name }}</strong>
                  <span>{{ row.description || row.host_os || '未填写说明' }}</span>
                </div>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="118">
            <template #default="{ row }">
              <el-tag :type="hostTagType(row)" size="small">
                <span class="tag-dot" :class="hostDotClass(row)" aria-hidden="true"></span>
                {{ hostStatusLabel(row) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="endpoint" label="Agent 地址" min-width="170" show-overflow-tooltip>
            <template #default="{ row }">
              <span class="mono">{{ row.endpoint || '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="host_ip" label="主机 IP" min-width="130" show-overflow-tooltip>
            <template #default="{ row }">
              <span class="mono">{{ row.host_ip || endpointHost(row.endpoint) || '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="容器摘要" min-width="210">
            <template #default="{ row }">
              <div class="container-summary">
                <span><strong>{{ row.containerStats.total }}</strong> 总</span>
                <span class="text-success"><strong>{{ row.containerStats.running }}</strong> 运行</span>
                <span :class="{ 'text-danger': row.containerStats.abnormal > 0 }">
                  <strong>{{ row.containerStats.abnormal }}</strong> 异常
                </span>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="docker_version" label="Docker" width="110" />
          <el-table-column label="最后同步" min-width="170">
            <template #default="{ row }">
              <div class="sync-cell">
                <span :class="syncTextClass(row)">{{ syncTimeText(row) }}</span>
                <small>{{ syncHint(row) }}</small>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="190" fixed="right" align="right">
            <template #default="{ row }">
              <div class="row-actions">
                <el-button link type="primary" size="small" :loading="refreshingHostId === row.id" @click.stop="handleRefresh(row)">刷新</el-button>
                <el-button link type="primary" size="small" @click.stop="goDetail(row)">详情</el-button>
                <el-dropdown trigger="click" @command="(command: string) => handleRowCommand(command, row)">
                  <el-button link type="primary" size="small" @click.stop>更多</el-button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item command="edit">编辑</el-dropdown-item>
                      <el-dropdown-item command="delete" divided>删除</el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :page-sizes="[20, 50, 100]"
          :total="filteredHosts.length"
          layout="total, sizes, prev, pager, next"
          small
        />
      </div>
    </div>

    <el-dialog v-model="hostDialogVisible" :title="editingHostId ? '编辑主机' : '注册 Docker 主机'" width="min(600px, 90vw)" destroy-on-close>
      <template v-if="!editingHostId">
        <el-steps :active="setupStep" finish-status="success" align-center class="setup-steps">
          <el-step title="部署 Agent" />
          <el-step title="注册主机" />
        </el-steps>

        <div v-if="setupStep === 0">
          <p class="setup-hint">在目标 Docker 主机上执行以下命令安装或升级 Agent：</p>
          <div class="setup-command-box">
            <pre class="setup-command">{{ agentInstallCmd }}</pre>
            <el-button type="primary" size="small" class="copy-btn" @click="copyAgentCmd">复制命令</el-button>
          </div>
          <el-button type="primary" class="next-btn" @click="setupStep = 1">下一步，填写信息</el-button>
        </div>

        <div v-if="setupStep === 1">
          <el-form ref="hostFormRef" :model="hostForm" :rules="hostRules" label-width="100px">
            <el-form-item label="主机名称" prop="name">
              <el-input v-model="hostForm.name" placeholder="例：docker-prod-01" />
            </el-form-item>
            <el-form-item label="Agent 地址" prop="endpoint">
              <el-input v-model="hostForm.endpoint" placeholder="例：192.168.1.200:9001" />
              <div class="endpoint-tip">填写目标主机 IP 和 Agent 端口（默认 9001）。</div>
            </el-form-item>
            <el-form-item label="说明">
              <el-input v-model="hostForm.description" placeholder="备注信息" />
            </el-form-item>
          </el-form>
        </div>
      </template>

      <el-form v-else ref="hostFormRef" :model="hostForm" :rules="hostRules" label-width="100px">
        <el-form-item label="主机名称" prop="name">
          <el-input v-model="hostForm.name" placeholder="例：docker-prod-01" />
        </el-form-item>
        <el-form-item label="Agent 地址" prop="endpoint">
          <el-input v-model="hostForm.endpoint" placeholder="例：192.168.1.200:9001" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="hostForm.description" placeholder="备注信息" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="hostDialogVisible = false">取消</el-button>
        <template v-if="!editingHostId">
          <el-button v-if="setupStep === 1" @click="setupStep = 0">上一步</el-button>
          <el-button v-if="setupStep === 1" type="primary" :loading="saving" @click="handleHostSubmit">注册</el-button>
        </template>
        <el-button v-else type="primary" :loading="saving" @click="handleHostSubmit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, type FormInstance } from 'element-plus'
import {
  getDockerOverview,
  getDockerHosts,
  getDockerContainers,
  createDockerHost,
  updateDockerHost,
  deleteDockerHost,
  refreshDockerHost,
} from '@/api/containers'
import { getHostSyncState, secondsSince, sortHostsByRisk, summarizeContainers } from '@/utils/dockerMonitor'

const router = useRouter()

const loading = ref(false)
const saving = ref(false)
const refreshingHostId = ref<number | null>(null)
const hosts = ref<any[]>([])
const containers = ref<any[]>([])
const overview = ref<any>({})
const hostKeyword = ref('')
const statusFilter = ref('all')
const sortMode = ref('risk')
const page = ref(1)
const pageSize = ref(20)
const autoRefresh = ref(false)
const lastRefreshAt = ref<Date | null>(null)

const hostDialogVisible = ref(false)
const editingHostId = ref<number | null>(null)
const setupStep = ref(0)
const hostFormRef = ref<FormInstance>()
const hostForm = reactive({ name: '', endpoint: '', description: '' })
const hostRules = {
  name: [{ required: true, message: '请输入主机名称', trigger: 'blur' }],
  endpoint: [{ required: true, message: '请输入 Agent 地址', trigger: 'blur' }],
}

const agentInstallCmd = `docker rm -f ops-agent >/dev/null 2>&1 || true
docker pull hub1.lczy.com/public/ops-agent:latest
docker run -d \\
  -p 9001:9001 \\
  --name ops-agent \\
  --restart=always \\
  -v /var/run/docker.sock:/var/run/docker.sock \\
  hub1.lczy.com/public/ops-agent:latest`

let refreshTimer: ReturnType<typeof setInterval> | null = null

const containerStatsByHost = computed(() => {
  const grouped = new Map<number, any[]>()
  for (const item of containers.value) {
    if (!grouped.has(item.host_id)) grouped.set(item.host_id, [])
    grouped.get(item.host_id)?.push(item)
  }
  return grouped
})

const enrichedHosts = computed(() => hosts.value.map((host) => ({
  ...host,
  containerStats: summarizeContainers(containerStatsByHost.value.get(host.id) || []),
})))

const filteredHosts = computed(() => {
  const keyword = hostKeyword.value.trim().toLowerCase()
  let list = enrichedHosts.value
  if (keyword) {
    list = list.filter((host) => [
      host.name,
      host.endpoint,
      host.host_ip,
      host.description,
    ].some((value) => String(value || '').toLowerCase().includes(keyword)))
  }
  if (statusFilter.value !== 'all') {
    list = list.filter((host) => {
      const syncState = getHostSyncState(host)
      if (statusFilter.value === 'offline') return syncState === 'offline' || syncState === 'never'
      if (statusFilter.value === 'stale') return syncState === 'stale'
      if (statusFilter.value === 'online') return syncState === 'fresh'
      if (statusFilter.value === 'abnormal') return host.containerStats.abnormal > 0
      return true
    })
  }
  if (sortMode.value === 'risk') return sortHostsByRisk(list)
  if (sortMode.value === 'heartbeat') {
    return [...list].sort((a, b) => new Date(b.last_heartbeat || 0).getTime() - new Date(a.last_heartbeat || 0).getTime())
  }
  if (sortMode.value === 'containers') {
    return [...list].sort((a, b) => b.containerStats.total - a.containerStats.total)
  }
  return [...list].sort((a, b) => a.name.localeCompare(b.name, 'zh-CN'))
})

const pagedHosts = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return filteredHosts.value.slice(start, start + pageSize.value)
})

const aggregateStats = computed(() => {
  const stale = enrichedHosts.value.filter((host) => getHostSyncState(host) === 'stale').length
  const offline = enrichedHosts.value.filter((host) => ['offline', 'never'].includes(getHostSyncState(host))).length
  const abnormal = containers.value.filter((item) => ['exited', 'dead', 'restarting', 'removing'].includes(item.status)).length
  return { stale, offline, abnormal }
})

const overviewCards = computed(() => [
  { label: '主机总数', value: overview.value.host_total ?? hosts.value.length, foot: '当前接入 Docker Agent', dotClass: 'dot-info', valueClass: '' },
  { label: '在线主机', value: overview.value.host_online ?? hosts.value.filter((host) => host.online).length, foot: '最近 60 秒内同步正常', dotClass: 'dot-success', valueClass: 'text-success' },
  { label: '离线主机', value: aggregateStats.value.offline, foot: '优先排在列表顶部', dotClass: 'dot-danger', valueClass: aggregateStats.value.offline ? 'text-danger' : '' },
  { label: '同步过期', value: aggregateStats.value.stale, foot: '超过 60 秒未成功同步', dotClass: 'dot-warning', valueClass: aggregateStats.value.stale ? 'text-warning' : '' },
  { label: '容器总数', value: overview.value.container_total ?? containers.value.length, foot: `运行中 ${overview.value.container_running ?? containers.value.filter((item) => item.status === 'running').length}`, dotClass: '', valueClass: '' },
  { label: '异常容器', value: aggregateStats.value.abnormal, foot: 'exited / restarting / dead', dotClass: 'dot-danger', valueClass: aggregateStats.value.abnormal ? 'text-danger' : '' },
])

const lastRefreshText = computed(() => lastRefreshAt.value ? lastRefreshAt.value.toLocaleTimeString('zh-CN', { hour12: false }) : '尚未刷新')

watch([hostKeyword, statusFilter, sortMode], () => { page.value = 1 })

function copyAgentCmd() {
  const cmd = agentInstallCmd
  navigator.clipboard.writeText(cmd).then(() => ElMessage.success('已复制命令'))
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

function syncTimeText(row: any) {
  return formatRelativeTime(row.last_heartbeat)
}

function syncHint(row: any) {
  const state = getHostSyncState(row)
  if (state === 'fresh') return '自动同步'
  if (state === 'stale') return '数据可能过期'
  if (state === 'offline') return row.status_message || 'Agent 连接失败'
  return '等待首次同步'
}

function hostStatusLabel(row: any) {
  const state = getHostSyncState(row)
  if (state === 'fresh') return '在线'
  if (state === 'stale') return '同步过期'
  if (state === 'offline') return '离线'
  return '未同步'
}

function hostTagType(row: any) {
  const state = getHostSyncState(row)
  if (state === 'fresh') return row.containerStats.abnormal > 0 ? 'warning' : 'success'
  if (state === 'stale') return 'warning'
  return 'danger'
}

function hostDotClass(row: any) {
  const state = getHostSyncState(row)
  if (state === 'fresh') return row.containerStats.abnormal > 0 ? 'dot-warning' : 'dot-success'
  if (state === 'stale') return 'dot-warning'
  return 'dot-danger'
}

function riskRailClass(row: any) {
  const state = getHostSyncState(row)
  if (state === 'offline' || state === 'never') return 'risk-danger'
  if (state === 'stale' || row.containerStats.abnormal > 0) return 'risk-warning'
  return 'risk-success'
}

function syncTextClass(row: any) {
  const state = getHostSyncState(row)
  if (state === 'stale') return 'text-warning'
  if (state === 'offline' || state === 'never') return 'text-danger'
  return ''
}

async function fetchOverview() {
  const res: any = await getDockerOverview()
  overview.value = res.data
}

async function fetchHosts() {
  const res: any = await getDockerHosts({ keyword: '' })
  hosts.value = res.data
}

async function fetchContainers() {
  const res: any = await getDockerContainers()
  containers.value = res.data || []
}

async function refreshAll() {
  loading.value = true
  try {
    await Promise.all([fetchOverview(), fetchHosts(), fetchContainers()])
    lastRefreshAt.value = new Date()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '加载失败')
  } finally {
    loading.value = false
  }
}

function handleCreate() {
  editingHostId.value = null
  setupStep.value = 0
  Object.assign(hostForm, { name: '', endpoint: '', description: '' })
  hostDialogVisible.value = true
}

function handleEdit(row: any) {
  editingHostId.value = row.id
  Object.assign(hostForm, { name: row.name, endpoint: row.endpoint, description: row.description || '' })
  hostDialogVisible.value = true
}

async function handleHostSubmit() {
  const valid = await hostFormRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    if (editingHostId.value) {
      await updateDockerHost(editingHostId.value, hostForm)
      ElMessage.success('更新成功')
    } else {
      const res: any = await createDockerHost(hostForm)
      ElMessage.success(res.msg || '注册成功')
    }
    hostDialogVisible.value = false
    refreshAll()
  } finally {
    saving.value = false
  }
}

async function handleDelete(row: any) {
  await ElMessageBox.confirm(`确定删除主机「${row.name}」？所有容器数据将被清除。`, '删除确认', { type: 'warning' })
  await deleteDockerHost(row.id)
  ElMessage.success('删除成功')
  refreshAll()
}

async function handleRefresh(row: any) {
  refreshingHostId.value = row.id
  try {
    await refreshDockerHost(row.id)
    ElMessage.success('刷新成功')
    await refreshAll()
  } catch {
    ElMessage.error('Agent 连接失败')
  } finally {
    refreshingHostId.value = null
  }
}

function handleRowCommand(command: string, row: any) {
  if (command === 'edit') handleEdit(row)
  if (command === 'delete') handleDelete(row)
}

function goDetail(row: any) {
  router.push(`/assets/docker/${row.id}`)
}

function toggleAutoRefresh() {
  autoRefresh.value = !autoRefresh.value
  if (autoRefresh.value) {
    refreshTimer = setInterval(refreshAll, 15000)
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

onMounted(refreshAll)
onUnmounted(stopAutoRefresh)
</script>

<style scoped>
.docker-header {
  align-items: flex-start;
}
.page-subtitle {
  margin: 5px 0 0;
  color: var(--text-secondary);
  font-size: 13px;
}
.header-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  justify-content: flex-end;
}
.summary-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 14px;
}
.metric-card {
  min-width: 0;
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: 12px 14px;
}
.metric-label {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  color: var(--text-secondary);
  font-size: 12px;
}
.metric-value {
  margin-top: 5px;
  color: var(--text-primary);
  font-size: 22px;
  font-weight: 750;
}
.metric-foot {
  margin-top: 4px;
  color: var(--text-muted);
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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
.text-success { color: var(--success-color); }
.text-warning { color: var(--warning-color); }
.text-danger { color: var(--danger-color); }
.docker-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px;
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  margin-bottom: 12px;
}
.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.search-input {
  width: 280px;
}
.status-select,
.sort-select {
  width: 130px;
}
.refresh-meta {
  color: var(--text-secondary);
  font-size: 12px;
}
.table-card {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  overflow: hidden;
}
.table-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  color: var(--text-secondary);
  font-size: 12px;
  border-bottom: 1px solid var(--border-color);
}
.host-table {
  cursor: pointer;
}
.host-cell {
  display: flex;
  align-items: center;
  gap: 9px;
  min-width: 0;
}
.risk-rail {
  width: 3px;
  height: 28px;
  border-radius: 99px;
  background: var(--border-color);
  flex: none;
}
.risk-success { background: var(--success-color); }
.risk-warning { background: var(--warning-color); }
.risk-danger { background: var(--danger-color); }
.host-copy {
  min-width: 0;
  display: grid;
  gap: 2px;
}
.host-copy strong {
  overflow: hidden;
  color: var(--text-primary);
  text-overflow: ellipsis;
  white-space: nowrap;
}
.host-copy span {
  overflow: hidden;
  color: var(--text-muted);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
}
.container-summary {
  display: flex;
  align-items: center;
  gap: 9px;
  color: var(--text-secondary);
  font-size: 12px;
}
.container-summary strong {
  color: var(--text-primary);
  font-size: 13px;
}
.sync-cell {
  display: grid;
  gap: 2px;
}
.sync-cell span {
  font-weight: 650;
}
.sync-cell small {
  color: var(--text-muted);
}
.row-actions {
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
.setup-steps {
  margin-bottom: 20px;
}
.setup-hint {
  margin: 0 0 12px;
  color: var(--text-secondary);
  font-size: 14px;
}
.copy-btn {
  margin-top: 8px;
}
.next-btn {
  margin-top: 16px;
}
.endpoint-tip {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 4px;
}
.setup-command-box {
  background: var(--text-primary);
  border-radius: var(--border-radius);
  padding: 16px;
}
.setup-command {
  color: var(--bg-color);
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 13px;
  line-height: 1.6;
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
}
@media (max-width: 1200px) {
  .summary-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
@media (max-width: 768px) {
  .docker-header,
  .docker-toolbar,
  .table-meta {
    align-items: stretch;
    flex-direction: column;
  }
  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .toolbar-left,
  .toolbar-right,
  .search-input,
  .status-select,
  .sort-select {
    width: 100%;
  }
}
</style>
