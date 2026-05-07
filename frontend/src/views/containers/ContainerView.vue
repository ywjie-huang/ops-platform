<template>
  <div>
    <div class="page-header"><h2 class="page-title">容器管理</h2></div>
    <!-- 概览卡片 -->
    <el-row :gutter="16" style="margin-bottom:16px">
      <el-col :span="6" v-for="item in overviewCards" :key="item.label">
        <div class="stat-card">
          <div class="stat-label">{{ item.label }}</div>
          <div class="stat-value">{{ item.value }}</div>
        </div>
      </el-col>
    </el-row>
    <!-- 集群列表 -->
    <div class="data-card">
      <h3 style="margin-bottom:12px">集群列表</h3>
      <el-table :data="clusters" stripe v-loading="loading">
        <el-table-column prop="name" label="名称"><template #default="{row}"><strong>{{ row.name }}</strong></template></el-table-column>
        <el-table-column prop="cluster_type" label="类型" />
        <el-table-column prop="status" label="状态"><template #default="{row}"><el-tag :type="row.status === 'running' ? 'success' : 'warning'" size="small">{{ row.status }}</el-tag></template></el-table-column>
        <el-table-column prop="api_server" label="API Server" />
        <el-table-column prop="description" label="说明" />
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'; import { getContainerOverview, getClusters } from '@/api/containers'
const loading = ref(false); const overview = ref<any>({}); const clusters = ref<any[]>([])
const overviewCards = computed(() => [
  { label: '集群数', value: overview.value.cluster_count ?? '-' },
  { label: 'Deployments', value: overview.value.deployment_count ?? '-' },
  { label: 'Pods', value: overview.value.pod_count ?? '-' },
  { label: 'Services', value: overview.value.service_count ?? '-' },
])
onMounted(async () => {
  loading.value = true
  try { const [o, c]: any = await Promise.all([getContainerOverview(), getClusters()]); overview.value = o.data; clusters.value = c.data } finally { loading.value = false }
})
</script>

<style scoped>.stat-card { background: #fff; border: 1px solid var(--border-color); border-radius: 8px; padding: 16px; }
.stat-label { font-size: 13px; color: var(--text-muted); } .stat-value { font-size: 24px; font-weight: 700; }</style>
