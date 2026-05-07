<template>
  <div>
    <div class="page-header">
      <h2 class="page-title">仪表盘</h2>
    </div>

    <!-- 指标卡片 -->
    <el-row :gutter="16" style="margin-bottom:16px">
      <el-col :xs="12" :sm="6" v-for="item in statCards" :key="item.label">
        <div class="stat-card">
          <div class="stat-label">{{ item.label }}</div>
          <div class="stat-value" :style="{ color: item.color }">{{ item.value }}</div>
        </div>
      </el-col>
    </el-row>

    <!-- 快捷统计 -->
    <el-row :gutter="16">
      <el-col :span="16">
        <div class="data-card">
          <h3 style="margin-bottom:12px">最近资产变更</h3>
          <el-table :data="summary.recent_asset_changes || []" stripe size="small">
            <el-table-column prop="title" label="资产" />
            <el-table-column prop="meta" label="信息" />
            <el-table-column prop="tag" label="状态">
              <template #default="{ row }">
                <el-tag :type="tagType(row.tone)" size="small">{{ row.tag }}</el-tag>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-col>
      <el-col :span="8">
        <div class="data-card" style="margin-bottom:16px">
          <h3 style="margin-bottom:12px">角色分布</h3>
          <div v-for="item in summary.role_distribution" :key="item.label" class="dist-item">
            <span>{{ item.label }}</span>
            <el-tag size="small">{{ item.value }}</el-tag>
          </div>
        </div>
        <div class="data-card">
          <h3 style="margin-bottom:12px">资产类型</h3>
          <div v-for="item in summary.type_breakdown" :key="item.label" class="dist-item">
            <span>{{ item.label }}</span>
            <el-progress :percentage="pct(item.value)" :color="item.color" :stroke-width="14" :text-inside="false" style="width:120px" />
          </div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { getDashboardStats, getDashboardSummary } from '@/api/dashboard'

const stats = ref<any>({})
const summary = ref<any>({})

const statCards = computed(() => [
  { label: '资产总数', value: stats.value.asset_total ?? '-', color: '#3b82f6' },
  { label: '在线主机', value: stats.value.online_hosts ?? '-', color: '#22c55e' },
  { label: '待处理告警', value: stats.value.open_alerts ?? '-', color: '#ef4444' },
  { label: '待处理工单', value: stats.value.pending_tickets ?? '-', color: '#f59e0b' },
])

function tagType(tone: string) {
  const map: Record<string, string> = { green: 'success', red: 'danger', orange: 'warning', blue: 'primary' }
  return map[tone] || 'info'
}

function pct(val: number) {
  const max = summary.value.max_type_value || 1
  return Math.round((val / max) * 100)
}

onMounted(async () => {
  try {
    const [s, d]: any = await Promise.all([getDashboardStats(), getDashboardSummary()])
    stats.value = s.data
    summary.value = d.data
  } catch {}
})
</script>

<style lang="scss" scoped>
.stat-card {
  background: #fff;
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: 18px 20px;
  margin-bottom: 16px;
}
.stat-label { font-size: 13px; color: var(--text-muted); margin-bottom: 4px; }
.stat-value { font-size: 28px; font-weight: 700; }
.dist-item { display: flex; justify-content: space-between; align-items: center; padding: 6px 0; font-size: 13px; }
</style>
