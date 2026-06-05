<template>
  <main>
    <div class="page-header">
      <div class="page-header-left">
        <el-button text @click="$router.push('/assets/containers')" aria-label="返回集群列表"><el-icon><ArrowLeft /></el-icon> 返回</el-button>
        <h2 class="page-title page-header-title">{{ cluster.name || '集群详情' }}</h2>
        <el-tag :type="statusType(cluster.status)" size="small">{{ cluster.status || 'unknown' }}</el-tag>
        <el-tag v-if="cluster.version" type="info" size="small">{{ cluster.version }}</el-tag>
        <el-tag v-if="cluster.status === 'stopped' && cluster.status_message" type="warning" size="small" effect="plain">
          {{ cluster.status_message }}
        </el-tag>
      </div>
      <el-button :loading="refreshing" @click="fetchResources" aria-label="刷新集群数据">
        <el-icon><Refresh /></el-icon> 刷新
      </el-button>
    </div>

    <!-- 集群加载失败 -->
    <div v-if="clusterError" class="error-banner">
      <span class="error-banner-text">集群信息加载失败：{{ clusterError }}</span>
      <el-button size="small" @click="fetchCluster">重试</el-button>
    </div>

    <!-- 异常摘要 -->
    <div v-if="anomalyList.length" class="anomaly-banner" role="alert">
      <div class="anomaly-banner-title">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="anomaly-icon"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
        发现 {{ anomalyList.length }} 项异常
      </div>
      <div class="anomaly-items">
        <el-button
          v-for="item in anomalyList"
          :key="item.tab"
          link
          type="warning"
          size="small"
          @click="activeTab = item.tab"
        >{{ item.text }}</el-button>
      </div>
    </div>

    <!-- 资源加载失败 -->
    <div v-if="resourcesError && !initialLoading" class="error-banner">
      <span class="error-banner-text">资源数据加载失败：{{ resourcesError }}</span>
      <el-button size="small" @click="fetchResources">重试</el-button>
    </div>

    <!-- 统计卡片骨架 / 实际卡片 -->
    <el-row :gutter="16" class="stat-row">
      <template v-if="initialLoading">
        <el-col :span="4" v-for="i in 6" :key="i">
          <div class="stat-card"><el-skeleton :rows="2" animated /></div>
        </el-col>
      </template>
      <template v-else>
        <el-col :span="4" v-for="item in statCards" :key="item.label">
          <div class="stat-card stat-card--clickable" role="button" tabindex="0" :aria-label="`${item.label}: ${item.value}`" @click="item.tab && (activeTab = item.tab)" @keydown.enter="item.tab && (activeTab = item.tab)">
            <div class="stat-label">{{ item.label }}</div>
            <div class="stat-value" :style="{ color: item.color }">{{ item.value }}</div>
          </div>
        </el-col>
      </template>
    </el-row>

    <!-- 资源 Tabs -->
    <div class="data-card" v-loading="refreshing && !initialLoading">
      <el-tabs v-model="activeTab">
        <!-- 命名空间 -->
        <el-tab-pane label="命名空间" name="namespaces">
          <el-table :data="pagedNamespaces" stripe aria-label="命名空间列表">
            <el-table-column prop="name" label="命名空间" min-width="180" show-overflow-tooltip />
            <el-table-column prop="pods" label="Pods" width="100" align="center" />
            <el-table-column prop="abnormal_pods" label="异常 Pods" width="120" align="center">
              <template #default="{row}">
                <el-tag :type="row.abnormal_pods > 0 ? 'warning' : 'success'" size="small">{{ row.abnormal_pods }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="deployments" label="Deployments" width="140" align="center" />
            <el-table-column prop="services" label="Services" width="120" align="center" />
          </el-table>
          <div class="pagination-wrap">
            <el-pagination
              v-model:current-page="nsPage"
              v-model:page-size="nsPageSize"
              :page-sizes="[10, 20, 50]"
              :total="(resources.namespace_overview || []).length"
              layout="total, sizes, prev, pager, next"
              small
            />
          </div>
        </el-tab-pane>

        <!-- 节点 -->
        <el-tab-pane label="节点" name="nodes">
          <el-table :data="pagedNodes" stripe aria-label="节点列表">
            <el-table-column prop="name" label="节点名称" min-width="200" show-overflow-tooltip />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{row}">
                <el-tag :type="row.status === 'Ready' ? 'success' : 'danger'" size="small">{{ row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="ip" label="IP" width="140" />
            <el-table-column prop="cpu" label="CPU" width="80" align="center">
              <template #default="{row}">{{ row.cpu }} 核</template>
            </el-table-column>
            <el-table-column prop="memory" label="内存" width="100">
              <template #default="{row}">{{ formatMemory(row.memory) }}</template>
            </el-table-column>
            <el-table-column prop="kubelet_version" label="kubelet" width="140" />
            <el-table-column prop="os_image" label="系统" min-width="200" show-overflow-tooltip />
            <el-table-column prop="container_runtime" label="容器运行时" width="200" show-overflow-tooltip />
          </el-table>
          <div class="pagination-wrap">
            <el-pagination
              v-model:current-page="nodePage"
              v-model:page-size="nodePageSize"
              :page-sizes="[10, 20, 50]"
              :total="(resources.nodes || []).length"
              layout="total, sizes, prev, pager, next"
              small
            />
          </div>
        </el-tab-pane>

        <!-- Pods -->
        <el-tab-pane label="Pods" name="pods">
          <div class="filter-bar">
            <el-select v-model="podNamespace" placeholder="命名空间" clearable style="width:150px" @change="fetchPods">
              <el-option v-for="ns in resources.namespaces || []" :key="ns" :label="ns" :value="ns" />
            </el-select>
            <el-input v-model="podSearch" placeholder="搜索名称 / 命名空间 / 节点 / 状态…" clearable style="width:280px" />
            <span class="filter-count">共 {{ filteredPods.length }} 个 Pod</span>
          </div>
          <el-table :data="pagedPods" stripe empty-text="暂无 Pod 数据" aria-label="Pod 列表">
            <el-table-column prop="name" label="名称" min-width="260" show-overflow-tooltip />
            <el-table-column prop="namespace" label="命名空间" width="110" />
            <el-table-column prop="status" label="状态" width="150">
              <template #default="{row}">
                <el-tag :type="podStatusType(row.status)" size="small">{{ row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="reason" label="异常原因" min-width="180" show-overflow-tooltip>
              <template #default="{row}">
                <el-tooltip v-if="row.reason || row.message" :content="row.message || row.reason" placement="top">
                  <el-tag :type="podReasonType(row.reason || row.status)" size="small" effect="plain">
                    {{ row.reason || '-' }}
                  </el-tag>
                </el-tooltip>
                <span v-else>-</span>
              </template>
            </el-table-column>
            <el-table-column prop="node" label="节点" width="150" show-overflow-tooltip />
            <el-table-column prop="pod_ip" label="Pod IP" width="130" />
            <el-table-column label="镜像" min-width="250" show-overflow-tooltip>
              <template #default="{row}">{{ (row.images || []).join(', ') }}</template>
            </el-table-column>
            <el-table-column prop="restarts" label="重启" width="70" align="center">
              <template #default="{row}">
                <span :class="{ 'text-danger': row.restarts > 5 }">{{ row.restarts }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="创建时间" width="170">
              <template #default="{row}">{{ formatTime(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="120" fixed="right">
              <template #default="{row}">
                <el-button link type="primary" size="small" :aria-label="`查看 ${row.name} 日志`" @click="openPodLogs(row)">日志</el-button>
                <el-button link type="info" size="small" :aria-label="`查看 ${row.name} 事件`" @click="openPodEvents(row)">事件</el-button>
                <el-button link type="danger" size="small" :aria-label="`删除 ${row.name}`" @click="confirmDeletePod(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div class="pagination-wrap">
            <el-pagination
              v-model:current-page="podPage"
              v-model:page-size="podPageSize"
              :page-sizes="[10, 20, 50, 100]"
              :total="filteredPods.length"
              layout="total, sizes, prev, pager, next"
              small
            />
          </div>
        </el-tab-pane>

        <!-- Deployments -->
        <el-tab-pane label="Deployments" name="deployments">
          <div class="filter-bar">
            <el-select v-model="depNamespace" placeholder="命名空间" clearable style="width:150px" @change="fetchDeployments">
              <el-option v-for="ns in resources.namespaces || []" :key="ns" :label="ns" :value="ns" />
            </el-select>
            <el-input v-model="depSearch" placeholder="搜索 Deployment…" clearable style="width:220px" />
            <span class="filter-count">共 {{ filteredDeployments.length }} 个 Deployment</span>
          </div>
          <el-table :data="pagedDeployments" stripe empty-text="暂无 Deployment 数据" aria-label="Deployment 列表">
            <el-table-column prop="name" label="名称" min-width="200" show-overflow-tooltip />
            <el-table-column prop="namespace" label="命名空间" width="110" />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{row}">
                <el-tag :type="depStatusType(row.status)" size="small">{{ row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="镜像" min-width="250" show-overflow-tooltip>
              <template #default="{row}">{{ (row.images || []).join(', ') }}</template>
            </el-table-column>
            <el-table-column label="副本" width="100" align="center">
              <template #default="{row}">
                <span :class="{ 'text-warning': row.ready_replicas < row.replicas }">
                  {{ row.ready_replicas }} / {{ row.replicas }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="创建时间" width="170">
              <template #default="{row}">{{ formatTime(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="90" fixed="right">
              <template #default="{row}">
                <el-button link type="warning" size="small" :aria-label="`重启 ${row.name}`" @click="confirmRestartDeployment(row)">重启</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div class="pagination-wrap">
            <el-pagination
              v-model:current-page="depPage"
              v-model:page-size="depPageSize"
              :page-sizes="[10, 20, 50]"
              :total="filteredDeployments.length"
              layout="total, sizes, prev, pager, next"
              small
            />
          </div>
        </el-tab-pane>

        <!-- Services -->
        <el-tab-pane label="Services" name="services">
          <div class="filter-bar">
            <el-select v-model="svcNamespace" placeholder="命名空间" clearable style="width:150px" @change="fetchServices">
              <el-option v-for="ns in resources.namespaces || []" :key="ns" :label="ns" :value="ns" />
            </el-select>
            <el-input v-model="svcSearch" placeholder="搜索 Service…" clearable style="width:220px" />
            <span class="filter-count">共 {{ filteredServices.length }} 个 Service</span>
          </div>
          <el-table :data="pagedServices" stripe empty-text="暂无 Service 数据" aria-label="Service 列表">
            <el-table-column prop="name" label="名称" min-width="200" show-overflow-tooltip />
            <el-table-column prop="namespace" label="命名空间" width="110" />
            <el-table-column prop="service_type" label="类型" width="120">
              <template #default="{row}"><el-tag size="small">{{ row.service_type }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="cluster_ip" label="Cluster IP" width="140" />
            <el-table-column prop="ports" label="端口" min-width="180" show-overflow-tooltip />
            <el-table-column prop="selector" label="Selector" min-width="180" show-overflow-tooltip />
            <el-table-column prop="created_at" label="创建时间" width="170">
              <template #default="{row}">{{ formatTime(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="80" fixed="right">
              <template #default="{row}">
                <el-button link type="primary" size="small" :aria-label="`查看 ${row.name} 详情`" @click="openServiceDetail(row)">详情</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div class="pagination-wrap">
            <el-pagination
              v-model:current-page="svcPage"
              v-model:page-size="svcPageSize"
              :page-sizes="[10, 20, 50]"
              :total="filteredServices.length"
              layout="total, sizes, prev, pager, next"
              small
            />
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- Pod 日志 Dialog -->
    <el-dialog v-model="logsDialogVisible" width="820px">
      <template #header="{ titleId, titleClass }">
        <div class="dialog-header-bar">
          <h3 :id="titleId" :class="titleClass">{{ podDialogTitle('日志') }}</h3>
          <div class="dialog-header-actions">
            <el-button size="small" @click="copyLogs">复制</el-button>
            <el-button size="small" @click="downloadLogs">下载</el-button>
          </div>
        </div>
      </template>
      <div v-loading="logsLoading">
        <pre class="log-box" tabindex="0" role="log" aria-label="Pod 日志">{{ podLogs || '暂无日志' }}</pre>
      </div>
    </el-dialog>

    <!-- Pod 事件 Dialog -->
    <el-dialog v-model="eventsDialogVisible" :title="podDialogTitle('事件')" width="900px">
      <el-table :data="pagedPodEvents" stripe v-loading="eventsLoading" empty-text="暂无事件" aria-label="Pod 事件列表">
        <el-table-column prop="type" label="类型" width="90">
          <template #default="{row}">
            <el-tag :type="row.type === 'Warning' ? 'warning' : 'info'" size="small">{{ row.type || '-' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="reason" label="原因" width="150" show-overflow-tooltip />
        <el-table-column prop="message" label="消息" min-width="300" show-overflow-tooltip />
        <el-table-column prop="count" label="次数" width="70" align="center" />
        <el-table-column prop="source" label="来源" width="120" show-overflow-tooltip />
        <el-table-column prop="last_timestamp" label="最后时间" width="170">
          <template #default="{row}">{{ formatTime(row.last_timestamp) }}</template>
        </el-table-column>
      </el-table>
      <div class="pagination-wrap" v-if="podEvents.length > 10">
        <el-pagination
          v-model:current-page="eventPage"
          v-model:page-size="eventPageSize"
          :page-sizes="[10, 20, 50]"
          :total="podEvents.length"
          layout="total, sizes, prev, pager, next"
          small
        />
      </div>
    </el-dialog>

    <!-- Service 详情 Dialog -->
    <el-dialog v-model="svcDetailVisible" :title="svcDialogTitle" width="600px">
      <el-descriptions :column="1" border v-if="selectedService">
        <el-descriptions-item label="名称">{{ selectedService.name }}</el-descriptions-item>
        <el-descriptions-item label="命名空间">{{ selectedService.namespace }}</el-descriptions-item>
        <el-descriptions-item label="类型">{{ selectedService.service_type }}</el-descriptions-item>
        <el-descriptions-item label="Cluster IP">{{ selectedService.cluster_ip || '-' }}</el-descriptions-item>
        <el-descriptions-item label="端口">{{ selectedService.ports || '-' }}</el-descriptions-item>
        <el-descriptions-item label="Selector">{{ selectedService.selector || '-' }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ formatTime(selectedService.created_at) }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </main>
</template>

<script setup lang="ts">
import { ref, computed, watch, onActivated, onDeactivated } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Refresh } from '@element-plus/icons-vue'
import { getCluster, getClusterResources, getClusterPods, getClusterServices, getClusterDeployments, getPodLogs, getPodEvents, deleteClusterPod, restartClusterDeployment } from '@/api/containers'

// ── 类型定义 ──
interface K8sPod {
  name: string
  namespace: string
  status: string
  reason?: string
  message?: string
  node?: string
  pod_ip?: string
  images?: string[]
  restarts?: number
  created_at?: string
}

interface K8sNode {
  name: string
  status: string
  ip?: string
  cpu?: number
  memory?: string
  kubelet_version?: string
  os_image?: string
  container_runtime?: string
}

interface K8sDeployment {
  name: string
  namespace: string
  status: string
  images?: string[]
  replicas: number
  ready_replicas: number
  created_at?: string
}

interface K8sService {
  name: string
  namespace: string
  service_type: string
  cluster_ip?: string
  ports?: string
  selector?: string
  created_at?: string
}

interface K8sNamespace {
  name: string
  pods: number
  abnormal_pods: number
  deployments: number
  services: number
}

interface K8sResources {
  connected?: boolean
  error?: string
  version?: string
  node_count?: number
  ready_nodes?: number
  pod_count?: number
  deployment_count?: number
  service_count?: number
  namespace_count?: number
  namespaces?: string[]
  namespace_overview?: K8sNamespace[]
  nodes?: K8sNode[]
  pods?: K8sPod[]
  deployments?: K8sDeployment[]
  services?: K8sService[]
}

interface PodEvent {
  type?: string
  reason?: string
  message?: string
  count?: number
  source?: string
  last_timestamp?: string
}

const route = useRoute()
const router = useRouter()

// ── Repair: 响应式 clusterId，支持路由参数变化 ──
const clusterId = computed(() => Number(route.params.id))

const cluster = ref<Record<string, any>>({})
const resources = ref<K8sResources>({})
const refreshing = ref(false)
const initialLoading = ref(true)
const clusterError = ref('')
const resourcesError = ref('')

// ── URL 同步 activeTab ──
const activeTab = ref(route.query.tab as string || 'namespaces')
watch(activeTab, (val) => {
  router.replace({ query: { ...route.query, tab: val } })
})
watch(() => route.query.tab, (val) => {
  if (val && typeof val === 'string') activeTab.value = val
})

const selectedPod = ref<K8sPod | null>(null)
const logsDialogVisible = ref(false)
const eventsDialogVisible = ref(false)
const logsLoading = ref(false)
const eventsLoading = ref(false)
const podLogs = ref('')
const podEvents = ref<PodEvent[]>([])
const eventPage = ref(1)
const eventPageSize = ref(10)

// Service 详情
const svcDetailVisible = ref(false)
const selectedService = ref<K8sService | null>(null)
const svcDialogTitle = computed(() => selectedService.value ? `Service: ${selectedService.value.name}` : 'Service 详情')

// 搜索和筛选
const podNamespace = ref('')
const podSearch = ref('')
const depNamespace = ref('')
const depSearch = ref('')
const svcNamespace = ref('')
const svcSearch = ref('')

// 分页
const nsPage = ref(1)
const nsPageSize = ref(20)
const nodePage = ref(1)
const nodePageSize = ref(20)
const podPage = ref(1)
const podPageSize = ref(20)
const depPage = ref(1)
const depPageSize = ref(20)
const svcPage = ref(1)
const svcPageSize = ref(20)

// 事件分页数据
const pagedPodEvents = computed(() => {
  const start = (eventPage.value - 1) * eventPageSize.value
  return podEvents.value.slice(start, start + eventPageSize.value)
})

// ── 异常摘要 ──
const anomalyList = computed(() => {
  const r = resources.value
  const list: { tab: string; text: string }[] = []
  const notReady = (r.nodes || []).filter((n) => n.status !== 'Ready')
  if (notReady.length) list.push({ tab: 'nodes', text: `${notReady.length} 个节点未就绪` })
  const abnormalPods = (r.pods || []).filter((p) => !['Running', 'Succeeded'].includes(p.status))
  if (abnormalPods.length) list.push({ tab: 'pods', text: `${abnormalPods.length} 个 Pod 异常` })
  const incompleteDeps = (r.deployments || []).filter((d) => d.ready_replicas < d.replicas)
  if (incompleteDeps.length) list.push({ tab: 'deployments', text: `${incompleteDeps.length} 个 Deployment 副本不足` })
  return list
})

// 过滤后的数据（Pod 搜索扩展到 namespace / node / status）
const filteredPods = computed(() => {
  let list = resources.value.pods || []
  if (podSearch.value) {
    const kw = podSearch.value.toLowerCase()
    list = list.filter((p) =>
      p.name.toLowerCase().includes(kw) ||
      (p.namespace || '').toLowerCase().includes(kw) ||
      (p.node || '').toLowerCase().includes(kw) ||
      (p.status || '').toLowerCase().includes(kw)
    )
  }
  return list
})

const filteredDeployments = computed(() => {
  let list = resources.value.deployments || []
  if (depSearch.value) {
    const kw = depSearch.value.toLowerCase()
    list = list.filter((d) => d.name.toLowerCase().includes(kw))
  }
  return list
})

const filteredServices = computed(() => {
  let list = resources.value.services || []
  if (svcSearch.value) {
    const kw = svcSearch.value.toLowerCase()
    list = list.filter((s) => s.name.toLowerCase().includes(kw))
  }
  return list
})

// 分页后的数据
const pagedNamespaces = computed(() => {
  const list = resources.value.namespace_overview || []
  const start = (nsPage.value - 1) * nsPageSize.value
  return list.slice(start, start + nsPageSize.value)
})
const pagedNodes = computed(() => {
  const list = resources.value.nodes || []
  const start = (nodePage.value - 1) * nodePageSize.value
  return list.slice(start, start + nodePageSize.value)
})
const pagedPods = computed(() => {
  const start = (podPage.value - 1) * podPageSize.value
  return filteredPods.value.slice(start, start + podPageSize.value)
})
const pagedDeployments = computed(() => {
  const start = (depPage.value - 1) * depPageSize.value
  return filteredDeployments.value.slice(start, start + depPageSize.value)
})
const pagedServices = computed(() => {
  const start = (svcPage.value - 1) * svcPageSize.value
  return filteredServices.value.slice(start, start + svcPageSize.value)
})

// 搜索时重置页码
watch(podSearch, () => { podPage.value = 1 })
watch(podNamespace, () => { podPage.value = 1 })
watch(depSearch, () => { depPage.value = 1 })
watch(depNamespace, () => { depPage.value = 1 })
watch(svcSearch, () => { svcPage.value = 1 })
watch(svcNamespace, () => { svcPage.value = 1 })

// 统计卡片（可点击跳转对应 Tab）
const statCards = computed(() => {
  const r = resources.value
  return [
    { label: '节点', value: r.node_count ?? '-', color: '', tab: 'nodes' },
    { label: '就绪节点', value: r.ready_nodes ?? '-', color: r.ready_nodes === 0 ? 'var(--danger-color)' : r.ready_nodes === r.node_count ? 'var(--success-color)' : 'var(--warning-color)', tab: 'nodes' },
    { label: 'Pods', value: r.pod_count ?? '-', color: '', tab: 'pods' },
    { label: 'Deployments', value: r.deployment_count ?? '-', color: '', tab: 'deployments' },
    { label: 'Services', value: r.service_count ?? '-', color: '', tab: 'services' },
    { label: '命名空间', value: r.namespace_count ?? '-', color: '', tab: 'namespaces' },
  ]
})

// Helpers
function statusType(s: string) { return s === 'running' ? 'success' : s === 'stopped' ? 'danger' : 'warning' }
function podStatusType(s: string) {
  if (s === 'Running' || s === 'Succeeded') return 'success'
  if (['Failed', 'CrashLoopBackOff', 'ImagePullBackOff', 'ErrImagePull', 'CreateContainerConfigError'].includes(s)) return 'danger'
  if (s === 'Pending' || s === 'NotReady' || s === 'ContainersNotReady') return 'warning'
  return 'info'
}
function podReasonType(s: string) {
  if (!s) return 'info'
  if (['CrashLoopBackOff', 'ImagePullBackOff', 'ErrImagePull', 'CreateContainerConfigError', 'Failed'].includes(s)) return 'danger'
  if (['Pending', 'NotReady', 'ContainersNotReady', 'ContainerCreating'].includes(s)) return 'warning'
  return 'info'
}
function depStatusType(s: string) { return s === 'running' ? 'success' : s === 'error' ? 'danger' : 'warning' }

function formatMemory(ki: string) {
  if (!ki) return '-'
  const num = parseInt(ki)
  if (ki.endsWith('Ki')) return (num / 1048576).toFixed(1) + ' GB'
  if (ki.endsWith('Mi')) return (num / 1024).toFixed(1) + ' GB'
  if (ki.endsWith('Gi')) return num.toFixed(1) + ' GB'
  return ki
}

function formatTime(ts: string) {
  if (!ts) return '-'
  try { return new Date(ts).toLocaleString('zh-CN') } catch { return ts }
}

function podDialogTitle(type: string) {
  if (!selectedPod.value) return `Pod ${type}`
  return `${selectedPod.value.namespace}/${selectedPod.value.name} ${type}`
}

// 日志复制 / 下载
function copyLogs() {
  if (!podLogs.value) return
  navigator.clipboard.writeText(podLogs.value).then(
    () => ElMessage.success('已复制到剪贴板'),
    () => ElMessage.error('复制失败'),
  )
}

function downloadLogs() {
  if (!podLogs.value || !selectedPod.value) return
  const blob = new Blob([podLogs.value], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${selectedPod.value.namespace}_${selectedPod.value.name}.log`
  a.click()
  URL.revokeObjectURL(url)
}

// Service 详情
function openServiceDetail(row: K8sService) {
  selectedService.value = row
  svcDetailVisible.value = true
}

async function openPodLogs(row: K8sPod) {
  selectedPod.value = row
  podLogs.value = ''
  logsDialogVisible.value = true
  logsLoading.value = true
  try {
    const res: any = await getPodLogs(clusterId.value, row.namespace, row.name, { tail_lines: 300 })
    podLogs.value = res.data?.logs || ''
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '加载日志失败')
  } finally { logsLoading.value = false }
}

async function openPodEvents(row: K8sPod) {
  selectedPod.value = row
  podEvents.value = []
  eventPage.value = 1
  eventsDialogVisible.value = true
  eventsLoading.value = true
  try {
    const res: any = await getPodEvents(clusterId.value, row.namespace, row.name)
    podEvents.value = res.data || []
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '加载事件失败')
  } finally { eventsLoading.value = false }
}

async function confirmDeletePod(row: K8sPod) {
  try {
    await ElMessageBox.confirm(
      `确定删除 Pod ${row.namespace}/${row.name}？删除后如该 Pod 属于某个工作负载，系统将自动创建新 Pod 替代。`,
      '删除 Pod',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
    await deleteClusterPod(clusterId.value, row.namespace, row.name)
    ElMessage.success('Pod 已删除')
    await fetchResources()
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error(e?.response?.data?.detail || '操作失败')
  }
}

async function confirmRestartDeployment(row: K8sDeployment) {
  try {
    await ElMessageBox.confirm(
      `确定滚动重启 Deployment ${row.namespace}/${row.name}？`,
      '重启 Deployment',
      { type: 'warning', confirmButtonText: '重启', cancelButtonText: '取消' },
    )
    await restartClusterDeployment(clusterId.value, row.namespace, row.name)
    ElMessage.success('重启已触发')
    await fetchDeployments()
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error(e?.response?.data?.detail || '操作失败')
  }
}

// Fetch
async function fetchCluster() {
  clusterError.value = ''
  try {
    const res: any = await getCluster(clusterId.value)
    cluster.value = res.data
  } catch (e: any) {
    clusterError.value = e?.response?.data?.detail || '加载失败'
  }
}

async function fetchResources() {
  refreshing.value = true
  resourcesError.value = ''
  try {
    const res: any = await getClusterResources(clusterId.value)
    resources.value = res.data
    cluster.value.status = res.data.connected ? 'running' : 'stopped'
    cluster.value.status_message = res.data.connected ? '' : (res.data.error || '连接失败')
    cluster.value.version = res.data.version || cluster.value.version
    cluster.value.node_count = res.data.node_count ?? cluster.value.node_count
  } catch (e: any) {
    resourcesError.value = e?.response?.data?.detail || '加载失败'
  } finally { refreshing.value = false; initialLoading.value = false }
}

async function fetchPods() {
  try {
    const res: any = await getClusterPods(clusterId.value, { namespace: podNamespace.value })
    resources.value.pods = res.data
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '加载失败') }
}

async function fetchDeployments() {
  try {
    const res: any = await getClusterDeployments(clusterId.value, { namespace: depNamespace.value })
    resources.value.deployments = res.data
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '加载失败') }
}

async function fetchServices() {
  try {
    const res: any = await getClusterServices(clusterId.value, { namespace: svcNamespace.value })
    resources.value.services = res.data
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '加载失败') }
}

// ── Repair: keep-alive 兼容 — onActivated 每次进入都刷新 ──
let timer: ReturnType<typeof setInterval> | null = null

onActivated(() => {
  initialLoading.value = true
  fetchCluster()
  fetchResources()
  timer = setInterval(fetchResources, 30000)
})

onDeactivated(() => {
  if (timer) { clearInterval(timer); timer = null }
})
</script>

<style scoped>
.page-header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.page-header-title {
  margin: 0;
}

/* ── 错误横幅 ── */
.error-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  margin-bottom: 16px;
  background: color-mix(in srgb, var(--danger-color) 8%, transparent);
  border: 1px solid color-mix(in srgb, var(--danger-color) 25%, transparent);
  border-radius: var(--border-radius);
}

.error-banner-text {
  font-size: 13px;
  color: var(--danger-color);
}

/* ── 异常横幅 ── */
.anomaly-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  margin-bottom: 16px;
  background: color-mix(in srgb, var(--warning-color) 8%, transparent);
  border: 1px solid color-mix(in srgb, var(--warning-color) 25%, transparent);
  border-radius: var(--border-radius);
}

.anomaly-banner-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--warning-color);
  white-space: nowrap;
}

.anomaly-icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}

.anomaly-items {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

/* ── 统计卡片 ── */
.stat-row {
  margin-bottom: 16px;
}

.stat-card {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 12px 16px;
  text-align: center;
}

.stat-card--clickable {
  cursor: pointer;
  transition: border-color 150ms ease-out, box-shadow 150ms ease-out;
}

.stat-card--clickable:hover {
  border-color: var(--primary-color);
  box-shadow: 0 0 0 1px var(--primary-color);
}

.stat-card--clickable:focus-visible {
  outline: 2px solid var(--primary-color);
  outline-offset: 2px;
}

.stat-label {
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 4px;
}

.stat-value {
  font-size: 22px;
  font-weight: 700;
}

/* ── 筛选栏 ── */
.filter-count {
  margin-left: auto;
  color: var(--text-muted);
  font-size: 13px;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.text-danger {
  color: var(--danger-color);
}

.text-warning {
  color: var(--warning-color);
}

/* ── Dialog ── */
.dialog-header-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.dialog-header-actions {
  display: flex;
  gap: 8px;
}

/* ── 日志终端 ── */
.log-box {
  --log-bg: #111827;
  --log-fg: #d1d5db;
  min-height: 320px;
  max-height: 560px;
  margin: 0;
  padding: 14px;
  overflow: auto;
  color: var(--log-fg);
  background: var(--log-bg);
  border-radius: 8px;
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

@media (prefers-reduced-motion: reduce) {
  .stat-card--clickable {
    transition: none;
  }
}
</style>
