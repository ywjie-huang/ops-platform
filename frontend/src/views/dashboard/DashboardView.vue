<template>
  <div class="dashboard">
    <!-- 顶部栏 -->
    <div class="dashboard-header">
      <div>
        <h2 class="greeting">{{ greeting }}，{{ authStore.fullName || '管理员' }}</h2>
        <p class="date-text">{{ currentDate }}</p>
      </div>
      <div class="time-tabs">
        <span
          v-for="tab in timeTabs"
          :key="tab.key"
          class="time-tab"
          :class="{ active: activeTab === tab.key }"
          @click="activeTab = tab.key"
        >{{ tab.label }}</span>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stat-grid">
      <div v-for="card in statCards" :key="card.label" class="stat-card">
        <div class="stat-card-top">
          <span class="stat-card-label">{{ card.label }}</span>
          <div class="stat-card-icon" :style="{ background: card.iconBg }">
            <el-icon :size="16" :style="{ color: card.iconColor }"><component :is="card.icon" /></el-icon>
          </div>
        </div>
        <div class="stat-card-value">{{ card.value }}</div>
        <div class="stat-card-bottom">
          <Sparkline :data="card.sparkline" :color="card.iconColor" :width="80" :height="28" />
          <span class="stat-change" :class="card.changeType">
            {{ card.change }}
          </span>
        </div>
      </div>
    </div>

    <!-- 主内容区 -->
    <div class="dashboard-grid">
      <!-- 左侧：活动时间线 -->
      <div class="activity-panel">
        <div class="panel-header">
          <h3>最近活动</h3>
          <div class="filter-tabs">
            <span
              v-for="f in activityFilters"
              :key="f.key"
              class="filter-tab"
              :class="{ active: activeFilter === f.key }"
              @click="handleFilterChange(f.key)"
            >{{ f.label }}</span>
          </div>
        </div>
        <div class="activity-list">
          <div v-for="(item, i) in activities" :key="i" class="activity-item">
            <div class="activity-dot" :class="'dot-' + item.type"></div>
            <div class="activity-body">
              <div class="activity-desc">{{ item.description }}</div>
              <div class="activity-meta">
                <span>{{ item.time }}</span>
                <span v-if="item.username"> · {{ item.username }}</span>
              </div>
            </div>
            <span class="activity-tag" :class="'tag-' + item.type">{{ item.type_label }}</span>
          </div>
          <div v-if="!activities.length" class="empty-hint">暂无活动记录</div>
        </div>
      </div>

      <!-- 右侧：图表 -->
      <div class="side-charts">
        <AlertTrendChart :dates="alertTrend.dates" :counts="alertTrend.counts" />
        <div class="type-panel">
          <div class="panel-header">
            <h3>资产类型</h3>
          </div>
          <div class="bar-list">
            <div v-for="item in typeBreakdown" :key="item.label" class="bar-item">
              <div class="bar-label">{{ item.label }}</div>
              <div class="bar-track">
                <div class="bar-fill" :style="{ width: typePct(item.value) + '%', background: item.color }"></div>
              </div>
              <div class="bar-value">{{ item.value }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { getDashboardStats, getSparkline, getActivities, getAlertTrend, getDashboardSummary } from '@/api/dashboard'
import { useAuthStore } from '@/stores/modules/auth'
import { Box, Monitor, Warning, Tickets } from '@element-plus/icons-vue'
import Sparkline from '@/components/Sparkline.vue'
import AlertTrendChart from '@/components/AlertTrendChart.vue'

const authStore = useAuthStore()

const stats = ref<any>({})
const sparkline = ref<any>({ dates: [], series: { assets: [], online: [], alerts: [], tickets: [] } })
const activities = ref<any[]>([])
const alertTrend = ref<any>({ dates: [], counts: [] })
const summary = ref<any>({})

const activeTab = ref('today')
const activeFilter = ref('all')

const timeTabs = [
  { key: 'today', label: '今天' },
  { key: 'week', label: '本周' },
  { key: 'month', label: '本月' },
]

const activityFilters = [
  { key: 'all', label: '全部' },
  { key: 'alert', label: '告警' },
  { key: 'ticket', label: '工单' },
  { key: 'asset', label: '资产' },
  { key: 'patrol', label: '巡检' },
  { key: 'user', label: '用户' },
]

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 12) return '早上好'
  if (h < 18) return '下午好'
  return '晚上好'
})

const currentDate = computed(() => {
  return new Date().toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' })
})

const statCards = computed(() => {
  const s = sparkline.value.series
  const changePct = (arr: number[]) => {
    if (!arr || arr.length < 2 || arr[arr.length - 2] === 0) return { text: '持平', type: 'neutral' }
    const pct = Math.round(((arr[arr.length - 1] - arr[arr.length - 2]) / arr[arr.length - 2]) * 100)
    if (pct > 0) return { text: `+${pct}%`, type: 'up' }
    if (pct < 0) return { text: `${pct}%`, type: 'down' }
    return { text: '持平', type: 'neutral' }
  }

  const assets = changePct(s.assets)
  const online = changePct(s.online)
  const alertsChange = changePct(s.alerts)
  const tickets = changePct(s.tickets)

  return [
    {
      label: '资产总数', value: stats.value.asset_total ?? '-',
      icon: Box, iconBg: '#eff6ff', iconColor: '#3b82f6',
      sparkline: s.assets || [], change: assets.text, changeType: assets.type,
    },
    {
      label: '在线主机', value: stats.value.online_hosts ?? '-',
      icon: Monitor, iconBg: '#f0fdf4', iconColor: '#22c55e',
      sparkline: s.online || [], change: online.text, changeType: online.type,
    },
    {
      label: '待处理告警', value: stats.value.open_alerts ?? '-',
      icon: Warning, iconBg: '#fef2f2', iconColor: '#ef4444',
      sparkline: s.alerts || [], change: alertsChange.text, changeType: alertsChange.type,
    },
    {
      label: '待处理工单', value: stats.value.pending_tickets ?? '-',
      icon: Tickets, iconBg: '#fffbeb', iconColor: '#f59e0b',
      sparkline: s.tickets || [], change: tickets.text, changeType: tickets.type,
    },
  ]
})

const typeBreakdown = computed(() => summary.value.type_breakdown || [])
const maxTypeValue = computed(() => summary.value.max_type_value || 1)
function typePct(val: number) { return Math.round((val / maxTypeValue.value) * 100) }

async function fetchActivities(type?: string) {
  try {
    const res: any = await getActivities(20, type)
    activities.value = res.data?.items || []
  } catch { activities.value = [] }
}

function handleFilterChange(key: string) {
  activeFilter.value = key
  fetchActivities(key === 'all' ? undefined : key)
}

onMounted(async () => {
  try {
    const [statsRes, sparkRes, actRes, trendRes, sumRes]: any = await Promise.all([
      getDashboardStats(),
      getSparkline(),
      getActivities(20),
      getAlertTrend(),
      getDashboardSummary(),
    ])
    stats.value = statsRes.data
    sparkline.value = sparkRes.data
    activities.value = actRes.data?.items || []
    alertTrend.value = trendRes.data
    summary.value = sumRes.data
  } catch {}
})
</script>

<style lang="scss" scoped>
.dashboard {
  width: 100%;
  padding-right: 16px;
}

// ── 顶部栏 ──
.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.greeting {
  font-size: 20px;
  font-weight: 700;
  color: #1e293b;
  margin-bottom: 4px;
}
.date-text {
  font-size: 13px;
  color: #94a3b8;
}
.time-tabs {
  display: flex;
  gap: 4px;
  background: #f1f5f9;
  border-radius: 8px;
  padding: 3px;
}
.time-tab {
  padding: 6px 14px;
  border-radius: 6px;
  font-size: 13px;
  color: #64748b;
  cursor: pointer;
  transition: all 0.15s;
  &.active {
    background: #fff;
    color: #1e293b;
    font-weight: 600;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  }
}

// ── 统计卡片 ──
.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}
.stat-card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 18px;
  transition: box-shadow 0.2s;
  &:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.06); }
}
.stat-card-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
.stat-card-label {
  font-size: 13px;
  color: #94a3b8;
}
.stat-card-icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.stat-card-value {
  font-size: 28px;
  font-weight: 800;
  color: #1e293b;
  margin-bottom: 10px;
}
.stat-card-bottom {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.stat-change {
  font-size: 12px;
  font-weight: 600;
  &.up { color: #22c55e; }
  &.down { color: #ef4444; }
  &.neutral { color: #94a3b8; }
}

// ── 主内容区 ──
.dashboard-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 16px;
}

// ── 活动时间线 ──
.activity-panel {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 18px;
}
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  h3 {
    font-size: 15px;
    font-weight: 700;
    color: #1e293b;
  }
}
.filter-tabs {
  display: flex;
  gap: 4px;
}
.filter-tab {
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 12px;
  color: #64748b;
  cursor: pointer;
  transition: all 0.15s;
  &.active {
    background: #e0e7ff;
    color: #4f46e5;
    font-weight: 600;
  }
  &:hover:not(.active) {
    background: #f1f5f9;
  }
}
.activity-list {
  display: flex;
  flex-direction: column;
}
.activity-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid #f1f5f9;
  &:last-child { border-bottom: none; }
}
.activity-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-top: 6px;
  flex-shrink: 0;
  &.dot-alert { background: #ef4444; }
  &.dot-ticket { background: #f59e0b; }
  &.dot-asset { background: #3b82f6; }
  &.dot-patrol { background: #22c55e; }
  &.dot-user { background: #8b5cf6; }
  &.dot-system { background: #94a3b8; }
}
.activity-body {
  flex: 1;
  min-width: 0;
}
.activity-desc {
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
}
.activity-meta {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 2px;
}
.activity-tag {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
  flex-shrink: 0;
  &.tag-alert { background: #fef2f2; color: #ef4444; }
  &.tag-ticket { background: #fffbeb; color: #f59e0b; }
  &.tag-asset { background: #eff6ff; color: #3b82f6; }
  &.tag-patrol { background: #f0fdf4; color: #22c55e; }
  &.tag-user { background: #f5f3ff; color: #8b5cf6; }
  &.tag-system { background: #f1f5f9; color: #64748b; }
}
.empty-hint {
  text-align: center;
  padding: 40px 0;
  color: #94a3b8;
  font-size: 13px;
}

// ── 右侧图表 ──
.side-charts {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.type-panel {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 18px;
}
.bar-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.bar-item {
  display: flex;
  align-items: center;
  gap: 10px;
}
.bar-label {
  width: 60px;
  font-size: 12px;
  color: #64748b;
  text-align: right;
  flex-shrink: 0;
}
.bar-track {
  flex: 1;
  height: 8px;
  background: #f1f5f9;
  border-radius: 4px;
  overflow: hidden;
}
.bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.6s ease;
}
.bar-value {
  width: 30px;
  font-size: 12px;
  font-weight: 700;
  color: #1e293b;
  text-align: right;
}

// ── 响应式 ──
@media (min-width: 1600px) {
  .stat-card-value { font-size: 32px; }
  .dashboard-grid { grid-template-columns: 2fr 420px; }
}
@media (min-width: 1920px) {
  .stat-grid { gap: 20px; }
  .stat-card { padding: 22px; }
  .stat-card-value { font-size: 36px; }
  .dashboard-grid { grid-template-columns: 2fr 480px; gap: 20px; }
}
@media (max-width: 1100px) {
  .stat-grid { grid-template-columns: repeat(2, 1fr); }
  .dashboard-grid { grid-template-columns: 1fr; }
}
@media (max-width: 600px) {
  .stat-grid { grid-template-columns: 1fr; }
}
</style>
