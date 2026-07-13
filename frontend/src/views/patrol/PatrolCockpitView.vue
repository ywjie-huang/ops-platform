<template>
  <div class="patrol-cockpit bigscreen-shell">
    <span class="corner tl" aria-hidden="true"></span>
    <span class="corner tr" aria-hidden="true"></span>
    <span class="corner bl" aria-hidden="true"></span>
    <span class="corner br" aria-hidden="true"></span>
    <div class="scanline" aria-hidden="true"></div>

    <header class="bigscreen-topbar">
      <div class="topbar-meta">
        <button class="return-link" type="button" aria-label="返回巡检指挥台" @click="router.push('/patrol')">
          <el-icon><Back /></el-icon>
          <span>返回指挥台</span>
        </button>
        <span class="report-meta">{{ latestReport?.operator || '系统任务' }}</span>
        <span class="report-meta">{{ relativeTime(latestReport?.created_at) }}</span>
        <span class="live-pill">LIVE</span>
      </div>

      <div class="topbar-title" aria-label="巡检态势大屏">
        <span class="title-line"></span>
        <div>
          <p>Patrol Situation</p>
          <h2>巡检态势大屏</h2>
        </div>
        <span class="title-line"></span>
      </div>

      <div class="topbar-actions">
        <span class="clock">{{ clockText }}</span>
        <el-button class="screen-action" :loading="running" @click="handleRun">
          <el-icon><VideoPlay /></el-icon>
          立即巡检
        </el-button>
      </div>
    </header>

    <main v-loading="loading" class="bigscreen-dashboard">
      <section class="metric-rail" aria-label="巡检核心指标">
        <article
          v-for="stat in cockpitStats"
          :key="stat.key"
          class="metric-tile"
          :class="[stat.tone, { hero: stat.key === 'health' }]"
        >
          <span class="label">{{ stat.label }}</span>
          <strong>{{ stat.value }}</strong>
          <div v-if="stat.key === 'health'" class="ring-mini" aria-hidden="true">
            <span>{{ stat.value }}</span>
          </div>
          <small>{{ stat.helper }}</small>
          <div class="glow" aria-hidden="true"></div>
        </article>
      </section>

      <section class="bigscreen-panel risk-queue" aria-label="高优先级风险队列">
        <div class="panel-heading">
          <div>
            <span>Priority Queue</span>
            <h3>优先风险队列</h3>
          </div>
          <strong>{{ priorityObjects.length }}</strong>
        </div>

        <div class="queue-list">
          <article
            v-for="(object, index) in priorityObjects"
            :key="object.key"
            class="queue-item"
            :class="object.tone"
          >
            <div class="q-no">{{ String(index + 1).padStart(2, '0') }}</div>
            <div class="q-body">
              <div class="queue-top">
                <span class="object-type">{{ object.categoryLabel }}</span>
                <span class="status-chip" :class="object.tone">{{ object.priority }}</span>
              </div>
              <strong>{{ object.targetName }}</strong>
              <p>{{ object.headline }}</p>
              <div class="queue-foot">
                <span>{{ object.critical }} 严重</span>
                <span>{{ object.warning }} 警告</span>
              </div>
            </div>
          </article>

          <div v-if="!priorityObjects.length" class="empty-state compact">
            <strong>暂无高优先级风险</strong>
            <span>最近巡检未发现 P1/P2 对象。</span>
          </div>
        </div>
      </section>

      <section class="bigscreen-panel radar-stage" role="img" aria-label="巡检风险雷达">
        <div class="radar-header">
          <span>Risk Radar</span>
          <strong :class="statusTone(overview.status)">{{ overview.priorityLabel }}</strong>
        </div>

        <div class="radar-canvas">
          <span class="radar-ring ring-outer"></span>
          <span class="radar-ring ring-middle"></span>
          <span class="radar-ring ring-inner"></span>
          <span class="radar-axis axis-x"></span>
          <span class="radar-axis axis-y"></span>
          <span class="radar-sweep"></span>
          <span class="radar-sector-label host">HOST</span>
          <span class="radar-sector-label k8s">K8S</span>
          <span class="radar-sector-label asset">ASSET</span>

          <span
            v-for="object in radarObjects"
            :key="object.key"
            class="radar-dot"
            :class="object.tone"
            :style="radarPointStyle(object)"
            aria-hidden="true"
          >
            <span>{{ object.priority }}</span>
          </span>

          <div class="radar-core" :class="statusTone(overview.status)">
            <span>{{ latestReport ? '当前态势' : '等待巡检' }}</span>
            <strong>{{ latestReport ? overview.priorityLabel : '暂无报告' }}</strong>
            <small>{{ latestReport?.summary || '执行一次巡检后将展示健康分、风险分布和战报。' }}</small>
            <el-button v-if="!latestReport" class="empty-action" :loading="running" @click="handleRun">立即巡检</el-button>
          </div>
        </div>
      </section>

      <aside class="side-stack">
        <section class="bigscreen-panel distribution-panel" aria-label="覆盖与风险分布">
          <div class="panel-heading">
            <div>
              <span>Coverage</span>
              <h3>覆盖与分布</h3>
            </div>
            <small>{{ relativeTime(latestReport?.created_at) }}</small>
          </div>

          <div class="category-grid">
            <div v-for="lane in riskLanes" :key="lane.key" class="category-cell">
              <span>{{ lane.label }}</span>
              <strong>{{ lane.objects.length }}</strong>
            </div>
          </div>

          <div class="severity-bars">
            <div class="severity-row danger">
              <span>严重</span>
              <i><b :style="{ width: `${severityWidth(overview.critical)}%` }"></b></i>
              <strong>{{ overview.critical }}</strong>
            </div>
            <div class="severity-row warning">
              <span>警告</span>
              <i><b :style="{ width: `${severityWidth(overview.warning)}%` }"></b></i>
              <strong>{{ overview.warning }}</strong>
            </div>
            <div class="severity-row success">
              <span>正常</span>
              <i><b :style="{ width: `${severityWidth(overview.normal)}%` }"></b></i>
              <strong>{{ overview.normal }}</strong>
            </div>
          </div>
        </section>

        <section class="bigscreen-panel trend-panel" aria-label="最近巡检趋势">
          <div class="panel-heading">
            <div>
              <span>Trend</span>
              <h3>巡检趋势</h3>
            </div>
            <small>最近 {{ reports.length }} 次</small>
          </div>

          <div class="legend">
            <span><i class="legend-critical"></i>严重</span>
            <span><i class="legend-warning"></i>警告</span>
            <span><i class="legend-normal"></i>正常</span>
          </div>

          <div class="trend-wrap">
            <svg class="trend-chart" viewBox="0 0 360 128" role="img" aria-label="最近巡检异常趋势">
              <defs>
                <linearGradient id="critFill" x1="0" x2="0" y1="0" y2="1">
                  <stop offset="0%" stop-color="rgba(255,93,108,.28)" />
                  <stop offset="100%" stop-color="rgba(255,93,108,0)" />
                </linearGradient>
                <linearGradient id="warnFill" x1="0" x2="0" y1="0" y2="1">
                  <stop offset="0%" stop-color="rgba(245,166,35,.18)" />
                  <stop offset="100%" stop-color="rgba(245,166,35,0)" />
                </linearGradient>
              </defs>
              <line class="grid" x1="0" y1="104" x2="360" y2="104" />
              <line class="grid" x1="0" y1="68" x2="360" y2="68" />
              <line class="grid" x1="0" y1="32" x2="360" y2="32" />
              <path class="area-critical" :d="trendArea('critical_count')" />
              <path class="area-warning" :d="trendArea('warning_count')" />
              <path class="line-critical" :d="trendPath('critical_count')" />
              <path class="line-warning" :d="trendPath('warning_count')" />
              <path class="line-normal" :d="trendPath('normal_count')" />
              <circle
                v-for="point in trendEndPoints"
                :key="point.key"
                class="dot"
                :cx="point.x"
                :cy="point.y"
                :r="point.r"
                :fill="point.fill"
              />
            </svg>
          </div>
        </section>
      </aside>

      <section class="battle-ticker" aria-label="巡检战报">
        <div class="ticker-label">
          <span>Battle Ticker</span>
          <strong>巡检战报</strong>
        </div>
        <div class="ticker-viewport">
          <div class="ticker-track" :class="{ still: !tickerItems.length }">
            <article v-for="item in tickerItems" :key="item.key" class="ticker-item" :class="item.tone">
              <span class="status-chip" :class="item.tone">{{ item.meta }}</span>
              <strong>{{ item.title }}</strong>
              <p>{{ item.detail }}</p>
            </article>
            <article v-if="!tickerItems.length" class="ticker-item success">
              <span class="status-chip success">正常</span>
              <strong>暂无风险战报</strong>
              <p>执行巡检后，这里会展示重点对象和最近批次摘要。</p>
            </article>
          </div>
        </div>
      </section>

      <div v-if="errorMessage" class="error-banner" role="alert">
        <strong>巡检态势加载失败</strong>
        <span>{{ errorMessage }}</span>
        <button type="button" @click="fetchCockpit">重试</button>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onActivated, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Back, VideoPlay } from '@element-plus/icons-vue'
import { getPatrolReportDetail, getPatrolReports, runPatrol } from '@/api/patrol'
import {
  buildCockpitStats,
  buildPatrolOverview,
  buildRadarObjects,
  buildRiskObjects,
  buildTickerItems,
  groupRiskObjectsByCategory,
  statusTone,
  type PatrolItemLike,
  type PatrolReportLike,
  type RadarObject,
} from '@/utils/patrolCommand'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const running = ref(false)
const reports = ref<PatrolReportLike[]>([])
const latestReport = ref<PatrolReportLike | null>(null)
const detailItems = ref<PatrolItemLike[]>([])
const errorMessage = ref('')
const clockText = ref('--:--:--')
let clockTimer: number | undefined

const overview = computed(() => buildPatrolOverview(latestReport.value))
const riskObjects = computed(() => buildRiskObjects(detailItems.value))
const riskLanes = computed(() => groupRiskObjectsByCategory(riskObjects.value))
const priorityObjects = computed(() => riskObjects.value.filter((item) => item.status !== 'normal').slice(0, 6))
const radarObjects = computed(() => buildRadarObjects(riskObjects.value))
const tickerItems = computed(() => buildTickerItems(priorityObjects.value, reports.value))
const cockpitStats = computed(() => buildCockpitStats(latestReport.value, riskObjects.value.length, relativeTime(latestReport.value?.created_at)))

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
    const res: any = await getPatrolReports({ page: 1, page_size: 7 })
    reports.value = res.data.items || []
    const requestedReportId = getRequestedReportId()
    latestReport.value = (requestedReportId != null
      ? reports.value.find((item) => item.id === requestedReportId)
      : null) || reports.value[0] || null

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
  } catch (e: any) {
    detailItems.value = []
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

function severityWidth(value: number) {
  const max = Math.max(overview.value.total, 1)
  return Math.max(value > 0 ? 8 : 0, Math.round((value / max) * 100))
}

function buildTrendCoords(field: 'normal_count' | 'warning_count' | 'critical_count') {
  const list = [...reports.value].reverse()
  if (!list.length) return [{ x: 10, y: 104 }, { x: 350, y: 104 }]
  const max = Math.max(...list.map((item) => item[field] || 0), 1)
  return list.map((item, index) => {
    const x = list.length === 1 ? 180 : Math.round((index / (list.length - 1)) * 340 + 10)
    const y = Math.round(108 - (((item[field] || 0) / max) * 84))
    return { x, y }
  })
}

function trendPath(field: 'normal_count' | 'warning_count' | 'critical_count') {
  const points = buildTrendCoords(field)
  return points.map((point, index) => (index === 0 ? 'M' : 'L') + point.x + ',' + point.y).join(' ')
}

function trendArea(field: 'normal_count' | 'warning_count' | 'critical_count') {
  const points = buildTrendCoords(field)
  if (!points.length) return 'M10,104 L350,104 Z'
  const line = points.map((point, index) => (index === 0 ? 'M' : 'L') + point.x + ',' + point.y).join(' ')
  const last = points[points.length - 1]
  const first = points[0]
  return line + ' L' + last.x + ',104 L' + first.x + ',104 Z'
}

function radarPointStyle(object: RadarObject) {
  const radians = (object.angle * Math.PI) / 180
  const x = Math.min(88, Math.max(12, 50 + Math.cos(radians) * object.ring * 0.52))
  const y = Math.min(86, Math.max(14, 50 + Math.sin(radians) * object.ring * 0.44))

  return {
    left: `${x}%`,
    top: `${y}%`,
    '--dot-size': `${object.size}px`,
  }
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
  clockText.value = new Date().toLocaleTimeString('zh-CN', { hour12: false })
}

onMounted(() => {
  tickClock()
  clockTimer = window.setInterval(tickClock, 1000)
})

onBeforeUnmount(() => {
  if (clockTimer) window.clearInterval(clockTimer)
})

onActivated(fetchCockpit)
</script>

<style scoped>
.bigscreen-shell {
  --cockpit-bg: #050914;
  --cockpit-panel: rgba(10, 16, 30, 0.78);
  --cockpit-panel-strong: rgba(14, 22, 40, 0.88);
  --cockpit-border: rgba(120, 146, 196, 0.22);
  --cockpit-border-hot: color-mix(in srgb, var(--primary-color) 48%, var(--cockpit-border));
  --cockpit-text: #eef5ff;
  --cockpit-soft: #a9b7d0;
  --cockpit-muted: #7f8eab;
  position: relative;
  min-height: calc(100vh - var(--header-height));
  margin: 0;
  padding: 14px;
  color: var(--cockpit-text);
  background:
    radial-gradient(circle at 50% 18%, rgba(109, 124, 255, 0.26), transparent 30%),
    radial-gradient(circle at 78% 10%, rgba(34, 211, 238, 0.16), transparent 22%),
    radial-gradient(circle at 18% 88%, rgba(34, 197, 94, 0.09), transparent 20%),
    radial-gradient(circle at 50% 70%, rgba(255, 93, 108, 0.05), transparent 28%),
    linear-gradient(180deg, #091321 0%, #050914 48%, #03060d 100%);
  border-radius: 12px;
  overflow: hidden;
}
.bigscreen-shell::before {
  content: "";
  position: absolute;
  inset: 0;
  pointer-events: none;
  opacity: 0.42;
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.03) 1px, transparent 1px);
  background-size: 46px 46px;
  mask-image: radial-gradient(circle at 50% 38%, #000 18%, transparent 78%);
}
.bigscreen-shell::after {
  content: "";
  position: absolute;
  inset: 8px;
  border: 1px solid rgba(125, 160, 220, 0.14);
  border-radius: 14px;
  pointer-events: none;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.03), inset 0 0 60px rgba(109, 124, 255, 0.04);
}
.corner {
  position: absolute;
  width: 18px;
  height: 18px;
  z-index: 3;
  pointer-events: none;
  opacity: 0.85;
}
.corner::before,
.corner::after {
  content: "";
  position: absolute;
  background: linear-gradient(90deg, rgba(125, 211, 252, 0.9), rgba(109, 124, 255, 0.2));
}
.corner::before { width: 18px; height: 1px; }
.corner::after { width: 1px; height: 18px; }
.corner.tl { top: 12px; left: 12px; }
.corner.tr { top: 12px; right: 12px; transform: scaleX(-1); }
.corner.bl { bottom: 12px; left: 12px; transform: scaleY(-1); }
.corner.br { bottom: 12px; right: 12px; transform: scale(-1); }
.scanline {
  position: absolute;
  left: 0;
  right: 0;
  height: 110px;
  top: -110px;
  pointer-events: none;
  z-index: 1;
  opacity: 0.1;
  background: linear-gradient(180deg, transparent, rgba(125, 211, 252, 0.4), transparent);
  animation: scan-move 9s linear infinite;
}
.bigscreen-topbar,
.bigscreen-dashboard {
  position: relative;
  z-index: 2;
}

.bigscreen-topbar {
  min-height: 58px;
  display: grid;
  grid-template-columns: minmax(240px, 1fr) auto minmax(180px, 1fr);
  align-items: center;
  gap: 16px;
  margin-bottom: 12px;
}

.topbar-meta,
.topbar-actions,
.return-link,
.topbar-title,
.legend,
.queue-top,
.queue-foot {
  display: flex;
  align-items: center;
}

.topbar-meta {
  gap: 10px;
  min-width: 0;
}

.return-link {
  min-height: 36px;
  gap: 7px;
  padding: 0 10px;
  border: 1px solid var(--cockpit-border);
  border-radius: 8px;
  color: var(--cockpit-text);
  background: color-mix(in srgb, var(--cockpit-panel) 88%, transparent);
  cursor: pointer;
  transition: border-color 180ms ease-out, background 180ms ease-out, transform 180ms ease-out;
}

.return-link:hover,
.return-link:focus-visible {
  border-color: var(--cockpit-border-hot);
  background: color-mix(in srgb, var(--primary-color) 12%, var(--cockpit-panel));
  outline: none;
}

.return-link:active {
  transform: translateY(1px);
}

.report-meta {
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--cockpit-soft);
  font-size: 12px;
}
.live-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #9df3bf;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.04em;
}
.live-pill::before {
  content: "";
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--success-color);
  box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.45);
  animation: pulse-green 1.8s ease-out infinite;
}
.clock {
  color: var(--cockpit-soft);
  font-size: 12px;
  font-variant-numeric: tabular-nums;
  padding: 0 4px;
}

.topbar-title {
  justify-content: center;
  gap: 14px;
  text-align: center;
}

.topbar-title p {
  margin: 0 0 2px;
  color: #7dd3fc;
  font-size: 11px;
  font-weight: 700;
}

.topbar-title h2 {
  margin: 0;
  font-size: 26px;
  line-height: 1.05;
  letter-spacing: 0.08em;
  text-shadow: 0 0 18px rgba(125, 211, 252, 0.22), 0 0 42px rgba(109, 124, 255, 0.18);
}

.title-line {
  width: 138px;
  height: 1px;
  background: linear-gradient(90deg, transparent, color-mix(in srgb, var(--primary-color) 82%, #7dd3fc));
}

.title-line:last-child {
  background: linear-gradient(90deg, color-mix(in srgb, var(--primary-color) 82%, #7dd3fc), transparent);
}

.topbar-actions {
  justify-content: flex-end;
}

.screen-action {
  min-height: 36px;
}

.bigscreen-dashboard {
  position: relative;
  display: grid;
  width: 100%;
  min-width: 0;
  grid-template-columns: minmax(230px, 0.82fr) minmax(420px, 1.55fr) minmax(250px, 0.88fr);
  grid-template-rows: auto minmax(420px, 1fr) 132px;
  grid-template-areas:
    "metrics metrics metrics"
    "queue radar side"
    "ticker ticker ticker";
  gap: 12px;
  min-height: calc(100vh - var(--header-height) - 86px);
}

.metric-rail {
  grid-area: metrics;
  display: grid;
  grid-template-columns: 1.35fr repeat(4, minmax(128px, 1fr));
  gap: 10px;
}

.metric-tile,
.bigscreen-panel,
.battle-ticker,
.error-banner {
  border: 1px solid var(--cockpit-border);
  border-radius: 14px;
  background:
    linear-gradient(180deg, rgba(20, 30, 52, 0.78), rgba(10, 16, 30, 0.72)),
    radial-gradient(circle at 0% 0%, rgba(109, 124, 255, 0.08), transparent 40%);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04), 0 14px 36px rgba(0, 0, 0, 0.22);
  backdrop-filter: blur(10px);
}

.metric-tile {
  min-width: 0;
  min-height: 96px;
  padding: 14px 16px;
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 6px 12px;
  align-content: center;
  position: relative;
  overflow: hidden;
  backdrop-filter: blur(8px);
}
.metric-tile .label {
  grid-column: 1 / -1;
  color: var(--cockpit-muted);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.04em;
}
.metric-tile .glow {
  position: absolute;
  left: 14px;
  right: 14px;
  bottom: 0;
  height: 2px;
  border-radius: 999px;
  background: linear-gradient(90deg, transparent, rgba(109, 124, 255, 0.8), rgba(34, 211, 238, 0.55), transparent);
}
.metric-tile.hero {
  background:
    radial-gradient(circle at 100% 0%, rgba(255, 93, 108, 0.2), transparent 42%),
    radial-gradient(circle at 0% 100%, rgba(109, 124, 255, 0.12), transparent 40%),
    linear-gradient(180deg, rgba(26, 34, 58, 0.92), rgba(12, 18, 32, 0.84));
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.05), 0 0 28px rgba(255, 93, 108, 0.08);
}
.metric-tile.hero strong {
  font-size: 34px;
  text-shadow: 0 0 18px rgba(255, 93, 108, 0.25);
}
.metric-tile.danger strong {
  animation: num-glow 2.4s ease-in-out infinite;
}
.ring-mini {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  position: relative;
  background: conic-gradient(#ff5d6c 0 28%, #f5a623 28% 48%, rgba(34, 197, 94, 0.85) 48% 100%);
  box-shadow: 0 0 18px rgba(255, 93, 108, 0.15);
}
.ring-mini::before {
  content: "";
  position: absolute;
  inset: 6px;
  border-radius: 50%;
  background: rgba(8, 14, 26, 0.95);
  border: 1px solid rgba(255, 255, 255, 0.05);
}
.ring-mini span {
  position: relative;
  font-size: 13px;
  font-weight: 800;
}

.metric-tile span,
.metric-tile small,
.panel-heading span,
.panel-heading small,
.radar-header span,
.ticker-label span,
.object-type {
  color: var(--cockpit-muted);
  font-size: 12px;
}

.metric-tile strong {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 30px;
  line-height: 1;
}

.metric-tile.health strong,
.metric-tile.danger strong,
.danger .status-chip,
.status-chip.danger {
  color: #ffb9bd;
}

.metric-tile.warning strong,
.warning .status-chip,
.status-chip.warning {
  color: #ffd18a;
}

.metric-tile.success strong,
.success .status-chip,
.status-chip.success {
  color: #9df3bf;
}

.metric-tile.info strong,
.status-chip.info {
  color: #8be9ff;
}

.risk-queue {
  grid-area: queue;
  min-width: 0;
  padding: 14px;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 12px;
}

.panel-heading {
  min-width: 0;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.panel-heading h3 {
  margin: 3px 0 0;
  font-size: 15px;
}

.panel-heading > strong {
  font-size: 26px;
  line-height: 1;
}

.queue-list {
  min-height: 0;
  overflow: auto;
  display: grid;
  align-content: start;
  gap: 9px;
  padding-right: 2px;
}

.queue-item {
  min-width: 0;
  padding: 12px 12px 12px 14px;
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr);
  gap: 10px;
  border: 1px solid rgba(120, 146, 196, 0.16);
  border-radius: 12px;
  background: rgba(8, 14, 26, 0.42);
  position: relative;
  overflow: hidden;
}
.queue-item::before {
  content: "";
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: rgba(125, 160, 220, 0.25);
}
.queue-item.danger {
  border-color: rgba(255, 93, 108, 0.42);
  box-shadow: inset 0 0 0 1px rgba(255, 93, 108, 0.08), 0 0 24px rgba(255, 93, 108, 0.1);
}
.queue-item.danger::before {
  background: linear-gradient(180deg, #ff8a95, #ff5d6c);
}
.queue-item.warning {
  border-color: rgba(245, 166, 35, 0.32);
}
.queue-item.warning::before {
  background: linear-gradient(180deg, #ffd18a, #f5a623);
}
.q-no {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  display: grid;
  place-items: center;
  font-size: 12px;
  font-weight: 900;
  color: var(--cockpit-soft);
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.05);
  font-variant-numeric: tabular-nums;
}
.queue-item.danger .q-no {
  color: #ffb4bb;
  border-color: rgba(255, 93, 108, 0.25);
  background: rgba(255, 93, 108, 0.08);
}
.queue-item.warning .q-no {
  color: #ffd18a;
  border-color: rgba(245, 166, 35, 0.22);
  background: rgba(245, 166, 35, 0.08);
}
.q-body {
  min-width: 0;
  display: grid;
  gap: 6px;
}

.queue-top,
.queue-foot {
  justify-content: space-between;
  gap: 8px;
}

.queue-item strong,
.ticker-item strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
}

.queue-item p,
.ticker-item p {
  margin: 0;
  color: var(--cockpit-soft);
  font-size: 12px;
  line-height: 1.45;
}

.queue-foot {
  color: var(--cockpit-muted);
  font-size: 12px;
}

.status-chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: fit-content;
  min-height: 22px;
  padding: 2px 8px;
  border: 1px solid currentColor;
  border-radius: 999px;
  background: color-mix(in srgb, currentColor 10%, transparent);
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
}

.radar-stage {
  grid-area: radar;
  min-width: 0;
  padding: 14px;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 10px;
  overflow: hidden;
}

.radar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.radar-header strong {
  font-size: 13px;
}

.radar-header strong.danger { color: #ffb9bd; }
.radar-header strong.warning { color: #ffd18a; }
.radar-header strong.success { color: #9df3bf; }
.radar-header strong.info { color: #8be9ff; }

.radar-canvas {
  position: relative;
  min-height: 0;
  overflow: hidden;
  border: 1px solid rgba(109, 124, 255, 0.38);
  border-radius: 14px;
  background:
    radial-gradient(circle at 50% 50%, rgba(109, 124, 255, 0.22), transparent 40%),
    radial-gradient(circle at 50% 50%, rgba(34, 211, 238, 0.08), transparent 58%),
    linear-gradient(rgba(255, 255, 255, 0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.04) 1px, transparent 1px),
    rgba(5, 10, 20, 0.94);
  background-size: auto, auto, 28px 28px, 28px 28px, auto;
  box-shadow: inset 0 0 50px rgba(109, 124, 255, 0.12), 0 0 30px rgba(109, 124, 255, 0.08);
}
.radar-canvas::after {
  content: "";
  position: absolute;
  inset: 12%;
  border-radius: 50%;
  pointer-events: none;
  border: 1px dashed rgba(125, 211, 252, 0.12);
  animation: radar-orbit 18s linear infinite;
}
.radar-sector-label {
  position: absolute;
  color: rgba(169, 183, 208, 0.72);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  text-shadow: 0 0 10px rgba(125, 211, 252, 0.25);
}
.radar-sector-label.host { left: 18%; top: 18%; }
.radar-sector-label.k8s { right: 16%; top: 22%; }
.radar-sector-label.asset { left: 46%; bottom: 12%; }

.radar-ring,
.radar-axis,
.radar-sweep,
.radar-core,
.radar-dot {
  position: absolute;
}

.radar-ring {
  inset: 50%;
  border: 1px solid color-mix(in srgb, var(--primary-color) 36%, transparent);
  border-radius: 50%;
  transform: translate(-50%, -50%);
}

.ring-outer { width: 82%; aspect-ratio: 1; }
.ring-middle { width: 56%; aspect-ratio: 1; }
.ring-inner { width: 30%; aspect-ratio: 1; }

.radar-axis {
  background: color-mix(in srgb, var(--primary-color) 26%, transparent);
}

.axis-x {
  left: 8%;
  right: 8%;
  top: 50%;
  height: 1px;
}

.axis-y {
  top: 8%;
  bottom: 8%;
  left: 50%;
  width: 1px;
}

.radar-sweep {
  inset: 8%;
  border-radius: 50%;
  background: conic-gradient(from -20deg, rgba(34, 211, 238, 0.38), rgba(109, 124, 255, 0.12), transparent 78deg);
  animation: radar-sweep 6.8s linear infinite;
  filter: blur(0.15px);
  mix-blend-mode: screen;
}

.radar-core {
  left: 50%;
  top: 50%;
  width: min(290px, 50%);
  min-height: 176px;
  padding: 18px 16px;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 8px;
  border: 1px solid rgba(109, 124, 255, 0.5);
  border-radius: 20px;
  text-align: center;
  background: linear-gradient(180deg, rgba(16, 26, 48, 0.94), rgba(8, 14, 26, 0.88));
  transform: translate(-50%, -50%);
  box-shadow: 0 0 50px rgba(109, 124, 255, 0.2), 0 0 24px rgba(255, 93, 108, 0.08), inset 0 1px 0 rgba(255, 255, 255, 0.06);
  backdrop-filter: blur(10px);
}

.radar-core span {
  color: var(--cockpit-muted);
  font-size: 12px;
}

.radar-core strong {
  font-size: 34px;
  letter-spacing: 0.04em;
  text-shadow: 0 0 18px rgba(255, 93, 108, 0.28);
}

.radar-core small {
  max-width: 32ch;
  color: var(--cockpit-soft);
  font-size: 12px;
  line-height: 1.55;
}

.empty-action {
  margin-top: 5px;
}

.radar-dot {
  width: var(--dot-size);
  height: var(--dot-size);
  min-width: 18px;
  min-height: 18px;
  padding: 0;
  display: grid;
  place-items: center;
  border: 1px solid currentColor;
  border-radius: 50%;
  color: #9df3bf;
  background: color-mix(in srgb, currentColor 34%, var(--cockpit-panel));
  transform: translate(-50%, -50%);
  animation: risk-pulse 2.7s ease-out infinite;
}

.radar-dot span {
  position: absolute;
  top: calc(100% + 5px);
  left: 50%;
  transform: translateX(-50%);
  padding: 1px 6px;
  border-radius: 999px;
  color: var(--cockpit-text);
  background: color-mix(in srgb, var(--cockpit-panel) 88%, transparent);
  font-size: 10px;
  font-weight: 800;
  white-space: nowrap;
}

.radar-dot.danger {
  color: #ff747d;
}

.radar-dot.warning {
  color: #ffbf58;
}

.radar-dot.success {
  color: #6ee7a0;
  animation: none;
}

.side-stack {
  grid-area: side;
  min-width: 0;
  display: grid;
  grid-template-rows: minmax(0, 0.92fr) minmax(0, 1fr);
  gap: 12px;
}

.distribution-panel,
.trend-panel {
  min-height: 0;
  padding: 14px;
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr);
  gap: 12px;
}

.category-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.category-cell {
  min-width: 0;
  padding: 9px;
  border: 1px solid color-mix(in srgb, var(--cockpit-border) 82%, transparent);
  border-radius: 8px;
  background: color-mix(in srgb, var(--cockpit-panel-strong) 74%, transparent);
  display: grid;
  gap: 3px;
}

.category-cell span {
  overflow: hidden;
  color: var(--cockpit-muted);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.category-cell strong {
  font-size: 21px;
}

.severity-bars {
  display: grid;
  align-content: start;
  gap: 10px;
}

.severity-row {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr) 32px;
  align-items: center;
  gap: 8px;
  color: var(--cockpit-soft);
  font-size: 12px;
}

.severity-row i {
  height: 8px;
  overflow: hidden;
  border-radius: 999px;
  background: color-mix(in srgb, #ffffff 8%, transparent);
}

.severity-row b {
  display: block;
  height: 100%;
  border-radius: inherit;
}

.severity-row.danger b { background: linear-gradient(90deg, #ff8a95, #ff5d6c); box-shadow: 0 0 12px rgba(255, 93, 108, 0.35); }
.severity-row.warning b { background: linear-gradient(90deg, #ffd18a, #f5a623); box-shadow: 0 0 12px rgba(245, 166, 35, 0.28); }
.severity-row.success b { background: linear-gradient(90deg, #86efac, #22c55e); box-shadow: 0 0 12px rgba(34, 197, 94, 0.22); }

.legend {
  gap: 10px;
  color: var(--cockpit-muted);
  font-size: 12px;
}

.legend span {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.legend i {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.legend-critical { background: var(--danger-color); }
.legend-warning { background: var(--warning-color); }
.legend-normal { background: var(--success-color); }

.trend-wrap { min-height: 0; }
.trend-chart {
  width: 100%;
  min-height: 118px;
  display: block;
}
.trend-chart .grid {
  stroke: rgba(120, 146, 196, 0.14);
}
.trend-chart .area-critical { fill: url(#critFill); }
.trend-chart .area-warning { fill: url(#warnFill); }
.trend-chart .line-critical,
.trend-chart .line-warning,
.trend-chart .line-normal {
  fill: none;
  stroke-width: 2.6;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.trend-chart .line-critical {
  stroke: var(--danger-color);
  filter: drop-shadow(0 0 4px rgba(255, 93, 108, 0.45));
}
.trend-chart .line-warning {
  stroke: var(--warning-color);
  filter: drop-shadow(0 0 3px rgba(245, 166, 35, 0.35));
}
.trend-chart .line-normal {
  stroke: var(--success-color);
  opacity: 0.9;
}
.trend-chart .dot {
  stroke: #fff;
  stroke-width: 1.2;
}

.battle-ticker {
  grid-area: ticker;
  min-width: 0;
  min-height: 0;
  height: 100%;
  padding: 8px 12px;
  display: grid;
  grid-template-columns: 158px minmax(0, 1fr);
  align-items: stretch;
  gap: 0;
  overflow: hidden;
}
.ticker-label {
  display: grid;
  align-content: center;
  align-self: stretch;
  gap: 4px;
  padding: 0 14px 0 2px;
  border-right: 1px solid var(--cockpit-border);
  position: relative;
  z-index: 5;
  background: linear-gradient(90deg, rgba(14, 22, 40, 0.98), rgba(14, 22, 40, 0.94));
  box-shadow: 12px 0 18px rgba(8, 14, 26, 0.55);
  isolation: isolate;
}
.ticker-label strong {
  font-size: 17px;
}
.ticker-viewport {
  min-width: 0;
  min-height: 0;
  height: 100%;
  overflow: hidden;
  position: relative;
  z-index: 1;
  padding-left: 12px;
  display: flex;
  align-items: stretch;
  mask-image: linear-gradient(90deg, transparent, #000 22px, #000 calc(100% - 18px), transparent);
}
.ticker-track {
  min-width: 0;
  min-height: 100%;
  height: 100%;
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: minmax(240px, 1fr);
  grid-auto-rows: 100%;
  align-items: stretch;
  gap: 10px;
  animation: ticker-drift 28s linear infinite;
  position: relative;
  width: max-content;
}
.ticker-track:hover,
.ticker-track.still {
  animation-play-state: paused;
}
.ticker-item {
  min-width: 0;
  min-height: 100%;
  height: 100%;
  padding: 10px 12px;
  display: grid;
  align-content: center;
  gap: 5px;
  border: 1px solid rgba(120, 146, 196, 0.16);
  border-radius: 12px;
  background: rgba(8, 14, 26, 0.42);
  position: relative;
  overflow: hidden;
}
.ticker-item::before {
  content: "";
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: rgba(125, 160, 220, 0.25);
}
.ticker-item.danger::before { background: linear-gradient(180deg, #ff8a95, #ff5d6c); }
.ticker-item.warning::before { background: linear-gradient(180deg, #ffd18a, #f5a623); }
.ticker-item.success::before { background: linear-gradient(180deg, #86efac, #22c55e); }

.ticker-item.danger {
  border-color: color-mix(in srgb, var(--danger-color) 42%, var(--cockpit-border));
}

.ticker-item.warning {
  border-color: color-mix(in srgb, var(--warning-color) 42%, var(--cockpit-border));
}

.ticker-item.success {
  border-color: color-mix(in srgb, var(--success-color) 34%, var(--cockpit-border));
}

.empty-state {
  min-height: 140px;
  padding: 18px;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 6px;
  color: var(--cockpit-soft);
  text-align: center;
}

.empty-state.compact {
  min-height: 120px;
  border: 1px dashed var(--cockpit-border);
  border-radius: 8px;
}

.empty-state strong {
  color: var(--cockpit-text);
}

.error-banner {
  position: absolute;
  right: 14px;
  bottom: 14px;
  max-width: min(420px, calc(100% - 28px));
  padding: 12px;
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 4px 12px;
  border-color: color-mix(in srgb, var(--danger-color) 48%, var(--cockpit-border));
  color: var(--cockpit-text);
}

.error-banner span {
  color: var(--cockpit-soft);
  font-size: 12px;
}

.error-banner button {
  grid-row: 1 / span 2;
  min-height: 34px;
  padding: 0 10px;
  border: 1px solid color-mix(in srgb, var(--danger-color) 45%, var(--cockpit-border));
  border-radius: 8px;
  color: #ffb9bd;
  background: color-mix(in srgb, var(--danger-color) 12%, var(--cockpit-panel));
  cursor: pointer;
}

@keyframes radar-sweep {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@keyframes risk-pulse {
  0%, 100% {
    box-shadow: 0 0 0 0 color-mix(in srgb, currentColor 24%, transparent), 0 0 18px color-mix(in srgb, currentColor 36%, transparent);
  }
  50% {
    box-shadow: 0 0 0 9px color-mix(in srgb, currentColor 8%, transparent), 0 0 24px color-mix(in srgb, currentColor 54%, transparent);
  }
}

@keyframes ticker-drift {
  from { transform: translateX(0); }
  to { transform: translateX(-18%); }
}

@media (max-width: 1180px) {
  .bigscreen-dashboard {
    grid-template-columns: 1fr 1fr;
    grid-template-rows: auto 520px auto 150px;
    grid-template-areas:
      "metrics metrics"
      "radar radar"
      "queue side"
      "ticker ticker";
  }

  .metric-rail {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 900px) {
  .bigscreen-shell {
    margin: 0;
    padding: 10px;
  }

  .bigscreen-topbar {
    grid-template-columns: 1fr;
    justify-items: stretch;
  }

  .topbar-title {
    order: -1;
  }

  .title-line {
    width: 72px;
  }

  .topbar-actions {
    justify-content: flex-start;
  }

  .bigscreen-dashboard {
    grid-template-columns: 1fr;
    grid-template-rows: auto 460px auto auto 190px;
    grid-template-areas:
      "metrics"
      "radar"
      "queue"
      "side"
      "ticker";
  }

  .metric-rail {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .category-grid {
    grid-template-columns: 1fr;
  }

  .side-stack {
    grid-template-rows: auto auto;
  }

  .battle-ticker {
    grid-template-columns: 1fr;
  }

  .ticker-label {
    border-right: 0;
    border-bottom: 1px solid var(--cockpit-border);
    padding-bottom: 8px;
    margin-bottom: 10px;
    box-shadow: none;
    background: transparent;
  }

  .ticker-viewport {
    mask-image: none;
  }

  .ticker-track {
    grid-auto-flow: row;
    animation: none;
    width: auto;
    height: auto;
  }

  .ticker-item {
    height: auto;
    min-height: 0;
  }
}

@media (max-width: 560px) {
  .metric-rail {
    grid-template-columns: 1fr;
  }

  .radar-core {
    width: min(260px, 72%);
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

  .ticker-track,
  .scanline,
  .radar-canvas::after,
  .radar-sweep {
    transform: none !important;
    animation: none !important;
  }
}
</style>
