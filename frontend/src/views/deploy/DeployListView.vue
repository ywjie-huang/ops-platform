<template>
  <div>
    <div class="page-header"><h2 class="page-title">发布记录</h2></div>
    <div class="filter-bar">
      <el-input v-model="filters.keyword" placeholder="搜索版本号…" clearable style="width:180px" @keyup.enter="fetchData" />
      <el-select v-model="filters.status" placeholder="状态" clearable style="width:120px" @change="fetchData">
        <el-option label="成功" value="success" />
        <el-option label="失败" value="failed" />
        <el-option label="构建中" value="building" />
        <el-option label="待审批" value="pending" />
        <el-option label="已驳回" value="rejected" />
      </el-select>
      <el-button @click="fetchData">筛选</el-button>
    </div>
    <div class="data-card">
      <el-table :data="items" stripe v-loading="loading">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="application_name" label="应用" min-width="140" show-overflow-tooltip />
        <el-table-column label="环境" width="100">
          <template #default="{row}"><el-tag size="small">{{ row.environment_display_name || row.environment_name }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="version" label="版本" min-width="130" show-overflow-tooltip />
        <el-table-column prop="deploy_method" label="方式" width="90">
          <template #default="{row}"><el-tag size="small" type="info">{{ row.deploy_method }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{row}"><el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="creator_name" label="发起人" width="80" />
        <el-table-column label="耗时" width="80">
          <template #default="{row}">{{ row.duration_seconds ? row.duration_seconds + 's' : '-' }}</template>
        </el-table-column>
        <el-table-column prop="created_at" label="时间" width="160">
          <template #default="{row}">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{row}">
            <el-button size="small" text type="primary" @click="$router.push(`/deploy/records/${row.id}`)">详情</el-button>
            <el-button v-if="row.status === 'failed' || row.status === 'rejected'" size="small" text type="warning" @click="handleRetry(row.id)">重试</el-button>
            <el-button v-if="row.status === 'success' || row.status === 'failed'" size="small" text type="warning" @click="handleRollback(row.id)">回滚</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-wrap">
        <el-pagination v-model:current-page="currentPage" v-model:page-size="pageSize" :page-sizes="[10,20,50]" :total="total" :layout="paginationLayout" @current-change="handleCurrentChange" @size-change="handleSizeChange" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onActivated } from 'vue'
import { getDeployRecords, retryDeployment, rollbackDeployment } from '@/api/deploy'
import { usePagination } from '@/hooks/usePagination'
import { ElMessage } from 'element-plus'

const loading = ref(false)
const items = ref<any[]>([])
const { currentPage, pageSize, total, paginationLayout, handleCurrentChange, handleSizeChange } = usePagination(fetchData)
const filters = reactive({ keyword: '', status: '' })

const statusType = (s: string) => ({ success: 'success', failed: 'danger', building: 'warning', deploying: 'warning', pending: 'info', approved: 'primary', rejected: 'danger', rolled_back: 'info' }[s] || 'info') as any
const statusLabel = (s: string) => ({ success: '成功', failed: '失败', building: '构建中', deploying: '部署中', pending: '待审批', approved: '已通过', rejected: '已驳回', rolled_back: '已回滚' }[s] || s)
const formatTime = (t: string) => t ? new Date(t).toLocaleString('zh-CN') : '-'

async function fetchData(extra?: any) {
  loading.value = true
  try {
    const params = { ...filters, page: extra?.page || currentPage.value, page_size: extra?.page_size || pageSize.value }
    const res: any = await getDeployRecords(params)
    items.value = res.data.items
    total.value = res.data.total
  } finally { loading.value = false }
}

async function handleRetry(id: number) {
  await retryDeployment(id)
  ElMessage.success('重试已触发')
  fetchData()
}

async function handleRollback(id: number) {
  await rollbackDeployment(id)
  ElMessage.success('回滚记录已创建')
  fetchData()
}

// keep-alive 下用 onActivated 每次进入都刷新
onActivated(fetchData)
</script>

<style scoped>
.pagination-wrap { display: flex; justify-content: flex-end; margin-top: 16px; }
</style>
