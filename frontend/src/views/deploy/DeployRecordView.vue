<template>
  <div>
    <div class="page-header">
      <h2 class="page-title">部署记录</h2>
    </div>

    <div class="filter-bar">
      <el-select v-model="filters.app_name" placeholder="筛选应用" clearable filterable style="width: 200px" @change="fetchData">
        <el-option v-for="a in appList" :key="a.id" :label="a.name" :value="a.name" />
      </el-select>
      <el-select v-model="filters.env_id" placeholder="筛选环境" clearable style="width: 130px" @change="fetchData">
        <el-option v-for="e in envList" :key="e.id" :label="e.name" :value="e.id" />
      </el-select>
      <el-select v-model="filters.status" placeholder="状态" clearable style="width: 130px" @change="fetchData">
        <el-option v-for="s in statusOptions" :key="s.value" :label="s.label" :value="s.value" />
      </el-select>
      <el-button @click="fetchData">筛选</el-button>
    </div>

    <div class="data-card">
      <el-table :data="items" stripe v-loading="loading" @row-click="handleRowClick" row-class-name="clickable-row">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="app_name" label="应用" min-width="120" />
        <el-table-column prop="env_name" label="环境" width="100">
          <template #default="{ row }">
            <el-tag size="small" effect="plain">{{ row.env_name || '—' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="version" label="版本" width="130">
          <template #default="{ row }">
            <code class="version-text">{{ row.version || '—' }}</code>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="trigger_type" label="触发方式" width="90">
          <template #default="{ row }">
            {{ triggerLabel(row.trigger_type) }}
          </template>
        </el-table-column>
        <el-table-column prop="trigger_user_name" label="触发人" width="90" />
        <el-table-column prop="duration" label="耗时" width="90">
          <template #default="{ row }">
            {{ row.duration != null ? formatDuration(row.duration) : '—' }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="时间" width="170">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
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
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onActivated, onDeactivated } from 'vue'
import { useRouter } from 'vue-router'
import { getDeployRecords, getDeployApps, getDeployEnvs } from '@/api/deploy'
import { usePagination } from '@/hooks/usePagination'

const router = useRouter()
const loading = ref(false)
const items = ref<any[]>([])
const { currentPage, pageSize, total, paginationLayout, handleCurrentChange, handleSizeChange } = usePagination(fetchData)

const filters = reactive({ app_name: '' as string, env_id: null as number | null, status: '' })

const appList = ref<any[]>([])
const envList = ref<any[]>([])

const statusOptions = [
  { label: '待执行', value: 'pending' },
  { label: '构建中', value: 'building' },
  { label: '部署中', value: 'deploying' },
  { label: 'Jenkins执行中', value: 'triggering' },
  { label: '成功', value: 'success' },
  { label: '失败', value: 'failed' },
  { label: '已取消', value: 'cancelled' },
]

const statusLabel = (v: string) => ({ pending: '待执行', building: '构建中', deploying: '部署中', triggering: 'Jenkins执行中', success: '成功', failed: '失败', cancelled: '已取消' }[v] || v)
const statusType = (v: string) => ({ pending: 'info', building: 'warning', deploying: 'warning', triggering: 'warning', success: 'success', failed: 'danger', cancelled: 'info' }[v] || '') as any
const triggerLabel = (v: string) => ({ manual: '手动', rollback: '回滚', webhook: 'Webhook' }[v] || v)

function formatDuration(sec: number) {
  if (sec < 60) return `${Math.round(sec)}s`
  const m = Math.floor(sec / 60)
  const s = Math.round(sec % 60)
  return `${m}m ${s}s`
}

function formatTime(iso: string) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('zh-CN')
}

async function fetchData(extra?: any, silent = false) {
  if (!silent) loading.value = true
  try {
    const params: any = {
      page: extra?.page || currentPage.value,
      page_size: extra?.page_size || pageSize.value,
    }
    if (filters.app_name) params.app_name = filters.app_name
    if (filters.env_id) params.env_id = filters.env_id
    if (filters.status) params.status = filters.status
    const res: any = await getDeployRecords(params)
    items.value = res.data.items
    total.value = res.data.total
  } finally {
    if (!silent) loading.value = false
  }
}

async function fetchDropdowns() {
  const [a, e] = await Promise.all([
    getDeployApps({ page_size: 200 }).catch(() => ({ data: { items: [] } })),
    getDeployEnvs().catch(() => ({ data: [] })),
  ])
  appList.value = (a as any).data?.items || []
  envList.value = (e as any).data || []
}

function handleRowClick(row: any) {
  router.push(`/deploy/records/${row.id}`)
}

// ── 自动刷新：进行中的部署（含模式 B triggering）状态变化无需手动刷新 ──
let refreshTimer: ReturnType<typeof setInterval> | null = null

function startAutoRefresh() {
  stopAutoRefresh()
  refreshTimer = setInterval(() => {
    // 存在进行中记录才刷新；全部终态则保持静态（新部署发起后下次激活/操作会恢复轮询）
    const active = items.value.some((r) =>
      ['pending', 'building', 'deploying', 'triggering'].includes(r.status),
    )
    if (active) fetchData(undefined, true)
  }, 3000)
}

function stopAutoRefresh() {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
}

onActivated(() => {
  fetchData()
  fetchDropdowns()
  startAutoRefresh()
})

onDeactivated(() => {
  stopAutoRefresh()
})
</script>

<style scoped>
.version-text {
  background: var(--bg-color);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
  color: var(--text-primary);
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

:deep(.clickable-row) {
  cursor: pointer;
}
</style>
