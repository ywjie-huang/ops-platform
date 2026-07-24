<template>
  <main>
    <div class="detail-header surface-card">
      <div class="detail-header-copy">
        <div class="detail-title-row">
          <el-button text @click="$router.push('/assets/containers')" aria-label="返回集群列表">
            <el-icon><ArrowLeft /></el-icon>
            返回
          </el-button>
          <h2 class="page-title detail-title">{{ cluster.name || '集群详情' }}</h2>
          <el-tag :type="statusType(cluster.status)" size="small">{{ cluster.status === 'running' ? '运行中' : '连接异常' }}</el-tag>
          <el-tag v-if="cluster.version" type="info" size="small">{{ cluster.version }}</el-tag>
        </div>
        <div class="detail-meta">
          <span>{{ cluster.description || '未填写说明' }}</span>
          <span class="mono">{{ cluster.endpoint || '-' }}</span>
          <span>最后刷新：{{ formatTime(cluster.updated_at) }}</span>
        </div>
      </div>
      <div class="detail-header-actions">
        <el-button :loading="refreshing" size="small" @click="fetchResources" aria-label="刷新集群数据">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </div>

    <div v-if="clusterError" class="error-banner">
      <span class="error-banner-text">集群信息加载失败：{{ clusterError }}</span>
      <el-button size="small" @click="fetchCluster">重试</el-button>
    </div>

    <div v-if="resourcesError && !initialLoading" class="error-banner">
      <span class="error-banner-text">资源数据加载失败：{{ resourcesError }}</span>
      <el-button size="small" @click="fetchResources">重试</el-button>
    </div>

    <div v-if="anomalyList.length" class="warning-banner" role="alert">
      <span>当前建议优先处理：{{ anomalyList[0]?.text }}{{ anomalyList[1] ? `，${anomalyList[1].text}` : '' }}。</span>
      <span class="warning-meta">异常优先</span>
    </div>

    <div class="summary-grid" role="region" aria-label="集群资源概览">
      <template v-if="initialLoading">
        <div v-for="i in 4" :key="i" class="summary-card"><el-skeleton :rows="2" animated /></div>
      </template>
      <template v-else>
        <div v-for="item in topSummaryCards" :key="item.label" class="summary-card">
          <div class="summary-label">{{ item.label }}</div>
          <div class="summary-value">{{ item.value }}</div>
          <div class="summary-foot">{{ item.foot }}</div>
        </div>
      </template>
    </div>

    <div class="workbench-grid">
      <section class="surface-card workbench-main" v-loading="refreshing && !initialLoading">
        <div class="tabs-row">
          <button v-for="item in visibleTabs" :key="item.value" type="button" class="tab-button" :class="{ active: activeTab === item.value }" @click="activeTab = item.value">
            {{ item.label }}
          </button>
        </div>

        <div v-if="activeTab === 'pods'" class="section-body">
          <div class="tool-row">
            <el-select v-model="podNamespace" placeholder="命名空间" clearable class="tool-select" @change="fetchPods">
              <el-option v-for="ns in resources.namespaces || []" :key="ns" :label="ns" :value="ns" />
            </el-select>
            <el-input v-model="podSearch" placeholder="搜索 Pod / 状态 / 节点" clearable class="tool-search" />
            <span class="tool-count">共 {{ filteredPods.length }} 个 Pod</span>
          </div>

          <div class="table-wrapper">
            <el-table :data="pagedPods" stripe empty-text="暂无 Pod 数据" aria-label="Pod 列表">
              <el-table-column label="Pod" min-width="260">
                <template #default="{ row }">
                  <div class="resource-primary">
                    <strong>{{ row.name }}</strong>
                    <span>{{ row.namespace || '-' }} · {{ row.pod_ip || row.node || '-' }}</span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column prop="status" label="状态" width="140">
                <template #default="{ row }">
                  <el-tag :type="podStatusType(row.status)" size="small">{{ row.status }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="原因" min-width="180" show-overflow-tooltip>
                <template #default="{ row }">
                  <el-tooltip v-if="row.reason || row.message" :content="row.message || row.reason" placement="top">
                    <el-tag :type="podReasonType(row.reason || row.status)" size="small" effect="plain">
                      {{ row.reason || '-' }}
                    </el-tag>
                  </el-tooltip>
                  <span v-else>-</span>
                </template>
              </el-table-column>
              <el-table-column prop="node" label="节点" width="150" show-overflow-tooltip />
              <el-table-column prop="restarts" label="重启" width="80" align="center">
                <template #default="{ row }">
                  <span :class="{ 'text-danger': row.restarts > 5 }">{{ row.restarts }}</span>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="140" fixed="right">
                <template #default="{ row }">
                  <el-button link type="primary" size="small" @click="openPodLogs(row)">日志</el-button>
                  <el-button link type="info" size="small" @click="openPodEvents(row)">事件</el-button>
                  <el-button link type="danger" size="small" @click="confirmDeletePod(row)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
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
        </div>

        <div v-else-if="activeTab === 'deployments'" class="section-body">
          <div class="tool-row">
            <el-select v-model="depNamespace" placeholder="命名空间" clearable class="tool-select" @change="fetchDeployments">
              <el-option v-for="ns in resources.namespaces || []" :key="ns" :label="ns" :value="ns" />
            </el-select>
            <el-input v-model="depSearch" placeholder="搜索 Deployment" clearable class="tool-search" />
            <span class="tool-count">共 {{ filteredDeployments.length }} 个 Deployment</span>
          </div>

          <div class="table-wrapper">
            <el-table :data="pagedDeployments" stripe empty-text="暂无 Deployment 数据" aria-label="Deployment 列表">
              <el-table-column label="Deployment" min-width="240">
                <template #default="{ row }">
                  <div class="resource-primary">
                    <strong>{{ row.name }}</strong>
                    <span>{{ row.namespace || '-' }} · {{ (row.images || []).join(', ') || '-' }}</span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column prop="status" label="状态" width="120">
                <template #default="{ row }">
                  <el-tag :type="depStatusType(row.status)" size="small">{{ row.status }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="副本" width="110" align="center">
                <template #default="{ row }">
                  <span :class="{ 'text-warning': row.ready_replicas < row.replicas }">{{ row.ready_replicas }} / {{ row.replicas }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="created_at" label="创建时间" width="170">
                <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
              </el-table-column>
              <el-table-column label="操作" width="100" fixed="right">
                <template #default="{ row }">
                  <el-button link type="warning" size="small" @click="confirmRestartDeployment(row)">重启</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
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
        </div>

        <div v-else-if="activeTab === 'nodes'" class="section-body">
          <div class="table-wrapper">
            <el-table :data="pagedNodes" stripe aria-label="节点列表">
              <el-table-column label="节点" min-width="220">
                <template #default="{ row }">
                  <div class="resource-primary">
                    <strong>{{ row.name }}</strong>
                    <span>{{ row.ip || '-' }} · {{ row.os_image || '-' }}</span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column prop="status" label="状态" width="100">
                <template #default="{ row }">
                  <el-tag :type="row.status === 'Ready' ? 'success' : 'danger'" size="small">{{ row.status }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="cpu" label="CPU" width="80" align="center">
                <template #default="{ row }">{{ row.cpu }} 核</template>
              </el-table-column>
              <el-table-column prop="memory" label="内存" width="110">
                <template #default="{ row }">{{ formatMemory(row.memory) }}</template>
              </el-table-column>
              <el-table-column prop="container_runtime" label="容器运行时" min-width="180" show-overflow-tooltip />
              <el-table-column label="操作" width="80" fixed="right">
                <template #default="{ row }">
                  <el-button link type="primary" size="small" @click="openNodeDetail(row)">详情</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
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
        </div>

        <div v-else-if="activeTab === 'namespaces'" class="section-body">
          <div class="table-wrapper">
            <el-table :data="pagedNamespaces" stripe aria-label="命名空间列表">
              <el-table-column label="命名空间" min-width="200">
                <template #default="{ row }">
                  <div class="resource-primary">
                    <strong>{{ row.name }}</strong>
                    <span>Pods {{ row.pods }} · Deployments {{ row.deployments }} · Services {{ row.services }}</span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column prop="abnormal_pods" label="异常 Pods" width="110" align="center">
                <template #default="{ row }">
                  <el-tag :type="row.abnormal_pods > 0 ? 'warning' : 'success'" size="small">{{ row.abnormal_pods }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="80" fixed="right">
                <template #default="{ row }">
                  <el-button link type="primary" size="small" @click="openNamespaceDetail(row)">详情</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
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
        </div>

        <div v-else class="section-body">
          <div class="tool-row">
            <el-select v-model="svcNamespace" placeholder="命名空间" clearable class="tool-select" @change="fetchServices">
              <el-option v-for="ns in resources.namespaces || []" :key="ns" :label="ns" :value="ns" />
            </el-select>
            <el-input v-model="svcSearch" placeholder="搜索 Service" clearable class="tool-search" />
            <span class="tool-count">共 {{ filteredServices.length }} 个 Service</span>
          </div>

          <div class="table-wrapper">
            <el-table :data="pagedServices" stripe empty-text="暂无 Service 数据" aria-label="Service 列表">
              <el-table-column label="Service" min-width="220">
                <template #default="{ row }">
                  <div class="resource-primary">
                    <strong>{{ row.name }}</strong>
                    <span>{{ row.namespace || '-' }} · {{ row.service_type || '-' }}</span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column prop="cluster_ip" label="Cluster IP" width="140" />
              <el-table-column prop="ports" label="端口" min-width="180" show-overflow-tooltip />
              <el-table-column label="操作" width="80" fixed="right">
                <template #default="{ row }">
                  <el-button link type="primary" size="small" @click="openServiceDetail(row)">详情</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
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
        </div>
      </section>

      <aside class="workbench-side">
        <div class="surface-card side-card">
          <div class="side-card-head">
            <h3>当前异常</h3>
            <span class="side-card-subtitle">只保留最值得先处理的线索</span>
          </div>
          <div class="side-list">
            <div v-for="item in sideHighlights" :key="item.key" class="side-item">
              <div class="side-item-top">
                <strong>{{ item.text }}</strong>
                <el-tag :type="item.key === 'pods' ? 'danger' : 'warning'" size="small">{{ item.count }}</el-tag>
              </div>
              <span>{{ sideHint(item.key) }}</span>
            </div>
            <div v-if="!sideHighlights.length" class="side-item">
              <div class="side-item-top">
                <strong>未发现明显异常</strong>
              </div>
              <span>可以继续查看 Pods、Deployments 或命名空间的实时状态。</span>
            </div>
          </div>
        </div>

        <div class="surface-card side-card">
          <div class="side-card-head">
            <h3>关联视图</h3>
            <span class="side-card-subtitle">帮助快速决定下一步看哪里</span>
          </div>
          <div class="side-list">
            <div class="side-item">
              <div class="side-item-top">
                <strong>Deployment 视图</strong>
                <el-tag size="small">{{ resourceSummary.deploymentGapCount }} 个异常</el-tag>
              </div>
              <span>当 Pod 持续重启或副本不齐时，优先切到 Deployment 视图判断滚动状态。</span>
            </div>
            <div class="side-item">
              <div class="side-item-top">
                <strong>节点视图</strong>
                <el-tag size="small">{{ resourceSummary.notReadyNodeCount }} 个未就绪</el-tag>
              </div>
              <span>节点异常通常会同时影响调度与资源压力，适合联动排查。</span>
            </div>
            <div class="side-item">
              <div class="side-item-top">
                <strong>命名空间视图</strong>
                <el-tag size="small">{{ resourceSummary.hotspotNamespace || '无热区' }}</el-tag>
              </div>
              <span>当异常集中在某个业务域时，从命名空间视角更容易看出影响范围。</span>
            </div>
          </div>
        </div>
      </aside>
    </div>

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

    <el-dialog v-model="eventsDialogVisible" :title="podDialogTitle('事件')" width="900px">
      <el-table :data="pagedPodEvents" stripe v-loading="eventsLoading" empty-text="暂无事件" aria-label="Pod 事件列表">
        <el-table-column prop="type" label="类型" width="90">
          <template #default="{ row }">
            <el-tag :type="row.type === 'Warning' ? 'warning' : 'info'" size="small">{{ row.type || '-' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="reason" label="原因" width="150" show-overflow-tooltip />
        <el-table-column prop="message" label="消息" min-width="300" show-overflow-tooltip />
        <el-table-column prop="count" label="次数" width="70" align="center" />
        <el-table-column prop="source" label="来源" width="120" show-overflow-tooltip />
        <el-table-column prop="last_timestamp" label="最后时间" width="170">
          <template #default="{ row }">{{ formatTime(row.last_timestamp) }}</template>
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

    <el-dialog v-model="svcDetailVisible" :title="svcDialogTitle" width="600px">
      <el-descriptions v-if="selectedService" :column="1" border>
        <el-descriptions-item label="名称">{{ selectedService.name }}</el-descriptions-item>
        <el-descriptions-item label="命名空间">{{ selectedService.namespace }}</el-descriptions-item>
        <el-descriptions-item label="类型">{{ selectedService.service_type }}</el-descriptions-item>
        <el-descriptions-item label="Cluster IP">{{ selectedService.cluster_ip || '-' }}</el-descriptions-item>
        <el-descriptions-item label="端口">{{ selectedService.ports || '-' }}</el-descriptions-item>
        <el-descriptions-item label="Selector">{{ selectedService.selector || '-' }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ formatTime(selectedService.created_at) }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>

    <el-dialog v-model="nodeDetailVisible" :title="nodeDialogTitle" width="600px">
      <el-descriptions v-if="selectedNode" :column="1" border>
        <el-descriptions-item label="节点名称">{{ selectedNode.name }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="selectedNode.status === 'Ready' ? 'success' : 'danger'" size="small">{{ selectedNode.status }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="IP">{{ selectedNode.ip || '-' }}</el-descriptions-item>
        <el-descriptions-item label="CPU">{{ selectedNode.cpu ? selectedNode.cpu + ' 核' : '-' }}</el-descriptions-item>
        <el-descriptions-item label="内存">{{ formatMemory(selectedNode.memory || '') }}</el-descriptions-item>
        <el-descriptions-item label="kubelet">{{ selectedNode.kubelet_version || '-' }}</el-descriptions-item>
        <el-descriptions-item label="系统">{{ selectedNode.os_image || '-' }}</el-descriptions-item>
        <el-descriptions-item label="容器运行时">{{ selectedNode.container_runtime || '-' }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>

    <el-dialog v-model="nsDetailVisible" :title="nsDialogTitle" width="500px">
      <el-descriptions v-if="selectedNamespace" :column="1" border>
        <el-descriptions-item label="命名空间">{{ selectedNamespace.name }}</el-descriptions-item>
        <el-descriptions-item label="Pods">{{ selectedNamespace.pods }}</el-descriptions-item>
        <el-descriptions-item label="异常 Pods">
          <el-tag :type="selectedNamespace.abnormal_pods > 0 ? 'warning' : 'success'" size="small">{{ selectedNamespace.abnormal_pods }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="Deployments">{{ selectedNamespace.deployments }}</el-descriptions-item>
        <el-descriptions-item label="Services">{{ selectedNamespace.services }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </main>
</template>

<script setup lang="ts">
import { computed, ref, watch, onActivated, onDeactivated } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Refresh } from '@element-plus/icons-vue'
import {
  deleteClusterPod,
  getCluster,
  getClusterDeployments,
  getClusterPods,
  getClusterResources,
  getClusterServices,
  getPodEvents,
  getPodLogs,
  restartClusterDeployment,
} from '@/api/containers'
import { buildClusterAnomalies, filterClusterPods, summarizeClusterResources } from '@/utils/k8sCluster'

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
const clusterName = computed(() => String(route.params.name ?? ''))

const cluster = ref<Record<string, any>>({})
const resources = ref<K8sResources>({})
const refreshing = ref(false)
const initialLoading = ref(true)
const clusterError = ref('')
const resourcesError = ref('')

const activeTab = ref((route.query.tab as string) || 'pods')
const nsPage = ref(Number(route.query.nsp) || 1)
const nsPageSize = ref(Number(route.query.nss) || 10)
const nodePage = ref(Number(route.query.ndp) || 1)
const nodePageSize = ref(Number(route.query.nds) || 10)
const podPage = ref(Number(route.query.pp) || 1)
const podPageSize = ref(Number(route.query.ps) || 10)
const depPage = ref(Number(route.query.dp) || 1)
const depPageSize = ref(Number(route.query.ds) || 10)
const svcPage = ref(Number(route.query.sp) || 1)
const svcPageSize = ref(Number(route.query.ss) || 10)

function syncUrl() {
  router.replace({
    query: {
      ...route.query,
      tab: activeTab.value,
      nsp: String(nsPage.value), nss: String(nsPageSize.value),
      ndp: String(nodePage.value), nds: String(nodePageSize.value),
      pp: String(podPage.value), ps: String(podPageSize.value),
      dp: String(depPage.value), ds: String(depPageSize.value),
      sp: String(svcPage.value), ss: String(svcPageSize.value),
    },
  })
}

watch(activeTab, syncUrl)
watch([nsPage, nsPageSize], syncUrl)
watch([nodePage, nodePageSize], syncUrl)
watch([podPage, podPageSize], syncUrl)
watch([depPage, depPageSize], syncUrl)
watch([svcPage, svcPageSize], syncUrl)
watch(() => route.query.tab, (value) => {
  if (value && typeof value === 'string') activeTab.value = value
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

const svcDetailVisible = ref(false)
const selectedService = ref<K8sService | null>(null)
const svcDialogTitle = computed(() => selectedService.value ? `Service: ${selectedService.value.name}` : 'Service 详情')

const nodeDetailVisible = ref(false)
const selectedNode = ref<K8sNode | null>(null)
const nodeDialogTitle = computed(() => selectedNode.value ? `节点: ${selectedNode.value.name}` : '节点详情')

const nsDetailVisible = ref(false)
const selectedNamespace = ref<K8sNamespace | null>(null)
const nsDialogTitle = computed(() => selectedNamespace.value ? `命名空间: ${selectedNamespace.value.name}` : '命名空间详情')

const podNamespace = ref('')
const podSearch = ref('')
const depNamespace = ref('')
const depSearch = ref('')
const svcNamespace = ref('')
const svcSearch = ref('')

const visibleTabs = [
  { label: 'Pods', value: 'pods' },
  { label: 'Deployments', value: 'deployments' },
  { label: '节点', value: 'nodes' },
  { label: '命名空间', value: 'namespaces' },
  { label: 'Services', value: 'services' },
]

const pagedPodEvents = computed(() => {
  const start = (eventPage.value - 1) * eventPageSize.value
  return podEvents.value.slice(start, start + eventPageSize.value)
})

const anomalyList = computed(() => buildClusterAnomalies(resources.value))
const resourceSummary = computed(() => summarizeClusterResources(resources.value))
const sideHighlights = computed(() => anomalyList.value.slice(0, 3))

const filteredPods = computed(() => filterClusterPods(resources.value.pods || [], podSearch.value))
const filteredDeployments = computed(() => {
  let list = resources.value.deployments || []
  if (depSearch.value) {
    const keyword = depSearch.value.toLowerCase()
    list = list.filter((item) => item.name.toLowerCase().includes(keyword))
  }
  return list
})
const filteredServices = computed(() => {
  let list = resources.value.services || []
  if (svcSearch.value) {
    const keyword = svcSearch.value.toLowerCase()
    list = list.filter((item) => item.name.toLowerCase().includes(keyword))
  }
  return list
})

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

watch(podSearch, () => { podPage.value = 1 })
watch(podNamespace, () => { podPage.value = 1 })
watch(depSearch, () => { depPage.value = 1 })
watch(depNamespace, () => { depPage.value = 1 })
watch(svcSearch, () => { svcPage.value = 1 })
watch(svcNamespace, () => { svcPage.value = 1 })
watch(eventsDialogVisible, (value) => { if (!value) eventPage.value = 1 })

const topSummaryCards = computed(() => [
  {
    label: '节点',
    value: resources.value.node_count ?? '-',
    foot: `未就绪 ${resourceSummary.value.notReadyNodeCount}`,
  },
  {
    label: 'Pods',
    value: resources.value.pod_count ?? '-',
    foot: `异常 ${resourceSummary.value.abnormalPodCount}`,
  },
  {
    label: 'Deployments',
    value: resources.value.deployment_count ?? '-',
    foot: `副本不足 ${resourceSummary.value.deploymentGapCount}`,
  },
  {
    label: '命名空间',
    value: resources.value.namespace_count ?? '-',
    foot: resourceSummary.value.hotspotNamespace ? `重点关注 ${resourceSummary.value.hotspotNamespace}` : '等待资源同步',
  },
])

function statusType(status: string) {
  return status === 'running' ? 'success' : status === 'stopped' ? 'danger' : 'warning'
}

function podStatusType(status: string) {
  if (status === 'Running' || status === 'Succeeded') return 'success'
  if (['Failed', 'CrashLoopBackOff', 'ImagePullBackOff', 'ErrImagePull', 'CreateContainerConfigError'].includes(status)) return 'danger'
  if (['Pending', 'NotReady', 'ContainersNotReady'].includes(status)) return 'warning'
  return 'info'
}

function podReasonType(value: string) {
  if (!value) return 'info'
  if (['CrashLoopBackOff', 'ImagePullBackOff', 'ErrImagePull', 'CreateContainerConfigError', 'Failed'].includes(value)) return 'danger'
  if (['Pending', 'NotReady', 'ContainersNotReady', 'ContainerCreating', 'BackOff'].includes(value)) return 'warning'
  return 'info'
}

function depStatusType(status: string) {
  return status === 'running' ? 'success' : status === 'error' ? 'danger' : 'warning'
}

function sideHint(key: string) {
  if (key === 'pods') return '建议先查看日志和事件，再决定是否删除或等待自愈。'
  if (key === 'deployments') return '建议检查副本数和滚动状态，必要时执行重启。'
  return '建议联动节点状态和资源负载继续排查。'
}

function formatMemory(value: string) {
  if (!value) return '-'
  const num = parseInt(value)
  if (value.endsWith('Ki')) return (num / 1048576).toFixed(1) + ' GB'
  if (value.endsWith('Mi')) return (num / 1024).toFixed(1) + ' GB'
  if (value.endsWith('Gi')) return num.toFixed(1) + ' GB'
  return value
}

function formatTime(value?: string) {
  if (!value) return '-'
  try {
    return new Date(value).toLocaleString('zh-CN')
  } catch {
    return value
  }
}

function podDialogTitle(type: string) {
  if (!selectedPod.value) return `Pod ${type}`
  return `${selectedPod.value.namespace}/${selectedPod.value.name} ${type}`
}

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
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = `${selectedPod.value.namespace}_${selectedPod.value.name}.log`
  anchor.click()
  URL.revokeObjectURL(url)
}

function openServiceDetail(row: K8sService) {
  selectedService.value = row
  svcDetailVisible.value = true
}

function openNodeDetail(row: K8sNode) {
  selectedNode.value = row
  nodeDetailVisible.value = true
}

function openNamespaceDetail(row: K8sNamespace) {
  selectedNamespace.value = row
  nsDetailVisible.value = true
}

async function openPodLogs(row: K8sPod) {
  selectedPod.value = row
  podLogs.value = ''
  logsDialogVisible.value = true
  logsLoading.value = true
  try {
    const res: any = await getPodLogs(clusterName.value, row.namespace, row.name, { tail_lines: 300 })
    podLogs.value = res.data?.logs || ''
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '加载日志失败')
  } finally {
    logsLoading.value = false
  }
}

async function openPodEvents(row: K8sPod) {
  selectedPod.value = row
  podEvents.value = []
  eventPage.value = 1
  eventsDialogVisible.value = true
  eventsLoading.value = true
  try {
    const res: any = await getPodEvents(clusterName.value, row.namespace, row.name)
    podEvents.value = res.data || []
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '加载事件失败')
  } finally {
    eventsLoading.value = false
  }
}

async function confirmDeletePod(row: K8sPod) {
  try {
    await ElMessageBox.confirm(
      `确定删除 Pod ${row.namespace}/${row.name}？删除后如该 Pod 属于某个工作负载，系统将自动创建新 Pod 替代。`,
      '删除 Pod',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
    await deleteClusterPod(clusterName.value, row.namespace, row.name)
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
    await restartClusterDeployment(clusterName.value, row.namespace, row.name)
    ElMessage.success('重启已触发')
    await fetchDeployments()
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error(e?.response?.data?.detail || '操作失败')
  }
}

async function fetchCluster() {
  clusterError.value = ''
  if (!clusterName.value) return false
  try {
    const res: any = await getCluster(clusterName.value)
    cluster.value = res.data
    return true
  } catch (e: any) {
    clusterError.value = e?.response?.data?.detail || '加载失败'
    return false
  }
}

async function fetchResources() {
  if (!clusterName.value) return
  refreshing.value = true
  resourcesError.value = ''
  try {
    const res: any = await getClusterResources(clusterName.value)
    resources.value = res.data
    cluster.value.status = res.data.connected ? 'running' : 'stopped'
    cluster.value.status_message = res.data.connected ? '' : (res.data.error || '连接失败')
    cluster.value.version = res.data.version || cluster.value.version
    cluster.value.node_count = res.data.node_count ?? cluster.value.node_count
  } catch (e: any) {
    resourcesError.value = e?.response?.data?.detail || '加载失败'
  } finally {
    refreshing.value = false
    initialLoading.value = false
  }
}

async function loadClusterDetail() {
  const routeRef = clusterName.value
  if (!routeRef || activeLoadRef === routeRef) return
  activeLoadRef = routeRef
  if (cluster.value.name && cluster.value.name !== routeRef) {
    cluster.value = {}
    resources.value = {}
  }
  initialLoading.value = true
  try {
    if (await fetchCluster()) await fetchResources()
    else initialLoading.value = false
  } finally {
    if (activeLoadRef === routeRef) activeLoadRef = ''
  }
}

async function fetchPods() {
  try {
    const res: any = await getClusterPods(clusterName.value, { namespace: podNamespace.value })
    resources.value.pods = res.data
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '加载失败')
  }
}

async function fetchDeployments() {
  try {
    const res: any = await getClusterDeployments(clusterName.value, { namespace: depNamespace.value })
    resources.value.deployments = res.data
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '加载失败')
  }
}

async function fetchServices() {
  try {
    const res: any = await getClusterServices(clusterName.value, { namespace: svcNamespace.value })
    resources.value.services = res.data
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '加载失败')
  }
}

let activeLoadRef = ''
watch(clusterName, loadClusterDetail)

let timer: ReturnType<typeof setInterval> | null = null

onActivated(() => {
  loadClusterDetail()
  timer = setInterval(fetchResources, 30000)
})

onDeactivated(() => {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
})
</script>

<style scoped>
.surface-card {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
}

.detail-header {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  padding: 14px 16px;
  margin-bottom: 16px;
}

.detail-header-copy {
  min-width: 0;
}

.detail-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.detail-title {
  margin: 0;
}

.detail-meta {
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
  margin-top: 8px;
  color: var(--text-secondary);
  font-size: 12px;
}

.detail-header-actions {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

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
  color: var(--danger-color);
  font-size: 13px;
}

.warning-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  margin-bottom: 16px;
  background: color-mix(in srgb, var(--warning-color) 10%, white);
  border: 1px solid color-mix(in srgb, var(--warning-color) 24%, white);
  border-radius: var(--border-radius);
  color: #8a5a08;
  font-size: 13px;
  font-weight: 600;
}

.warning-meta {
  color: var(--text-secondary);
  font-weight: 500;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.summary-card {
  padding: 14px 16px;
}

.summary-label {
  color: var(--text-muted);
  font-size: 12px;
  margin-bottom: 8px;
}

.summary-value {
  color: var(--text-primary);
  font-size: 24px;
  font-weight: 750;
}

.summary-foot {
  margin-top: 4px;
  color: var(--text-secondary);
  font-size: 12px;
}

.workbench-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.45fr) minmax(280px, 0.92fr);
  gap: 16px;
}

.workbench-main {
  overflow: hidden;
}

.tabs-row {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 0 18px;
  border-bottom: 1px solid var(--border-color);
}

.tab-button {
  height: 42px;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 600;
  border-bottom: 2px solid transparent;
  cursor: pointer;
}

.tab-button.active {
  color: var(--primary-color);
  border-bottom-color: var(--primary-color);
}

.section-body {
  padding: 14px 18px 16px;
}

.tool-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.tool-select {
  width: 160px;
}

.tool-search {
  width: 260px;
}

.tool-count {
  margin-left: auto;
  color: var(--text-muted);
  font-size: 13px;
}

.resource-primary {
  display: grid;
  gap: 4px;
}

.resource-primary strong {
  color: var(--text-primary);
}

.resource-primary span {
  color: var(--text-muted);
  font-size: 12px;
}

.workbench-side {
  display: grid;
  gap: 16px;
}

.side-card {
  padding: 16px;
}

.side-card-head {
  display: grid;
  gap: 3px;
  margin-bottom: 12px;
}

.side-card-head h3 {
  margin: 0;
  font-size: 14px;
}

.side-card-subtitle {
  color: var(--text-secondary);
  font-size: 12px;
}

.side-list {
  display: grid;
  gap: 10px;
}

.side-item {
  display: grid;
  gap: 6px;
  padding: 12px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
}

.side-item-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.side-item span {
  color: var(--text-secondary);
  font-size: 12px;
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

.dialog-header-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.dialog-header-actions {
  display: flex;
  gap: 8px;
}

.log-box {
  min-height: 320px;
  max-height: 560px;
  margin: 0;
  padding: 14px;
  overflow: auto;
  color: var(--log-fg, #d1d5db);
  background: var(--log-bg, #111827);
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

@media (max-width: 1200px) {
  .workbench-grid {
    grid-template-columns: 1fr;
  }

  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .detail-header,
  .warning-banner {
    grid-template-columns: 1fr;
    align-items: stretch;
  }

  .detail-header,
  .warning-banner,
  .tool-row {
    flex-direction: column;
  }

  .detail-header-actions,
  .tool-select,
  .tool-search,
  .tool-count {
    width: 100%;
  }

  .summary-grid {
    grid-template-columns: 1fr;
  }

  .tool-count {
    margin-left: 0;
  }
}
</style>
