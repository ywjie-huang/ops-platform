<template>
  <div>
    <div class="page-header">
      <h2 class="page-title">主机管理</h2>
      <el-button type="primary" @click="showDialog()">+ 新增资产</el-button>
    </div>
    <div class="filter-bar">
      <el-input v-model="filters.keyword" placeholder="搜索名称/IP…" clearable style="width:220px" @keyup.enter="fetchData" />
      <el-select v-model="filters.asset_type" placeholder="类型" clearable style="width:120px" @change="fetchData">
        <el-option v-for="t in assetTypes" :key="t" :label="t" :value="t" />
      </el-select>
      <el-select v-model="filters.status" placeholder="状态" clearable style="width:120px" @change="fetchData">
        <el-option v-for="s in statusList" :key="s.value" :label="s.label" :value="s.value" />
      </el-select>
      <el-button @click="fetchData">筛选</el-button>
      <el-button text @click="resetFilters">重置</el-button>
    </div>
    <div class="data-card">
      <el-table :data="items" stripe v-loading="loading">
        <el-table-column prop="id" label="ID" width="60" />

        <el-table-column label="主机信息" min-width="180">
          <template #default="{ row }">
            <div class="cell-stack">
              <span class="cell-primary">{{ row.name }}</span>
              <span class="cell-secondary">{{ row.ip_address }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="主机规格" min-width="150">
          <template #default="{ row }">
            <div class="cell-stack">
              <span class="cell-primary">{{ row.spec || '-' }}</span>
              <span class="cell-secondary">{{ row.os || '-' }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" size="small" round>{{ row.status }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="description" label="描述" min-width="160" show-overflow-tooltip />

        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <div class="action-cell">
              <el-button size="small" type="primary" link @click="$router.push(`/monitoring/hosts/${row.id}/ssh`)">
                <el-icon><Monitor /></el-icon> SSH
              </el-button>
              <el-button size="small" type="info" link @click="$router.push(`/assets/${row.id}`)">详情</el-button>
              <el-popconfirm title="确认删除该资产？" @confirm="handleDelete(row.id)">
                <template #reference>
                  <el-button size="small" type="danger" link>删除</el-button>
                </template>
              </el-popconfirm>
            </div>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50]"
          :total="total"
          :layout="paginationLayout"
          @current-change="handleCurrentChange"
          @size-change="handleSizeChange"
        />
      </div>
    </div>

    <el-dialog v-model="dialogVisible" title="新增资产" width="580px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="名称" prop="name"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="类型" prop="asset_type">
          <el-select v-model="form.asset_type" style="width:100%">
            <el-option v-for="t in assetTypes" :key="t" :label="t" :value="t" />
          </el-select>
        </el-form-item>
        <el-form-item label="IP" prop="ip_address"><el-input v-model="form.ip_address" /></el-form-item>
        <el-form-item label="规格"><el-input v-model="form.spec" placeholder="如 4C8G" /></el-form-item>
        <el-form-item label="系统"><el-input v-model="form.os" placeholder="如 Ubuntu 22.04" /></el-form-item>
        <el-form-item label="状态" prop="status">
          <el-select v-model="form.status" style="width:100%">
            <el-option v-for="s in statusList" :key="s.value" :label="s.label" :value="s.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="负责人"><el-input v-model="form.owner" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="form.description" type="textarea" :rows="2" /></el-form-item>
        <el-divider content-position="left">SSH 配置</el-divider>
        <el-form-item label="SSH 端口"><el-input-number v-model="form.ssh_port" :min="1" :max="65535" style="width:100%" /></el-form-item>
        <el-form-item label="SSH 用户名"><el-input v-model="form.ssh_username" placeholder="root" /></el-form-item>
        <el-form-item label="SSH 密码"><el-input v-model="form.ssh_password" type="password" show-password placeholder="请输入 SSH 密码" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getAssets, createAsset, deleteAsset } from '@/api/assets'
import { usePagination } from '@/hooks/usePagination'
import { ElMessage, ElMessageBox, type FormInstance } from 'element-plus'
import { Monitor } from '@element-plus/icons-vue'

const router = useRouter()
const loading = ref(false)
const saving = ref(false)
const items = ref<any[]>([])
const dialogVisible = ref(false)
const formRef = ref<FormInstance>()

const assetTypes = ['云主机', '数据库', '网络设备', '中间件', '其他']
const statusList = [
  { label: '使用中', value: '使用中' },
  { label: '已关机', value: '已关机' },
  { label: '已删除', value: '已删除' },
]

function statusTagType(status: string) {
  const map: Record<string, string> = { '使用中': 'success', '已关机': 'warning', '已删除': 'info' }
  return map[status] || 'info'
}

const { currentPage, pageSize, total, paginationLayout, handleCurrentChange, handleSizeChange, resetPagination } = usePagination(fetchData)

const filters = reactive({ keyword: '', asset_type: '', status: '' })
const form = reactive({
  name: '', asset_type: '云主机', ip_address: '', status: '使用中', owner: '', description: '',
  spec: '', os: '', ssh_port: 22, ssh_username: 'root', ssh_password: '',
})
const rules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  asset_type: [{ required: true, message: '请选择类型', trigger: 'change' }],
  ip_address: [{ required: true, message: '请输入IP', trigger: 'blur' }],
  status: [{ required: true, message: '请选择状态', trigger: 'change' }],
}

async function fetchData(extra?: any) {
  loading.value = true
  try {
    const params = { ...filters, page: extra?.page || currentPage.value, page_size: extra?.page_size || pageSize.value }
    const res: any = await getAssets(params)
    items.value = res.data.items
    total.value = res.data.total
  } finally { loading.value = false }
}

function resetFilters() {
  Object.assign(filters, { keyword: '', asset_type: '', status: '' })
  resetPagination()
  fetchData()
}

function showDialog() {
  Object.assign(form, {
    name: '', asset_type: '云主机', ip_address: '', status: '使用中', owner: '', description: '',
    spec: '', os: '', ssh_port: 22, ssh_username: 'root', ssh_password: '',
  })
  dialogVisible.value = true
}

async function handleSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    await createAsset(form)
    ElMessage.success('创建成功')
    dialogVisible.value = false
    fetchData()
  } finally { saving.value = false }
}

async function handleDelete(id: number) {
  await ElMessageBox.confirm('确认删除该资产？删除后关联的告警和工单将解除关联。', '确认删除', { type: 'warning' })
  await deleteAsset(id)
  ElMessage.success('删除成功')
  fetchData()
}

onMounted(fetchData)
</script>

<style scoped>
.cell-stack {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.cell-primary {
  font-weight: 600;
  font-size: 13px;
  color: var(--text-primary);
}
.cell-secondary {
  font-size: 12px;
  color: var(--text-muted);
}
.action-cell {
  display: flex;
  align-items: center;
  gap: 4px;
}
.pagination-wrap { display: flex; justify-content: flex-end; margin-top: 16px; }
</style>
