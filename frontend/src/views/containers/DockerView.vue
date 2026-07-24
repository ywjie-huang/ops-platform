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

    <el-dialog v-model="hostDialogVisible" :title="editingHostName ? '编辑主机' : '注册 Docker 主机'" width="min(720px, 90vw)" destroy-on-close>
      <template v-if="!editingHostName">
        <div class="access-mode">
          <div class="access-mode-label">接入方式</div>
          <el-radio-group v-model="accessMode" aria-label="选择 Docker Agent 接入方式">
            <el-radio-button value="deploy">部署新 Agent</el-radio-button>
            <el-radio-button value="existing">使用已有 Agent</el-radio-button>
          </el-radio-group>
          <p class="access-mode-tip">
            {{ accessMode === 'deploy' ? '按步骤构建镜像、部署 Agent，再注册到平台。' : 'Agent 已在目标主机运行时，直接填写平台可访问的地址。' }}
          </p>
        </div>

        <el-steps v-if="accessMode === 'deploy'" :active="setupStep" finish-status="success" align-center class="setup-steps">
          <el-step title="发布镜像" />
          <el-step title="部署 Agent" />
          <el-step title="注册主机" />
        </el-steps>

        <section v-if="accessMode === 'deploy' && setupStep === 0" class="setup-panel" aria-labelledby="publish-agent-title">
          <div class="setup-heading">
            <h3 id="publish-agent-title">从源码构建并发布 Agent 镜像</h3>
            <p>在获取本仓库源码的开发机上进入 <code>agent</code> 目录，将镜像推送到你有权限访问的仓库。</p>
          </div>
          <el-form label-position="top">
            <el-form-item label="镜像地址" required>
              <el-input
                v-model="agentImage"
                placeholder="例：registry.example.com/ops/ops-agent:v1.0.0"
                aria-label="Agent 镜像地址"
              />
              <div class="setup-field-tip">请使用你自己的镜像仓库地址；目标 Docker 主机需要具备拉取权限。</div>
            </el-form-item>
          </el-form>
          <div v-if="agentPublishCmd" class="setup-command-box">
            <pre class="setup-command" role="region" aria-label="Agent 构建与推送命令">{{ agentPublishCmd }}</pre>
            <el-button type="primary" size="small" class="copy-btn" @click="copySetupCommand(agentPublishCmd, '构建与推送命令已复制')">复制命令</el-button>
          </div>
          <div v-else class="setup-command-empty">填写镜像地址后生成构建、登录和推送命令。</div>
        </section>

        <section v-if="accessMode === 'deploy' && setupStep === 1" class="setup-panel" aria-labelledby="deploy-agent-title">
          <div class="setup-heading">
            <h3 id="deploy-agent-title">在目标主机部署 Agent</h3>
            <p>填写管理平台能够访问的目标主机管理网 IP。端口暴露范围和防火墙规则请在服务器侧限制。</p>
          </div>
          <el-form label-position="top">
            <el-form-item label="管理网 IP" required>
              <el-input
                v-model="agentManagementIp"
                placeholder="例：10.10.20.15"
                aria-label="Docker 主机管理网 IP"
              />
              <div class="setup-field-tip">生成的命令会将 Agent 绑定到该地址的 9001 端口，不修改 Agent 业务逻辑。</div>
            </el-form-item>
          </el-form>
          <div v-if="agentRunCmd" class="setup-command-box">
            <pre class="setup-command" role="region" aria-label="Agent 拉取与运行命令">{{ agentRunCmd }}</pre>
            <el-button type="primary" size="small" class="copy-btn" @click="copySetupCommand(agentRunCmd, '拉取与运行命令已复制')">复制命令</el-button>
          </div>
          <div v-else class="setup-command-empty">填写镜像地址和管理网 IP 后生成拉取与运行命令。</div>
        </section>

        <section v-if="accessMode === 'existing' || setupStep === 2" class="setup-panel" aria-labelledby="register-agent-title">
          <div class="setup-heading">
            <h3 id="register-agent-title">{{ accessMode === 'existing' ? '注册已有 Agent' : '将 Agent 注册到平台' }}</h3>
            <p>平台会通过 Agent 地址拉取 Docker 数据并执行容器管理操作，注册后将立即尝试连接。</p>
          </div>
          <el-form ref="hostFormRef" :model="hostForm" :rules="hostRules" label-width="100px">
            <el-form-item label="主机名称" prop="name">
              <el-input v-model="hostForm.name" placeholder="例：docker-prod-01" />
            </el-form-item>
            <el-form-item label="Agent 地址" prop="endpoint">
              <el-input v-model="hostForm.endpoint" placeholder="例：10.10.20.15:9001" />
              <div class="endpoint-tip">
                {{ accessMode === 'existing' ? '填写管理平台可以访问的 Agent 地址，支持 IP:端口或完整 URL。' : '默认根据上一步的管理网 IP 生成，也可按实际网络配置修改。' }}
              </div>
            </el-form-item>
            <el-form-item label="说明">
              <el-input v-model="hostForm.description" placeholder="备注信息" />
            </el-form-item>
          </el-form>
        </section>
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
        <template v-if="!editingHostName">
          <el-button v-if="accessMode === 'deploy' && setupStep > 0" @click="setupStep -= 1">上一步</el-button>
          <el-button v-if="accessMode === 'deploy' && setupStep < 2" type="primary" @click="goToNextSetupStep">
            {{ setupStep === 0 ? '下一步，部署 Agent' : '下一步，注册主机' }}
          </el-button>
          <el-button v-else-if="accessMode === 'existing' || setupStep === 2" type="primary" :loading="saving" @click="handleHostSubmit">注册</el-button>
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
import { buildAgentEndpoint, buildAgentPublishCommand, buildAgentRunCommand } from '@/utils/dockerAgentSetup'

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
const editingHostName = ref('')
const accessMode = ref<'deploy' | 'existing'>('deploy')
const setupStep = ref(0)
const agentImage = ref('')
const agentManagementIp = ref('')
const hostFormRef = ref<FormInstance>()
const hostForm = reactive({ name: '', endpoint: '', description: '' })
const hostRules = {
  name: [{ required: true, message: '请输入主机名称', trigger: 'blur' }],
  endpoint: [{ required: true, message: '请输入 Agent 地址', trigger: 'blur' }],
}

const agentPublishCmd = computed(() => buildAgentPublishCommand(agentImage.value))
const agentRunCmd = computed(() => buildAgentRunCommand(agentImage.value, agentManagementIp.value))
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
watch(accessMode, () => {
  setupStep.value = 0
  hostFormRef.value?.clearValidate()
})

async function copySetupCommand(command: string, successMessage: string) {
  if (!command) {
    ElMessage.warning('请先填写生成命令所需的信息')
    return
  }
  try {
    await navigator.clipboard.writeText(command)
    ElMessage.success(successMessage)
  } catch {
    ElMessage.error('复制失败，请手动选择命令复制')
  }
}

function goToNextSetupStep() {
  if (setupStep.value === 0 && !agentPublishCmd.value) {
    ElMessage.warning('请先填写有效的镜像地址')
    return
  }
  if (setupStep.value === 1) {
    if (!agentRunCmd.value) {
      ElMessage.warning('请先填写有效的管理网 IP')
      return
    }
    if (!hostForm.endpoint) {
      hostForm.endpoint = buildAgentEndpoint(agentManagementIp.value)
    }
  }
  setupStep.value += 1
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
  editingHostName.value = ''
  accessMode.value = 'deploy'
  setupStep.value = 0
  agentImage.value = ''
  agentManagementIp.value = ''
  Object.assign(hostForm, { name: '', endpoint: '', description: '' })
  hostDialogVisible.value = true
}

function handleEdit(row: any) {
  editingHostName.value = row.name
  Object.assign(hostForm, { name: row.name, endpoint: row.endpoint, description: row.description || '' })
  hostDialogVisible.value = true
}

async function handleHostSubmit() {
  const valid = await hostFormRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    if (editingHostName.value) {
      await updateDockerHost(editingHostName.value, hostForm)
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
  await deleteDockerHost(row.name)
  ElMessage.success('删除成功')
  refreshAll()
}

async function handleRefresh(row: any) {
  refreshingHostId.value = row.id
  try {
    await refreshDockerHost(row.name)
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
  router.push({ name: 'DockerDetail', params: { name: row.name } })
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
  margin-bottom: 24px;
}
.access-mode {
  display: grid;
  gap: 8px;
  margin-bottom: 22px;
}
.access-mode-label {
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 650;
}
.access-mode :deep(.el-radio-group) {
  width: 100%;
}
.access-mode :deep(.el-radio-button) {
  flex: 1;
}
.access-mode :deep(.el-radio-button__inner) {
  width: 100%;
}
.access-mode-tip {
  margin: 0;
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.5;
}
.setup-panel {
  display: grid;
  gap: 16px;
}
.setup-heading {
  display: grid;
  gap: 6px;
}
.setup-heading h3 {
  margin: 0;
  color: var(--text-primary);
  font-size: 16px;
  font-weight: 650;
}
.setup-heading p {
  max-width: 70ch;
  margin: 0;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.6;
}
.setup-heading code {
  padding: 1px 5px;
  color: var(--text-primary);
  background: var(--bg-color);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}
.setup-field-tip,
.endpoint-tip {
  margin-top: 5px;
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.5;
}
.setup-command-box {
  padding: 14px;
  background: var(--text-primary);
  border: 1px solid var(--text-primary);
  border-radius: var(--border-radius);
}
.setup-command {
  max-height: 260px;
  margin: 0;
  overflow: auto;
  color: var(--bg-color);
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
  line-height: 1.65;
  white-space: pre-wrap;
  word-break: break-word;
}
.setup-command-empty {
  padding: 24px 16px;
  color: var(--text-secondary);
  background: var(--bg-color);
  border: 1px dashed var(--border-color);
  border-radius: var(--border-radius);
  font-size: 13px;
  text-align: center;
}
.copy-btn {
  margin-top: 10px;
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
  .setup-steps :deep(.el-step__title) {
    font-size: 12px;
  }
  .setup-command-box {
    padding: 12px;
  }
}
</style>
