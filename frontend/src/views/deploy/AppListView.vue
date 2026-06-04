<template>
  <div>
    <div class="page-header">
      <h2 class="page-title">应用管理</h2>
      <el-button type="primary" @click="$router.push('/deploy/apps/create')">
        <el-icon><Plus /></el-icon>创建应用
      </el-button>
    </div>

    <div class="filter-bar">
      <el-input
        v-model="filters.keyword"
        placeholder="搜索应用名称…"
        clearable
        style="width: 220px"
        @keyup.enter="fetchData"
      >
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <el-select v-model="filters.app_type" placeholder="应用类型" clearable style="width: 130px" @change="fetchData">
        <el-option v-for="t in appTypes" :key="t.value" :label="t.label" :value="t.value" />
      </el-select>
      <el-select v-model="filters.deploy_strategy" placeholder="部署策略" clearable style="width: 130px" @change="fetchData">
        <el-option v-for="s in strategies" :key="s.value" :label="s.label" :value="s.value" />
      </el-select>
      <el-select v-model="filters.status" placeholder="状态" clearable style="width: 110px" @change="fetchData">
        <el-option label="活跃" value="active" />
        <el-option label="已归档" value="archived" />
      </el-select>
      <el-button @click="fetchData">筛选</el-button>
    </div>

    <div v-loading="loading">
      <!-- 空状态 -->
      <el-empty v-if="!loading && items.length === 0" description="暂无应用，点击右上角创建" />

      <!-- 卡片网格 -->
      <div v-else class="app-grid">
        <div
          v-for="app in items"
          :key="app.id"
          class="app-card"
          @click="$router.push(`/deploy/apps/${app.id}`)"
        >
          <div class="app-card-header">
            <span class="app-card-name">{{ app.name }}</span>
            <el-tag :type="statusType(app.status)" size="small">{{ statusLabel(app.status) }}</el-tag>
          </div>
          <p class="app-card-desc">{{ app.description || '暂无描述' }}</p>
          <div class="app-card-meta">
            <el-tag size="small" type="info" effect="plain">{{ typeLabel(app.app_type) }}</el-tag>
            <el-tag size="small" effect="plain" :type="strategyType(app.deploy_strategy)">
              {{ strategyLabel(app.deploy_strategy) }}
            </el-tag>
          </div>
          <div class="app-card-footer">
            <span class="app-card-time">{{ formatTime(app.updated_at) }}</span>
          </div>
        </div>
      </div>

      <!-- 分页 -->
      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[12, 24, 48]"
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
import { ref, reactive, onMounted } from 'vue'
import { Plus, Search } from '@element-plus/icons-vue'
import { getDeployApps } from '@/api/deploy'
import { usePagination } from '@/hooks/usePagination'

const loading = ref(false)
const items = ref<any[]>([])
const { currentPage, pageSize, total, paginationLayout, handleCurrentChange, handleSizeChange } = usePagination(fetchData)

const filters = reactive({ keyword: '', app_type: '', deploy_strategy: '', status: '' })

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
const strategyType = (v: string) => ({ ssh: '', docker: 'warning', k8s: 'danger' }[v] || '') as any

function formatTime(iso: string) {
  if (!iso) return ''
  const d = new Date(iso)
  const now = new Date()
  const diffMs = now.getTime() - d.getTime()
  const diffMin = Math.floor(diffMs / 60000)
  if (diffMin < 1) return '刚刚'
  if (diffMin < 60) return `${diffMin} 分钟前`
  const diffHour = Math.floor(diffMin / 60)
  if (diffHour < 24) return `${diffHour} 小时前`
  const diffDay = Math.floor(diffHour / 24)
  if (diffDay < 7) return `${diffDay} 天前`
  return d.toLocaleDateString('zh-CN')
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

onMounted(fetchData)
</script>

<style scoped>
.app-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

.app-card {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: 20px;
  cursor: pointer;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.app-card:hover {
  border-color: var(--primary-color);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
}

.app-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.app-card-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 70%;
}

.app-card-desc {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.app-card-meta {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.app-card-footer {
  display: flex;
  justify-content: flex-end;
}

.app-card-time {
  font-size: 12px;
  color: var(--text-muted);
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
