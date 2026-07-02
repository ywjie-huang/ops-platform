<template>
  <div v-loading="loading" class="dashboard">
    <section class="page-head">
      <div>
        <div class="eyebrow">Dashboard Preview / Duty First</div>
        <h1>先看异常，再看影响，再进入处理</h1>
        <div class="page-subtitle">
          这个首页直接按预览稿的逻辑展开：第一屏优先回答现在有什么问题、影响到哪里、值班人员该先点哪里。
        </div>
      </div>
      <div class="shift-meta">
        <strong>当前值班：{{ authStore.fullName || '管理员' }}</strong>
        <span>{{ currentDateLabel }} · {{ currentDateTime }}</span>
      </div>
    </section>

    <section class="risk-strip" aria-label="当前风险指标">
      <article v-for="card in metricCards" :key="card.key" class="metric">
        <div class="metric-top">
          <div class="metric-label">{{ card.label }}</div>
          <div class="metric-tone" :class="toneDotClass(card.tone)"></div>
        </div>
        <div class="metric-value">{{ card.value }}</div>
        <div class="metric-hint">{{ card.hint }}</div>
        <div class="metric-tag" :class="toneTagClass(card.tone)">{{ metricTag(card) }}</div>
      </article>
    </section>

    <section class="main-grid">
      <div class="stack">
        <article class="panel">
          <div class="panel-head">
            <div>
              <div class="panel-title">今日关注</div>
              <div class="panel-note">把首页黄金区域留给最需要先处理的对象，而不是最近发生过的所有事情。</div>
            </div>
            <div class="segmented" role="tablist" aria-label="Focus filter">
              <button
                v-for="filter in focusFilters"
                :key="filter.key"
                type="button"
                :class="{ active: activeFocusFilter === filter.key }"
                @click="activeFocusFilter = filter.key"
              >
                {{ filter.label }}
              </button>
            </div>
          </div>

          <div v-if="filteredFocusItems.length" class="focus-list">
            <article v-for="item in filteredFocusItems" :key="item.key" class="focus-item">
              <div class="focus-badge" :class="toneTagClass(item.tone)">{{ item.badge }}</div>
              <div class="focus-main">
                <div class="focus-title">{{ item.title }}</div>
                <div class="focus-meta">{{ item.meta }}</div>
                <div class="focus-desc">{{ item.detail }}</div>
                <div class="focus-actions">
                  <button type="button" class="btn primary" @click="navigate(item.primaryActionPath)">
                    {{ item.primaryActionLabel }}
                  </button>
                  <button
                    v-if="item.secondaryActionLabel && item.secondaryActionPath"
                    type="button"
                    class="btn"
                    @click="navigate(item.secondaryActionPath)"
                  >
                    {{ item.secondaryActionLabel }}
                  </button>
                  <button v-else type="button" class="btn subtle" @click="navigate('/tickets')">
                    继续跟进
                  </button>
                </div>
              </div>
              <div class="eta">
                <strong>{{ focusEta(item).headline }}</strong>
                {{ focusEta(item).detail }}
              </div>
            </article>
          </div>
          <div v-else class="empty-state">
            <p>当前没有需要优先处理的对象，新的告警、工单或资产异常会优先显示在这里。</p>
          </div>
        </article>

        <div class="mini-grid">
          <article class="panel">
            <div class="panel-head">
              <div>
                <div class="panel-title">处置入口</div>
                <div class="panel-note">入口本身带状态，不再只是静态跳转。</div>
              </div>
            </div>
            <div class="shortcut-list">
              <button
                v-for="item in shortcutItems"
                :key="item.key"
                type="button"
                class="shortcut"
                @click="navigate(item.path)"
              >
                <div class="shortcut-icon" :class="toneTagClass(item.tone)">
                  {{ shortcutAbbr[item.key] }}
                </div>
                <div>
                  <div class="shortcut-name">{{ item.label }}</div>
                  <div class="shortcut-desc">{{ item.description }}</div>
                </div>
                <div class="shortcut-state">
                  <strong>{{ item.value }}</strong>
                  {{ item.valueLabel }}
                </div>
              </button>
            </div>
          </article>

          <article class="panel">
            <div class="panel-head">
              <div>
                <div class="panel-title">告警趋势</div>
                <div class="panel-note">趋势保留，但退到辅助判断层，不抢主任务视线。</div>
              </div>
            </div>
            <div class="trend-wrap">
              <div class="trend-legend">
                <span>近 7 天告警总量</span>
                <strong>{{ alertTrendTotal }}</strong>
              </div>
              <AlertTrendChart :dates="alertTrend.dates" :counts="alertTrend.counts" />
              <div class="trend-axis">
                <span v-for="date in alertTrend.dates" :key="date">{{ date }}</span>
              </div>
            </div>
          </article>
        </div>
      </div>

      <div class="stack">
        <article class="panel">
          <div class="duty-card">
            <div class="duty-top">
              <div>
                <div class="duty-title">值班视角摘要</div>
                <div class="duty-copy">这里替代原来的欢迎区，用更少的话告诉值班人当前节奏、值班角色和整体风险态势。</div>
              </div>
              <div class="clock">
                <strong>{{ currentDateTime }}</strong>
                <span>实时更新时间</span>
              </div>
            </div>
            <div class="duty-facts">
              <div v-for="fact in dutyFacts" :key="fact.label" class="fact">
                <div class="fact-label">{{ fact.label }}</div>
                <div class="fact-value">{{ fact.value }}</div>
              </div>
            </div>
          </div>
        </article>

        <article class="panel">
          <div class="panel-head">
            <div>
              <div class="panel-title">资产结构</div>
              <div class="panel-note">降级到辅助信息层，用于背景认知而不是第一优先级判断。</div>
            </div>
          </div>
          <div v-if="typeRows.length" class="asset-list">
            <div v-for="item in typeRows" :key="item.key" class="asset-row">
              <div class="asset-name">{{ item.label }}</div>
              <div class="asset-bar">
                <div class="asset-fill" :class="typeFillClass(item.tone)" :style="{ width: typeFillWidth(item) }"></div>
              </div>
              <div class="asset-value">{{ item.value }}</div>
            </div>
          </div>
          <div v-else class="empty-state empty-state--compact">
            <p>暂无资产类型分布</p>
          </div>
        </article>

        <article class="panel">
          <div class="panel-head">
            <div>
              <div class="panel-title">最近活动</div>
              <div class="panel-note">保留，但降低权重，不让它压过当前风险对象。</div>
            </div>
          </div>
          <div class="activity-list">
            <div class="segmented segmented--activity" role="tablist" aria-label="活动筛选">
              <button
                v-for="filter in activityFilters"
                :key="filter.key"
                type="button"
                :class="{ active: activeFilter === filter.key }"
                @click="handleFilterChange(filter.key)"
              >
                {{ filter.label }}
              </button>
            </div>
            <template v-if="formattedActivities.length">
              <div v-for="item in formattedActivities" :key="`${item.time}-${item.description}`" class="activity-item">
                <div class="activity-top">
                  <div class="activity-text">{{ item.description }}</div>
                  <div class="activity-chip" :class="activityToneClass(item.type)">{{ item.type_label }}</div>
                </div>
                <div class="activity-meta">{{ item.displayTime }}<span v-if="item.username"> · {{ item.username }}</span></div>
              </div>
            </template>
            <div v-else class="empty-state empty-state--compact">
              <p>暂无活动记录</p>
            </div>
          </div>
        </article>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onActivated, onDeactivated, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { getActivities, getAlertTrend, getDashboardStats, getDashboardSummary, getSparkline } from '@/api/dashboard'
import AlertTrendChart from '@/components/AlertTrendChart.vue'
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
const activeFocusFilter = ref('all')
const now = ref(new Date())

let clockTimer: ReturnType<typeof setInterval> | undefined

const shortcutAbbr: Record<DashboardShortcutKey, string> = { ssh: 'SSH', batch: '批', patrol: '巡', tickets: '单' }

const focusFilters = [
  { key: 'all', label: '全部' },
  { key: 'danger', label: '高优先' },
  { key: 'warning', label: '工单' },
  { key: 'info', label: '资产' },
] as const

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
const filteredFocusItems = computed(() => {
  if (activeFocusFilter.value === 'all') return focusItems.value
  return focusItems.value.filter((item) => item.tone === activeFocusFilter.value)
})
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

function toneTagClass(tone: 'danger' | 'warning' | 'success' | 'info' | 'muted') {
  return {
    danger: 'tone-danger',
    warning: 'tone-warning',
    success: 'tone-success',
    info: 'tone-info',
    muted: 'tone-muted',
  }[tone]
}

function toneDotClass(tone: 'danger' | 'warning' | 'success' | 'info') {
  return {
    danger: 'dot-danger',
    warning: 'dot-warning',
    success: 'dot-success',
    info: 'dot-info',
  }[tone]
}

function metricTag(card: (typeof metricCards.value)[number]) {
  if (card.tone === 'danger') return '需要优先处理'
  if (card.tone === 'warning') return '影响服务范围'
  if (card.tone === 'success') return '可控范围'
  return '协作中'
}

function focusEta(item: (typeof focusItems.value)[number]) {
  const match = item.meta.match(/(\d{2}:\d{2})/)
  if (item.tone === 'danger') return { headline: match?.[1] || '立即', detail: '优先排查' }
  if (item.tone === 'warning') return { headline: match?.[1] || '跟进', detail: '最近变更' }
  if (item.tone === 'info') return { headline: match?.[1] || '协同', detail: '继续推进' }
  if (item.tone === 'success') return { headline: match?.[1] || '稳定', detail: '保持观察' }
  return { headline: match?.[1] || '处理中', detail: item.summaryTag }
}

function activityToneClass(type: DashboardActivity['type']) {
  return {
    alert: 'tone-danger',
    ticket: 'tone-warning',
    asset: 'tone-info',
    patrol: 'tone-success',
    user: 'tone-muted',
    system: 'tone-muted',
  }[type]
}

function typeFillClass(tone: (typeof typeRows.value)[number]['tone']) {
  return `asset-fill--${tone}`
}

function typeFillWidth(item: (typeof typeRows.value)[number]) {
  return `${Math.max(8, Math.round((item.value / item.max) * 100))}%`
}

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
  padding: 24px 16px 24px 0;
}

.page-head {
  display: flex;
  justify-content: space-between;
  align-items: end;
  gap: 16px;
  margin-bottom: 24px;
}

.eyebrow {
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 8px;
}

h1 {
  margin: 0;
  font-size: 28px;
  line-height: 1.15;
  letter-spacing: 0;
  color: var(--text-primary);
  overflow-wrap: anywhere;
}

.page-subtitle {
  margin: 12px 0 0;
  max-width: 58ch;
  color: var(--text-secondary);
  font-size: 16px;
  line-height: 1.6;
}

.shift-meta {
  display: grid;
  justify-items: end;
  gap: 2px;
  text-align: right;
}

.shift-meta strong {
  font-size: 16px;
  font-weight: 700;
}

.shift-meta span {
  font-size: 13px;
  color: var(--text-muted);
  font-family: 'SF Mono', 'Cascadia Code', monospace;
}

.risk-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.metric,
.panel {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
  overflow: hidden;
}

.metric {
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 132px;
}

.metric-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.metric-label {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 600;
}

.metric-tone {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  flex: 0 0 auto;
}

.metric-value {
  font-size: 30px;
  line-height: 1;
  font-weight: 800;
  font-family: 'SF Mono', 'Cascadia Code', monospace;
}

.metric-hint {
  font-size: 14px;
  color: var(--text-secondary);
  min-height: 44px;
}

.metric-tag,
.focus-badge,
.activity-chip {
  width: fit-content;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}

.tone-danger {
  background: rgba(229, 72, 77, 0.1);
  color: #e5484d;
}

.tone-warning {
  background: rgba(245, 166, 35, 0.12);
  color: #f5a623;
}

.tone-success {
  background: rgba(34, 197, 94, 0.1);
  color: #22c55e;
}

.tone-info {
  background: rgba(47, 124, 246, 0.1);
  color: #2f7cf6;
}

.tone-muted {
  background: #f3f5f9;
  color: var(--text-secondary);
}

.dot-danger { background: #e5484d; }
.dot-warning { background: #f5a623; }
.dot-success { background: #22c55e; }
.dot-info { background: #2f7cf6; }

.main-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.55fr) minmax(320px, 0.95fr);
  gap: 16px;
  align-items: start;
  margin-top: 16px;
}

.stack {
  display: grid;
  gap: 16px;
}

.panel-head {
  padding: 16px 18px;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.panel-title,
.duty-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
}

.panel-note,
.duty-copy {
  font-size: 13px;
  color: var(--text-muted);
  line-height: 1.5;
}

.focus-list,
.shortcut-list,
.activity-list,
.asset-list {
  display: grid;
}

.segmented {
  display: inline-flex;
  gap: 2px;
  padding: 2px;
  border-radius: 8px;
  background: #f3f5f9;
}

.segmented button {
  border: 0;
  background: transparent;
  color: var(--text-secondary);
  padding: 6px 10px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.segmented button.active {
  background: var(--surface-color);
  color: var(--text-primary);
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}

.segmented--activity {
  margin: 10px 18px 0;
  width: fit-content;
}

.focus-item,
.shortcut,
.activity-item,
.asset-row {
  border-top: 1px solid var(--border-color);
}

.focus-item:first-child,
.shortcut:first-child,
.activity-item:first-child,
.asset-row:first-child {
  border-top: 0;
}

.focus-item {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 16px;
  padding: 18px;
  align-items: start;
}

.focus-main {
  min-width: 0;
}

.focus-title {
  font-size: 16px;
  font-weight: 700;
  margin-bottom: 4px;
}

.focus-meta {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 6px;
}

.focus-desc {
  font-size: 14px;
  color: var(--text-secondary);
  line-height: 1.6;
  max-width: 64ch;
}

.focus-actions {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.btn {
  min-height: 36px;
  padding: 0 12px;
  border-radius: 8px;
  border: 1px solid #d9deea;
  background: var(--surface-color);
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.btn.primary {
  background: var(--primary-color);
  color: #fff;
  border-color: var(--primary-color);
}

.btn.subtle {
  background: #f3f5f9;
  border-color: transparent;
  color: var(--text-secondary);
}

.eta {
  text-align: right;
  font-size: 13px;
  color: var(--text-muted);
  min-width: 88px;
}

.eta strong {
  display: block;
  font-size: 15px;
  color: var(--text-primary);
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  margin-bottom: 2px;
}

.mini-grid {
  display: grid;
  grid-template-columns: 1.08fr 0.92fr;
  gap: 16px;
}

.shortcut {
  padding: 16px 18px;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
  cursor: pointer;
}

.shortcut-icon {
  width: 34px;
  height: 34px;
  border-radius: 8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 700;
}

.shortcut-name {
  font-size: 15px;
  font-weight: 700;
  margin-bottom: 2px;
}

.shortcut-desc {
  font-size: 13px;
  color: var(--text-secondary);
}

.shortcut-state {
  text-align: right;
  font-size: 12px;
  color: var(--text-muted);
}

.shortcut-state strong {
  display: block;
  font-size: 15px;
  color: var(--text-primary);
  font-family: 'SF Mono', 'Cascadia Code', monospace;
}

.trend-wrap {
  padding: 16px 18px 18px;
}

.trend-legend {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  font-size: 13px;
  color: var(--text-muted);
}

.trend-legend strong {
  color: #e5484d;
  font-weight: 700;
  font-family: 'SF Mono', 'Cascadia Code', monospace;
}

.trend-axis {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 10px;
  font-family: 'SF Mono', 'Cascadia Code', monospace;
}

.duty-card {
  padding: 18px;
  display: grid;
  gap: 16px;
}

.duty-top {
  display: flex;
  justify-content: space-between;
  align-items: start;
  gap: 16px;
}

.clock {
  text-align: right;
  font-family: 'SF Mono', 'Cascadia Code', monospace;
}

.clock strong {
  display: block;
  font-size: 24px;
  line-height: 1;
}

.clock span {
  font-size: 12px;
  color: var(--text-muted);
}

.duty-facts {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.fact {
  padding: 12px;
  border-radius: 8px;
  background: #f3f5f9;
}

.fact-label {
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 4px;
}

.fact-value {
  font-size: 15px;
  font-weight: 700;
}

.activity-item,
.asset-row {
  padding: 14px 18px;
  display: grid;
  gap: 2px;
}

.activity-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.activity-text {
  font-size: 14px;
  font-weight: 600;
}

.activity-meta {
  font-size: 12px;
  color: var(--text-muted);
  font-family: 'SF Mono', 'Cascadia Code', monospace;
}

.asset-row {
  grid-template-columns: 84px minmax(0, 1fr) 32px;
  align-items: center;
  gap: 12px;
}

.asset-name {
  font-size: 13px;
  color: var(--text-secondary);
  text-align: right;
  font-weight: 600;
}

.asset-bar {
  height: 8px;
  background: #f3f5f9;
  border-radius: 999px;
  overflow: hidden;
}

.asset-fill {
  height: 100%;
  border-radius: inherit;
}

.asset-fill--blue { background: #5e6ad2; }
.asset-fill--violet { background: #7c3aed; }
.asset-fill--cyan { background: #2f7cf6; }
.asset-fill--amber { background: #f5a623; }
.asset-fill--slate { background: #94a3b8; }

.asset-value {
  font-size: 13px;
  font-weight: 700;
  text-align: right;
  font-family: 'SF Mono', 'Cascadia Code', monospace;
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
  .btn,
  .shortcut,
  .segmented button {
    transition: none;
  }
}

@media (max-width: 1180px) {
  .risk-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .main-grid,
  .mini-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 860px) {
  .page-head {
    align-items: start;
    flex-direction: column;
  }

  .shift-meta {
    justify-items: start;
    text-align: left;
  }
}

@media (max-width: 640px) {
  .dashboard {
    padding-left: 0;
    padding-right: 0;
  }

  h1 {
    font-size: 24px;
    line-height: 1.2;
  }

  .page-subtitle {
    font-size: 15px;
  }

  .risk-strip,
  .duty-card__facts {
    grid-template-columns: 1fr;
  }

  .focus-item,
  .shortcut {
    grid-template-columns: 1fr;
  }

  .eta,
  .shortcut-state {
    text-align: left;
    min-width: 0;
  }

  .panel-head {
    align-items: start;
    flex-direction: column;
  }

  .segmented,
  .segmented--activity {
    width: 100%;
    overflow-x: auto;
    margin-left: 0;
    margin-right: 0;
  }
}
</style>
