<template>
  <div class="dashboard">
    <!-- 欢迎区 -->
    <div class="welcome">
      <h1>{{ greeting }}，{{ authStore.fullName || '管理员' }}</h1>
      <p>{{ currentDate }}</p>
    </div>

    <!-- 快捷操作 -->
    <div class="quick-actions">
      <div v-for="action in quickActions" :key="action.label" class="action-item" @click="$router.push(action.path)">
        <div class="action-icon" :style="{ background: action.bg }">
          <el-icon :size="16" :style="{ color: action.color }"><component :is="action.icon" /></el-icon>
        </div>
        <span class="action-label">{{ action.label }}</span>
      </div>
    </div>

    <!-- 统计条 -->
    <div class="stats-bar">
      <div v-for="card in statCards" :key="card.label" class="stat-item">
        <div class="stat-label">{{ card.label }}</div>
        <div class="stat-row">
          <span class="stat-value">{{ card.value }}</span>
          <span class="stat-change" :class="card.changeType">{{ card.change }}</span>
        </div>
        <Sparkline :data="card.sparkline" :color="card.lineColor" :width="100" :height="20" />
      </div>
    </div>

    <!-- 主内容区 -->
    <div class="dashboard-grid">
      <!-- 左侧：活动时间线 -->
      <div class="panel">
        <div class="panel-header">
          <h3>最近活动</h3>
          <div class="filter-pills">
            <span
              v-for="f in activityFilters"
              :key="f.key"
              class="pill"
              :class="{ active: activeFilter === f.key }"
              @click="handleFilterChange(f.key)"
            >{{ f.label }}</span>
          </div>
        </div>
        <div class="activity-list">
          <TransitionGroup name="act">
            <div v-for="(item, i) in activities" :key="i" class="act-item">
              <div class="act-dot" :class="'dot-' + item.type"></div>
              <div class="act-body">
                <div class="act-text">{{ item.description }}</div>
                <div class="act-meta">
                  <span>{{ item.time }}</span>
                  <span v-if="item.username"> · {{ item.username }}</span>
                </div>
              </div>
              <span class="act-tag" :class="'tag-' + item.type">{{ item.type_label }}</span>
            </div>
          </TransitionGroup>
          <div v-if="!activities.length" class="empty-state">
            <p>暂无活动记录</p>
          </div>
        </div>
      </div>

      <!-- 右侧 -->
      <div class="side-panels">
        <!-- 告警趋势 -->
        <div class="panel">
          <div class="panel-header">
            <h3>告警趋势</h3>
            <span class="trend-meta">近 7 天 · {{ alertTrendTotal }} 次</span>
          </div>
          <AlertTrendChart :dates="alertTrend.dates" :counts="alertTrend.counts" />
        </div>

        <!-- 资产类型 -->
        <div class="panel">
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
import { ElMessage } from 'element-plus'
import { getDashboardStats, getSparkline, getActivities, getAlertTrend, getDashboardSummary } from '@/api/dashboard'
import { useAuthStore } from '@/stores/modules/auth'
import { Box, Monitor, Warning, Tickets, Connection, Setting, Document } from '@element-plus/icons-vue'
import Sparkline from '@/components/Sparkline.vue'
import AlertTrendChart from '@/components/AlertTrendChart.vue'

const authStore = useAuthStore()

const stats = ref<any>({})
const sparkline = ref<any>({ dates: [], series: { assets: [], online: [], alerts: [], tickets: [] } })
const activities = ref<any[]>([])
const alertTrend = ref<any>({ dates: [], counts: [] })
const summary = ref<any>({})

const activeFilter = ref('all')

const quickActions = [
  { label: 'SSH 终端', icon: Connection, color: '#5e6ad2', bg: 'rgba(94,106,210,0.08)', path: '/assets' },
  { label: '批量执行', icon: Setting, color: '#7c3aed', bg: 'rgba(124,58,237,0.06)', path: '/batch-exec' },
  { label: '巡检任务', icon: Monitor, color: '#22c55e', bg: 'rgba(34,197,94,0.08)', path: '/patrol' },
  { label: '工单中心', icon: Document, color: '#f5a623', bg: 'rgba(245,166,35,0.08)', path: '/tickets' },
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
    if (!arr || arr.length < 2 || arr[arr.length - 2] === 0) return { text: '—', type: 'flat' }
    const pct = Math.round(((arr[arr.length - 1] - arr[arr.length - 2]) / arr[arr.length - 2]) * 100)
    if (pct > 0) return { text: `+${pct}%`, type: 'up' }
    if (pct < 0) return { text: `${pct}%`, type: 'down' }
    return { text: '—', type: 'flat' }
  }

  return [
    { label: '资产总数', value: stats.value.asset_total ?? '-', sparkline: s.assets || [], ...changePct(s.assets), lineColor: '#5e6ad2' },
    { label: '在线主机', value: stats.value.online_hosts ?? '-', sparkline: s.online || [], ...changePct(s.online), lineColor: '#22c55e' },
    { label: '待处理告警', value: stats.value.open_alerts ?? '-', sparkline: s.alerts || [], ...changePct(s.alerts), lineColor: '#e5484d' },
    { label: '待处理工单', value: stats.value.pending_tickets ?? '-', sparkline: s.tickets || [], ...changePct(s.tickets), lineColor: '#f5a623' },
  ]
})

const alertTrendTotal = computed(() => (alertTrend.value.counts || []).reduce((a: number, b: number) => a + b, 0))
const typeBreakdown = computed(() => summary.value.type_breakdown || [])
const maxTypeValue = computed(() => summary.value.max_type_value || 1)
function typePct(val: number) { return Math.round((val / maxTypeValue.value) * 100) }

async function fetchActivities(type?: string) {
  try {
    const res: any = await getActivities(10, type)
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
      getActivities(10),
      getAlertTrend(),
      getDashboardSummary(),
    ])
    stats.value = statsRes.data
    sparkline.value = sparkRes.data
    activities.value = actRes.data?.items || []
    alertTrend.value = trendRes.data
    summary.value = sumRes.data
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '加载失败') }
})
</script>

<style lang="scss" scoped>
.dashboard {
  width: 100%;
  padding-right: 16px;
}

// ── 欢迎区 ──
.welcome {
  margin-bottom: 20px;
  h1 {
    font-size: 20px;
    font-weight: 700;
    color: var(--text-primary);
    letter-spacing: -0.01em;
    margin-bottom: 2px;
  }
  p {
    font-size: 13px;
    color: var(--text-muted);
  }
}

// ── 快捷操作 ──
.quick-actions {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}
.action-item {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 10px;
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: 10px 14px;
  cursor: pointer;
  transition: all 0.15s;
  &:hover {
    border-color: #5e6ad2;
    box-shadow: 0 0 0 1px rgba(94, 106, 210, 0.08);
  }
}
.action-icon {
  width: 30px;
  height: 30px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.action-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

// ── 统计条 ──
.stats-bar {
  display: flex;
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  margin-bottom: 16px;
  overflow: hidden;
}
.stat-item {
  flex: 1;
  padding: 14px 16px;
  & + & {
    border-left: 1px solid var(--border-color);
  }
}
.stat-label {
  font-size: 11px;
  color: var(--text-muted);
  font-weight: 500;
  margin-bottom: 6px;
}
.stat-row {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 6px;
}
.stat-value {
  font-family: 'SF Mono', 'Cascadia Code', 'Fira Code', monospace;
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.02em;
}
.stat-change {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 11px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 4px;
  &.up { color: #22c55e; background: rgba(34, 197, 94, 0.08); }
  &.down { color: #e5484d; background: rgba(229, 72, 77, 0.08); }
  &.flat { color: var(--text-muted); background: #f5f5f5; }
}

// ── 主内容区 ──
.dashboard-grid {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 16px;
}

// ── 面板通用 ──
.panel {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
}
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 16px;
  border-bottom: 1px solid #f0f0f0;
  h3 {
    font-size: 13px;
    font-weight: 600;
    color: var(--text-primary);
  }
}

// ── Filter Pills ──
.filter-pills {
  display: flex;
  gap: 1px;
  background: #f5f5f5;
  border-radius: 5px;
  padding: 1px;
}
.pill {
  padding: 3px 10px;
  border-radius: 4px;
  font-size: 12px;
  color: var(--text-muted);
  cursor: pointer;
  font-weight: 500;
  transition: all 0.12s;
  &.active {
    background: var(--surface-color);
    color: var(--text-primary);
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
  }
  &:hover:not(.active) {
    color: var(--text-secondary);
  }
}

// ── 活动流 ──
.activity-list {
  padding: 8px 16px 16px;
  max-height: 400px;
  overflow-y: auto;
  &::-webkit-scrollbar { width: 4px; }
  &::-webkit-scrollbar-thumb { background: var(--border-color); border-radius: 2px; }
}
.act-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px solid #f5f5f5;
  &:last-child { border-bottom: none; }
}
.act-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  margin-top: 7px;
  flex-shrink: 0;
  &.dot-alert { background: #e5484d; }
  &.dot-ticket { background: #f5a623; }
  &.dot-asset { background: #5e6ad2; }
  &.dot-patrol { background: #22c55e; }
  &.dot-user { background: #7c3aed; }
  &.dot-system { background: var(--text-muted); }
}
.act-body {
  flex: 1;
  min-width: 0;
}
.act-text {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  line-height: 1.5;
}
.act-meta {
  font-size: 11px;
  color: #bbb;
  margin-top: 2px;
}
.act-tag {
  padding: 2px 7px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 600;
  flex-shrink: 0;
  align-self: center;
  &.tag-alert { background: rgba(229, 72, 77, 0.08); color: #e5484d; }
  &.tag-ticket { background: rgba(245, 166, 35, 0.08); color: #d4a017; }
  &.tag-asset { background: rgba(94, 106, 210, 0.08); color: #5e6ad2; }
  &.tag-patrol { background: rgba(34, 197, 94, 0.08); color: #22c55e; }
  &.tag-user { background: rgba(124, 58, 237, 0.06); color: #7c3aed; }
  &.tag-system { background: #f5f5f5; color: var(--text-muted); }
}
.empty-state {
  text-align: center;
  padding: 40px 0;
  p { color: var(--text-muted); font-size: 13px; }
}

// ── 过渡动画 ──
.act-enter-active { transition: all 0.2s ease; }
.act-leave-active { transition: all 0.15s ease; }
.act-enter-from { opacity: 0; transform: translateY(-4px); }
.act-leave-to { opacity: 0; }

// ── 右侧面板 ──
.side-panels {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.trend-meta {
  font-size: 11px;
  color: var(--text-muted);
  font-family: 'SF Mono', 'Cascadia Code', monospace;
}

// ── 资产条形图 ──
.bar-list {
  padding: 12px 16px 16px;
}
.bar-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 0;
  & + & { border-top: 1px solid #f5f5f5; }
}
.bar-label {
  width: 48px;
  font-size: 12px;
  color: var(--text-secondary);
  text-align: right;
  flex-shrink: 0;
}
.bar-track {
  flex: 1;
  height: 4px;
  background: #f5f5f5;
  border-radius: 2px;
  overflow: hidden;
}
.bar-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.6s cubic-bezier(0.22, 1, 0.36, 1);
}
.bar-value {
  width: 24px;
  font-size: 12px;
  font-weight: 700;
  color: var(--text-primary);
  text-align: right;
  font-family: 'SF Mono', 'Cascadia Code', monospace;
}

// ── 响应式 ──
@media (max-width: 1100px) {
  .stats-bar { flex-wrap: wrap; }
  .stat-item { flex: 1 1 45%; }
  .stat-item:nth-child(n+3) { border-top: 1px solid var(--border-color); }
  .dashboard-grid { grid-template-columns: 1fr; }
}
@media (max-width: 600px) {
  .stat-item { flex: 1 1 100%; border-left: none !important; }
  .quick-actions { flex-wrap: wrap; }
  .action-item { flex: 1 1 45%; }
}
</style>
