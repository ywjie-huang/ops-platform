<template>
  <div>
    <div class="page-header"><h2 class="page-title">审计日志</h2></div>
    <div class="filter-bar">
      <el-input v-model="filters.keyword" placeholder="搜索…" clearable style="width:200px" @keyup.enter="fetchData" />
      <el-select v-model="filters.action" placeholder="操作类型" clearable style="width:120px" @change="fetchData">
        <el-option v-for="a in ['login','logout','create','update','delete']" :key="a" :label="a" :value="a" />
      </el-select>
      <el-select v-model="filters.target_type" placeholder="对象类型" clearable style="width:120px" @change="fetchData">
        <el-option v-for="t in ['auth','asset','user','role','ticket','alert']" :key="t" :label="t" :value="t" />
      </el-select>
      <el-button @click="fetchData">筛选</el-button>
    </div>
    <div class="data-card">
      <el-table :data="items" stripe v-loading="loading">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="user" label="操作人" width="100" />
        <el-table-column prop="action" label="操作" width="80"><template #default="{row}"><el-tag size="small">{{ row.action }}</el-tag></template></el-table-column>
        <el-table-column prop="target_type" label="对象类型" width="90" />
        <el-table-column prop="target_name" label="对象名称" />
        <el-table-column prop="detail" label="详情" />
        <el-table-column prop="ip_address" label="IP" width="120" />
        <el-table-column prop="created_at" label="时间" width="170" />
      </el-table>
      <div class="pagination-wrap"><el-pagination v-model:current-page="currentPage" v-model:page-size="pageSize" :page-sizes="[10,20,50]" :total="total" :layout="paginationLayout" @current-change="handleCurrentChange" @size-change="handleSizeChange" /></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { getAuditLogs } from '@/api/audit'
import { usePagination } from '@/hooks/usePagination'

const loading = ref(false); const items = ref<any[]>([])
const { currentPage, pageSize, total, paginationLayout, handleCurrentChange, handleSizeChange } = usePagination(fetchData)
const filters = reactive({ keyword: '', action: '', target_type: '' })

async function fetchData(extra?: any) {
  loading.value = true
  try {
    const params = { ...filters, page: extra?.page || currentPage.value, page_size: extra?.page_size || pageSize.value }
    const res: any = await getAuditLogs(params); items.value = res.data.items; total.value = res.data.total
  } finally { loading.value = false }
}
onMounted(fetchData)
</script>

<style scoped>.pagination-wrap { display: flex; justify-content: flex-end; margin-top: 16px; }</style>
