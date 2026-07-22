<template>
  <div class="cockpit">
    <div class="aurora" aria-hidden="true">
      <span class="a1"></span>
      <span class="a2"></span>
      <span class="a3"></span>
    </div>
    <div class="grain" aria-hidden="true"></div>

    <div class="shell">
      <!-- 顶栏 -->
      <header class="topbar">
        <div class="brand">
          <div class="brand-mark">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round">
              <path d="M3 12h4l3-8 4 16 3-8h4" />
            </svg>
          </div>
          <div>
            <div class="brand-eyebrow">Mission Control</div>
            <div class="brand-title">巡检态势</div>
          </div>
        </div>
        <div class="topbar-right">
          <span class="live"><i></i>LIVE</span>
          <span class="updated-pill">更新于 {{ updatedClock }}</span>
          <div class="clock-box">
            <div class="clock mono">{{ clockText }}</div>
            <div class="date">{{ dateText }}</div>
          </div>
          <button class="btn-ghost" type="button" @click="router.push('/patrol')">返回指挥台</button>
          <button class="btn-solid" type="button" :disabled="running" @click="handleRun">
            {{ running ? '巡检中…' : '立即巡检' }}
          </button>
        </div>
      </header>

      <main v-loading="loading" class="main">
        <!-- 左：优先风险队列 -->
        <section class="panel anim-panel" style="animation-delay: 0.1s" aria-label="优先风险队列">
          <div class="panel-head">
            <div>
              <div class="eyebrow">Priority Queue</div>
              <h3>优先风险</h3>
            </div>
            <span class="count">{{ queueObjects.length }}</span>
          </div>
          <div class="queue">
            <article
              v-for="(object, index) in queueObjects"
              :key="object.key"
              class="q-item anim-item"
              :class="[toneClass(object.tone), { 'is-new': object.isNew, active: activeRisk === object.key }]"
              :style="{ animationDelay: 0.2 + index * 0.09 + 's' }"
              @click="activeRisk = activeRisk === object.key ? '' : object.key"
            >
              <div class="q-top">
                <span class="q-type">{{ object.categoryLabel }}</span>
                <span class="q-pill" :class="toneClass(object.tone)">{{ object.priority }}</span>
                <span v-if="object.isNew" class="q-pill new">新增</span>
                <span class="q-time">发现于 {{ foundAt }}</span>
              </div>
              <div class="q-name">{{ object.targetName }}</div>
              <div class="q-head">{{ object.headline }}，{{ object.impact }}</div>
              <div v-if="object.worst" class="q-metric">
                <span>{{ object.worst.name }}</span>
                <div class="track">
                  <div class="fill" :style="{ width: entered ? Math.min(object.worst.pct, 100) + '%' : '0%' }"></div>
                </div>
                <b>{{ object.worst.value }}</b>
              </div>
            </article>
            <div v-if="!queueObjects.length" class="empty-state">
              <strong>暂无高优先级风险</strong>
              <span>{{ latestReport ? '最近巡检未发现 P1/P2 对象。' : '执行一次巡检后展示风险队列。' }}</span>
            </div>
          </div>
        </section>

        <!-- 中：健康仪表盘 + 趋势 -->
        <div class="center-stack">
          <section class="panel gauge-panel anim-panel" style="animation-delay: 0.18s" aria-label="全局健康指数">
            <div class="panel-head" style="width: 100%">
              <div>
                <div class="eyebrow">Health Index</div>
                <h3>全局健康指数</h3>
              </div>
              <span class="head-meta">{{ relativeTime(latestReport?.created_at) }} · {{ latestReport?.operator || '系统任务' }}</span>
            </div>
            <div class="gauge-wrap">
              <svg width="300" height="300" viewBox="0 0 300 300">
                <defs>
                  <linearGradient id="gaugeGrad" x1="0" y1="1" x2="1" y2="0">
                    <stop offset="0%" stop-color="#8b8cf8" />
                    <stop offset="55%" stop-color="#4dd8e6" />
                    <stop offset="100%" stop-color="#3ddc97" />
                  </linearGradient>
                </defs>
                <g class="gauge-ticks">
                  <line v-for="(tick, i) in gaugeTicks" :key="i" :x1="tick.x1" :y1="tick.y1" :x2="tick.x2" :y2="tick.y2" />
                </g>
                <circle
                  class="gauge-track"
                  cx="150"
                  cy="150"
                  r="120"
                  fill="none"
                  stroke-width="13"
                  :stroke-dasharray="arcLen"
                  :stroke-dashoffset="arcTrackOffset"
                  stroke-linecap="round"
                  transform="rotate(150 150 150)"
                />
                <circle
                  class="gauge-value"
                  cx="150"
                  cy="150"
                  r="120"
                  fill="none"
                  stroke-width="13"
                  :stroke-dasharray="arcLen"
                  :stroke-dashoffset="arcValueOffset"
                  transform="rotate(150 150 150)"
                />
              </svg>
              <div class="gauge-center">
                <div class="gauge-score mono" :class="{ crit: scoreTone === 'crit' }">
                  {{ latestReport ? displayScore : '—' }}
                </div>
                <div class="gauge-label">Health Score</div>
                <div class="gauge-status" :class="scoreTone">{{ statusText }}</div>
                <button v-if="!latestReport" class="btn-solid" style="margin-top: 12px" :disabled="running" @click="handleRun">
                  立即巡检
                </button>
                <div v-else class="gauge-cats">
                  <span v-for="chip in catChips" :key="chip.key" class="cat-chip">
                    <i :style="{ background: chip.color }"></i>{{ chip.short }} <b>{{ chip.count }}</b>
                  </span>
                </div>
              </div>
            </div>
          </section>

          <section class="panel trend-panel anim-panel" style="animation-delay: 0.26s" aria-label="健康分走势">
            <div class="panel-head">
              <div>
                <div class="eyebrow">Trend</div>
                <h3>健康分走势</h3>
              </div>
              <span class="head-meta">近 {{ trendItems.length }} 次巡检</span>
            </div>
            <div v-if="trendPoints.length" ref="trendBodyRef" class="trend-body">
              <svg
                class="trend-svg"
                viewBox="0 0 640 150"
                preserveAspectRatio="none"
                @mousemove="onTrendHover"
                @mouseleave="hoverIdx = -1"
              >
                <defs>
                  <linearGradient id="trendFill" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="0%" stop-color="rgba(77, 216, 230, 0.2)" />
                    <stop offset="100%" stop-color="rgba(77, 216, 230, 0)" />
                  </linearGradient>
                </defs>
                <line class="grid" x1="14" y1="30" x2="626" y2="30" />
                <line class="grid" x1="14" y1="70" x2="626" y2="70" />
                <line class="grid" x1="14" y1="110" x2="626" y2="110" />
                <line
                  v-if="hoverIdx >= 0 && trendPoints[hoverIdx]"
                  class="crosshair"
                  :x1="trendPoints[hoverIdx].x"
                  y1="14"
                  :x2="trendPoints[hoverIdx].x"
                  y2="126"
                />
                <path class="area" :d="trendArea" />
                <path class="line" :d="trendLine" />
                <circle
                  v-for="(point, i) in trendPoints"
                  :key="i"
                  :class="[point.crit ? 'pt-crit' : 'pt', { 'pt-hover': i === hoverIdx }]"
                  :cx="point.x"
                  :cy="point.y"
                  :r="i === hoverIdx ? 5 : point.crit ? 4 : 3"
                />
                <text
                  v-for="tick in trendTicks"
                  :key="'x' + tick.x"
                  class="axis-label"
                  :x="tick.x"
                  y="146"
                  text-anchor="middle"
                >
                  {{ tick.label }}
                </text>
              </svg>
              <div v-if="hoverItem" class="trend-tip" :style="tipStyle">
                <div>
                  <span class="tt-score mono" :style="{ color: hoverItem.crit ? 'var(--c-crit)' : 'var(--c-cyan)' }">
                    {{ hoverItem.score }}
                  </span>
                  分
                </div>
                <div class="tt-time">{{ hoverItem.full }}</div>
                <div v-if="hoverItem.crit" class="tt-crit">⚠ 含严重项</div>
              </div>
            </div>
            <div v-else class="empty-state">
              <strong>暂无趋势数据</strong>
              <span>执行巡检后展示健康分走势。</span>
            </div>
            <div class="trend-foot">
              <span><i style="background: var(--c-cyan)"></i>健康分</span>
              <span><i style="background: var(--c-crit)"></i>含严重项的批次</span>
              <span v-if="deltaText" style="margin-left: auto">
                较上次 <b :style="{ color: deltaColor }">{{ deltaText }}</b>
              </span>
            </div>
          </section>
        </div>

        <!-- 右：异常构成 + 本批概览 -->
        <div class="right-stack">
          <section class="panel anim-panel" style="animation-delay: 0.22s" aria-label="异常构成">
            <div class="panel-head">
              <div>
                <div class="eyebrow">Issue Types</div>
                <h3>异常构成</h3>
              </div>
            </div>
            <div v-if="donutSegments.length" class="donut-wrap">
              <div class="donut">
                <svg width="128" height="128" viewBox="0 0 128 128">
                  <circle
                    v-for="seg in donutSegments"
                    :key="seg.type"
                    cx="64"
                    cy="64"
                    r="50"
                    fill="none"
                    stroke-width="15"
                    :stroke="seg.color"
                    :stroke-dasharray="seg.dash"
                    :stroke-dashoffset="seg.offset"
                    opacity="0.92"
                  />
                </svg>
                <div class="donut-center">
                  <b class="mono">{{ totalIssues }}</b>
                  <span>异常项</span>
                </div>
              </div>
              <div class="donut-legend">
                <div v-for="seg in donutSegments" :key="'l' + seg.type" class="dl-row">
                  <i :style="{ background: seg.color, color: seg.color }"></i>{{ seg.type }}<b>{{ seg.count }}</b>
                </div>
              </div>
            </div>
            <div v-else class="empty-state">
              <strong>未发现异常</strong>
              <span>{{ latestReport ? '本批巡检全部通过。' : '执行巡检后展示异常构成。' }}</span>
            </div>
          </section>

          <section class="panel anim-panel" style="animation-delay: 0.3s" aria-label="本批概览">
            <div class="panel-head">
              <div>
                <div class="eyebrow">Overview</div>
                <h3>本批概览</h3>
              </div>
            </div>
            <div class="mini-grid">
              <div class="mini-tile crit">
                <span class="mt-label">严重项</span><b>{{ overview.critical }}</b><small>P1 立即处置</small>
              </div>
              <div class="mini-tile warn">
                <span class="mt-label">警告项</span><b>{{ overview.warning }}</b><small>P2 需观察</small>
              </div>
              <div class="mini-tile ok">
                <span class="mt-label">正常项</span><b>{{ overview.normal }}</b><small>共 {{ overview.total }} 项</small>
              </div>
              <div class="mini-tile info">
                <span class="mt-label">覆盖对象</span><b>{{ riskObjects.length }}</b><small>主机 / K8s / 资产</small>
              </div>
            </div>
          </section>
        </div>
      </main>

      <!-- 底部：风险榜单 -->
      <section class="panel rank-panel anim-panel" style="animation-delay: 0.36s" aria-label="风险榜单">
        <div class="panel-head">
          <div>
            <div class="eyebrow">Top Risks</div>
            <h3>风险榜单</h3>
          </div>
          <span class="head-meta">按严重程度排序</span>
        </div>
        <div v-if="topRisks.length" class="rank-grid">
          <article v-for="(object, index) in topRisks" :key="object.key" class="rk" :class="{ first: index === 0 }">
            <div class="rk-top">
              <span class="rk-no">{{ index + 1 }}</span>
              <span class="rk-name">{{ object.targetName }}</span>
              <span class="q-pill" :class="toneClass(object.tone)" style="margin-left: auto">{{ object.priority }}</span>
            </div>
            <div v-if="object.worst" class="rk-metric">
              {{ object.worst.name }} <b>{{ object.worst.value }}</b> / 阈值 {{ object.worst.threshold }}
            </div>
            <div v-if="object.worst" class="rk-track">
              <div
                class="rk-fill"
                :class="toneClass(object.tone)"
                :style="{ width: entered ? Math.min(object.worst.pct, 100) + '%' : '0%' }"
              ></div>
            </div>
          </article>
        </div>
        <div v-else class="empty-state">
          <strong>暂无风险对象</strong>
          <span>执行巡检后按严重程度展示 Top 风险。</span>
        </div>
      </section>
    </div>

    <div v-if="errorMessage" class="error-banner" role="alert">
      <strong>巡检态势加载失败</strong>
      <span>{{ errorMessage }}</span>
      <button type="button" @click="fetchCockpit">重试</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onActivated, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getPatrolReportDetail, getPatrolReports, runPatrol } from '@/api/patrol'
import {
  buildPatrolOverview,
  buildRiskObjects,
  groupRiskObjectsByCategory,
  type PatrolItemLike,
  type PatrolReportLike,
  type PatrolTone,
  type RiskObject,
} from '@/utils/patrolCommand'

interface WorstMetric {
  name: string
  value: string
  threshold: string
  pct: number
}

interface QueueObject extends RiskObject {
  isNew: boolean
  worst: WorstMetric | null
}

interface TrendItem {
  id?: number
  label: string
  full: string
  score: number
  crit: boolean
}

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const running = ref(false)
const reports = ref<PatrolReportLike[]>([])
const latestReport = ref<PatrolReportLike | null>(null)
const detailItems = ref<PatrolItemLike[]>([])
const prevDetailItems = ref<PatrolItemLike[]>([])
const errorMessage = ref('')
const clockText = ref('--:--:--')
const dateText = ref('')
const entered = ref(false)
const activeRisk = ref('')
let clockTimer: number | undefined
let scoreRaf = 0

const overview = computed(() => buildPatrolOverview(latestReport.value))
const riskObjects = computed(() => buildRiskObjects(detailItems.value))

const foundAt = computed(() => relativeTime(latestReport.value?.created_at))

const updatedClock = computed(() => {
  const value = latestReport.value?.created_at
  if (!value) return '--:--'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '--:--'
  return date.toLocaleTimeString('zh-CN', { hour12: false })
})

// ── 风险队列 ──
const queueObjects = computed<QueueObject[]>(() => {
  const prevKeys = new Set(
    prevDetailItems.value.map((item) => `${item.category || 'other'}::${item.target_name || '未知对象'}`),
  )
  return riskObjects.value
    .filter((object) => object.status !== 'normal')
    .map((object) => ({
      ...object,
      isNew: prevDetailItems.value.length > 0 && !prevKeys.has(object.key),
      worst: worstOf(object),
    }))
})

const topRisks = computed(() => queueObjects.value.filter((object) => object.worst).slice(0, 5))

function parseNum(value?: string) {
  const match = String(value ?? '').match(/-?\d+(\.\d+)?/)
  return match ? Number.parseFloat(match[0]) : null
}

function worstOf(object: RiskObject): WorstMetric | null {
  const lead =
    object.items.find((item) => item.status === 'critical') ||
    object.items.find((item) => item.status === 'warning')
  if (!lead) return null
  const value = parseNum(lead.value)
  const threshold = parseNum(lead.threshold)
  let pct = 55
  if (value != null && threshold != null && threshold > 0) {
    pct = Math.min(100, Math.round((value / threshold) * 100))
  } else if (value != null) {
    pct = 70
  }
  return {
    name: lead.check_name || '指标',
    value: lead.value || '-',
    threshold: lead.threshold || '-',
    pct,
  }
}

function toneClass(tone: PatrolTone) {
  if (tone === 'danger') return 'crit'
  if (tone === 'warning') return 'warn'
  return 'ok'
}

// ── 仪表盘 ──
const displayScore = ref(0)
const arcLen = 2 * Math.PI * 120
const arcFraction = 240 / 360
const arcTrackOffset = arcLen * (1 - arcFraction)
const arcValueOffset = computed(() => arcLen * (1 - arcFraction * (displayScore.value / 100)))

const gaugeTicks = computed(() => {
  const ticks: Array<{ x1: number; y1: number; x2: number; y2: number }> = []
  for (let i = 0; i <= 20; i += 1) {
    const angle = ((150 + (i / 20) * 240) * Math.PI) / 180
    const r1 = 132
    const r2 = i % 5 === 0 ? 124 : 128
    ticks.push({
      x1: 150 + Math.cos(angle) * r1,
      y1: 150 + Math.sin(angle) * r1,
      x2: 150 + Math.cos(angle) * r2,
      y2: 150 + Math.sin(angle) * r2,
    })
  }
  return ticks
})

const scoreTone = computed(() => {
  if (!latestReport.value) return ''
  const score = overview.value.healthScore
  if (score >= 95) return 'ok'
  if (score >= 90) return 'warn'
  return 'crit'
})

const statusText = computed(() => {
  if (!latestReport.value) return '暂无报告'
  if (overview.value.critical > 0) return '需立即处置'
  if (overview.value.warning > 0) return '需观察'
  return '运行良好'
})

const LANE_STYLE: Record<string, { short: string; color: string }> = {
  host: { short: '主机', color: '#4dd8e6' },
  k8s: { short: 'K8s', color: '#8b8cf8' },
  asset: { short: '资产', color: '#3ddc97' },
}

const catChips = computed(() =>
  groupRiskObjectsByCategory(riskObjects.value).map((lane) => ({
    key: lane.key,
    short: LANE_STYLE[lane.key]?.short || lane.label,
    color: LANE_STYLE[lane.key]?.color || '#98a2b6',
    count: lane.objects.length,
  })),
)

function animateScore(target: number) {
  cancelAnimationFrame(scoreRaf)
  const from = displayScore.value
  const duration = 1300
  const start = performance.now()
  const frame = (now: number) => {
    const progress = Math.min((now - start) / duration, 1)
    const eased = 1 - Math.pow(1 - progress, 3)
    displayScore.value = Math.round(from + (target - from) * eased)
    if (progress < 1) scoreRaf = requestAnimationFrame(frame)
  }
  scoreRaf = requestAnimationFrame(frame)
}

// ── 趋势 ──
const trendItems = computed<TrendItem[]>(() =>
  [...reports.value].reverse().map((report) => ({
    id: report.id,
    label: barLabel(report.created_at),
    full: fullTime(report.created_at),
    score: buildPatrolOverview(report).healthScore,
    crit: (report.critical_count || 0) > 0,
  })),
)

const trendPoints = computed(() => {
  const list = trendItems.value
  if (!list.length) return [] as Array<{ x: number; y: number; crit: boolean }>
  const scores = list.map((item) => item.score)
  const min = Math.min(...scores, 60)
  const span = Math.max(100 - min, 10)
  return list.map((item, index) => ({
    x: list.length === 1 ? 320 : Math.round(14 + (index * 612) / (list.length - 1)),
    y: Math.round(112 - ((item.score - min) / span) * 88),
    crit: item.crit,
  }))
})

const trendLine = computed(() =>
  trendPoints.value.map((point, index) => (index === 0 ? 'M' : 'L') + point.x + ',' + point.y).join(' '),
)

const trendArea = computed(() => {
  const points = trendPoints.value
  if (!points.length) return ''
  const last = points[points.length - 1]
  const first = points[0]
  return trendLine.value + ` L${last.x},126 L${first.x},126 Z`
})

const trendTicks = computed(() => {
  const step = trendItems.value.length > 8 ? 2 : 1
  return trendItems.value
    .map((item, index) => ({ x: trendPoints.value[index]?.x || 0, label: item.label }))
    .filter((_, index) => index % step === 0)
})

const trendDelta = computed(() => {
  const list = trendItems.value
  return list.length >= 2 ? list[list.length - 1].score - list[list.length - 2].score : null
})

const deltaText = computed(() => {
  if (trendDelta.value == null) return ''
  if (trendDelta.value > 0) return `▲ +${trendDelta.value}`
  if (trendDelta.value < 0) return `▼ ${trendDelta.value}`
  return '— 持平'
})

const deltaColor = computed(() => {
  if (trendDelta.value == null || trendDelta.value === 0) return 'var(--c-soft)'
  return trendDelta.value > 0 ? 'var(--c-ok)' : 'var(--c-crit)'
})

const hoverIdx = ref(-1)
const trendBodyRef = ref<HTMLElement | null>(null)
const tipStyle = ref({ left: '0px', top: '0px' })
const hoverItem = computed(() => (hoverIdx.value >= 0 ? trendItems.value[hoverIdx.value] : null))

function onTrendHover(event: MouseEvent) {
  const el = event.currentTarget as HTMLElement
  const rect = el.getBoundingClientRect()
  const relX = ((event.clientX - rect.left) / rect.width) * 640
  let best = 0
  let bestDist = Infinity
  trendPoints.value.forEach((point, index) => {
    const dist = Math.abs(point.x - relX)
    if (dist < bestDist) {
      bestDist = dist
      best = index
    }
  })
  hoverIdx.value = best
  const body = trendBodyRef.value
  const point = trendPoints.value[best]
  if (body && point) {
    const bodyRect = body.getBoundingClientRect()
    tipStyle.value = {
      left: (point.x / 640) * bodyRect.width + 'px',
      top: (point.y / 150) * bodyRect.height + 'px',
    }
  }
}

// ── 异常构成 ──
const TYPE_COLORS: Record<string, string> = {
  磁盘: '#ff6473',
  内存: '#ffc24b',
  CPU: '#f47c48',
  负载: '#8b8cf8',
  Pod: '#4dd8e6',
  证书: '#3ddc97',
  连接: '#f472b6',
  其他: '#98a2b6',
}

function issueType(checkName = '') {
  if (/磁盘|disk/i.test(checkName)) return '磁盘'
  if (/内存|memory/i.test(checkName)) return '内存'
  if (/cpu/i.test(checkName)) return 'CPU'
  if (/负载|load/i.test(checkName)) return '负载'
  if (/pod|容器|集群|k8s/i.test(checkName)) return 'Pod'
  if (/证书|cert|ssl/i.test(checkName)) return '证书'
  if (/连接|网络|ping|tcp|端口/i.test(checkName)) return '连接'
  return '其他'
}

const typeCounts = computed(() => {
  const counts = new Map<string, number>()
  detailItems.value
    .filter((item) => item.status !== 'normal')
    .forEach((item) => {
      const type = issueType(item.check_name)
      counts.set(type, (counts.get(type) || 0) + 1)
    })
  return Array.from(counts.entries())
    .map(([type, count]) => ({ type, count, color: TYPE_COLORS[type] || TYPE_COLORS['其他'] }))
    .sort((a, b) => b.count - a.count)
})

const totalIssues = computed(() => typeCounts.value.reduce((sum, item) => sum + item.count, 0))

const donutSegments = computed(() => {
  const circumference = 2 * Math.PI * 50
  let acc = 0
  return typeCounts.value.map((item) => {
    const frac = totalIssues.value > 0 ? item.count / totalIssues.value : 0
    const segment = {
      ...item,
      dash: `${Math.max(frac * circumference - 3, 0)} ${circumference - Math.max(frac * circumference - 3, 0)}`,
      offset: -acc * circumference,
    }
    acc += frac
    return segment
  })
})

// ── 数据加载 ──
function getRequestedReportId() {
  const raw = route.query.reportId
  const value = Array.isArray(raw) ? raw[0] : raw
  const parsed = Number(value)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null
}

async function fetchCockpit() {
  loading.value = true
  errorMessage.value = ''
  try {
    const res: any = await getPatrolReports({ page: 1, page_size: 12 })
    reports.value = res.data.items || []
    const requestedReportId = getRequestedReportId()
    latestReport.value =
      (requestedReportId != null ? reports.value.find((item) => item.id === requestedReportId) : null) ||
      reports.value[0] ||
      null

    if (requestedReportId != null && latestReport.value?.id !== requestedReportId) {
      const detail: any = await getPatrolReportDetail(requestedReportId)
      latestReport.value = detail.data.report
      detailItems.value = detail.data.items
    } else if (latestReport.value?.id) {
      const detail: any = await getPatrolReportDetail(latestReport.value.id)
      latestReport.value = detail.data.report
      detailItems.value = detail.data.items
    } else {
      detailItems.value = []
    }

    // 拉取上一批报告用于“新增”判断（失败不影响主流程）
    prevDetailItems.value = []
    const currentIndex = reports.value.findIndex((item) => item.id === latestReport.value?.id)
    const prevReport = reports.value[currentIndex + 1]
    if (prevReport?.id) {
      try {
        const prevDetail: any = await getPatrolReportDetail(prevReport.id)
        prevDetailItems.value = prevDetail.data.items || []
      } catch {
        prevDetailItems.value = []
      }
    }

    if (latestReport.value) animateScore(overview.value.healthScore)
  } catch (e: any) {
    detailItems.value = []
    prevDetailItems.value = []
    errorMessage.value = e?.response?.data?.detail || '请检查巡检报告接口或稍后重试。'
  } finally {
    loading.value = false
  }
}

async function handleRun() {
  running.value = true
  try {
    const res: any = await runPatrol()
    ElMessage.success(`巡检完成：${res.data.summary}`)
    await fetchCockpit()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '巡检执行失败')
  } finally {
    running.value = false
  }
}

// ── 工具 ──
function pad(value: number) {
  return String(value).padStart(2, '0')
}

function barLabel(value?: string) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  const sameDay = date.toDateString() === new Date().toDateString()
  if (sameDay) return `${pad(date.getHours())}:${pad(date.getMinutes())}`
  return `${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

function fullTime(value?: string) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return `${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

function relativeTime(value?: string) {
  if (!value) return '-'
  const timestamp = new Date(value).getTime()
  if (!Number.isFinite(timestamp)) return value
  const diff = Date.now() - timestamp
  const minute = 60 * 1000
  const hour = 60 * minute
  const day = 24 * hour

  if (diff < minute) return '刚刚'
  if (diff < hour) return `${Math.max(1, Math.floor(diff / minute))} 分钟前`
  if (diff < day) return `${Math.floor(diff / hour)} 小时前`
  if (diff < 7 * day) return `${Math.floor(diff / day)} 天前`
  return new Date(value).toLocaleString('zh-CN', { hour12: false })
}

function tickClock() {
  const now = new Date()
  clockText.value = now.toLocaleTimeString('zh-CN', { hour12: false })
  dateText.value = now.toLocaleDateString('zh-CN', { month: 'long', day: 'numeric', weekday: 'long' })
}

onMounted(() => {
  tickClock()
  clockTimer = window.setInterval(tickClock, 1000)
  window.setTimeout(() => {
    entered.value = true
  }, 350)
})

onBeforeUnmount(() => {
  if (clockTimer) window.clearInterval(clockTimer)
  cancelAnimationFrame(scoreRaf)
})

onActivated(fetchCockpit)
</script>

<style scoped>
.cockpit {
  --c-bg: #0a0d14;
  --c-panel: rgba(255, 255, 255, 0.028);
  --c-panel-hover: rgba(255, 255, 255, 0.05);
  --c-hairline: rgba(255, 255, 255, 0.075);
  --c-hairline-strong: rgba(255, 255, 255, 0.14);
  --c-text: #f2f5fa;
  --c-soft: #98a2b6;
  --c-muted: #5f6a80;
  --c-cyan: #4dd8e6;
  --c-violet: #8b8cf8;
  --c-ok: #3ddc97;
  --c-warn: #ffc24b;
  --c-crit: #ff6473;

  position: relative;
  min-height: calc(100vh - var(--header-height));
  padding: 22px 26px 26px;
  color: var(--c-text);
  background: var(--c-bg);
  border-radius: 12px;
  overflow: hidden;
  font-feature-settings: 'tnum';
}

.mono {
  font-family: 'SF Mono', 'JetBrains Mono', Consolas, monospace;
}

/* ═══ 极光背景 ═══ */
.aurora {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 0;
}
.aurora span {
  position: absolute;
  border-radius: 50%;
  filter: blur(90px);
  opacity: 0.5;
}
.aurora .a1 {
  width: 560px;
  height: 560px;
  left: -140px;
  top: -180px;
  background: radial-gradient(circle, rgba(139, 140, 248, 0.2), transparent 65%);
  animation: drift1 26s ease-in-out infinite alternate;
}
.aurora .a2 {
  width: 520px;
  height: 520px;
  right: -120px;
  top: 6%;
  background: radial-gradient(circle, rgba(77, 216, 230, 0.14), transparent 65%);
  animation: drift2 32s ease-in-out infinite alternate;
}
.aurora .a3 {
  width: 620px;
  height: 620px;
  left: 32%;
  bottom: -280px;
  background: radial-gradient(circle, rgba(61, 220, 151, 0.1), transparent 65%);
  animation: drift3 38s ease-in-out infinite alternate;
}
@keyframes drift1 {
  to {
    transform: translate(90px, 60px) scale(1.12);
  }
}
@keyframes drift2 {
  to {
    transform: translate(-80px, 90px) scale(0.92);
  }
}
@keyframes drift3 {
  to {
    transform: translate(-70px, -60px) scale(1.08);
  }
}
.grain {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 0;
  opacity: 0.5;
  background-image: radial-gradient(rgba(255, 255, 255, 0.035) 1px, transparent 1px);
  background-size: 26px 26px;
  mask-image: radial-gradient(ellipse at 50% 30%, #000 20%, transparent 75%);
}

.shell {
  position: relative;
  z-index: 1;
  max-width: 1680px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: calc(100vh - var(--header-height) - 48px);
}

/* ═══ 入场动效 ═══ */
@keyframes fadeUp {
  from {
    opacity: 0;
    transform: translateY(18px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(-14px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}
.anim-panel {
  animation: fadeUp 0.55s cubic-bezier(0.25, 0.8, 0.3, 1) backwards;
}
.anim-item {
  animation: slideIn 0.45s cubic-bezier(0.25, 0.8, 0.3, 1) backwards;
}

/* ═══ 顶栏 ═══ */
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  animation: fadeUp 0.5s backwards;
}
.brand {
  display: flex;
  align-items: center;
  gap: 14px;
}
.brand-mark {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: linear-gradient(140deg, #8b8cf8, #4dd8e6);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 8px 24px -6px rgba(139, 140, 248, 0.55), inset 0 1px 0 rgba(255, 255, 255, 0.35);
}
.brand-mark svg {
  width: 21px;
  height: 21px;
  color: #0a0d14;
}
.brand-eyebrow {
  font-size: 10px;
  letter-spacing: 0.3em;
  color: var(--c-muted);
  text-transform: uppercase;
}
.brand-title {
  font-size: 20px;
  font-weight: 800;
  letter-spacing: 0.06em;
  margin-top: 1px;
}
.topbar-right {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
}
.live {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 11px;
  letter-spacing: 0.14em;
  color: var(--c-soft);
}
.live i {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--c-ok);
  box-shadow: 0 0 10px var(--c-ok);
  animation: livePulse 2s infinite;
}
@keyframes livePulse {
  50% {
    opacity: 0.35;
  }
}
.updated-pill {
  border: 1px solid var(--c-hairline);
  border-radius: 10px;
  padding: 7px 13px;
  background: rgba(255, 255, 255, 0.02);
  font-size: 11px;
  color: var(--c-muted);
  font-variant-numeric: tabular-nums;
}
.clock-box {
  text-align: right;
}
.clock-box .clock {
  font-size: 20px;
  font-weight: 700;
  letter-spacing: 0.04em;
}
.clock-box .date {
  font-size: 11px;
  color: var(--c-muted);
  margin-top: 1px;
}
.btn-ghost {
  background: var(--c-panel);
  border: 1px solid var(--c-hairline-strong);
  color: var(--c-text);
  border-radius: 10px;
  padding: 9px 16px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  font-family: inherit;
  transition: all 0.18s;
}
.btn-ghost:hover {
  background: var(--c-panel-hover);
  border-color: rgba(255, 255, 255, 0.25);
  transform: translateY(-1px);
}
.btn-solid {
  background: linear-gradient(135deg, #8b8cf8, #6a6de8);
  color: #fff;
  border: none;
  border-radius: 10px;
  padding: 10px 18px;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  font-family: inherit;
  box-shadow: 0 8px 22px -8px rgba(139, 140, 248, 0.7);
  transition: all 0.18s;
}
.btn-solid:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 12px 26px -8px rgba(139, 140, 248, 0.85);
}
.btn-solid:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* ═══ 面板通用 ═══ */
.panel {
  background: var(--c-panel);
  border: 1px solid var(--c-hairline);
  border-radius: 18px;
  padding: 18px 20px;
  backdrop-filter: blur(14px);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.05), 0 20px 50px -30px rgba(0, 0, 0, 0.7);
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.panel-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}
.panel-head .eyebrow {
  font-size: 10px;
  letter-spacing: 0.26em;
  color: var(--c-muted);
  text-transform: uppercase;
}
.panel-head h3 {
  font-size: 15px;
  font-weight: 700;
  margin: 3px 0 0;
}
.panel-head .count {
  font-size: 20px;
  font-weight: 800;
  color: var(--c-cyan);
}
.head-meta {
  font-size: 11px;
  color: var(--c-muted);
}

/* ═══ 主网格 ═══ */
.main {
  display: grid;
  grid-template-columns: 350px minmax(0, 1fr) 350px;
  gap: 16px;
  flex: 1;
  min-height: 0;
}

/* ── 左：风险队列 ── */
.queue {
  display: flex;
  flex-direction: column;
  gap: 10px;
  overflow-y: auto;
  flex: 1;
  padding-right: 4px;
}
.queue::-webkit-scrollbar {
  width: 4px;
}
.queue::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.12);
  border-radius: 2px;
}
.q-item {
  border: 1px solid var(--c-hairline);
  border-radius: 14px;
  padding: 13px 15px;
  background: rgba(255, 255, 255, 0.02);
  transition: all 0.2s;
  position: relative;
  overflow: hidden;
  cursor: pointer;
}
.q-item:hover {
  background: var(--c-panel-hover);
  border-color: var(--c-hairline-strong);
  transform: translateX(3px);
}
.q-item.active {
  border-color: rgba(77, 216, 230, 0.45);
  background: rgba(77, 216, 230, 0.05);
}
.q-item::before {
  content: '';
  position: absolute;
  left: 0;
  top: 14px;
  bottom: 14px;
  width: 3px;
  border-radius: 2px;
  background: var(--tone);
  box-shadow: 0 0 12px var(--tone);
}
.q-item.crit {
  --tone: var(--c-crit);
}
.q-item.warn {
  --tone: var(--c-warn);
}
.q-item.crit.is-new::after {
  content: '';
  position: absolute;
  top: 10px;
  right: 10px;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--c-crit);
  box-shadow: 0 0 0 0 rgba(255, 100, 115, 0.6);
  animation: ping 1.6s cubic-bezier(0, 0, 0.2, 1) infinite;
}
@keyframes ping {
  70% {
    box-shadow: 0 0 0 7px rgba(255, 100, 115, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(255, 100, 115, 0);
  }
}
.q-top {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
  padding-left: 8px;
}
.q-type {
  font-size: 10px;
  color: var(--c-muted);
  letter-spacing: 0.05em;
}
.q-pill {
  font-size: 10px;
  font-weight: 800;
  padding: 2px 8px;
  border-radius: 9px;
  white-space: nowrap;
}
.q-pill.crit {
  background: rgba(255, 100, 115, 0.14);
  color: var(--c-crit);
}
.q-pill.warn {
  background: rgba(255, 194, 75, 0.13);
  color: var(--c-warn);
}
.q-pill.new {
  background: rgba(77, 216, 230, 0.13);
  color: var(--c-cyan);
}
.q-time {
  font-size: 10px;
  color: var(--c-muted);
  margin-left: auto;
}
.q-item.is-new .q-time {
  margin-left: 0;
}
.q-name {
  font-size: 13.5px;
  font-weight: 700;
  padding-left: 8px;
}
.q-head {
  font-size: 11.5px;
  color: var(--c-soft);
  margin: 5px 0 9px;
  line-height: 1.55;
  padding-left: 8px;
}
.q-metric {
  display: flex;
  align-items: center;
  gap: 9px;
  padding-left: 8px;
  font-size: 10.5px;
  color: var(--c-muted);
}
.q-metric .track {
  flex: 1;
  height: 4px;
  border-radius: 2px;
  background: rgba(255, 255, 255, 0.07);
  overflow: hidden;
}
.q-metric .fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.8s cubic-bezier(0.3, 0, 0.2, 1);
}
.q-item.crit .fill {
  background: linear-gradient(90deg, var(--c-warn), var(--c-crit));
  box-shadow: 0 0 8px rgba(255, 100, 115, 0.6);
}
.q-item.warn .fill {
  background: var(--c-warn);
}
.q-metric b {
  color: var(--c-text);
}

/* ── 中：仪表盘 + 趋势 ── */
.center-stack {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 0;
}
.gauge-panel {
  flex: 1.15;
  align-items: center;
  position: relative;
  overflow: hidden;
}
.gauge-wrap {
  position: relative;
  width: 300px;
  height: 300px;
  margin: 6px auto 0;
}
.gauge-track {
  stroke: rgba(255, 255, 255, 0.07);
}
.gauge-value {
  stroke: url(#gaugeGrad);
  stroke-linecap: round;
  filter: drop-shadow(0 0 14px rgba(77, 216, 230, 0.45));
  transition: stroke-dashoffset 0.1s linear;
}
.gauge-ticks line {
  stroke: rgba(255, 255, 255, 0.14);
  stroke-width: 1.5;
}
.gauge-center {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
.gauge-score {
  font-size: 76px;
  font-weight: 800;
  letter-spacing: -0.04em;
  line-height: 1;
  text-shadow: 0 0 44px rgba(77, 216, 230, 0.4);
}
.gauge-score.crit {
  color: var(--c-crit);
  text-shadow: 0 0 44px rgba(255, 100, 115, 0.55);
  animation: critBreath 2.2s ease-in-out infinite;
}
@keyframes critBreath {
  50% {
    text-shadow: 0 0 70px rgba(255, 100, 115, 0.85);
  }
}
.gauge-label {
  font-size: 11px;
  letter-spacing: 0.3em;
  color: var(--c-muted);
  margin-top: 8px;
  text-transform: uppercase;
}
.gauge-status {
  margin-top: 10px;
  font-size: 13px;
  font-weight: 700;
  padding: 4px 14px;
  border-radius: 14px;
}
.gauge-status.warn {
  color: var(--c-warn);
  background: rgba(255, 194, 75, 0.1);
}
.gauge-status.ok {
  color: var(--c-ok);
  background: rgba(61, 220, 151, 0.1);
}
.gauge-status.crit {
  color: var(--c-crit);
  background: rgba(255, 100, 115, 0.1);
}
.gauge-cats {
  display: flex;
  gap: 10px;
  margin-top: 18px;
}
.cat-chip {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 11.5px;
  color: var(--c-soft);
  border: 1px solid var(--c-hairline);
  border-radius: 12px;
  padding: 6px 13px;
  background: rgba(255, 255, 255, 0.02);
  transition: all 0.18s;
}
.cat-chip:hover {
  border-color: var(--c-hairline-strong);
  background: var(--c-panel-hover);
}
.cat-chip b {
  color: var(--c-text);
  font-size: 13px;
}
.cat-chip i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.trend-panel {
  flex: 1;
}
.trend-body {
  position: relative;
  flex: 1;
  min-height: 110px;
  display: flex;
}
.trend-svg {
  width: 100%;
  flex: 1;
  min-height: 110px;
  cursor: crosshair;
}
.trend-svg .grid {
  stroke: rgba(255, 255, 255, 0.06);
}
.trend-svg .axis-label {
  fill: var(--c-muted);
  font-size: 9.5px;
}
.trend-svg .area {
  fill: url(#trendFill);
}
.trend-svg .line {
  fill: none;
  stroke: var(--c-cyan);
  stroke-width: 2.2;
  filter: drop-shadow(0 0 6px rgba(77, 216, 230, 0.5));
}
.trend-svg .pt {
  fill: #0a0d14;
  stroke: var(--c-cyan);
  stroke-width: 2;
}
.trend-svg .pt-crit {
  fill: var(--c-crit);
  stroke: var(--c-crit);
}
.trend-svg .pt-hover {
  stroke: #fff;
  stroke-width: 2.5;
}
.trend-svg .crosshair {
  stroke: rgba(255, 255, 255, 0.3);
  stroke-dasharray: 3 4;
}
.trend-tip {
  position: absolute;
  pointer-events: none;
  z-index: 5;
  background: rgba(16, 20, 30, 0.92);
  border: 1px solid var(--c-hairline-strong);
  border-radius: 10px;
  padding: 8px 12px;
  font-size: 11px;
  line-height: 1.6;
  backdrop-filter: blur(8px);
  box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.8);
  transform: translate(-50%, calc(-100% - 12px));
  white-space: nowrap;
}
.trend-tip .tt-score {
  font-size: 16px;
  font-weight: 800;
}
.trend-tip .tt-time {
  color: var(--c-muted);
}
.trend-tip .tt-crit {
  color: var(--c-crit);
  font-weight: 700;
}
.trend-foot {
  display: flex;
  gap: 18px;
  font-size: 11px;
  color: var(--c-soft);
  margin-top: 10px;
}
.trend-foot i {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 6px;
}

/* ── 右：异常构成 + 指标格 ── */
.right-stack {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 0;
}
.donut-wrap {
  display: flex;
  align-items: center;
  gap: 18px;
  flex: 1;
}
.donut {
  position: relative;
  width: 128px;
  height: 128px;
  flex-shrink: 0;
}
.donut svg {
  transform: rotate(-90deg);
}
.donut circle {
  transition: stroke-dasharray 1s cubic-bezier(0.3, 0, 0.2, 1), stroke-dashoffset 1s cubic-bezier(0.3, 0, 0.2, 1);
}
.donut-center {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
.donut-center b {
  font-size: 24px;
  font-weight: 800;
}
.donut-center span {
  font-size: 9.5px;
  color: var(--c-muted);
  letter-spacing: 0.1em;
}
.donut-legend {
  display: flex;
  flex-direction: column;
  gap: 9px;
  flex: 1;
}
.dl-row {
  display: flex;
  align-items: center;
  gap: 9px;
  font-size: 12px;
  color: var(--c-soft);
}
.dl-row i {
  width: 8px;
  height: 8px;
  border-radius: 3px;
  box-shadow: 0 0 8px currentColor;
}
.dl-row b {
  margin-left: auto;
  color: var(--c-text);
  font-size: 13px;
}

.mini-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  flex: 1;
}
.mini-tile {
  border: 1px solid var(--c-hairline);
  border-radius: 14px;
  padding: 13px 15px;
  background: rgba(255, 255, 255, 0.02);
  display: flex;
  flex-direction: column;
  justify-content: center;
  transition: all 0.2s;
}
.mini-tile:hover {
  background: var(--c-panel-hover);
  transform: translateY(-2px);
}
.mini-tile .mt-label {
  font-size: 10.5px;
  color: var(--c-muted);
  letter-spacing: 0.05em;
}
.mini-tile b {
  font-size: 26px;
  font-weight: 800;
  line-height: 1.3;
}
.mini-tile.crit b {
  color: var(--c-crit);
  text-shadow: 0 0 18px rgba(255, 100, 115, 0.4);
}
.mini-tile.warn b {
  color: var(--c-warn);
  text-shadow: 0 0 18px rgba(255, 194, 75, 0.35);
}
.mini-tile.ok b {
  color: var(--c-ok);
  text-shadow: 0 0 18px rgba(61, 220, 151, 0.35);
}
.mini-tile.info b {
  color: var(--c-cyan);
  text-shadow: 0 0 18px rgba(77, 216, 230, 0.35);
}
.mini-tile small {
  font-size: 10.5px;
  color: var(--c-muted);
}

/* ═══ 底部榜单 ═══ */
.rank-panel {
  padding-bottom: 14px;
}
.rank-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 14px;
}
.rk {
  border: 1px solid var(--c-hairline);
  border-radius: 14px;
  padding: 13px 15px;
  background: rgba(255, 255, 255, 0.02);
  transition: all 0.2s;
  position: relative;
}
.rk:hover {
  background: var(--c-panel-hover);
  transform: translateY(-3px);
  border-color: var(--c-hairline-strong);
}
.rk.first:hover {
  box-shadow: 0 14px 34px -14px rgba(255, 100, 115, 0.4);
}
.rk-top {
  display: flex;
  align-items: center;
  gap: 9px;
  margin-bottom: 7px;
}
.rk-no {
  width: 23px;
  height: 23px;
  border-radius: 8px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 800;
  background: rgba(255, 255, 255, 0.07);
  color: var(--c-soft);
}
.rk.first .rk-no {
  background: linear-gradient(135deg, #ff8a94, var(--c-crit));
  color: #fff;
  box-shadow: 0 0 16px rgba(255, 100, 115, 0.55);
}
.rk-name {
  font-size: 12.5px;
  font-weight: 700;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.rk-metric {
  font-size: 10.5px;
  color: var(--c-muted);
  margin-bottom: 7px;
}
.rk-metric b {
  color: var(--c-text);
  font-size: 11.5px;
}
.rk-track {
  height: 5px;
  border-radius: 3px;
  background: rgba(255, 255, 255, 0.07);
  overflow: hidden;
}
.rk-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.9s cubic-bezier(0.3, 0, 0.2, 1);
}
.rk-fill.crit {
  background: linear-gradient(90deg, var(--c-warn), var(--c-crit));
  box-shadow: 0 0 10px rgba(255, 100, 115, 0.5);
}
.rk-fill.warn {
  background: linear-gradient(90deg, #ffd97a, var(--c-warn));
}

/* ═══ 空态 / 错误 ═══ */
.empty-state {
  flex: 1;
  min-height: 100px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  color: var(--c-soft);
  text-align: center;
  border: 1px dashed var(--c-hairline);
  border-radius: 12px;
  padding: 18px;
}
.empty-state strong {
  color: var(--c-text);
  font-size: 13px;
}
.empty-state span {
  font-size: 11.5px;
}

.error-banner {
  position: absolute;
  right: 26px;
  bottom: 26px;
  z-index: 10;
  max-width: min(420px, calc(100% - 52px));
  padding: 14px 16px;
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 4px 12px;
  border: 1px solid rgba(255, 100, 115, 0.4);
  border-radius: 14px;
  background: rgba(16, 20, 30, 0.95);
  backdrop-filter: blur(10px);
}
.error-banner span {
  color: var(--c-soft);
  font-size: 12px;
}
.error-banner button {
  grid-row: 1 / span 2;
  align-self: center;
  min-height: 34px;
  padding: 0 14px;
  border: 1px solid rgba(255, 100, 115, 0.4);
  border-radius: 8px;
  color: var(--c-crit);
  background: rgba(255, 100, 115, 0.1);
  cursor: pointer;
  font-family: inherit;
}

/* ═══ 响应式 ═══ */
@media (max-width: 1200px) {
  .main {
    grid-template-columns: 1fr;
  }
  .queue {
    max-height: 420px;
  }
}

@media (max-width: 640px) {
  .cockpit {
    padding: 14px;
  }
  .topbar {
    flex-direction: column;
    align-items: flex-start;
  }
  .clock-box {
    display: none;
  }
  .donut-wrap {
    flex-direction: column;
  }
}

@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
</style>
