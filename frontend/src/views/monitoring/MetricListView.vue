<template>
  <div>
    <div class="page-header"><h2 class="page-title">监控指标</h2><el-button type="primary" @click="showDialog()">+ 新增指标</el-button></div>
    <div class="data-card">
      <el-table :data="items" stripe v-loading="loading">
        <el-table-column prop="name" label="名称"><template #default="{row}"><strong>{{ row.name }}</strong></template></el-table-column>
        <el-table-column prop="code" label="编码"><template #default="{row}"><code>{{ row.code }}</code></template></el-table-column>
        <el-table-column prop="unit" label="单位" width="80" />
        <el-table-column prop="category" label="分类" width="100" />
        <el-table-column prop="warning_threshold" label="告警阈值" width="100" />
        <el-table-column prop="critical_threshold" label="严重阈值" width="100" />
        <el-table-column label="操作" width="140">
          <template #default="{row}">
            <el-button size="small" text type="primary" @click="showDialog(row)">编辑</el-button>
            <el-popconfirm v-if="!row.is_system" title="确认删除？" @confirm="handleDelete(row.id)">
              <template #reference><el-button size="small" text type="danger">删除</el-button></template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </div>
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑指标' : '新增指标'" width="500px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="编码"><el-input v-model="form.code" :disabled="!!editingId" /></el-form-item>
        <el-form-item label="单位"><el-input v-model="form.unit" /></el-form-item>
        <el-form-item label="分类"><el-input v-model="form.category" /></el-form-item>
        <el-form-item label="告警阈值"><el-input v-model="form.warning_threshold" /></el-form-item>
        <el-form-item label="严重阈值"><el-input v-model="form.critical_threshold" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="dialogVisible = false">取消</el-button><el-button type="primary" @click="handleSave">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'; import { getMetrics, createMetric, updateMetric, deleteMetric } from '@/api/monitoring'; import { ElMessage } from 'element-plus'
const loading = ref(false); const items = ref<any[]>([]); const dialogVisible = ref(false); const editingId = ref<number | null>(null)
const form = reactive({ name: '', code: '', unit: '', category: '', warning_threshold: '', critical_threshold: '' })
async function fetchData() { loading.value = true; try { const res: any = await getMetrics(); items.value = res.data } finally { loading.value = false } }
function showDialog(row?: any) { editingId.value = row?.id || null; Object.assign(form, row || { name: '', code: '', unit: '', category: '', warning_threshold: '', critical_threshold: '' }); dialogVisible.value = true }
async function handleSave() { if (editingId.value) { await updateMetric(editingId.value, form); ElMessage.success('更新成功') } else { await createMetric(form); ElMessage.success('创建成功') }; dialogVisible.value = false; fetchData() }
async function handleDelete(id: number) { await deleteMetric(id); ElMessage.success('删除成功'); fetchData() }
onMounted(fetchData)
</script>
