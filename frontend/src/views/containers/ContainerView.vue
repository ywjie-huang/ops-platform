<template>
  <div>
    <div class="page-header cluster-header">
      <div>
        <h2 class="page-title">K8s 集群</h2>
        <p class="page-subtitle">先定位需要处理的集群，再进入单集群工作台查看资源与异常。</p>
      </div>
      <div class="header-actions">
        <el-input
          v-model="keyword"
          placeholder="搜索集群"
          clearable
          class="search-input"
          aria-label="搜索 K8s 集群"
          @keyup.enter="fetchClusters"
        />
        <el-button size="small" :loading="loading" @click="fetchClusters">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
        <el-button type="primary" size="small" @click="handleCreate">接入集群</el-button>
      </div>
    </div>

    <div class="summary-grid" role="region" aria-label="K8s 集群总览">
      <div v-for="item in overviewCards" :key="item.label" class="summary-card">
        <div class="summary-label">{{ item.label }}</div>
        <div class="summary-value">{{ item.value }}</div>
        <div class="summary-foot">{{ item.foot }}</div>
      </div>
    </div>

    <div v-if="riskBannerText" class="warning-banner" role="alert">
      <span>{{ riskBannerText }}</span>
      <span class="warning-meta">按风险排序</span>
    </div>

    <div class="table-card">
      <div class="table-meta">
        <span>默认优先展示连接异常和资源异常的集群。</span>
        <span>共 {{ sortedClusters.length }} 个集群</span>
      </div>
      <div class="table-wrapper">
        <el-table :data="sortedClusters" v-loading="loading" stripe class="cluster-table" @row-click="handleRowClick">
          <el-table-column label="集群" min-width="240" fixed>
            <template #default="{ row }">
              <div class="cluster-cell">
                <div class="cluster-copy">
                  <strong>{{ row.name }}</strong>
                  <span>{{ row.version || '-' }} · {{ row.description || row.endpoint || '未填写说明' }}</span>
                </div>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="120">
            <template #default="{ row }">
              <el-tooltip v-if="row.status === 'stopped' && row.status_message" :content="row.status_message" placement="top">
                <el-tag :type="statusType(row.status)" size="small">
                  <span class="tag-dot" :class="row.status === 'running' ? 'dot-success' : 'dot-danger'" aria-hidden="true"></span>
                  {{ row.status === 'running' ? '运行中' : '连接异常' }}
                </el-tag>
              </el-tooltip>
              <el-tag v-else :type="statusType(row.status)" size="small">
                <span class="tag-dot" :class="row.status === 'running' ? 'dot-success' : 'dot-warning'" aria-hidden="true"></span>
                {{ row.status === 'running' ? '运行中' : '待处理' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="节点" min-width="130">
            <template #default="{ row }">
              <div class="metric-cell">
                <strong>{{ row.ready_nodes ?? row.node_count ?? 0 }} / {{ row.node_count ?? 0 }}</strong>
                <span>{{ nodeHint(row) }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="异常工作负载" min-width="180">
            <template #default="{ row }">
              <div class="metric-cell">
                <strong>{{ workloadSummary(row).primary }}</strong>
                <span>{{ workloadSummary(row).secondary }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="连接信息" min-width="220" show-overflow-tooltip>
            <template #default="{ row }">
              <div class="metric-cell">
                <strong class="mono">{{ row.endpoint || '-' }}</strong>
                <span>{{ row.status_message || '连接正常' }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="最近更新" width="170">
            <template #default="{ row }">
              <div class="metric-cell">
                <strong>{{ formatTime(row.updated_at || row.created_at) }}</strong>
                <span>{{ row.created_at ? '已接入平台' : '等待同步' }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="140" fixed="right" align="right">
            <template #default="{ row }">
              <div class="row-actions">
                <el-button link type="primary" size="small" @click.stop="handleEdit(row)">编辑</el-button>
                <el-button link type="primary" size="small" @click.stop="handleRowClick(row)">进入</el-button>
                <el-button link type="danger" size="small" @click.stop="handleDelete(row)">删除</el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <el-dialog v-model="dialogVisible" :title="editingName ? '编辑 K8s 集群' : '接入 K8s 集群'" width="520px" destroy-on-close>
      <el-alert type="info" :closable="false" style="margin-bottom: 16px">
        <template v-if="editingName">更新集群信息，Token 留空则保留原值。</template>
        <template v-else>填入 K8s API Server 地址和 ServiceAccount Token，系统将自动测试连接并发现集群资源。</template>
      </el-alert>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
        <el-form-item label="集群名称" prop="name">
          <el-input v-model="form.name" placeholder="例：prod-k8s" />
        </el-form-item>
        <el-form-item label="API Server" prop="endpoint">
          <el-input v-model="form.endpoint" placeholder="例：https://10.0.0.1:6443" />
        </el-form-item>
        <el-form-item label="Token">
          <el-input v-model="form.token" type="textarea" :rows="4" placeholder="ServiceAccount Bearer Token（可选，不填则只保存集群信息）" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="form.description" placeholder="备注信息" />
        </el-form-item>
      </el-form>

      <div v-if="testResult" class="test-result">
        <el-tag v-if="testResult.ok" type="success" size="large">✅ 连接成功 · K8s {{ testResult.version }}</el-tag>
        <el-tag v-else type="danger" size="large">❌ {{ testResult.error }}</el-tag>
      </div>

      <template #footer>
        <el-button :loading="testing" @click="handleTest">测试连接</el-button>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSubmit">{{ editingName ? '保存' : '接入' }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, type FormInstance } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { createCluster, deleteCluster, getClusters, testConnection, updateCluster } from '@/api/containers'
import { buildClusterOverview, sortClustersByRisk } from '@/utils/k8sCluster'

type ClusterRow = {
  id: number
  name: string
  status: string
  status_message?: string
  version?: string
  endpoint?: string
  node_count?: number
  ready_nodes?: number
  abnormal_pod_count?: number
  deployment_gap_count?: number
  description?: string
  created_at?: string
  updated_at?: string
}

const router = useRouter()
const loading = ref(false)
const saving = ref(false)
const testing = ref(false)
const keyword = ref('')
const clusters = ref<ClusterRow[]>([])
const dialogVisible = ref(false)
const editingName = ref('')
const testResult = ref<any>(null)
const formRef = ref<FormInstance>()

const form = reactive({ name: '', endpoint: '', token: '', description: '' })
const rules = {
  name: [{ required: true, message: '请输入集群名称', trigger: 'blur' }],
  endpoint: [{ required: true, message: '请输入 API Server 地址', trigger: 'blur' }],
}

const sortedClusters = computed(() => sortClustersByRisk(clusters.value))
const overviewCards = computed(() => buildClusterOverview(sortedClusters.value))

const riskBannerText = computed(() => {
  const risky = sortedClusters.value.filter((item) => item.status !== 'running' || (item.abnormal_pod_count ?? 0) > 0 || (item.deployment_gap_count ?? 0) > 0)
  if (!risky.length) return ''
  const first = risky[0]
  if (first.status !== 'running') return `当前建议优先处理：${first.name} 连接异常。`
  const workload = workloadSummary(first)
  return `当前建议优先处理：${first.name} ${workload.primary}，${workload.secondary}。`
})

function statusType(status: string) {
  return status === 'running' ? 'success' : status === 'stopped' ? 'danger' : 'warning'
}

function nodeHint(row: ClusterRow) {
  const notReady = Math.max((row.node_count ?? 0) - (row.ready_nodes ?? row.node_count ?? 0), 0)
  return notReady > 0 ? `${notReady} 个节点未就绪` : '节点状态正常'
}

function workloadSummary(row: ClusterRow) {
  const abnormalPods = row.abnormal_pod_count ?? 0
  const deploymentGaps = row.deployment_gap_count ?? 0
  if (!abnormalPods && !deploymentGaps) {
    return { primary: '未提供异常摘要', secondary: '进入详情查看实时资源' }
  }
  return {
    primary: `${abnormalPods} 个异常 Pod`,
    secondary: `${deploymentGaps} 个 Deployment 副本不足`,
  }
}

function formatTime(value?: string) {
  if (!value) return '-'
  try {
    return new Date(value).toLocaleString('zh-CN')
  } catch {
    return value
  }
}

async function fetchClusters() {
  loading.value = true
  try {
    const res: any = await getClusters({ keyword: keyword.value })
    clusters.value = res.data || []
  } finally {
    loading.value = false
  }
}

function handleCreate() {
  editingName.value = ''
  Object.assign(form, { name: '', endpoint: '', token: '', description: '' })
  testResult.value = null
  dialogVisible.value = true
}

function handleEdit(row: ClusterRow) {
  editingName.value = row.name
  Object.assign(form, { name: row.name, endpoint: row.endpoint || '', token: '', description: row.description || '' })
  testResult.value = null
  dialogVisible.value = true
}

async function handleTest() {
  if (!form.endpoint) {
    ElMessage.warning('请先填写 API Server 地址')
    return
  }
  testing.value = true
  testResult.value = null
  try {
    const res: any = await testConnection({ endpoint: form.endpoint, token: form.token })
    testResult.value = res.data
  } catch {
    testResult.value = { ok: false, error: '请求失败' }
  } finally {
    testing.value = false
  }
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    if (editingName.value) {
      await updateCluster(editingName.value, form)
      ElMessage.success('更新成功')
    } else {
      await createCluster(form)
      ElMessage.success('接入成功')
    }
    dialogVisible.value = false
    await fetchClusters()
  } finally {
    saving.value = false
  }
}

async function handleDelete(row: ClusterRow) {
  await ElMessageBox.confirm(`确定删除集群「${row.name}」？`, '删除确认', { type: 'warning' })
  await deleteCluster(row.name)
  ElMessage.success('删除成功')
  await fetchClusters()
}

function handleRowClick(row: ClusterRow) {
  router.push({ name: 'ContainerDetail', params: { name: row.name } })
}

onMounted(fetchClusters)
</script>

<style scoped>
.cluster-header {
  align-items: flex-start;
}

.page-subtitle {
  margin: 5px 0 0;
  color: var(--text-secondary);
  font-size: 13px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.search-input {
  width: 220px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.summary-card {
  min-width: 0;
  padding: 14px 16px;
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
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
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
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
  border-bottom: 1px solid var(--border-color);
  color: var(--text-secondary);
  font-size: 12px;
}

.cluster-table {
  cursor: pointer;
}

.cluster-cell {
  display: flex;
  align-items: center;
  min-width: 0;
}

.cluster-copy {
  min-width: 0;
  display: grid;
  gap: 4px;
}

.cluster-copy strong,
.cluster-copy span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cluster-copy span {
  color: var(--text-muted);
  font-size: 12px;
}

.metric-cell {
  display: grid;
  gap: 4px;
}

.metric-cell strong {
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 700;
}

.metric-cell span {
  color: var(--text-muted);
  font-size: 12px;
}

.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.row-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 4px;
}

.tag-dot {
  display: inline-block;
  width: 7px;
  height: 7px;
  margin-right: 5px;
  border-radius: 50%;
}

.dot-success {
  background: var(--success-color);
}

.dot-warning {
  background: var(--warning-color);
}

.dot-danger {
  background: var(--danger-color);
}

.test-result {
  margin-top: 8px;
}

@media (max-width: 1200px) {
  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .cluster-header,
  .table-meta {
    align-items: stretch;
    flex-direction: column;
  }

  .header-actions,
  .search-input {
    width: 100%;
  }

  .summary-grid {
    grid-template-columns: 1fr;
  }

  .warning-banner {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
