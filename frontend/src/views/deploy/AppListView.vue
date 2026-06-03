<template>
  <div>
    <div class="page-header">
      <h2 class="page-title">应用管理</h2>
      <el-button type="primary" @click="showDialog()">+ 注册应用</el-button>
    </div>
    <div class="filter-bar">
      <el-input v-model="filters.keyword" placeholder="搜索应用名称…" clearable style="width:200px" @keyup.enter="fetchData" />
      <el-select v-model="filters.deploy_method" placeholder="部署方式" clearable style="width:120px" @change="fetchData">
        <el-option label="Jenkins" value="jenkins" />
        <el-option label="Docker" value="docker" />
        <el-option label="Kubernetes" value="kubernetes" />
      </el-select>
      <el-select v-model="filters.status" placeholder="状态" clearable style="width:100px" @change="fetchData">
        <el-option label="活跃" value="active" />
        <el-option label="已归档" value="archived" />
      </el-select>
      <el-button @click="fetchData">筛选</el-button>
    </div>
    <div class="data-card">
      <el-table :data="items" stripe v-loading="loading">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column label="应用名称" min-width="160">
          <template #default="{row}">
            <strong>{{ row.display_name || row.name }}</strong>
            <div style="font-size: 12px; color: var(--text-muted);">{{ row.name }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="app_type" label="类型" width="80">
          <template #default="{row}"><el-tag size="small" :type="appTypeType(row.app_type)">{{ appTypeLabel(row.app_type) }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="deploy_method" label="部署方式" width="100">
          <template #default="{row}"><el-tag size="small" type="info">{{ row.deploy_method }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="repo_url" label="仓库地址" min-width="200" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{row}"><el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">{{ row.status === 'active' ? '活跃' : '已归档' }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="160">
          <template #default="{row}">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{row}">
            <el-button size="small" text type="primary" @click="$router.push(`/deploy/apps/${row.id}`)">详情</el-button>
            <el-button size="small" text type="primary" @click="showDialog(row)">编辑</el-button>
            <el-popconfirm title="确认删除该应用？" @confirm="handleDelete(row.id)">
              <template #reference><el-button size="small" text type="danger">删除</el-button></template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-wrap">
        <el-pagination v-model:current-page="currentPage" v-model:page-size="pageSize" :page-sizes="[10,20,50]" :total="total" :layout="paginationLayout" @current-change="handleCurrentChange" @size-change="handleSizeChange" />
      </div>
    </div>

    <!-- 新增/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑应用' : '注册应用'" width="520px" destroy-on-close>
      <el-form :model="form" label-width="90px">
        <el-form-item label="应用标识"><el-input v-model="form.name" placeholder="如 user-service" /></el-form-item>
        <el-form-item label="显示名称"><el-input v-model="form.display_name" placeholder="中文名称" /></el-form-item>
        <el-form-item label="应用类型">
          <el-select v-model="form.app_type" style="width:100%">
            <el-option label="后端" value="backend" />
            <el-option label="前端" value="frontend" />
            <el-option label="服务" value="service" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
        <el-form-item label="部署方式">
          <el-select v-model="form.deploy_method" style="width:100%">
            <el-option label="Jenkins" value="jenkins" />
            <el-option label="SSH 部署" value="ssh" />
            <el-option label="Docker" value="docker" />
            <el-option label="Kubernetes" value="kubernetes" />
          </el-select>
        </el-form-item>
        <el-form-item label="仓库地址"><el-input v-model="form.repo_url" placeholder="https://git.example.com/..." /></el-form-item>
        <el-form-item label="默认分支"><el-input v-model="form.repo_branch" placeholder="main" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="form.description" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { getDeployApps, createDeployApp, updateDeployApp, deleteDeployApp } from '@/api/deploy'
import { usePagination } from '@/hooks/usePagination'
import { ElMessage } from 'element-plus'

const loading = ref(false)
const items = ref<any[]>([])
const { currentPage, pageSize, total, paginationLayout, handleCurrentChange, handleSizeChange } = usePagination(fetchData)
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const filters = reactive({ keyword: '', deploy_method: '', status: '' })
const form = reactive({ name: '', display_name: '', app_type: 'backend', deploy_method: 'jenkins', repo_url: '', repo_branch: 'main', description: '' })

const appTypeType = (t: string) => ({ backend: '', frontend: 'success', service: 'warning', other: 'info' }[t] || '') as any
const appTypeLabel = (t: string) => ({ backend: '后端', frontend: '前端', service: '服务', other: '其他' }[t] || t)
const formatTime = (t: string) => t ? new Date(t).toLocaleString('zh-CN') : '-'

async function fetchData(extra?: any) {
  loading.value = true
  try {
    const params = { ...filters, page: extra?.page || currentPage.value, page_size: extra?.page_size || pageSize.value }
    const res: any = await getDeployApps(params)
    items.value = res.data.items
    total.value = res.data.total
  } finally { loading.value = false }
}

function showDialog(row?: any) {
  editingId.value = row?.id || null
  Object.assign(form, row || { name: '', display_name: '', app_type: 'backend', deploy_method: 'jenkins', repo_url: '', repo_branch: 'main', description: '' })
  dialogVisible.value = true
}

async function handleSave() {
  if (editingId.value) {
    await updateDeployApp(editingId.value, form)
    ElMessage.success('更新成功')
  } else {
    await createDeployApp(form)
    ElMessage.success('创建成功')
  }
  dialogVisible.value = false
  fetchData()
}

async function handleDelete(id: number) {
  await deleteDeployApp(id)
  ElMessage.success('删除成功')
  fetchData()
}

onMounted(fetchData)
</script>

<style scoped>
.pagination-wrap { display: flex; justify-content: flex-end; margin-top: 16px; }
</style>
