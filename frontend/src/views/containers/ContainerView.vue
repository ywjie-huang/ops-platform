<template>
  <div>
    <div class="page-header"><h2 class="page-title">容器管理</h2></div>

    <!-- 概览卡片 -->
    <el-row :gutter="16" style="margin-bottom:16px">
      <el-col :span="6" v-for="item in overviewCards" :key="item.label">
        <div class="stat-card">
          <div class="stat-label">{{ item.label }}</div>
          <div class="stat-value">{{ item.value }}</div>
        </div>
      </el-col>
    </el-row>

    <!-- 集群列表 -->
    <div class="data-card">
      <div class="filter-bar">
        <el-input v-model="keyword" placeholder="搜索集群…" clearable style="width:220px" @keyup.enter="fetchClusters" />
        <el-button type="primary" @click="handleCreate">接入集群</el-button>
      </div>

      <el-table :data="clusters" stripe v-loading="loading" @row-click="handleRowClick" style="cursor:pointer">
        <el-table-column prop="name" label="集群名称" min-width="140">
          <template #default="{row}">
            <strong>{{ row.name }}</strong>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="140">
          <template #default="{row}">
            <el-tooltip v-if="row.status === 'stopped' && row.status_message" :content="row.status_message" placement="top">
              <el-tag :type="statusType(row.status)" size="small">
                {{ row.status }} <el-icon style="vertical-align:-2px"><WarningFilled /></el-icon>
              </el-tag>
            </el-tooltip>
            <el-tag v-else :type="statusType(row.status)" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="version" label="K8s 版本" width="130" />
        <el-table-column prop="node_count" label="节点数" width="80" align="center" />
        <el-table-column prop="endpoint" label="API Server" min-width="220" show-overflow-tooltip />
        <el-table-column prop="description" label="说明" min-width="150" show-overflow-tooltip />
        <el-table-column prop="created_at" label="接入时间" width="170" />
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{row}">
            <el-button link type="primary" size="small" @click.stop="handleEdit(row)">编辑</el-button>
            <el-button link type="danger" size="small" @click.stop="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 接入/编辑集群弹窗 -->
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑 K8s 集群' : '接入 K8s 集群'" width="520px" destroy-on-close>
      <el-alert type="info" :closable="false" style="margin-bottom:16px">
        <template v-if="editingId">更新集群信息，Token 留空则保留原值。</template>
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

      <!-- 连接测试结果 -->
      <div v-if="testResult" style="margin-top:8px">
        <el-tag v-if="testResult.ok" type="success" size="large">
          ✅ 连接成功 · K8s {{ testResult.version }}
        </el-tag>
        <el-tag v-else type="danger" size="large">
          ❌ {{ testResult.error }}
        </el-tag>
      </div>

      <template #footer>
        <el-button :loading="testing" @click="handleTest">测试连接</el-button>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSubmit">{{ editingId ? '保存' : '接入' }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, type FormInstance } from 'element-plus'
import { WarningFilled } from '@element-plus/icons-vue'
import { getClusters, createCluster, updateCluster, deleteCluster, testConnection } from '@/api/containers'

const router = useRouter()
const loading = ref(false)
const saving = ref(false)
const testing = ref(false)
const keyword = ref('')
const clusters = ref<any[]>([])
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const testResult = ref<any>(null)
const formRef = ref<FormInstance>()

const form = reactive({ name: '', endpoint: '', token: '', description: '' })
const rules = {
  name: [{ required: true, message: '请输入集群名称', trigger: 'blur' }],
  endpoint: [{ required: true, message: '请输入 API Server 地址', trigger: 'blur' }],
}

const overviewCards = computed(() => {
  const total = clusters.value.length
  const running = clusters.value.filter(c => c.status === 'running').length
  const nodes = clusters.value.reduce((sum, c) => sum + (c.node_count || 0), 0)
  const versions = [...new Set(clusters.value.map(c => c.version).filter(Boolean))]
  return [
    { label: '集群总数', value: total },
    { label: '运行中', value: running },
    { label: '总节点数', value: nodes },
    { label: 'K8s 版本', value: versions.join(', ') || '-' },
  ]
})

function statusType(s: string) { return s === 'running' ? 'success' : s === 'stopped' ? 'danger' : 'warning' }

async function fetchClusters() {
  loading.value = true
  try {
    const res: any = await getClusters({ keyword: keyword.value })
    clusters.value = res.data
  } finally { loading.value = false }
}

function handleCreate() {
  editingId.value = null
  Object.assign(form, { name: '', endpoint: '', token: '', description: '' })
  testResult.value = null
  dialogVisible.value = true
}

function handleEdit(row: any) {
  editingId.value = row.id
  Object.assign(form, { name: row.name, endpoint: row.endpoint, token: '', description: row.description || '' })
  testResult.value = null
  dialogVisible.value = true
}

async function handleTest() {
  if (!form.endpoint) { ElMessage.warning('请先填写 API Server 地址'); return }
  testing.value = true
  testResult.value = null
  try {
    const res: any = await testConnection({ endpoint: form.endpoint, token: form.token })
    testResult.value = res.data
  } catch {
    testResult.value = { ok: false, error: '请求失败' }
  } finally { testing.value = false }
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    if (editingId.value) {
      await updateCluster(editingId.value, form)
      ElMessage.success('更新成功')
    } else {
      await createCluster(form)
      ElMessage.success('接入成功')
    }
    dialogVisible.value = false
    fetchClusters()
  } finally { saving.value = false }
}

async function handleDelete(row: any) {
  await ElMessageBox.confirm(`确定删除集群「${row.name}」？`, '删除确认', { type: 'warning' })
  await deleteCluster(row.id)
  ElMessage.success('删除成功')
  fetchClusters()
}

function handleRowClick(row: any) {
  router.push(`/assets/containers/${row.id}`)
}

onMounted(fetchClusters)
</script>

<style scoped>
.stat-card { background: #fff; border: 1px solid var(--border-color); border-radius: 8px; padding: 16px; }
.stat-label { font-size: 13px; color: var(--text-muted); }
.stat-value { font-size: 24px; font-weight: 700; }
</style>
