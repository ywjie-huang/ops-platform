<template>
  <div>
    <div class="page-header"><h2 class="page-title">工单协作</h2><el-button type="primary" @click="showDialog()">+ 新增工单</el-button></div>
    <div class="filter-bar">
      <el-input v-model="filters.keyword" placeholder="搜索…" clearable style="width:200px" @keyup.enter="fetchData" />
      <el-select v-model="filters.status" placeholder="状态" clearable style="width:120px" @change="fetchData">
        <el-option v-for="s in ['open','in_progress','resolved','closed']" :key="s" :label="s" :value="s" />
      </el-select>
      <el-button @click="fetchData">筛选</el-button>
    </div>
    <div class="data-card">
      <el-table :data="items" stripe v-loading="loading">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="title" label="标题"><template #default="{row}"><strong>{{ row.title }}</strong></template></el-table-column>
        <el-table-column prop="priority" label="优先级" width="90"><template #default="{row}"><el-tag :type="priorityType(row.priority)" size="small">{{ row.priority }}</el-tag></template></el-table-column>
        <el-table-column prop="status" label="状态" width="110"><template #default="{row}"><el-tag :type="statusType(row.status)" size="small">{{ row.status }}</el-tag></template></el-table-column>
        <el-table-column prop="assignee" label="指派人" width="100" />
        <el-table-column label="操作" width="180">
          <template #default="{row}">
            <el-button size="small" text type="primary" @click="$router.push(`/tickets/${row.id}`)">详情</el-button>
            <el-button size="small" text type="primary" @click="showDialog(row)">编辑</el-button>
            <el-popconfirm title="确认删除？" @confirm="handleDelete(row.id)">
              <template #reference><el-button size="small" text type="danger">删除</el-button></template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-wrap"><el-pagination v-model:current-page="currentPage" v-model:page-size="pageSize" :page-sizes="[10,20,50]" :total="total" :layout="paginationLayout" @current-change="handleCurrentChange" @size-change="handleSizeChange" /></div>
    </div>
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑工单' : '新增工单'" width="520px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="标题"><el-input v-model="form.title" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="form.description" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="优先级"><el-select v-model="form.priority" style="width:100%"><el-option v-for="p in ['low','normal','high','critical']" :key="p" :label="p" :value="p" /></el-select></el-form-item>
        <el-form-item label="状态"><el-select v-model="form.status" style="width:100%"><el-option v-for="s in ['open','in_progress','resolved','closed']" :key="s" :label="s" :value="s" /></el-select></el-form-item>
        <el-form-item label="指派人"><el-input v-model="form.assignee" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="dialogVisible = false">取消</el-button><el-button type="primary" @click="handleSave">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { getTickets, createTicket, updateTicket, deleteTicket } from '@/api/tickets'
import { usePagination } from '@/hooks/usePagination'
import { ElMessage } from 'element-plus'

const loading = ref(false); const items = ref<any[]>([])
const { currentPage, pageSize, total, paginationLayout, handleCurrentChange, handleSizeChange } = usePagination(fetchData)
const dialogVisible = ref(false); const editingId = ref<number | null>(null)
const filters = reactive({ keyword: '', status: '' })
const form = reactive({ title: '', description: '', priority: 'normal', status: 'open', assignee: '' })
const priorityType = (p: string) => ({ low: 'info', normal: '', high: 'warning', critical: 'danger' }[p] || '') as any
const statusType = (s: string) => ({ open: 'primary', in_progress: 'warning', resolved: 'success', closed: 'info' }[s] || '') as any

async function fetchData(extra?: any) {
  loading.value = true
  try {
    const params = { ...filters, page: extra?.page || currentPage.value, page_size: extra?.page_size || pageSize.value }
    const res: any = await getTickets(params); items.value = res.data.items; total.value = res.data.total
  } finally { loading.value = false }
}
function showDialog(row?: any) { editingId.value = row?.id || null; Object.assign(form, row || { title: '', description: '', priority: 'normal', status: 'open', assignee: '' }); dialogVisible.value = true }
async function handleSave() { if (editingId.value) { await updateTicket(editingId.value, form); ElMessage.success('更新成功') } else { await createTicket(form); ElMessage.success('创建成功') }; dialogVisible.value = false; fetchData() }
async function handleDelete(id: number) { await deleteTicket(id); ElMessage.success('删除成功'); fetchData() }
onMounted(fetchData)
</script>

<style scoped>.pagination-wrap { display: flex; justify-content: flex-end; margin-top: 16px; }</style>
