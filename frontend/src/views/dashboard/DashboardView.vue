<template>
  <div v-loading="loading" class="command-dashboard">
    <header class="command-header">
      <div class="command-heading">
        <div class="command-kicker">
          <span class="live-dot" aria-hidden="true"></span>
          当前值班 · {{ authStore.fullName || '管理员' }}
        </div>
        <h1>事件指挥台</h1>
        <p>10 秒发现异常，30 秒定位影响，1 分钟进入处置。</p>
      </div>

      <div class="command-meta">
        <div class="command-clock" aria-label="当前时间">
          <strong>{{ currentTime }}</strong>
          <span>{{ currentDateLabel }}</span>
        </div>
        <button
          type="button"
          class="refresh-button"
          :disabled="refreshing"
          aria-label="刷新仪表盘数据"
          @click="refreshDashboard(true)"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M20 11a8 8 0 1 0-2.34 5.66M20 4v7h-7" />
          </svg>
          {{ refreshing ? '刷新中' : '刷新' }}
        </button>
        <span class="updated-at">更新于 {{ lastUpdatedLabel }}</span>
      </div>
    </header>

    <section class="status-strip" aria-label="当前运行态势">
      <article
        v-for="metric in healthMetrics"
        :key="metric.key"
        class="status-metric"
        :class="`status-metric--${metric.tone}`"
      >
        <div class="status-metric__label">
          <span class="status-indicator" aria-hidden="true"></span>
          {{ metric.label }}
        </div>
        <div class="status-metric__value">
          {{ metric.value }}<small v-if="metric.unit">{{ metric.unit }}</small>
        </div>
        <p>{{ metric.hint }}</p>
      </article>
    </section>

    <div v-if="coreError" class="notice notice--danger" role="alert">
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M12 9v4m0 4h.01M10.3 3.8 2.4 17.5A2 2 0 0 0 4.1 20h15.8a2 2 0 0 0 1.7-2.5L13.7 3.8a2 2 0 0 0-3.4 0Z" />
      </svg>
      部分核心数据加载失败，页面已保留成功返回的内容。可稍后刷新重试。
    </div>

    <main class="command-layout">
      <div class="primary-column">
        <section class="command-panel event-queue" aria-labelledby="event-queue-title">
          <div class="panel-header">
            <div>
              <div class="panel-heading-line">
                <h2 id="event-queue-title">优先事件队列</h2>
                <span class="count-badge">{{ focusItems.length }}</span>
              </div>
              <p>按严重程度聚合告警、工单与资产变化，先处理最可能扩大影响的事项。</p>
            </div>
            <div class="segmented-control" role="group" aria-label="事件类型筛选">
              <button
                v-for="filter in focusFilters"
                :key="filter.key"
                type="button"
                :aria-pressed="activeFocusFilter === filter.key"
                :class="{ active: activeFocusFilter === filter.key }"
                @click="handleFocusFilter(filter.key)"
              >
                {{ filter.label }}
              </button>
            </div>
          </div>

          <div v-if="filteredFocusItems.length" class="event-list">
            <button
              v-for="item in filteredFocusItems"
              :key="item.key"
              type="button"
              class="event-row"
              :class="[`event-row--${item.tone}`, { selected: activeFocusItem?.key === item.key }]"
              :aria-label="`查看事件：${item.title}`"
              @click="selectEvent(item)"
            >
              <span class="event-severity" :class="toneClass(item.tone)">{{ item.badge }}</span>
              <span class="event-copy">
                <strong>{{ item.title }}</strong>
                <span class="event-meta">{{ item.meta }}</span>
                <span class="event-description">{{ item.detail }}</span>
              </span>
              <span class="event-side">
                <span>{{ item.summaryTag }}</span>
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="m9 18 6-6-6-6" />
                </svg>
              </span>
            </button>
          </div>

          <div v-else class="empty-state">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M20 6 9 17l-5-5" />
            </svg>
            <strong>当前没有匹配的优先事件</strong>
            <span>新的告警、工单或资产异常会自动进入这里。</span>
          </div>
        </section>

        <section class="command-panel resource-panel" aria-labelledby="resource-title">
          <div class="panel-header">
            <div>
              <div class="panel-heading-line">
                <h2 id="resource-title">资源健康</h2>
                <span class="coverage-badge" :class="coverageToneClass">
                  采集覆盖 {{ resourceCoverageLabel }}
                </span>
              </div>
              <p>CPU（容量加权）与内存（总体使用）按全主机池容量计算；P95 与热点数用于识别局部过载。</p>
            </div>
            <button type="button" class="text-action" @click="navigate('/monitoring/hosts')">
              查看主机明细
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m9 18 6-6-6-6" /></svg>
            </button>
          </div>

          <div v-if="resourceError" class="notice notice--warning" role="status">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M12 9v4m0 4h.01M10.3 3.8 2.4 17.5A2 2 0 0 0 4.1 20h15.8a2 2 0 0 0 1.7-2.5L13.7 3.8a2 2 0 0 0-3.4 0Z" />
            </svg>
            Prometheus 资源聚合暂不可用，不影响告警、工单与资产数据查看。
          </div>

          <div class="table-wrapper">
            <table class="resource-table">
              <thead>
                <tr>
                  <th scope="col">资源指标</th>
                  <th scope="col">总体使用</th>
                  <th scope="col">P95</th>
                  <th scope="col">热点主机</th>
                  <th scope="col">容量口径</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in resourceRows" :key="row.key">
                  <th scope="row">
                    <span class="resource-name">{{ row.label }}</span>
                    <span class="resource-state" :class="toneClass(row.tone)">{{ resourceStateLabel(row.tone) }}</span>
                  </th>
                  <td class="resource-usage">
                    <div class="resource-value">{{ row.valueLabel }}</div>
                    <progress
                      class="resource-progress"
                      :class="`resource-progress--${row.tone}`"
                      :value="row.value ?? 0"
                      max="100"
                      :aria-label="`${row.label}总体使用率${row.valueLabel}`"
                    >
                      {{ row.valueLabel }}
                    </progress>
                  </td>
                  <td><strong class="mono-value">{{ row.p95Label }}</strong></td>
                  <td><span :class="{ 'hot-hosts': row.hotHosts > 0 }">{{ row.hotHostLabel }}</span></td>
                  <td>{{ row.detail }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <footer class="resource-footnote">
            <span>CPU = Σ（单机 CPU% × 核心数）÷ Σ核心数</span>
            <span>内存 = Σ已用字节 ÷ Σ总字节</span>
            <span>根分区 = Σ已用字节 ÷ Σ总字节</span>
            <span v-if="resourcePool?.unmonitored">{{ resourcePool.unmonitored }} 台主机未纳入容量汇总</span>
          </footer>
        </section>

        <section class="command-panel activity-panel" aria-labelledby="activity-title">
          <div class="panel-header panel-header--compact">
            <div>
              <h2 id="activity-title">最近活动</h2>
              <p>保留处置链路中的关键操作，便于接班时快速回看。</p>
            </div>
            <div class="segmented-control segmented-control--scroll" role="group" aria-label="活动类型筛选">
              <button
                v-for="filter in activityFilters"
                :key="filter.key"
                type="button"
                :aria-pressed="activeActivityFilter === filter.key"
                :class="{ active: activeActivityFilter === filter.key }"
                @click="handleActivityFilter(filter.key)"
              >
                {{ filter.label }}
              </button>
            </div>
          </div>

          <ol v-if="formattedActivities.length" class="activity-timeline">
            <li v-for="activity in formattedActivities" :key="`${activity.time}-${activity.description}`">
              <span class="timeline-marker" :class="activityToneClass(activity.type)" aria-hidden="true"></span>
              <div class="timeline-copy">
                <div>
                  <strong>{{ activity.description }}</strong>
                  <span>{{ activity.type_label }}</span>
                </div>
                <p v-if="activity.detail">{{ activity.detail }}</p>
                <time>{{ activity.displayTime }}<template v-if="activity.username"> · {{ activity.username }}</template></time>
              </div>
            </li>
          </ol>
          <div v-else class="empty-state empty-state--small">
            <strong>暂无活动记录</strong>
            <span>系统关键操作会在这里形成可回看的时间线。</span>
          </div>
        </section>
      </div>

      <aside class="secondary-column" aria-label="影响与处置辅助信息">
        <section class="command-panel impact-panel" aria-labelledby="impact-title">
          <div class="panel-header panel-header--compact">
            <div>
              <h2 id="impact-title">影响与处置</h2>
              <p>当前选中事件的定位线索与下一步入口。</p>
            </div>
            <button
              v-if="activeFocusItem"
              type="button"
              class="icon-button"
              aria-label="打开事件详情"
              @click="openEventDrawer"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M8 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-3M15 3h6v6m-9 3 9-9" />
              </svg>
            </button>
          </div>

          <div v-if="activeFocusItem" class="impact-content">
            <div class="impact-event">
              <span class="event-severity" :class="toneClass(activeFocusItem.tone)">{{ activeFocusItem.badge }}</span>
              <h3>{{ activeFocusItem.title }}</h3>
              <p>{{ activeFocusItem.detail }}</p>
            </div>

            <ol class="response-steps" aria-label="事件处置路径">
              <li>
                <span>01</span>
                <div><strong>发现</strong><p>{{ activeFocusItem.summaryTag }} 已进入优先队列</p></div>
              </li>
              <li>
                <span>02</span>
                <div><strong>定位</strong><p>{{ activeFocusItem.meta }}</p></div>
              </li>
              <li>
                <span>03</span>
                <div><strong>处置</strong><p>{{ activeFocusItem.primaryActionLabel }}</p></div>
              </li>
            </ol>

            <div class="impact-actions">
              <button type="button" class="primary-action" @click="navigate(activeFocusItem.primaryActionPath)">
                {{ activeFocusItem.primaryActionLabel }}
              </button>
              <button
                v-if="activeFocusItem.secondaryActionPath"
                type="button"
                class="secondary-action"
                @click="navigate(activeFocusItem.secondaryActionPath)"
              >
                {{ activeFocusItem.secondaryActionLabel }}
              </button>
              <button type="button" class="secondary-action" @click="openEventDrawer">事件详情</button>
            </div>
          </div>

          <div v-else class="empty-state">
            <strong>当前无优先事件</strong>
            <span>可前往告警或工单列表查看全部事项。</span>
          </div>
        </section>

        <section class="command-panel action-panel" aria-labelledby="action-title">
          <div class="panel-header panel-header--compact">
            <div>
              <h2 id="action-title">值班动作</h2>
              <p>以处置任务组织入口，而不是按系统模块堆叠。</p>
            </div>
          </div>

          <div class="action-list">
            <button type="button" @click="navigate('/monitoring/hosts')">
              <span class="action-icon">
                <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5h16v10H4zM8 19h8m-4-4v4M7 9h.01M10 9h4" /></svg>
              </span>
              <span><strong>打开主机监控</strong><small>{{ onlineHostLabel }} 可进入</small></span>
              <svg class="action-arrow" viewBox="0 0 24 24" aria-hidden="true"><path d="m9 18 6-6-6-6" /></svg>
            </button>
            <button type="button" @click="navigate('/batch-exec')">
              <span class="action-icon">
                <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m8 9 3 3-3 3m5 0h3M4 5h16v14H4z" /></svg>
              </span>
              <span><strong>批量执行任务</strong><small>面向同类主机快速处置</small></span>
              <svg class="action-arrow" viewBox="0 0 24 24" aria-hidden="true"><path d="m9 18 6-6-6-6" /></svg>
            </button>
            <button type="button" @click="navigate('/patrol')">
              <span class="action-icon">
                <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 11 12 14 22 4M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" /></svg>
              </span>
              <span><strong>发起巡检</strong><small>{{ maintenanceAssetLabel }} 需留意</small></span>
              <svg class="action-arrow" viewBox="0 0 24 24" aria-hidden="true"><path d="m9 18 6-6-6-6" /></svg>
            </button>
            <button type="button" @click="navigate('/tickets')">
              <span class="action-icon">
                <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 3h12v18H6zM9 7h6m-6 4h6m-6 4h4" /></svg>
              </span>
              <span><strong>进入工单队列</strong><small>{{ pendingTicketLabel }} 待推进</small></span>
              <svg class="action-arrow" viewBox="0 0 24 24" aria-hidden="true"><path d="m9 18 6-6-6-6" /></svg>
            </button>
          </div>
        </section>

        <section class="command-panel trend-panel" aria-labelledby="trend-title">
          <div class="panel-header panel-header--compact">
            <div>
              <h2 id="trend-title">7 日告警走势</h2>
              <p>趋势只做态势参考，处置优先级以事件队列为准。</p>
            </div>
            <strong class="trend-total">{{ alertTrendTotal }}</strong>
          </div>

          <div v-if="alertTrend.counts.length" class="trend-chart">
            <svg viewBox="0 0 560 128" role="img" aria-label="近七日告警数量折线图" preserveAspectRatio="none">
              <path class="chart-grid" d="M24 24H544M24 64H544M24 104H544" />
              <polyline class="chart-line" :points="alertTrendPoints" />
              <circle
                v-for="point in alertTrendDots"
                :key="`${point.x}-${point.y}`"
                class="chart-dot"
                :cx="point.x"
                :cy="point.y"
                r="3"
              />
            </svg>
            <div class="trend-axis">
              <span v-for="date in alertTrend.dates" :key="date">{{ date }}</span>
            </div>
          </div>
          <div v-else class="empty-state empty-state--small">
            <strong>暂无告警趋势</strong>
            <span>产生告警后会展示最近七日变化。</span>
          </div>
        </section>
      </aside>
    </main>

    <el-drawer
      v-model="eventDrawerOpen"
      title="事件详情"
      direction="rtl"
      size="420px"
      class="event-drawer"
    >
      <div v-if="activeFocusItem" class="drawer-content">
        <span class="event-severity" :class="toneClass(activeFocusItem.tone)">{{ activeFocusItem.badge }}</span>
        <h2>{{ activeFocusItem.title }}</h2>
        <dl>
          <div><dt>定位线索</dt><dd>{{ activeFocusItem.meta }}</dd></div>
          <div><dt>当前状态</dt><dd>{{ activeFocusItem.summaryTag }}</dd></div>
          <div><dt>事件描述</dt><dd>{{ activeFocusItem.detail }}</dd></div>
        </dl>
        <div class="drawer-guidance">
          <strong>建议下一步</strong>
          <p>先在对应业务列表核对实时状态，再根据主机监控、工单协作或资产信息继续处置。</p>
        </div>
        <div class="drawer-actions">
          <button type="button" class="primary-action" @click="navigate(activeFocusItem.primaryActionPath)">
            {{ activeFocusItem.primaryActionLabel }}
          </button>
          <button type="button" class="secondary-action" @click="navigate('/monitoring/events')">查看告警事件</button>
          <button type="button" class="secondary-action" @click="navigate('/tickets')">进入工单队列</button>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onActivated, onDeactivated, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import {
  getActivities,
  getAlertTrend,
  getDashboardResourceHealth,
  getDashboardStats,
  getDashboardSummary,
} from '@/api/dashboard'
import { useAuthStore } from '@/stores/modules/auth'
import {
  buildDashboardFocusItems,
  buildDashboardHealthMetrics,
  buildDashboardResourceRows,
  filterDashboardFocusItems,
  type DashboardFocusFilterKey,
  type DashboardFocusItem,
  type DashboardResourceHealthLike,
  type DashboardResourceRow,
  type DashboardStatsLike,
  type DashboardSummaryLike,
} from '@/utils/dashboard'

interface DashboardActivity {
  time: string
  description: string
  detail?: string
  type: 'alert' | 'ticket' | 'asset' | 'patrol' | 'user' | 'system'
  type_label: string
  username?: string
}


const authStore = useAuthStore()
const router = useRouter()

const stats = ref<DashboardStatsLike>({})
const summary = ref<DashboardSummaryLike>({})
const resourceHealth = ref<DashboardResourceHealthLike>()
const activities = ref<DashboardActivity[]>([])
const alertTrend = ref<{ dates: string[]; counts: number[] }>({ dates: [], counts: [] })
const selectedFocusItem = ref<DashboardFocusItem>()
const activeFocusFilter = ref<DashboardFocusFilterKey>('all')
const activeActivityFilter = ref('all')
const loading = ref(false)
const refreshing = ref(false)
const resourceError = ref(false)
const coreError = ref(false)
const eventDrawerOpen = ref(false)
const now = ref(new Date())
const lastUpdated = ref<Date>()

let clockTimer: ReturnType<typeof setInterval> | undefined
let refreshTimer: ReturnType<typeof setInterval> | undefined

const focusFilters: Array<{ key: DashboardFocusFilterKey; label: string }> = [
  { key: 'all', label: '全部' },
  { key: 'high', label: '高优先' },
  { key: 'ticket', label: '工单' },
  { key: 'asset', label: '资产' },
]

const activityFilters = [
  { key: 'all', label: '全部' },
  { key: 'alert', label: '告警' },
  { key: 'ticket', label: '工单' },
  { key: 'asset', label: '资产' },
  { key: 'patrol', label: '巡检' },
]

const currentTime = computed(() => now.value.toLocaleTimeString('zh-CN', {
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
  hour12: false,
}))

const currentDateLabel = computed(() => now.value.toLocaleDateString('zh-CN', {
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  weekday: 'short',
}))

const lastUpdatedLabel = computed(() => {
  if (!lastUpdated.value) return '—'
  return lastUpdated.value.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false })
})

const healthMetrics = computed(() => buildDashboardHealthMetrics(stats.value, resourceHealth.value))
const focusItems = computed(() => buildDashboardFocusItems(summary.value))
const filteredFocusItems = computed(() => filterDashboardFocusItems(
  focusItems.value,
  activeFocusFilter.value,
))
const activeFocusItem = computed(() => {
  const selected = selectedFocusItem.value
  if (selected && filteredFocusItems.value.some((item) => item.key === selected.key)) return selected
  if (filteredFocusItems.value[0]) return filteredFocusItems.value[0]
  return activeFocusFilter.value === 'all' ? focusItems.value[0] : undefined
})
const resourceRows = computed(() => buildDashboardResourceRows(resourceHealth.value))
const resourcePool = computed(() => resourceHealth.value?.host_pool)
const resourceCoverageLabel = computed(() => {
  const pool = resourcePool.value
  if (!pool || resourceError.value) return '—'
  if (!Number(pool.total || 0)) return '暂无主机'
  return `${Number(pool.coverage || 0).toFixed(1)}% · ${pool.monitored || 0}/${pool.total || 0} 台`
})
const coverageToneClass = computed(() => {
  const coverage = Number(resourcePool.value?.coverage || 0)
  if (resourceError.value || !resourcePool.value || !Number(resourcePool.value.total || 0)) return 'tone-muted'
  if (coverage < 80) return 'tone-danger'
  if (coverage < 100) return 'tone-warning'
  return 'tone-success'
})
const formattedActivities = computed(() => activities.value.map((item) => ({
  ...item,
  displayTime: formatActivityTime(item.time),
})))
const alertTrendTotal = computed(() => alertTrend.value.counts.reduce((sum, count) => sum + Number(count || 0), 0))
const alertTrendDots = computed(() => {
  const values = alertTrend.value.counts.map((value) => Number(value || 0))
  if (!values.length) return []
  const max = Math.max(...values, 1)
  const width = 520
  const height = 80
  return values.map((value, index) => ({
    x: 24 + (values.length === 1 ? width / 2 : (index / (values.length - 1)) * width),
    y: 104 - (value / max) * height,
  }))
})
const alertTrendPoints = computed(() => alertTrendDots.value.map((point) => `${point.x},${point.y}`).join(' '))
const onlineHostLabel = computed(() => `${Number(stats.value.online_hosts || 0)}/${Number(stats.value.asset_total || 0)} 在线`)
const maintenanceAssetLabel = computed(() => `${Number(stats.value.maintenance_assets || 0)} 个已关机资产`)
const pendingTicketLabel = computed(() => `${Number(stats.value.pending_tickets || 0)} 个工单`)

function toneClass(tone: DashboardFocusItem['tone'] | DashboardResourceRow['tone']) {
  return `tone-${tone}`
}

function resourceStateLabel(tone: DashboardResourceRow['tone']) {
  return {
    danger: '高风险',
    warning: '需关注',
    success: '正常',
    muted: '不可用',
  }[tone]
}

function activityToneClass(type: DashboardActivity['type']) {
  return {
    alert: 'timeline-marker--danger',
    ticket: 'timeline-marker--warning',
    asset: 'timeline-marker--info',
    patrol: 'timeline-marker--success',
    user: 'timeline-marker--muted',
    system: 'timeline-marker--muted',
  }[type]
}

function formatActivityTime(value: string) {
  if (!value) return '—'
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

function handleFocusFilter(key: DashboardFocusFilterKey) {
  activeFocusFilter.value = key
  selectedFocusItem.value = undefined
}

function selectEvent(item: DashboardFocusItem) {
  selectedFocusItem.value = item
}

function openEventDrawer() {
  if (activeFocusItem.value) eventDrawerOpen.value = true
}

function navigate(path: string) {
  eventDrawerOpen.value = false
  void router.push(path)
}

async function fetchActivities(type?: string) {
  try {
    const response: any = await getActivities(8, type)
    activities.value = response.data?.items || []
  } catch {
    activities.value = []
  }
}

async function handleActivityFilter(key: string) {
  activeActivityFilter.value = key
  await fetchActivities(key === 'all' ? undefined : key)
}

async function refreshDashboard(showFeedback = false) {
  if (refreshing.value) return
  const firstLoad = !lastUpdated.value
  loading.value = firstLoad
  refreshing.value = true
  coreError.value = false
  resourceError.value = false

  const results = await Promise.allSettled([
    getDashboardStats(),
    getAlertTrend(),
    getDashboardSummary(),
    getDashboardResourceHealth(),
    getActivities(8, activeActivityFilter.value === 'all' ? undefined : activeActivityFilter.value),
  ])

  const [statsResult, trendResult, summaryResult, resourceResult, activitiesResult] = results
  if (statsResult.status === 'fulfilled') stats.value = (statsResult.value as any).data || {}
  if (trendResult.status === 'fulfilled') alertTrend.value = (trendResult.value as any).data || { dates: [], counts: [] }
  if (summaryResult.status === 'fulfilled') summary.value = (summaryResult.value as any).data || {}
  if (resourceResult.status === 'fulfilled') {
    resourceHealth.value = (resourceResult.value as any).data || {}
  } else {
    resourceError.value = true
    resourceHealth.value = undefined
  }
  if (activitiesResult.status === 'fulfilled') {
    activities.value = (activitiesResult.value as any).data?.items || []
  }

  coreError.value = [statsResult, trendResult, summaryResult].some((result) => result.status === 'rejected')
  lastUpdated.value = new Date()
  refreshing.value = false
  loading.value = false

  if (showFeedback) {
    if (coreError.value) ElMessage.warning('部分数据刷新失败')
    else ElMessage.success('仪表盘已刷新')
  }
}

function startTimers() {
  stopTimers()
  now.value = new Date()
  clockTimer = setInterval(() => {
    now.value = new Date()
  }, 1000)
  refreshTimer = setInterval(() => {
    void refreshDashboard(false)
  }, 60000)
}

function stopTimers() {
  if (clockTimer) clearInterval(clockTimer)
  if (refreshTimer) clearInterval(refreshTimer)
  clockTimer = undefined
  refreshTimer = undefined
}

onActivated(() => {
  startTimers()
  void refreshDashboard(false)
})

onDeactivated(() => {
  stopTimers()
})
</script>

<style lang="scss" scoped>
.command-dashboard {
  --dashboard-border: color-mix(in srgb, var(--border-color) 88%, var(--text-muted));
  display: grid;
  gap: 16px;
  min-width: 0;
  color: var(--text-primary);
}

.command-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  padding: 4px 2px 8px;
}

.command-heading {
  min-width: 0;
}

.command-kicker {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 650;
  letter-spacing: 0.04em;
}

.live-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--success-color);
  box-shadow: 0 0 0 4px color-mix(in srgb, var(--success-color) 14%, transparent);
}

.command-heading h1 {
  margin: 0;
  font-size: 28px;
  line-height: 1.2;
  letter-spacing: -0.03em;
}

.command-heading p {
  margin-top: 8px;
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.6;
}

.command-meta {
  display: grid;
  grid-template-columns: auto auto;
  align-items: center;
  justify-items: end;
  gap: 5px 12px;
  flex: 0 0 auto;
}

.command-clock {
  display: grid;
  justify-items: end;
  line-height: 1.1;
}

.command-clock strong,
.updated-at,
.mono-value,
.trend-total {
  font-family: "SFMono-Regular", "Cascadia Code", Consolas, monospace;
  font-variant-numeric: tabular-nums;
}

.command-clock strong {
  font-size: 20px;
  letter-spacing: -0.03em;
}

.command-clock span,
.updated-at {
  color: var(--text-muted);
  font-size: 11px;
}

.updated-at {
  grid-column: 1 / -1;
}

.refresh-button,
.icon-button,
.text-action,
.primary-action,
.secondary-action,
.segmented-control button,
.event-row,
.action-list button {
  font: inherit;
}

.refresh-button {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  min-height: 36px;
  padding: 0 13px;
  border: 1px solid var(--dashboard-border);
  border-radius: 6px;
  background: var(--surface-color);
  color: var(--text-primary);
  cursor: pointer;
  transition: border-color 180ms ease-out, background-color 180ms ease-out, color 180ms ease-out;
}

.refresh-button svg,
.text-action svg,
.icon-button svg,
.notice svg,
.event-side svg,
.action-list svg,
.empty-state svg {
  width: 17px;
  height: 17px;
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.8;
}

.refresh-button:hover:not(:disabled) {
  border-color: var(--primary-color);
  color: var(--primary-color);
  background: var(--primary-bg);
}

.refresh-button:disabled {
  cursor: wait;
  opacity: 0.65;
}

.status-strip {
  display: grid;
  grid-template-columns: 1.2fr repeat(4, minmax(0, 1fr));
  overflow: hidden;
  border: 1px solid var(--dashboard-border);
  border-radius: var(--border-radius);
  background: var(--surface-color);
}

.status-metric {
  position: relative;
  min-width: 0;
  padding: 18px 20px;
}

.status-metric + .status-metric {
  border-left: 1px solid var(--dashboard-border);
}

.status-metric::after {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  height: 2px;
  content: "";
  background: transparent;
}

.status-metric--danger::after { background: var(--danger-color); }
.status-metric--warning::after { background: var(--warning-color); }
.status-metric--success::after { background: var(--success-color); }
.status-metric--info::after { background: var(--primary-color); }

.status-metric__label {
  display: flex;
  align-items: center;
  gap: 7px;
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 650;
}

.status-indicator {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--text-muted);
}

.status-metric--danger .status-indicator { background: var(--danger-color); }
.status-metric--warning .status-indicator { background: var(--warning-color); }
.status-metric--success .status-indicator { background: var(--success-color); }
.status-metric--info .status-indicator { background: var(--primary-color); }

.status-metric__value {
  margin-top: 11px;
  font-family: "SFMono-Regular", "Cascadia Code", Consolas, monospace;
  font-size: 27px;
  font-weight: 720;
  line-height: 1;
  letter-spacing: -0.05em;
}

.status-metric__value small {
  margin-left: 4px;
  color: var(--text-muted);
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0;
}

.status-metric p {
  overflow: hidden;
  margin-top: 9px;
  color: var(--text-muted);
  font-size: 11px;
  line-height: 1.4;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.command-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.65fr) minmax(310px, 0.75fr);
  align-items: start;
  gap: 16px;
}

.primary-column,
.secondary-column {
  display: grid;
  gap: 16px;
  min-width: 0;
}

.command-panel {
  min-width: 0;
  border: 1px solid var(--dashboard-border);
  border-radius: var(--border-radius);
  background: var(--surface-color);
}

.panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  padding: 18px 20px;
  border-bottom: 1px solid var(--dashboard-border);
}

.panel-header--compact {
  padding-bottom: 15px;
}

.panel-heading-line {
  display: flex;
  align-items: center;
  gap: 9px;
}

.panel-header h2 {
  margin: 0;
  font-size: 15px;
  line-height: 1.3;
}

.panel-header p {
  margin-top: 5px;
  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.5;
}

.count-badge,
.coverage-badge,
.event-severity,
.resource-state,
.timeline-copy > div > span {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 20px;
  padding: 2px 7px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 650;
  white-space: nowrap;
}

.count-badge {
  min-width: 22px;
  color: var(--primary-color);
  background: var(--primary-bg);
}

.tone-danger {
  color: var(--danger-color);
  background: color-mix(in srgb, var(--danger-color) 10%, transparent);
}

.tone-warning {
  color: color-mix(in srgb, var(--warning-color) 72%, var(--text-primary));
  background: color-mix(in srgb, var(--warning-color) 14%, transparent);
}

.tone-success {
  color: color-mix(in srgb, var(--success-color) 76%, var(--text-primary));
  background: color-mix(in srgb, var(--success-color) 10%, transparent);
}

.tone-info {
  color: var(--primary-color);
  background: var(--primary-bg);
}

.tone-muted {
  color: var(--text-secondary);
  background: color-mix(in srgb, var(--text-muted) 12%, transparent);
}

.segmented-control {
  display: inline-flex;
  padding: 3px;
  border: 1px solid var(--dashboard-border);
  border-radius: 6px;
  background: var(--bg-color);
}

.segmented-control button {
  min-height: 28px;
  padding: 0 10px;
  border: 0;
  border-radius: 4px;
  background: transparent;
  color: var(--text-secondary);
  font-size: 12px;
  cursor: pointer;
  transition: background-color 160ms ease-out, color 160ms ease-out;
}

.segmented-control button:hover,
.segmented-control button.active {
  background: var(--surface-color);
  color: var(--text-primary);
}

.segmented-control button.active {
  box-shadow: inset 0 0 0 1px var(--dashboard-border);
  font-weight: 650;
}

.event-list {
  display: grid;
}

.event-row {
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr) auto;
  align-items: start;
  gap: 14px;
  width: 100%;
  padding: 16px 20px;
  border: 0;
  border-bottom: 1px solid var(--dashboard-border);
  background: transparent;
  color: inherit;
  text-align: left;
  cursor: pointer;
  transition: background-color 180ms ease-out, box-shadow 180ms ease-out;
}

.event-row:last-child {
  border-bottom: 0;
}

.event-row:hover,
.event-row.selected {
  background: color-mix(in srgb, var(--primary-color) 4%, var(--surface-color));
}

.event-row.selected {
  box-shadow: inset 3px 0 0 var(--primary-color);
}

.event-row--danger.selected { box-shadow: inset 3px 0 0 var(--danger-color); }
.event-row--warning.selected { box-shadow: inset 3px 0 0 var(--warning-color); }

.event-copy {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.event-copy strong {
  overflow: hidden;
  font-size: 14px;
  line-height: 1.4;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.event-meta,
.event-description {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.event-meta {
  color: var(--text-muted);
  font-family: "SFMono-Regular", "Cascadia Code", Consolas, monospace;
  font-size: 11px;
}

.event-description {
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.5;
}

.event-side {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-top: 2px;
  color: var(--text-muted);
  font-size: 11px;
  white-space: nowrap;
}

.event-side svg {
  width: 15px;
  height: 15px;
}

.text-action,
.icon-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 0;
  background: transparent;
  color: var(--primary-color);
  cursor: pointer;
}

.text-action {
  gap: 4px;
  min-height: 30px;
  font-size: 12px;
  white-space: nowrap;
}

.text-action svg {
  width: 14px;
  height: 14px;
}

.icon-button {
  width: 32px;
  height: 32px;
  border: 1px solid var(--dashboard-border);
  border-radius: 6px;
}

.notice {
  display: flex;
  align-items: flex-start;
  gap: 9px;
  padding: 11px 14px;
  border: 1px solid currentColor;
  border-radius: 6px;
  font-size: 12px;
  line-height: 1.5;
}

.notice svg {
  flex: 0 0 auto;
  margin-top: 1px;
}

.notice--warning {
  margin: 14px 20px 0;
  color: color-mix(in srgb, var(--warning-color) 68%, var(--text-primary));
  background: color-mix(in srgb, var(--warning-color) 8%, var(--surface-color));
}

.notice--danger {
  color: var(--danger-color);
  background: color-mix(in srgb, var(--danger-color) 7%, var(--surface-color));
}

.resource-table {
  width: 100%;
  min-width: 720px;
  border-collapse: collapse;
  font-size: 12px;
}

.resource-table th,
.resource-table td {
  padding: 14px 18px;
  border-bottom: 1px solid var(--dashboard-border);
  text-align: left;
  vertical-align: middle;
}

.resource-table thead th {
  color: var(--text-muted);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.02em;
  white-space: nowrap;
}

.resource-table tbody tr:last-child th,
.resource-table tbody tr:last-child td {
  border-bottom: 0;
}

.resource-table tbody th {
  min-width: 175px;
}

.resource-name {
  display: block;
  margin-bottom: 6px;
  color: var(--text-primary);
  font-size: 13px;
}

.resource-state {
  min-height: 18px;
  padding: 1px 6px;
}

.resource-usage {
  min-width: 170px;
}

.resource-value {
  margin-bottom: 7px;
  font-family: "SFMono-Regular", "Cascadia Code", Consolas, monospace;
  font-size: 14px;
  font-weight: 700;
}

.resource-progress {
  display: block;
  width: 132px;
  height: 6px;
  overflow: hidden;
  border: 0;
  border-radius: 0;
  appearance: none;
  background: color-mix(in srgb, var(--text-muted) 16%, transparent);
}

.resource-progress::-webkit-progress-bar {
  background: color-mix(in srgb, var(--text-muted) 16%, transparent);
}

.resource-progress::-webkit-progress-value { background: var(--primary-color); }
.resource-progress--danger::-webkit-progress-value { background: var(--danger-color); }
.resource-progress--warning::-webkit-progress-value { background: var(--warning-color); }
.resource-progress--success::-webkit-progress-value { background: var(--success-color); }
.resource-progress--muted::-webkit-progress-value { background: var(--text-muted); }
.resource-progress::-moz-progress-bar { background: var(--primary-color); }
.resource-progress--danger::-moz-progress-bar { background: var(--danger-color); }
.resource-progress--warning::-moz-progress-bar { background: var(--warning-color); }
.resource-progress--success::-moz-progress-bar { background: var(--success-color); }
.resource-progress--muted::-moz-progress-bar { background: var(--text-muted); }

.hot-hosts {
  color: color-mix(in srgb, var(--warning-color) 70%, var(--text-primary));
  font-weight: 650;
}

.resource-footnote {
  display: flex;
  flex-wrap: wrap;
  gap: 7px 18px;
  padding: 11px 18px;
  border-top: 1px solid var(--dashboard-border);
  background: color-mix(in srgb, var(--bg-color) 65%, var(--surface-color));
  color: var(--text-muted);
  font-size: 10px;
  line-height: 1.4;
}

.impact-content {
  padding: 18px 20px 20px;
}

.impact-event h3 {
  margin-top: 11px;
  font-size: 16px;
  line-height: 1.4;
}

.impact-event p {
  margin-top: 7px;
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.65;
}

.response-steps {
  display: grid;
  gap: 0;
  margin: 18px 0;
  list-style: none;
}

.response-steps li {
  position: relative;
  display: grid;
  grid-template-columns: 28px minmax(0, 1fr);
  gap: 11px;
  min-height: 58px;
}

.response-steps li:not(:last-child)::after {
  position: absolute;
  top: 27px;
  bottom: 2px;
  left: 13px;
  width: 1px;
  content: "";
  background: var(--dashboard-border);
}

.response-steps li > span {
  position: relative;
  z-index: 1;
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border: 1px solid var(--dashboard-border);
  border-radius: 50%;
  background: var(--surface-color);
  color: var(--text-muted);
  font-family: "SFMono-Regular", "Cascadia Code", Consolas, monospace;
  font-size: 9px;
}

.response-steps strong {
  display: block;
  padding-top: 2px;
  font-size: 12px;
}

.response-steps p {
  margin-top: 3px;
  color: var(--text-muted);
  font-size: 11px;
  line-height: 1.45;
}

.impact-actions,
.drawer-actions {
  display: grid;
  grid-template-columns: 1fr;
  gap: 8px;
}

.primary-action,
.secondary-action {
  min-height: 36px;
  padding: 0 13px;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 170ms ease-out, border-color 170ms ease-out, color 170ms ease-out;
}

.primary-action {
  border: 1px solid var(--primary-color);
  background: var(--primary-color);
  color: var(--surface-color);
}

.primary-action:hover {
  background: var(--primary-hover);
  border-color: var(--primary-hover);
}

.secondary-action {
  border: 1px solid var(--dashboard-border);
  background: var(--surface-color);
  color: var(--text-primary);
}

.secondary-action:hover {
  border-color: var(--primary-color);
  color: var(--primary-color);
  background: var(--primary-bg);
}

.action-list {
  display: grid;
}

.action-list button {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr) 18px;
  align-items: center;
  gap: 11px;
  width: 100%;
  padding: 13px 18px;
  border: 0;
  border-bottom: 1px solid var(--dashboard-border);
  background: transparent;
  color: inherit;
  text-align: left;
  cursor: pointer;
  transition: background-color 170ms ease-out;
}

.action-list button:last-child {
  border-bottom: 0;
}

.action-list button:hover {
  background: var(--primary-bg);
}

.action-icon {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border: 1px solid var(--dashboard-border);
  border-radius: 6px;
  color: var(--primary-color);
  background: color-mix(in srgb, var(--primary-color) 5%, var(--surface-color));
}

.action-icon svg {
  width: 18px;
  height: 18px;
}

.action-list button > span:nth-child(2) {
  display: grid;
  gap: 3px;
}

.action-list strong {
  font-size: 12px;
}

.action-list small {
  color: var(--text-muted);
  font-size: 10px;
}

.action-arrow {
  color: var(--text-muted);
}

.trend-total {
  color: var(--danger-color);
  font-size: 22px;
}

.trend-chart {
  padding: 14px 18px 16px;
}

.trend-chart svg {
  display: block;
  width: 100%;
  height: 128px;
  overflow: visible;
}

.chart-grid {
  fill: none;
  stroke: var(--dashboard-border);
  stroke-width: 1;
}

.chart-line {
  fill: none;
  stroke: var(--danger-color);
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 2;
}

.chart-dot {
  fill: var(--surface-color);
  stroke: var(--danger-color);
  stroke-width: 2;
}

.trend-axis {
  display: flex;
  justify-content: space-between;
  margin-top: 6px;
  color: var(--text-muted);
  font-family: "SFMono-Regular", "Cascadia Code", Consolas, monospace;
  font-size: 9px;
}

.activity-timeline {
  margin: 0;
  padding: 5px 20px 10px;
  list-style: none;
}

.activity-timeline li {
  position: relative;
  display: grid;
  grid-template-columns: 12px minmax(0, 1fr);
  gap: 12px;
  padding: 12px 0;
}

.activity-timeline li:not(:last-child)::after {
  position: absolute;
  top: 25px;
  bottom: -1px;
  left: 5px;
  width: 1px;
  content: "";
  background: var(--dashboard-border);
}

.timeline-marker {
  position: relative;
  z-index: 1;
  width: 11px;
  height: 11px;
  margin-top: 4px;
  border: 3px solid var(--surface-color);
  border-radius: 50%;
  background: var(--text-muted);
  box-shadow: 0 0 0 1px var(--dashboard-border);
}

.timeline-marker--danger { background: var(--danger-color); }
.timeline-marker--warning { background: var(--warning-color); }
.timeline-marker--success { background: var(--success-color); }
.timeline-marker--info { background: var(--primary-color); }
.timeline-marker--muted { background: var(--text-muted); }

.timeline-copy {
  min-width: 0;
}

.timeline-copy > div {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.timeline-copy strong {
  overflow: hidden;
  font-size: 12px;
  line-height: 1.4;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.timeline-copy > div > span {
  min-height: 18px;
  color: var(--text-secondary);
  background: color-mix(in srgb, var(--text-muted) 10%, transparent);
}

.timeline-copy p {
  margin-top: 4px;
  color: var(--text-secondary);
  font-size: 11px;
  line-height: 1.5;
}

.timeline-copy time {
  display: block;
  margin-top: 4px;
  color: var(--text-muted);
  font-family: "SFMono-Regular", "Cascadia Code", Consolas, monospace;
  font-size: 10px;
}

.empty-state {
  display: grid;
  place-items: center;
  gap: 7px;
  min-height: 180px;
  padding: 28px;
  color: var(--text-muted);
  text-align: center;
}

.empty-state svg {
  width: 28px;
  height: 28px;
  color: var(--success-color);
}

.empty-state strong {
  color: var(--text-secondary);
  font-size: 13px;
}

.empty-state span {
  font-size: 11px;
  line-height: 1.5;
}

.empty-state--small {
  min-height: 110px;
}

.drawer-content {
  display: grid;
  gap: 18px;
}

.drawer-content h2 {
  margin: -5px 0 0;
  font-size: 20px;
  line-height: 1.4;
}

.drawer-content dl {
  display: grid;
  gap: 0;
  margin: 0;
  border-top: 1px solid var(--dashboard-border);
}

.drawer-content dl > div {
  display: grid;
  grid-template-columns: 76px minmax(0, 1fr);
  gap: 12px;
  padding: 13px 0;
  border-bottom: 1px solid var(--dashboard-border);
}

.drawer-content dt {
  color: var(--text-muted);
  font-size: 11px;
}

.drawer-content dd {
  margin: 0;
  color: var(--text-primary);
  font-size: 12px;
  line-height: 1.55;
}

.drawer-guidance {
  padding: 14px;
  border: 1px solid color-mix(in srgb, var(--primary-color) 32%, var(--dashboard-border));
  background: var(--primary-bg);
}

.drawer-guidance strong {
  font-size: 12px;
}

.drawer-guidance p {
  margin-top: 5px;
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.6;
}

:deep(.event-drawer) {
  max-width: 100vw;
}

:deep(.event-drawer .el-drawer__header) {
  margin-bottom: 0;
  padding: 18px 20px;
  border-bottom: 1px solid var(--dashboard-border);
  color: var(--text-primary);
  font-weight: 700;
}

:deep(.event-drawer .el-drawer__body) {
  padding: 20px;
}

button:focus-visible,
.event-row:focus-visible {
  outline: 2px solid var(--primary-color);
  outline-offset: 2px;
}

@media (prefers-reduced-motion: reduce) {
  .refresh-button,
  .primary-action,
  .secondary-action,
  .segmented-control button,
  .event-row,
  .action-list button {
    transition: none;
  }
}

@media (max-width: 1180px) {
  .status-strip {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .status-metric:nth-child(4) {
    border-left: 0;
    border-top: 1px solid var(--dashboard-border);
  }

  .status-metric:nth-child(5) {
    border-top: 1px solid var(--dashboard-border);
  }

  .command-layout {
    grid-template-columns: 1fr;
  }

  .secondary-column {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .impact-panel {
    grid-row: span 2;
  }
}

@media (max-width: 860px) {
  .command-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .command-meta {
    grid-template-columns: auto auto;
    justify-items: start;
  }

  .command-clock {
    justify-items: start;
  }

  .status-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .status-metric:nth-child(3),
  .status-metric:nth-child(5) {
    border-left: 0;
  }

  .status-metric:nth-child(n + 3) {
    border-top: 1px solid var(--dashboard-border);
  }

  .secondary-column {
    grid-template-columns: 1fr;
  }

  .impact-panel {
    grid-row: auto;
  }
}

@media (max-width: 768px) {
  .command-heading h1 {
    font-size: 24px;
  }

  .status-strip {
    grid-template-columns: 1fr;
  }

  .status-metric + .status-metric {
    border-top: 1px solid var(--dashboard-border);
    border-left: 0;
  }

  .panel-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .segmented-control--scroll {
    width: 100%;
    overflow-x: auto;
  }

  .event-row {
    grid-template-columns: 1fr auto;
  }

  .event-row > .event-severity {
    grid-column: 1 / -1;
    justify-self: start;
  }

  .event-description {
    white-space: normal;
  }

  .event-side span {
    display: none;
  }
}
</style>
