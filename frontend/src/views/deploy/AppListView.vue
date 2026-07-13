<template>
  <div>
    <div class="page-header">
      <h2 class="page-title">应用管理</h2>
      <el-button type="primary" @click="$router.push('/deploy/apps/create')">
        <el-icon><Plus /></el-icon>创建应用
      </el-button>
    </div>

    <!-- 统计卡片 -->
    <div class="stat-grid" role="region" aria-label="应用统计">
      <div class="stat-card">
        <div class="stat-icon stat-icon--primary">
          <el-icon size="20"><Folder /></el-icon>
        </div>
        <div>
          <div class="stat-label">应用总数</div>
          <div class="stat-value">{{ stats.total }}</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon stat-icon--green">
          <el-icon size="20"><CircleCheckFilled /></el-icon>
        </div>
        <div>
          <div class="stat-label">活跃</div>
          <div class="stat-value">{{ stats.by_status.active || 0 }}</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon stat-icon--gray">
          <el-icon size="20"><Box /></el-icon>
        </div>
        <div>
          <div class="stat-label">已归档</div>
          <div class="stat-value">{{ stats.by_status.archived || 0 }}</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon stat-icon--amber">
          <el-icon size="20"><Upload /></el-icon>
        </div>
        <div>
          <div class="stat-label">SSH 部署</div>
          <div class="stat-value">{{ stats.by_strategy.ssh || 0 }}</div>
        </div>
      </div>
    </div>

    <!-- 筛选栏 + 表格 -->
    <div class="data-card">
      <div class="toolbar">
        <div class="toolbar-actions">
          <el-input
            v-model="filters.keyword"
            placeholder="搜索应用名称…"
            clearable
            class="filter-input"
            aria-label="搜索应用名称"
            @input="handleSearchInput"
            @keyup.enter="fetchData"
            @clear="handleSearchClear"
          >
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
          <el-select v-model="filters.app_type" placeholder="应用类型" clearable class="filter-select" aria-label="应用类型筛选" @change="fetchData">
            <el-option v-for="t in appTypes" :key="t.value" :label="t.label" :value="t.value" />
          </el-select>
          <el-select v-model="filters.deploy_strategy" placeholder="部署策略" clearable class="filter-select" aria-label="部署策略筛选" @change="fetchData">
            <el-option v-for="s in strategies" :key="s.value" :label="s.label" :value="s.value" />
          </el-select>
          <el-select v-model="filters.status" placeholder="状态" clearable class="filter-select--status" aria-label="状态筛选" @change="fetchData">
            <el-option label="活跃" value="active" />
            <el-option label="已归档" value="archived" />
          </el-select>
          <el-button text @click="resetFilters">重置</el-button>
        </div>
      </div>

      <div class="table-wrapper">
        <el-table :data="items" stripe v-loading="loading">
          <el-table-column label="应用信息" min-width="180">
            <template #default="{ row }">
              <div class="cell-stack">
                <span class="cell-primary">{{ row.name }}</span>
                <span class="cell-secondary">{{ row.description || '暂无描述' }}</span>
              </div>
            </template>
          </el-table-column>

          <el-table-column label="类型" width="110">
            <template #default="{ row }">
              <span class="cell-body">{{ typeLabel(row.app_type) }}</span>
            </template>
          </el-table-column>

          <el-table-column label="部署策略" width="110">
            <template #default="{ row }">
              <span class="cell-body">{{ strategyLabel(row.deploy_strategy) }}</span>
            </template>
          </el-table-column>

          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <el-tag :type="statusType(row.status)" size="small" effect="plain">{{ statusLabel(row.status) }}</el-tag>
            </template>
          </el-table-column>

          <el-table-column label="更新时间" width="140">
            <template #default="{ row }">
              <span class="cell-body" :title="formatFullDateTime(row.updated_at)">{{ formatRelativeTime(row.updated_at) }}</span>
            </template>
          </el-table-column>

          <el-table-column label="操作" width="180" fixed="right">
            <template #default="{ row }">
              <div class="action-cell">
                <el-button size="small" type="primary" link :aria-label="`查看 ${row.name} 详情`" @click="$router.push(`/deploy/apps/${row.name}`)">详情</el-button>
                <el-button size="small" type="info" link :aria-label="`编辑 ${row.name}`" @click="$router.push(`/deploy/apps/${row.name}/edit`)">编辑</el-button>
                <el-popconfirm :title="`确认删除应用「${row.name}」？`" @confirm="handleDelete(row.name)">
                  <template #reference>
                    <el-button size="small" type="danger" link :aria-label="`删除 ${row.name}`">删除</el-button>
                  </template>
                </el-popconfirm>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 空状态 -->
      <el-empty v-if="!loading && items.length === 0" description="还没有应用，创建第一个开始部署吧">
        <el-button type="primary" @click="$router.push('/deploy/apps/create')">创建应用</el-button>
      </el-empty>

      <!-- 分页 -->
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
import { ref, reactive, onActivated } from 'vue'
import { Plus, Search, Folder, CircleCheckFilled, Box, Upload } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getDeployApps, getDeployAppStats, deleteDeployApp } from '@/api/deploy'
import { usePagination } from '@/hooks/usePagination'
import { formatRelativeTime, formatFullDateTime } from '@/utils/time'

const loading = ref(false)
const items = ref<any[]>([])
const { currentPage, pageSize, total, paginationLayout, handleCurrentChange, handleSizeChange, resetPagination } = usePagination(fetchData)

const filters = reactive({ keyword: '', app_type: '', deploy_strategy: '', status: '' })

const stats = ref<{ total: number; by_status: Record<string, number>; by_type: Record<string, number>; by_strategy: Record<string, number> }>({
  total: 0,
  by_status: {},
  by_type: {},
  by_strategy: {},
})

const appTypes = [
  { label: 'Web 应用', value: 'web' },
  { label: 'API 服务', value: 'api' },
  { label: '后台任务', value: 'worker' },
  { label: '前端项目', value: 'frontend' },
  { label: '其他', value: 'other' },
]

const strategies = [
  { label: 'SSH', value: 'ssh' },
  { label: 'Docker', value: 'docker' },
  { label: 'Kubernetes', value: 'k8s' },
]

const typeLabel = (v: string) => appTypes.find(t => t.value === v)?.label || v
const strategyLabel = (v: string) => strategies.find(s => s.value === v)?.label || v
const statusLabel = (v: string) => ({ active: '活跃', archived: '已归档' }[v] || v)
const statusType = (v: string) => ({ active: 'success', archived: 'info' }[v] || '') as any

let searchTimer: ReturnType<typeof setTimeout> | null = null

function handleSearchInput() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => fetchData(), 300)
}

function handleSearchClear() {
  if (searchTimer) clearTimeout(searchTimer)
  fetchData()
}

function resetFilters() {
  Object.assign(filters, { keyword: '', app_type: '', deploy_strategy: '', status: '' })
  resetPagination()
  fetchData()
}

async function handleDelete(name: string) {
  await deleteDeployApp(name)
  ElMessage.success('删除成功')
  fetchData()
  fetchStats()
}

async function fetchStats() {
  try {
    const res: any = await getDeployAppStats()
    stats.value = res.data
  } catch {
    // 统计加载失败不影响列表
  }
}

async function fetchData(extra?: any) {
  loading.value = true
  try {
    const params = {
      ...filters,
      page: extra?.page || currentPage.value,
      page_size: extra?.page_size || pageSize.value,
    }
    const res: any = await getDeployApps(params)
    items.value = res.data.items
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}

onActivated(() => {
  fetchData()
  fetchStats()
})
</script>

<style scoped>
.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 12px;
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: 16px 20px;
}

.stat-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 10px;
  flex-shrink: 0;
}

.stat-icon--primary {
  background: var(--primary-bg);
  color: var(--primary-color);
}

.stat-icon--green {
  background: color-mix(in srgb, var(--success-color) 10%, transparent);
  color: var(--success-color);
}

.stat-icon--gray {
  background: color-mix(in srgb, var(--text-muted) 10%, transparent);
  color: var(--text-muted);
}

.stat-icon--amber {
  background: color-mix(in srgb, var(--warning-color) 10%, transparent);
  color: var(--warning-color);
}

.stat-label {
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1.4;
}

.stat-value {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.2;
}

.filter-input {
  width: 220px;
}

.filter-select {
  width: 130px;
}

.filter-select--status {
  width: 110px;
}

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
  color: var(--text-secondary);
}

.cell-body {
  font-size: 13px;
  color: var(--text-primary);
}

.action-cell {
  display: flex;
  align-items: center;
  gap: 4px;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

@media (max-width: 768px) {
  .stat-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .filter-input,
  .filter-select,
  .filter-select--status {
    width: 100%;
  }
}
</style>
