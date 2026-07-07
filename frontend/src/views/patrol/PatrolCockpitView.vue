<template>
  <div class="patrol-cockpit bigscreen-shell">
    <header class="bigscreen-topbar">
      <div class="topbar-meta">
        <button class="return-link" type="button" aria-label="返回巡检指挥台" @click="router.push('/patrol')">
          <el-icon><Back /></el-icon>
          <span>返回指挥台</span>
        </button>
        <span class="report-meta">{{ latestReport?.operator || '系统任务' }}</span>
        <span class="report-meta">{{ relativeTime(latestReport?.created_at) }}</span>
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
        <el-button class="screen-action" :loading="running" @click="handleRun">
          <el-icon><VideoPlay /></el-icon>
          立即巡检
        </el-button>
      </div>
    </header>

    <main v-loading="loading" class="bigscreen-dashboard">
      <section class="metric-rail" aria-label="巡检核心指标">
        <article v-for="stat in cockpitStats" :key="stat.key" class="metric-tile" :class="stat.tone">
          <span>{{ stat.label }}</span>
          <strong>{{ stat.value }}</strong>
          <small>{{ stat.helper }}</small>
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
          <article v-for="object in priorityObjects" :key="object.key" class="queue-item" :class="object.tone">
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

          <svg class="trend-chart" viewBox="0 0 360 128" role="img" aria-label="最近巡检异常趋势">
            <line x1="0" y1="104" x2="360" y2="104" />
            <line x1="0" y1="68" x2="360" y2="68" />
            <line x1="0" y1="32" x2="360" y2="32" />
            <polyline :points="trendPoints('critical_count')" class="trend-critical" />
            <polyline :points="trendPoints('warning_count')" class="trend-warning" />
            <polyline :points="trendPoints('normal_count')" class="trend-normal" />
          </svg>
        </section>
      </aside>

      <section class="battle-ticker" aria-label="巡检战报">
        <div class="ticker-label">
          <span>Battle Ticker</span>
          <strong>巡检战报</strong>
        </div>
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
import { computed, onActivated, ref } from 'vue'
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

function trendPoints(field: 'normal_count' | 'warning_count' | 'critical_count') {
  const list = [...reports.value].reverse()
  if (!list.length) return '0,104 360,104'
  const max = Math.max(...list.map((item) => item[field] || 0), 1)
  return list.map((item, index) => {
    const x = list.length === 1 ? 180 : Math.round((index / (list.length - 1)) * 340 + 10)
    const y = Math.round(108 - (((item[field] || 0) / max) * 84))
    return `${x},${y}`
  }).join(' ')
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

onActivated(fetchCockpit)
</script>

<style scoped>
.bigscreen-shell {
  --cockpit-bg: #060a12;
  --cockpit-panel: #0c1320;
  --cockpit-panel-strong: #111a2a;
  --cockpit-border: #26344b;
  --cockpit-border-hot: color-mix(in srgb, var(--primary-color) 48%, var(--cockpit-border));
  --cockpit-text: #eef5ff;
  --cockpit-soft: #a8b5cc;
  --cockpit-muted: #7f8da6;
  min-height: calc(100vh - var(--header-height));
  margin: -4px 0 0;
  padding: 12px;
  color: var(--cockpit-text);
  background:
    radial-gradient(circle at 50% 34%, color-mix(in srgb, var(--primary-color) 22%, transparent), transparent 38%),
    radial-gradient(circle at 78% 16%, color-mix(in srgb, #06b6d4 18%, transparent), transparent 28%),
    radial-gradient(circle at 20% 84%, color-mix(in srgb, var(--success-color) 8%, transparent), transparent 26%),
    linear-gradient(180deg, #08101c 0%, var(--cockpit-bg) 100%);
  border-radius: 8px;
  overflow: hidden;
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
  font-size: 23px;
  line-height: 1.1;
  letter-spacing: 0;
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
  grid-template-rows: auto minmax(420px, 1fr) 146px;
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
  border-radius: 8px;
  background:
    linear-gradient(180deg, color-mix(in srgb, var(--cockpit-panel-strong) 90%, transparent), color-mix(in srgb, var(--cockpit-panel) 94%, transparent));
}

.metric-tile {
  min-width: 0;
  min-height: 88px;
  padding: 12px;
  display: grid;
  gap: 5px;
  align-content: center;
  position: relative;
  overflow: hidden;
}

.metric-tile::after {
  content: "";
  position: absolute;
  inset: auto 12px 0;
  height: 2px;
  background: var(--cockpit-border-hot);
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
  padding: 11px;
  display: grid;
  gap: 7px;
  border: 1px solid color-mix(in srgb, var(--cockpit-border) 76%, transparent);
  border-radius: 8px;
  background: color-mix(in srgb, var(--cockpit-panel-strong) 80%, transparent);
}

.queue-item.danger {
  border-color: color-mix(in srgb, var(--danger-color) 44%, var(--cockpit-border));
}

.queue-item.warning {
  border-color: color-mix(in srgb, var(--warning-color) 40%, var(--cockpit-border));
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
  border: 1px solid color-mix(in srgb, var(--primary-color) 36%, var(--cockpit-border));
  border-radius: 8px;
  background:
    linear-gradient(color-mix(in srgb, #ffffff 5%, transparent) 1px, transparent 1px),
    linear-gradient(90deg, color-mix(in srgb, #ffffff 5%, transparent) 1px, transparent 1px),
    radial-gradient(circle at 50% 50%, color-mix(in srgb, var(--primary-color) 18%, transparent), transparent 48%),
    color-mix(in srgb, var(--cockpit-panel) 92%, #02050a);
  background-size: 30px 30px, 30px 30px, 100% 100%, 100% 100%;
}

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
  inset: 9%;
  border-radius: 50%;
  background: conic-gradient(from -24deg, color-mix(in srgb, #22d3ee 24%, transparent), transparent 72deg);
  animation: radar-sweep 8s linear infinite;
}

.radar-core {
  left: 50%;
  top: 50%;
  width: min(260px, 46%);
  min-height: 154px;
  padding: 18px;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 7px;
  border: 1px solid color-mix(in srgb, var(--primary-color) 44%, var(--cockpit-border));
  border-radius: 8px;
  text-align: center;
  background: color-mix(in srgb, var(--cockpit-panel) 86%, transparent);
  transform: translate(-50%, -50%);
}

.radar-core span {
  color: var(--cockpit-muted);
  font-size: 12px;
}

.radar-core strong {
  font-size: 30px;
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

.severity-row.danger b { background: var(--danger-color); }
.severity-row.warning b { background: var(--warning-color); }
.severity-row.success b { background: var(--success-color); }

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

.trend-chart {
  width: 100%;
  min-height: 118px;
}

.trend-chart line {
  stroke: color-mix(in srgb, var(--cockpit-border) 86%, transparent);
}

.trend-chart polyline {
  fill: none;
  stroke-width: 3;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.trend-critical { stroke: var(--danger-color); }
.trend-warning { stroke: var(--warning-color); }
.trend-normal { stroke: var(--success-color); }

.battle-ticker {
  grid-area: ticker;
  min-width: 0;
  padding: 12px;
  display: grid;
  grid-template-columns: 150px minmax(0, 1fr);
  align-items: stretch;
  gap: 12px;
  overflow: hidden;
}

.ticker-label {
  display: grid;
  align-content: center;
  gap: 4px;
  border-right: 1px solid var(--cockpit-border);
}

.ticker-label strong {
  font-size: 17px;
}

.ticker-track {
  min-width: 0;
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: minmax(220px, 1fr);
  gap: 10px;
  animation: ticker-drift 24s linear infinite;
}

.ticker-track:hover,
.ticker-track.still {
  animation-play-state: paused;
}

.ticker-item {
  min-width: 0;
  padding: 10px;
  display: grid;
  align-content: center;
  gap: 5px;
  border: 1px solid color-mix(in srgb, var(--cockpit-border) 80%, transparent);
  border-radius: 8px;
  background: color-mix(in srgb, var(--cockpit-panel-strong) 72%, transparent);
}

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
  }

  .ticker-track {
    grid-auto-flow: row;
    animation: none;
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

  .ticker-track {
    transform: none !important;
  }
}
</style>
