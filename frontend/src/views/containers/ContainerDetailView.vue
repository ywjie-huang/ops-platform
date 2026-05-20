<template>
  <div>
    <div class="page-header">
      <div style="display:flex;align-items:center;gap:12px">
        <el-button text @click="$router.push('/assets/containers')"><el-icon><ArrowLeft /></el-icon> 返回</el-button>
        <h2 class="page-title" style="margin:0">{{ cluster.name || '集群详情' }}</h2>
        <el-tag :type="statusType(cluster.status)" size="small">{{ cluster.status || 'unknown' }}</el-tag>
        <el-tag v-if="cluster.version" type="info" size="small">{{ cluster.version }}</el-tag>
        <el-tag v-if="cluster.status === 'stopped' && cluster.status_message" type="warning" size="small" effect="plain">
          {{ cluster.status_message }}
        </el-tag>
      </div>
      <el-button :loading="refreshing" @click="fetchResources">
        <el-icon><Refresh /></el-icon> 刷新
      </el-button>
    </div>

    <!-- 集群概览 -->
    <el-row :gutter="16" style="margin-bottom:16px">
      <el-col :span="4" v-for="item in statCards" :key="item.label">
        <div class="stat-card">
          <div class="stat-label">{{ item.label }}</div>
          <div class="stat-value" :style="{ color: item.color }">{{ item.value }}</div>
        </div>
      </el-col>
    </el-row>

    <!-- 资源 Tabs -->
    <div class="data-card" v-loading="refreshing">
      <el-tabs v-model="activeTab">
        <!-- Namespaces -->
        <el-tab-pane label="命名空间" name="namespaces">
          <el-table :data="pagedNamespaces" stripe>
            <el-table-column prop="name" label="Namespace" min-width="180" />
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

        <!-- Nodes -->
        <el-tab-pane label="节点" name="nodes">
          <el-table :data="pagedNodes" stripe>
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
            <el-input v-model="podSearch" placeholder="搜索 Pod…" clearable style="width:220px" />
            <span style="margin-left:auto;color:var(--text-muted);font-size:13px">
              共 {{ filteredPods.length }} 个 Pod
            </span>
          </div>
          <el-table :data="pagedPods" stripe>
            <el-table-column prop="name" label="名称" min-width="260" show-overflow-tooltip />
            <el-table-column prop="namespace" label="Namespace" width="110" />
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
                <span :style="{ color: row.restarts > 5 ? 'var(--el-color-danger)' : '' }">{{ row.restarts }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="创建时间" width="170">
              <template #default="{row}">{{ formatTime(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="120" fixed="right">
              <template #default="{row}">
                <el-button link type="primary" size="small" @click="openPodLogs(row)">日志</el-button>
                <el-button link type="info" size="small" @click="openPodEvents(row)">事件</el-button>
                <el-button link type="danger" size="small" @click="confirmDeletePod(row)">删除</el-button>
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
            <span style="margin-left:auto;color:var(--text-muted);font-size:13px">
              共 {{ filteredDeployments.length }} 个 Deployment
            </span>
          </div>
          <el-table :data="pagedDeployments" stripe>
            <el-table-column prop="name" label="名称" min-width="200" />
            <el-table-column prop="namespace" label="Namespace" width="110" />
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
                <span :style="{ color: row.ready_replicas < row.replicas ? 'var(--el-color-warning)' : '' }">
                  {{ row.ready_replicas }} / {{ row.replicas }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="创建时间" width="170">
              <template #default="{row}">{{ formatTime(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="90" fixed="right">
              <template #default="{row}">
                <el-button link type="warning" size="small" @click="confirmRestartDeployment(row)">重启</el-button>
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
            <span style="margin-left:auto;color:var(--text-muted);font-size:13px">
              共 {{ filteredServices.length }} 个 Service
            </span>
          </div>
          <el-table :data="pagedServices" stripe>
            <el-table-column prop="name" label="名称" min-width="200" />
            <el-table-column prop="namespace" label="Namespace" width="110" />
            <el-table-column prop="service_type" label="类型" width="120">
              <template #default="{row}"><el-tag size="small">{{ row.service_type }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="cluster_ip" label="Cluster IP" width="140" />
            <el-table-column prop="ports" label="端口" min-width="180" show-overflow-tooltip />
            <el-table-column prop="selector" label="Selector" min-width="180" show-overflow-tooltip />
            <el-table-column prop="created_at" label="创建时间" width="170">
              <template #default="{row}">{{ formatTime(row.created_at) }}</template>
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

    <el-dialog v-model="logsDialogVisible" :title="podDialogTitle('日志')" width="820px">
      <div v-loading="logsLoading">
        <pre class="log-box">{{ podLogs || '暂无日志' }}</pre>
      </div>
    </el-dialog>

    <el-dialog v-model="eventsDialogVisible" :title="podDialogTitle('事件')" width="900px">
      <el-table :data="podEvents" stripe v-loading="eventsLoading">
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
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Refresh } from '@element-plus/icons-vue'
import { getCluster, getClusterResources, getClusterPods, getClusterServices, getClusterDeployments, getPodLogs, getPodEvents, deleteClusterPod, restartClusterDeployment } from '@/api/containers'

const route = useRoute()
const clusterId = ref(Number(route.params.id))
const cluster = ref<any>({})
const resources = ref<any>({})
const refreshing = ref(false)
const activeTab = ref('namespaces')
const selectedPod = ref<any>(null)
const logsDialogVisible = ref(false)
const eventsDialogVisible = ref(false)
const logsLoading = ref(false)
const eventsLoading = ref(false)
const podLogs = ref('')
const podEvents = ref<any[]>([])

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

// 过滤后的数据
const filteredPods = computed(() => {
  let list = resources.value.pods || []
  if (podSearch.value) {
    const kw = podSearch.value.toLowerCase()
    list = list.filter((p: any) => p.name.toLowerCase().includes(kw))
  }
  return list
})

const filteredDeployments = computed(() => {
  let list = resources.value.deployments || []
  if (depSearch.value) {
    const kw = depSearch.value.toLowerCase()
    list = list.filter((d: any) => d.name.toLowerCase().includes(kw))
  }
  return list
})

const filteredServices = computed(() => {
  let list = resources.value.services || []
  if (svcSearch.value) {
    const kw = svcSearch.value.toLowerCase()
    list = list.filter((s: any) => s.name.toLowerCase().includes(kw))
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

// 统计卡片
const statCards = computed(() => {
  const r = resources.value
  return [
    { label: '节点', value: r.node_count ?? '-', color: '' },
    { label: '就绪节点', value: r.ready_nodes ?? '-', color: r.ready_nodes === r.node_count ? 'var(--el-color-success)' : 'var(--el-color-warning)' },
    { label: 'Pods', value: r.pod_count ?? '-', color: '' },
    { label: 'Deployments', value: r.deployment_count ?? '-', color: '' },
    { label: 'Services', value: r.service_count ?? '-', color: '' },
    { label: '命名空间', value: r.namespace_count ?? '-', color: '' },
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

async function openPodLogs(row: any) {
  selectedPod.value = row
  podLogs.value = ''
  logsDialogVisible.value = true
  logsLoading.value = true
  try {
    const res: any = await getPodLogs(clusterId.value, row.namespace, row.name, { tail_lines: 300 })
    podLogs.value = res.data?.logs || ''
  } finally { logsLoading.value = false }
}

async function openPodEvents(row: any) {
  selectedPod.value = row
  podEvents.value = []
  eventsDialogVisible.value = true
  eventsLoading.value = true
  try {
    const res: any = await getPodEvents(clusterId.value, row.namespace, row.name)
    podEvents.value = res.data || []
  } finally { eventsLoading.value = false }
}

async function confirmDeletePod(row: any) {
  try {
    await ElMessageBox.confirm(
      `确定删除 Pod ${row.namespace}/${row.name} 吗？如由 Deployment/StatefulSet 管理，控制器通常会自动重建。`,
      '删除 Pod',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
    await deleteClusterPod(clusterId.value, row.namespace, row.name)
    ElMessage.success('Pod 删除成功')
    await fetchResources()
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '操作失败') }
}

async function confirmRestartDeployment(row: any) {
  try {
    await ElMessageBox.confirm(
      `确定滚动重启 Deployment ${row.namespace}/${row.name} 吗？`,
      '重启 Deployment',
      { type: 'warning', confirmButtonText: '重启', cancelButtonText: '取消' },
    )
    await restartClusterDeployment(clusterId.value, row.namespace, row.name)
    ElMessage.success('Deployment 重启已触发')
    await fetchDeployments()
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '操作失败') }
}

// Fetch
async function fetchCluster() {
  try { const res: any = await getCluster(clusterId.value); cluster.value = res.data } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '加载失败') }
}

async function fetchResources() {
  refreshing.value = true
  try {
    const res: any = await getClusterResources(clusterId.value)
    resources.value = res.data
    // 更新集群元数据
    cluster.value.status = res.data.connected ? 'running' : 'stopped'
    cluster.value.status_message = res.data.connected ? '' : (res.data.error || '连接失败')
    cluster.value.version = res.data.version || cluster.value.version
    cluster.value.node_count = res.data.node_count ?? cluster.value.node_count
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '加载失败') } finally { refreshing.value = false }
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

onMounted(() => { fetchCluster(); fetchResources() })
</script>

<style scoped>
.stat-card { background: #fff; border: 1px solid var(--border-color); border-radius: 8px; padding: 12px 16px; text-align: center; }
.stat-label { font-size: 12px; color: var(--text-muted); margin-bottom: 4px; }
.stat-value { font-size: 22px; font-weight: 700; }
.pagination-wrap { display: flex; justify-content: flex-end; margin-top: 16px; }
.log-box {
  min-height: 320px;
  max-height: 560px;
  margin: 0;
  padding: 14px;
  overflow: auto;
  color: #d1d5db;
  background: #111827;
  border-radius: 8px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
