<template>
  <div v-loading="loading" class="dashboard">
    <section class="page-head">
      <div class="page-copy">
        <p class="page-kicker">值班态首页</p>
        <h1>先看异常，再看影响，再进入处理</h1>
        <p class="page-summary">
          首页优先展示待处理告警、阻塞工单和最近资产异常，把真正需要先点开的对象抬到第一屏。
        </p>
      </div>
      <div class="page-meta">
        <strong>当前值班：{{ authStore.fullName || '管理员' }}</strong>
        <span>{{ currentDateTime }}</span>
        <small>{{ currentDateLabel }}</small>
      </div>
    </section>

    <section class="metric-strip" aria-label="当前风险指标">
      <article v-for="card in metricCards" :key="card.key" class="metric-card" :class="`metric-card--${card.tone}`">
        <div class="metric-card__head">
          <span class="metric-card__label">{{ card.label }}</span>
          <span class="metric-card__dot"></span>
        </div>
        <div class="metric-card__value-row">
          <strong class="metric-card__value">{{ card.value }}</strong>
          <span class="metric-card__delta" :class="`metric-card__delta--${card.deltaType}`">{{ card.delta }}</span>
        </div>
        <p class="metric-card__hint">{{ card.hint }}</p>
        <Sparkline :data="card.series" :color="card.lineColor" :width="132" :height="28" />
      </article>
    </section>

    <div class="dashboard-layout">
      <div class="dashboard-main">
        <section class="panel panel--focus">
          <div class="panel__head">
            <div>
              <h2 class="panel__title">今日关注</h2>
              <p class="panel__hint">比起“最近发生过什么”，这里更强调“值班人应该先打开什么”。</p>
            </div>
          </div>

          <div v-if="focusItems.length" class="focus-list">
            <article v-for="item in focusItems" :key="item.key" class="focus-item">
              <div class="focus-item__badge" :class="`focus-item__badge--${item.tone}`">{{ item.badge }}</div>
              <div class="focus-item__body">
                <div class="focus-item__title-row">
                  <h3 class="focus-item__title">{{ item.title }}</h3>
                  <span class="focus-item__tag" :class="`focus-item__tag--${item.tone}`">{{ item.summaryTag }}</span>
                </div>
                <p class="focus-item__meta">{{ item.meta }}</p>
                <p class="focus-item__detail">{{ item.detail }}</p>
                <div class="focus-item__actions">
                  <button type="button" class="action-button action-button--primary" @click="navigate(item.primaryActionPath)">
                    {{ item.primaryActionLabel }}
                  </button>
                  <button
                    v-if="item.secondaryActionLabel && item.secondaryActionPath"
                    type="button"
                    class="action-button"
                    @click="navigate(item.secondaryActionPath)"
                  >
                    {{ item.secondaryActionLabel }}
                  </button>
                </div>
              </div>
            </article>
          </div>
          <div v-else class="empty-state">
            <p>当前没有需要优先处理的对象，新的告警、工单或资产异常会优先显示在这里。</p>
          </div>
        </section>

        <div class="dashboard-subgrid">
          <section class="panel">
            <div class="panel__head">
              <div>
                <h2 class="panel__title">处置入口</h2>
                <p class="panel__hint">入口本身带状态，不再只是静态跳转。</p>
              </div>
            </div>
            <div class="shortcut-list">
              <button
                v-for="item in shortcutItems"
                :key="item.key"
                type="button"
                class="shortcut-item"
                @click="navigate(item.path)"
              >
                <div class="shortcut-item__icon" :class="`shortcut-item__icon--${item.tone}`">
                  <el-icon>
                    <component :is="shortcutIcons[item.key]" />
                  </el-icon>
                </div>
                <div class="shortcut-item__body">
                  <span class="shortcut-item__label">{{ item.label }}</span>
                  <span class="shortcut-item__desc">{{ item.description }}</span>
                </div>
                <div class="shortcut-item__meta">
                  <strong>{{ item.value }}</strong>
                  <span>{{ item.valueLabel }}</span>
                </div>
              </button>
            </div>
          </section>

          <section class="panel panel--trend">
            <div class="panel__head">
              <div>
                <h2 class="panel__title">告警趋势</h2>
                <p class="panel__hint">趋势保留在辅助判断层，不抢主任务视线。</p>
              </div>
              <span class="panel__meta">近 7 天 · {{ alertTrendTotal }} 次</span>
            </div>
            <div class="trend-panel">
              <AlertTrendChart :dates="alertTrend.dates" :counts="alertTrend.counts" />
            </div>
          </section>
        </div>
      </div>

      <aside class="dashboard-side dashboard-side--summary">
        <section class="panel panel--duty">
          <div class="duty-card">
            <div class="duty-card__head">
              <div>
                <h2 class="panel__title">值班视角摘要</h2>
                <p class="panel__hint">把当前班次最需要的背景认知压缩在这里，先帮助判断，再进入处理。</p>
              </div>
              <div class="duty-card__clock">
                <strong>{{ currentDateTime }}</strong>
                <span>实时值班时间</span>
              </div>
            </div>
            <div class="duty-card__facts">
              <div v-for="fact in dutyFacts" :key="fact.label" class="summary-fact" :class="`summary-fact--${fact.tone}`">
                <span class="summary-fact__label">{{ fact.label }}</span>
                <strong class="summary-fact__value">{{ fact.value }}</strong>
                <p class="summary-fact__hint">{{ fact.hint }}</p>
              </div>
            </div>
          </div>
        </section>

          <section class="panel">
          <div class="panel__head">
            <div>
              <h2 class="panel__title">资产结构</h2>
              <p class="panel__hint">作为背景认知保留，不再占首页主视觉。</p>
            </div>
          </div>
          <div v-if="typeRows.length" class="type-list">
            <div v-for="item in typeRows" :key="item.key" class="type-row">
              <span class="type-row__label">{{ item.label }}</span>
              <progress class="type-row__progress" :class="`type-row__progress--${item.tone}`" :value="item.value" :max="item.max"></progress>
              <strong class="type-row__value">{{ item.value }}</strong>
            </div>
          </div>
          <div v-else class="empty-state empty-state--compact">
            <p>暂无资产类型分布</p>
          </div>
        </section>

        <section class="panel panel--activity">
          <div class="panel__head panel__head--compact">
            <div>
              <h2 class="panel__title">最近活动</h2>
              <p class="panel__hint">保留活动流，但降低权重，不让它压过当前风险对象。</p>
            </div>
            <div class="filter-pills" role="tablist" aria-label="活动筛选">
              <button
                v-for="filter in activityFilters"
                :key="filter.key"
                type="button"
                class="filter-pills__button"
                :class="{ 'is-active': activeFilter === filter.key }"
                @click="handleFilterChange(filter.key)"
              >
                {{ filter.label }}
              </button>
            </div>
          </div>
          <div v-if="formattedActivities.length" class="activity-list">
            <div v-for="item in formattedActivities" :key="`${item.time}-${item.description}`" class="activity-item">
              <div class="activity-item__dot" :class="`activity-item__dot--${item.type}`"></div>
              <div class="activity-item__body">
                <div class="activity-item__title-row">
                  <p class="activity-item__text">{{ item.description }}</p>
                  <span class="activity-item__tag" :class="`activity-item__tag--${item.type}`">{{ item.type_label }}</span>
                </div>
                <p class="activity-item__meta">
                  {{ item.displayTime }}
                  <span v-if="item.username"> · {{ item.username }}</span>
                </p>
              </div>
            </div>
          </div>
          <div v-else class="empty-state empty-state--compact">
            <p>暂无活动记录</p>
          </div>
        </section>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onActivated, onDeactivated, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Connection, Document, Monitor, Setting } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'
import { getActivities, getAlertTrend, getDashboardStats, getDashboardSummary, getSparkline } from '@/api/dashboard'
import AlertTrendChart from '@/components/AlertTrendChart.vue'
import Sparkline from '@/components/Sparkline.vue'
import { useAuthStore } from '@/stores/modules/auth'
import {
  buildDashboardFocusItems,
  buildDashboardMetricCards,
  buildDashboardShortcutItems,
  buildDashboardTypeRows,
  type DashboardQuickStatLike,
  type DashboardShortcutKey,
  type DashboardSparklineLike,
  type DashboardStatsLike,
  type DashboardSummaryLike,
} from '@/utils/dashboard'

interface DashboardActivity {
  time: string
  description: string
  type: 'alert' | 'ticket' | 'asset' | 'patrol' | 'user' | 'system'
  type_label: string
  username?: string
}

const authStore = useAuthStore()
const router = useRouter()

const stats = ref<DashboardStatsLike>({})
const sparkline = ref<DashboardSparklineLike>({ series: { assets: [], online: [], alerts: [], tickets: [] } })
const activities = ref<DashboardActivity[]>([])
const alertTrend = ref<{ dates: string[]; counts: number[] }>({ dates: [], counts: [] })
const summary = ref<DashboardSummaryLike>({})
const loading = ref(false)
const activeFilter = ref('all')
const now = ref(new Date())

let clockTimer: ReturnType<typeof setInterval> | undefined

const shortcutIcons: Record<DashboardShortcutKey, unknown> = {
  ssh: Connection,
  batch: Setting,
  patrol: Monitor,
  tickets: Document,
}

const activityFilters = [
  { key: 'all', label: '全部' },
  { key: 'alert', label: '告警' },
  { key: 'ticket', label: '工单' },
  { key: 'asset', label: '资产' },
  { key: 'patrol', label: '巡检' },
  { key: 'user', label: '用户' },
]

const currentDateTime = computed(() => {
  return now.value.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false })
})

const currentDateLabel = computed(() => {
  return now.value.toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' })
})

const metricCards = computed(() => buildDashboardMetricCards(stats.value, sparkline.value))
const focusItems = computed(() => buildDashboardFocusItems(summary.value))
const shortcutItems = computed(() => buildDashboardShortcutItems(stats.value))
const typeRows = computed(() => buildDashboardTypeRows(summary.value))
const dutyFacts = computed(() => summaryFacts.value.slice(0, 4))

const summaryFacts = computed(() => {
  const quickStats = summary.value.quick_stats || []

  if (quickStats.length) {
    return quickStats.map((item: DashboardQuickStatLike) => ({
      label: item.label || '概览',
      value: item.value || '-',
      hint: item.hint || '暂无说明',
      tone: item.tone === 'red' ? 'danger' : item.tone === 'orange' ? 'warning' : item.tone === 'green' ? 'success' : 'info',
    }))
  }

  const totalAssets = Number(stats.value.asset_total || 0)
  const onlineHosts = Number(stats.value.online_hosts || 0)
  const alertCount = Number(stats.value.open_alerts || 0)
  const ticketCount = Number(stats.value.pending_tickets || 0)
  const ratio = totalAssets ? `${Math.round((onlineHosts / totalAssets) * 100)}%` : '0%'

  return [
    { label: '在线率', value: ratio, hint: `在线 ${onlineHosts} / 总资产 ${totalAssets}`, tone: 'success' },
    { label: '待处理告警', value: String(alertCount), hint: '需要继续跟进的告警数量', tone: 'danger' },
    { label: '处理中工单', value: String(ticketCount), hint: '当前 open / in_progress 工单', tone: 'warning' },
  ]
})

const formattedActivities = computed(() => {
  return activities.value.map((item) => ({
    ...item,
    displayTime: formatActivityTime(item.time),
  }))
})

const alertTrendTotal = computed(() => alertTrend.value.counts.reduce((sum, count) => sum + count, 0))

function startClock() {
  stopClock()
  now.value = new Date()
  clockTimer = setInterval(() => {
    now.value = new Date()
  }, 1000)
}

function stopClock() {
  if (!clockTimer) return
  clearInterval(clockTimer)
  clockTimer = undefined
}

function formatActivityTime(value: string) {
  if (!value) return '--'
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return value
  return parsed.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}

async function fetchActivities(type?: string) {
  try {
    const response: any = await getActivities(10, type)
    activities.value = response.data?.items || []
  } catch {
    activities.value = []
  }
}

async function loadDashboard() {
  loading.value = true
  try {
    const [statsRes, sparkRes, trendRes, summaryRes]: any = await Promise.all([
      getDashboardStats(),
      getSparkline(),
      getAlertTrend(),
      getDashboardSummary(),
    ])

    stats.value = statsRes.data || {}
    sparkline.value = sparkRes.data || { series: { assets: [], online: [], alerts: [], tickets: [] } }
    alertTrend.value = trendRes.data || { dates: [], counts: [] }
    summary.value = summaryRes.data || {}
    await fetchActivities(activeFilter.value === 'all' ? undefined : activeFilter.value)
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '加载失败')
  } finally {
    loading.value = false
  }
}

function handleFilterChange(key: string) {
  activeFilter.value = key
  void fetchActivities(key === 'all' ? undefined : key)
}

function navigate(path: string) {
  router.push(path)
}

onActivated(() => {
  startClock()
  void loadDashboard()
})

onDeactivated(() => {
  stopClock()
})
</script>

<style lang="scss" scoped>
.dashboard {
  width: 100%;
  padding-right: 16px;
}

.page-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 16px;
  margin-bottom: 16px;
}

.page-copy {
  padding-top: 4px;
  min-width: 0;
}

.page-kicker {
  margin: 0 0 8px;
  font-size: 12px;
  color: var(--text-muted);
  font-weight: 600;
}

h1 {
  margin: 0;
  font-size: 32px;
  line-height: 1.12;
  letter-spacing: 0;
  color: var(--text-primary);
  text-wrap: balance;
}

.page-summary {
  margin: 12px 0 0;
  max-width: 58ch;
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.7;
}

.panel,
.metric-card {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}

.page-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
  text-align: right;
  min-width: 188px;
}

.page-meta strong {
  font-size: 15px;
  line-height: 1.3;
  color: var(--text-primary);
}

.page-meta span {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
}

.page-meta small {
  font-size: 12px;
  color: var(--text-muted);
}

.duty-card__head {
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.panel__title {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
}

.panel__hint {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--text-secondary);
}

.duty-card {
  padding: 18px;
  display: grid;
  gap: 14px;
}

.duty-card__clock {
  text-align: right;
}

.duty-card__clock strong {
  display: block;
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 24px;
  line-height: 1;
  color: var(--text-primary);
}

.duty-card__clock span {
  display: block;
  margin-top: 4px;
  font-size: 12px;
  color: var(--text-muted);
}

.duty-card__facts {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.summary-fact {
  padding: 12px;
  border-radius: 8px;
  background: #f7f8fc;
}

.summary-fact__label {
  display: block;
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 4px;
}

.summary-fact__value {
  display: block;
  font-size: 18px;
  font-weight: 700;
  line-height: 1.1;
  color: var(--text-primary);
  margin-bottom: 6px;
}

.summary-fact__hint {
  margin: 0;
  font-size: 12px;
  line-height: 1.5;
  color: var(--text-secondary);
}

.summary-fact--danger {
  background: rgba(229, 72, 77, 0.08);
}

.summary-fact--warning {
  background: rgba(245, 166, 35, 0.1);
}

.summary-fact--success {
  background: rgba(34, 197, 94, 0.08);
}

.summary-fact--info {
  background: rgba(94, 106, 210, 0.08);
}

.metric-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.metric-card {
  padding: 16px;
  min-height: 154px;
  display: grid;
  gap: 10px;
}

.metric-card__head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.metric-card__label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
}

.metric-card__dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
}

.metric-card__value-row {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.metric-card__value {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 32px;
  line-height: 1;
  font-weight: 800;
  color: var(--text-primary);
}

.metric-card__delta {
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  font-family: 'SF Mono', 'Cascadia Code', monospace;
}

.metric-card__delta--up {
  color: #16a34a;
  background: rgba(34, 197, 94, 0.12);
}

.metric-card__delta--down {
  color: #e5484d;
  background: rgba(229, 72, 77, 0.12);
}

.metric-card__delta--flat {
  color: var(--text-muted);
  background: #f5f5f5;
}

.metric-card__hint {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  color: var(--text-secondary);
}

.metric-card--danger {
  color: #e5484d;
}

.metric-card--warning {
  color: #f5a623;
}

.metric-card--success {
  color: #22c55e;
}

.metric-card--info {
  color: #5e6ad2;
}

.dashboard-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.55fr) minmax(320px, 0.95fr);
  gap: 16px;
  align-items: start;
}

.dashboard-main,
.dashboard-side {
  display: grid;
  gap: 16px;
}

.dashboard-subgrid {
  display: grid;
  grid-template-columns: minmax(0, 1.08fr) minmax(0, 0.92fr);
  gap: 16px;
}

.panel__head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  padding: 16px 18px;
  border-bottom: 1px solid #eef1f6;
}

.panel__head--compact {
  align-items: center;
}

.panel--trend .trend-panel {
  padding-top: 16px;
}

.panel__meta {
  font-size: 12px;
  color: var(--text-muted);
  font-family: 'SF Mono', 'Cascadia Code', monospace;
}

.focus-list,
.shortcut-list,
.activity-list,
.type-list {
  display: grid;
}

.focus-item,
.shortcut-item,
.activity-item,
.type-row {
  border-top: 1px solid #eef1f6;
}

.focus-item:first-child,
.shortcut-item:first-child,
.activity-item:first-child,
.type-row:first-child {
  border-top: 0;
}

.focus-item {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 14px;
  padding: 18px;
}

.focus-item__badge,
.focus-item__tag,
.activity-item__tag {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
}

.focus-item__badge {
  padding: 4px 10px;
  height: fit-content;
}

.focus-item__body {
  min-width: 0;
}

.focus-item__title-row,
.activity-item__title-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.focus-item__title {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  line-height: 1.4;
  color: var(--text-primary);
}

.focus-item__tag {
  padding: 3px 8px;
  flex: 0 0 auto;
}

.focus-item__meta,
.focus-item__detail {
  margin: 8px 0 0;
  font-size: 13px;
  line-height: 1.65;
}

.focus-item__meta {
  color: var(--text-secondary);
}

.focus-item__detail {
  color: var(--text-secondary);
  max-width: 64ch;
}

.focus-item__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.action-button {
  min-height: 36px;
  padding: 0 12px;
  border-radius: 8px;
  border: 1px solid var(--border-color);
  background: var(--surface-color);
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: border-color 0.18s ease, background-color 0.18s ease;
}

.action-button:hover,
.shortcut-item:hover,
.filter-pills__button:hover {
  border-color: var(--primary-color);
}

.action-button--primary {
  border-color: var(--primary-color);
  background: var(--primary-color);
  color: #fff;
}

.shortcut-item {
  width: 100%;
  padding: 16px 18px;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 12px;
  background: transparent;
  text-align: left;
  cursor: pointer;
}

.shortcut-item__icon {
  width: 34px;
  height: 34px;
  border-radius: 8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
}

.shortcut-item__body {
  display: grid;
  gap: 3px;
  min-width: 0;
}

.shortcut-item__label {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
}

.shortcut-item__desc {
  font-size: 12px;
  line-height: 1.55;
  color: var(--text-secondary);
}

.shortcut-item__meta {
  text-align: right;
}

.shortcut-item__meta strong {
  display: block;
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 18px;
  line-height: 1;
  color: var(--text-primary);
}

.shortcut-item__meta span {
  display: block;
  margin-top: 4px;
  font-size: 11px;
  color: var(--text-muted);
}

.shortcut-item__icon--info {
  color: #5e6ad2;
  background: rgba(94, 106, 210, 0.1);
}

.shortcut-item__icon--warning {
  color: #f5a623;
  background: rgba(245, 166, 35, 0.12);
}

.shortcut-item__icon--success {
  color: #22c55e;
  background: rgba(34, 197, 94, 0.1);
}

.shortcut-item__icon--danger {
  color: #e5484d;
  background: rgba(229, 72, 77, 0.1);
}

.filter-pills {
  display: inline-flex;
  gap: 2px;
  padding: 2px;
  border-radius: 8px;
  background: #f6f7fb;
}

.filter-pills__button {
  border: 0;
  background: transparent;
  color: var(--text-secondary);
  padding: 6px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.filter-pills__button.is-active {
  background: var(--surface-color);
  color: var(--text-primary);
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05);
}

.activity-item {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 12px;
  padding: 14px 18px;
}

.activity-item__dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-top: 6px;
}

.activity-item__body {
  min-width: 0;
}

.activity-item__text {
  margin: 0;
  font-size: 13px;
  line-height: 1.55;
  color: var(--text-primary);
  font-weight: 600;
}

.activity-item__meta {
  margin: 6px 0 0;
  font-size: 12px;
  color: var(--text-muted);
  font-family: 'SF Mono', 'Cascadia Code', monospace;
}

.activity-item__tag {
  padding: 3px 8px;
  flex: 0 0 auto;
}

.activity-item__dot--alert {
  background: #e5484d;
}

.activity-item__dot--ticket {
  background: #f5a623;
}

.activity-item__dot--asset {
  background: #5e6ad2;
}

.activity-item__dot--patrol {
  background: #22c55e;
}

.activity-item__dot--user,
.activity-item__dot--system {
  background: #7b8190;
}

.focus-item__badge--danger,
.focus-item__tag--danger,
.activity-item__tag--alert {
  color: #e5484d;
  background: rgba(229, 72, 77, 0.1);
}

.focus-item__badge--warning,
.focus-item__tag--warning,
.activity-item__tag--ticket {
  color: #f5a623;
  background: rgba(245, 166, 35, 0.12);
}

.focus-item__badge--success,
.focus-item__tag--success,
.activity-item__tag--patrol {
  color: #22c55e;
  background: rgba(34, 197, 94, 0.1);
}

.focus-item__badge--info,
.focus-item__tag--info,
.activity-item__tag--asset {
  color: #5e6ad2;
  background: rgba(94, 106, 210, 0.1);
}

.focus-item__badge--muted,
.focus-item__tag--muted,
.activity-item__tag--user,
.activity-item__tag--system {
  color: var(--text-secondary);
  background: #f2f4f8;
}

.trend-panel {
  padding: 12px 18px 18px;
}

.type-row {
  display: grid;
  grid-template-columns: 64px minmax(0, 1fr) 32px;
  gap: 10px;
  align-items: center;
  padding: 12px 18px;
}

.type-row__label {
  font-size: 12px;
  color: var(--text-secondary);
  font-weight: 600;
  text-align: right;
}

.type-row__value {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 12px;
  color: var(--text-primary);
  text-align: right;
}

.type-row__progress {
  width: 100%;
  height: 8px;
  appearance: none;
  border: 0;
}

.type-row__progress::-webkit-progress-bar {
  background: #edf0f5;
  border-radius: 999px;
}

.type-row__progress::-webkit-progress-value {
  border-radius: 999px;
}

.type-row__progress::-moz-progress-bar {
  border-radius: 999px;
}

.type-row__progress--blue::-webkit-progress-value,
.type-row__progress--blue::-moz-progress-bar {
  background: #3b82f6;
}

.type-row__progress--violet::-webkit-progress-value,
.type-row__progress--violet::-moz-progress-bar {
  background: #8b5cf6;
}

.type-row__progress--cyan::-webkit-progress-value,
.type-row__progress--cyan::-moz-progress-bar {
  background: #06b6d4;
}

.type-row__progress--amber::-webkit-progress-value,
.type-row__progress--amber::-moz-progress-bar {
  background: #f59e0b;
}

.type-row__progress--slate::-webkit-progress-value,
.type-row__progress--slate::-moz-progress-bar {
  background: #94a3b8;
}

.empty-state {
  padding: 24px 18px;
  color: var(--text-muted);
  font-size: 13px;
  line-height: 1.6;
}

.empty-state p {
  margin: 0;
}

.empty-state--compact {
  padding-top: 18px;
  padding-bottom: 18px;
}

@media (prefers-reduced-motion: reduce) {
  .action-button,
  .shortcut-item,
  .filter-pills__button {
    transition: none;
  }
}

@media (max-width: 1040px) {
  .metric-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 960px) {
  .dashboard-layout,
  .dashboard-subgrid,
  .duty-card__facts {
    grid-template-columns: 1fr;
  }

  .page-head {
    align-items: flex-start;
    flex-direction: column;
  }
}

@media (max-width: 640px) {
  .dashboard {
    padding-right: 0;
  }

      h1 {
        font-size: 28px;
      }

      .metric-strip {
        grid-template-columns: 1fr;
      }

      .panel__head,
      .panel__head--compact,
      .duty-card__head,
      .focus-item,
      .shortcut-item,
      .type-row,
      .focus-item__title-row,
      .activity-item__title-row {
    grid-template-columns: 1fr;
    flex-direction: column;
    align-items: stretch;
  }

      .page-meta,
      .duty-card__clock,
      .shortcut-item__meta,
      .type-row__label,
      .type-row__value {
        text-align: left;
        align-items: flex-start;
      }

  .shortcut-item {
    grid-template-columns: auto minmax(0, 1fr);
  }

  .shortcut-item__meta {
    grid-column: 1 / -1;
  }

  .type-row {
    grid-template-columns: 1fr;
  }

  .filter-pills {
    width: 100%;
    overflow-x: auto;
  }
}
</style>
