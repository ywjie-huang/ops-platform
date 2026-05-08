<template>
  <div>
    <div class="page-header">
      <h2 class="page-title">主机管理</h2>
      <el-button type="primary" @click="showDialog()">+ 新增资产</el-button>
    </div>
    <div class="filter-bar">
      <el-input v-model="filters.keyword" placeholder="搜索名称/IP…" clearable style="width:220px" @keyup.enter="fetchData" />
      <el-select v-model="filters.asset_type" placeholder="类型" clearable style="width:120px" @change="fetchData">
        <el-option v-for="t in ['云主机','数据库','网络设备','中间件','其他']" :key="t" :label="t" :value="t" />
      </el-select>
      <el-select v-model="filters.status" placeholder="状态" clearable style="width:120px" @change="fetchData">
        <el-option v-for="s in ['在线','离线','维护中']" :key="s" :label="s" :value="s" />
      </el-select>
      <el-button @click="fetchData">筛选</el-button>
      <el-button text @click="resetFilters">重置</el-button>
    </div>
    <div class="data-card">
      <el-table :data="items" stripe v-loading="loading">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name" label="名称">
          <template #default="{ row }"><strong>{{ row.name }}</strong></template>
        </el-table-column>
        <el-table-column prop="asset_type" label="类型" />
        <el-table-column prop="ip_address" label="IP" />
        <el-table-column prop="status" label="状态">
          <template #default="{ row }">
            <el-tag :type="row.status === '在线' ? 'success' : row.status === '离线' ? 'danger' : 'warning'" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="owner" label="负责人" />
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button size="small" text type="primary" @click="$router.push(`/assets/${row.id}`)">详情</el-button>
            <el-button size="small" text type="primary" @click="showDialog(row)">编辑</el-button>
            <el-popconfirm title="确认删除？" @confirm="handleDelete(row.id)">
              <template #reference><el-button size="small" text type="danger">删除</el-button></template>
            </el-popconfirm>
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

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑资产' : '新增资产'" width="520px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="名称" prop="name"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="类型" prop="asset_type">
          <el-select v-model="form.asset_type" style="width:100%">
            <el-option v-for="t in ['云主机','数据库','网络设备','中间件','其他']" :key="t" :label="t" :value="t" />
          </el-select>
        </el-form-item>
        <el-form-item label="IP" prop="ip_address"><el-input v-model="form.ip_address" /></el-form-item>
        <el-form-item label="状态" prop="status">
          <el-select v-model="form.status" style="width:100%">
            <el-option v-for="s in ['在线','离线','维护中']" :key="s" :label="s" :value="s" />
          </el-select>
        </el-form-item>
        <el-form-item label="负责人"><el-input v-model="form.owner" /></el-form-item>
        <el-form-item label="说明"><el-input v-model="form.description" type="textarea" :rows="2" /></el-form-item>
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
import { getAssets, createAsset, updateAsset, deleteAsset } from '@/api/assets'
import { usePagination } from '@/hooks/usePagination'
import { ElMessage, type FormInstance } from 'element-plus'

const loading = ref(false)
const saving = ref(false)
const items = ref<any[]>([])
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const formRef = ref<FormInstance>()

const { currentPage, pageSize, total, paginationLayout, handleCurrentChange, handleSizeChange, resetPagination } = usePagination(fetchData)

const filters = reactive({ keyword: '', asset_type: '', status: '' })
const form = reactive({ name: '', asset_type: '云主机', ip_address: '', status: '在线', owner: '', description: '' })
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

function showDialog(row?: any) {
  editingId.value = row?.id || null
  Object.assign(form, row || { name: '', asset_type: '云主机', ip_address: '', status: '在线', owner: '', description: '' })
  dialogVisible.value = true
}

async function handleSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    if (editingId.value) {
      await updateAsset(editingId.value, form)
      ElMessage.success('更新成功')
    } else {
      await createAsset(form)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchData()
  } finally { saving.value = false }
}

async function handleDelete(id: number) {
  await deleteAsset(id)
  ElMessage.success('删除成功')
  fetchData()
}

onMounted(fetchData)
</script>

<style scoped>
.pagination-wrap { display: flex; justify-content: flex-end; margin-top: 16px; }
</style>
