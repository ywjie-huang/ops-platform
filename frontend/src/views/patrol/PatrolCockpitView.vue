<template>
  <div class="patrol-cockpit">
    <header class="cockpit-topbar">
      <div class="cockpit-heading">
        <span class="cockpit-logo">
          <svg class="cockpit-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M4 19V5"/><path d="M4 19h16"/><path d="m7 15 4-4 3 3 5-7"/></svg>
        </span>
        <div>
          <h2>巡检驾驶舱</h2>
          <p>全局态势、风险分布与异常趋势总览。</p>
        </div>
      </div>
      <div class="cockpit-actions">
        <el-button @click="$router.push('/patrol')">
          <el-icon><Back /></el-icon> 返回指挥台
        </el-button>
        <el-button type="primary" :loading="running" @click="handleRun">
          <el-icon><VideoPlay /></el-icon> 立即巡检
        </el-button>
      </div>
    </header>

    <main v-loading="loading" class="cockpit-dashboard">
      <section class="health-row">
        <article class="cockpit-card hero-card">
          <div class="score-ring" :style="{ '--score': `${overview.healthScore}%` }">
            <strong>{{ overview.healthScore }}</strong>
          </div>
          <div class="hero-copy">
            <h3>{{ latestReport?.title || '暂无巡检报告' }}</h3>
            <p>{{ latestReport?.summary || '执行一次巡检后，这里会展示生产环境健康分、风险分布和重点对象。' }}</p>
          </div>
          <span class="cockpit-pill" :class="statusTone(overview.status)">{{ overview.priorityLabel }}</span>
        </article>
        <article class="cockpit-card metric danger">
          <span>严重项</span>
          <strong>{{ overview.critical }}</strong>
          <small>{{ riskObjects.filter((item) => item.status === 'critical').length }} 个对象</small>
        </article>
        <article class="cockpit-card metric warning">
          <span>警告项</span>
          <strong>{{ overview.warning }}</strong>
          <small>{{ riskObjects.filter((item) => item.status === 'warning').length }} 个对象</small>
        </article>
        <article class="cockpit-card metric success">
          <span>正常项</span>
          <strong>{{ overview.normal }}</strong>
          <small>{{ overview.total }} 项检查</small>
        </article>
        <article class="cockpit-card metric info">
          <span>覆盖对象</span>
          <strong>{{ riskObjects.length }}</strong>
          <small>主机 / K8s / 资产</small>
        </article>
      </section>

      <section class="cockpit-card coverage-panel">
        <div class="panel-head">
          <div class="panel-title">
            <svg class="cockpit-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/></svg>
            <span>覆盖与分布</span>
          </div>
          <span>{{ relativeTime(latestReport?.created_at) }}</span>
        </div>
        <div class="coverage-body">
          <div class="coverage-grid">
            <div v-for="lane in riskLanes" :key="lane.key" class="coverage-box">
              <span>{{ lane.label }}</span>
              <strong>{{ lane.objects.length }}</strong>
            </div>
          </div>
          <div class="bars">
            <div v-for="lane in riskLanes" :key="`${lane.key}-bar`" class="bar-row">
              <span>{{ lane.label }}</span>
              <div class="track">
                <i :style="{ width: `${barWidth(lane.objects.length)}%` }"></i>
              </div>
              <strong>{{ lane.objects.length }}</strong>
            </div>
          </div>
        </div>
      </section>

      <section class="cockpit-card map-panel">
        <div class="panel-head">
          <div class="panel-title">
            <svg class="cockpit-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/></svg>
            <span>风险拓扑</span>
          </div>
          <span>按风险对象聚合</span>
        </div>
        <div class="map-body">
          <span class="map-line line-a"></span>
          <span class="map-line line-b"></span>
          <span class="map-line line-c"></span>
          <span class="map-line line-d"></span>
          <article
            v-for="(object, index) in topologyObjects"
            :key="object.key"
            class="map-node"
            :class="[object.tone, `node-${index}`]"
          >
            <strong>{{ object.targetName }}</strong>
            <span>{{ object.categoryLabel }} · {{ object.headline }}</span>
            <em>{{ object.priority }}</em>
          </article>
        </div>
      </section>

      <section class="cockpit-card events-panel">
        <div class="panel-head">
          <div class="panel-title">
            <svg class="cockpit-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 8v5l3 3"/><circle cx="12" cy="12" r="10"/></svg>
            <span>风险事件</span>
          </div>
          <span>按优先级</span>
        </div>
        <div class="event-list">
          <article v-for="object in priorityObjects" :key="object.key" class="event-card">
            <div>
              <strong>{{ object.targetName }}</strong>
              <p>{{ object.headline }}，{{ object.impact }}</p>
            </div>
            <span class="cockpit-pill" :class="object.tone">{{ object.priority }}</span>
          </article>
          <div v-if="!priorityObjects.length" class="cockpit-empty">暂无风险事件</div>
        </div>
      </section>

      <section class="cockpit-card trend-panel">
        <div class="panel-head">
          <div class="panel-title">
            <svg class="cockpit-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-3 3"/></svg>
            <span>巡检趋势</span>
          </div>
          <span>最近 {{ reports.length }} 次</span>
        </div>
        <div class="trend-body">
          <div class="legend">
            <span><i class="legend-critical"></i>严重</span>
            <span><i class="legend-warning"></i>警告</span>
            <span><i class="legend-normal"></i>正常</span>
          </div>
          <svg class="trend-chart" viewBox="0 0 720 180" role="img" aria-label="最近巡检趋势">
            <line x1="0" y1="145" x2="720" y2="145" />
            <line x1="0" y1="96" x2="720" y2="96" />
            <line x1="0" y1="47" x2="720" y2="47" />
            <polyline :points="trendPoints('critical_count')" class="trend-critical" />
            <polyline :points="trendPoints('warning_count')" class="trend-warning" />
            <polyline :points="trendPoints('normal_count')" class="trend-normal" />
          </svg>
        </div>
      </section>

      <section class="cockpit-card table-panel">
        <div class="panel-head">
          <div class="panel-title">
            <svg class="cockpit-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="M16 13H8"/><path d="M16 17H8"/></svg>
            <span>重点对象明细</span>
          </div>
          <span>可返回指挥台处置</span>
        </div>
        <div class="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>对象</th>
                <th>类型</th>
                <th>风险</th>
                <th>结论</th>
                <th>异常数</th>
                <th>影响</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="object in priorityObjects" :key="object.key">
                <td><strong>{{ object.targetName }}</strong></td>
                <td>{{ object.categoryLabel }}</td>
                <td><span class="cockpit-pill" :class="object.tone">{{ object.priority }}</span></td>
                <td>{{ object.headline }}</td>
                <td>{{ object.critical }} 严重 / {{ object.warning }} 警告</td>
                <td>{{ object.impact }}</td>
              </tr>
            </tbody>
          </table>
          <div v-if="!priorityObjects.length" class="cockpit-empty">暂无重点对象</div>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onActivated, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Back, VideoPlay } from '@element-plus/icons-vue'
import { getPatrolReportDetail, getPatrolReports, runPatrol } from '@/api/patrol'
import { formatRelativeTime } from '@/utils/time'
import {
  buildPatrolOverview,
  buildRiskObjects,
  groupRiskObjectsByCategory,
  statusTone,
  type PatrolItemLike,
  type PatrolReportLike,
} from '@/utils/patrolCommand'

const route = useRoute()
const loading = ref(false)
const running = ref(false)
const reports = ref<PatrolReportLike[]>([])
const latestReport = ref<PatrolReportLike | null>(null)
const detailItems = ref<PatrolItemLike[]>([])

const overview = computed(() => buildPatrolOverview(latestReport.value))
const riskObjects = computed(() => buildRiskObjects(detailItems.value))
const riskLanes = computed(() => groupRiskObjectsByCategory(riskObjects.value))
const priorityObjects = computed(() => riskObjects.value.filter((item) => item.status !== 'normal').slice(0, 8))
const topologyObjects = computed(() => (priorityObjects.value.length ? priorityObjects.value : riskObjects.value).slice(0, 5))

function getRequestedReportId() {
  const raw = route.query.reportId
  const value = Array.isArray(raw) ? raw[0] : raw
  const parsed = Number(value)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null
}

async function fetchCockpit() {
  loading.value = true
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
  } finally {
    running.value = false
  }
}

function barWidth(value: number) {
  const max = Math.max(...riskLanes.value.map((lane) => lane.objects.length), 1)
  return Math.max(8, Math.round((value / max) * 100))
}

function trendPoints(field: 'normal_count' | 'warning_count' | 'critical_count') {
  const list = [...reports.value].reverse()
  if (!list.length) return '0,145 720,145'
  const max = Math.max(...list.map((item) => item[field] || 0), 1)
  return list.map((item, index) => {
    const x = list.length === 1 ? 360 : Math.round((index / (list.length - 1)) * 700 + 10)
    const y = Math.round(150 - (((item[field] || 0) / max) * 110))
    return `${x},${y}`
  }).join(' ')
}

function relativeTime(value?: string) {
  return value ? formatRelativeTime(value) : '-'
}

onActivated(fetchCockpit)
</script>

<style scoped>
.patrol-cockpit {
  min-height: calc(100vh - var(--header-height));
  margin: -4px;
  padding: 14px;
  color: #f3f5fa;
  background:
    radial-gradient(circle at 18% 14%, color-mix(in srgb, var(--primary-color) 18%, transparent), transparent 30%),
    radial-gradient(circle at 84% 16%, rgba(6, 182, 212, 0.14), transparent 28%),
    linear-gradient(180deg, #11141d 0%, #0f1117 46%, #0c0e14 100%);
  border-radius: 8px;
}

.cockpit-topbar,
.cockpit-card {
  border: 1px solid #2a3040;
  border-radius: 8px;
  background: rgba(23, 26, 34, 0.9);
}

.cockpit-topbar {
  min-height: 58px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 11px 14px;
  margin-bottom: 12px;
}

.cockpit-heading,
.cockpit-actions,
.panel-title,
.legend {
  display: flex;
  align-items: center;
  gap: 10px;
}

.cockpit-logo {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  background: #3340a8;
}

.cockpit-heading h2 {
  margin: 0;
  font-size: 18px;
}

.cockpit-heading p {
  margin: 2px 0 0;
  color: #8f98aa;
  font-size: 12px;
}

.cockpit-icon {
  width: 16px;
  height: 16px;
  flex: 0 0 auto;
}

.cockpit-dashboard {
  display: grid;
  grid-template-columns: 1.05fr 1.5fr 0.95fr;
  grid-template-rows: 132px minmax(420px, 1fr) 220px;
  gap: 12px;
}

.health-row {
  grid-column: 1 / -1;
  display: grid;
  grid-template-columns: 1.25fr repeat(4, minmax(120px, 0.5fr));
  gap: 12px;
}

.hero-card {
  padding: 14px;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 14px;
}

.score-ring {
  --score: 100%;
  width: 90px;
  aspect-ratio: 1;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: conic-gradient(var(--success-color) 0 var(--score), #2a3040 var(--score) 100%);
  position: relative;
}

.score-ring::after {
  content: "";
  position: absolute;
  inset: 8px;
  border-radius: 50%;
  background: #171a22;
}

.score-ring strong {
  position: relative;
  z-index: 1;
  font-size: 28px;
}

.hero-copy h3 {
  margin: 0;
  font-size: 18px;
}

.hero-copy p {
  margin: 6px 0 0;
  color: #8f98aa;
  font-size: 12px;
  line-height: 1.55;
}

.metric {
  padding: 13px;
  display: grid;
  align-content: space-between;
}

.metric span,
.metric small,
.panel-head > span {
  color: #8f98aa;
  font-size: 12px;
}

.metric strong {
  font-size: 28px;
  line-height: 1;
}

.metric.danger strong { color: var(--danger-color); }
.metric.warning strong { color: var(--warning-color); }
.metric.success strong { color: var(--success-color); }
.metric.info strong { color: #06b6d4; }

.cockpit-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: fit-content;
  min-height: 22px;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 12px;
  font-style: normal;
  font-weight: 700;
  white-space: nowrap;
}

.cockpit-pill.danger {
  color: #ffc4c8;
  background: rgba(229, 72, 77, 0.14);
  border: 1px solid rgba(229, 72, 77, 0.32);
}

.cockpit-pill.warning {
  color: #ffd89b;
  background: rgba(245, 166, 35, 0.13);
  border: 1px solid rgba(245, 166, 35, 0.28);
}

.cockpit-pill.success {
  color: #a7f3c4;
  background: rgba(34, 197, 94, 0.12);
  border: 1px solid rgba(34, 197, 94, 0.25);
}

.cockpit-pill.info {
  color: #a7edff;
  background: rgba(6, 182, 212, 0.12);
  border: 1px solid rgba(6, 182, 212, 0.25);
}

.coverage-panel,
.events-panel,
.trend-panel {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
}

.panel-head {
  min-height: 44px;
  padding: 10px 12px;
  border-bottom: 1px solid #2a3040;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.panel-title {
  min-width: 0;
  font-size: 13px;
  font-weight: 700;
}

.coverage-body,
.trend-body {
  min-height: 0;
  padding: 12px;
  display: grid;
  gap: 12px;
}

.coverage-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.coverage-box {
  border: 1px solid #2a3040;
  border-radius: 7px;
  padding: 9px;
  background: #121620;
  display: grid;
  gap: 5px;
}

.coverage-box span {
  color: #8f98aa;
  font-size: 12px;
}

.coverage-box strong {
  font-size: 17px;
}

.bars {
  display: grid;
  align-content: start;
  gap: 10px;
}

.bar-row {
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr) 38px;
  gap: 8px;
  align-items: center;
  color: #c7ccd8;
  font-size: 12px;
}

.track {
  height: 8px;
  border-radius: 999px;
  background: #252b3a;
  overflow: hidden;
}

.track i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: #06b6d4;
}

.map-panel {
  grid-column: 2;
  grid-row: 2 / 4;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
}

.map-body {
  position: relative;
  min-height: 0;
  overflow: hidden;
  background:
    linear-gradient(rgba(255, 255, 255, 0.035) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.035) 1px, transparent 1px);
  background-size: 34px 34px;
}

.map-line {
  position: absolute;
  height: 1px;
  background: rgba(143, 152, 170, 0.42);
  transform-origin: left center;
}

.line-a { width: 210px; left: 22%; top: 34%; transform: rotate(12deg); }
.line-b { width: 190px; left: 48%; top: 38%; transform: rotate(38deg); }
.line-c { width: 180px; left: 26%; top: 61%; transform: rotate(-23deg); }
.line-d { width: 160px; left: 55%; top: 63%; transform: rotate(-38deg); }

.map-node {
  position: absolute;
  width: 132px;
  border: 1px solid #2a3040;
  border-radius: 8px;
  background: rgba(18, 22, 32, 0.94);
  padding: 9px;
  display: grid;
  gap: 6px;
}

.map-node.danger { border-color: rgba(229, 72, 77, 0.55); }
.map-node.warning { border-color: rgba(245, 166, 35, 0.5); }
.map-node strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
}

.map-node span {
  color: #8f98aa;
  font-size: 12px;
}

.map-node em {
  width: fit-content;
  border-radius: 999px;
  padding: 1px 7px;
  color: #f3f5fa;
  background: #252b3a;
  font-size: 11px;
  font-style: normal;
  font-weight: 700;
}

.node-0 { left: 8%; top: 27%; }
.node-1 { left: 39%; top: 21%; }
.node-2 { left: 69%; top: 42%; }
.node-3 { left: 21%; top: 66%; }
.node-4 { left: 56%; top: 70%; }

.event-list {
  min-height: 0;
  overflow-y: auto;
  padding: 10px;
  display: grid;
  align-content: start;
  gap: 8px;
}

.event-card {
  border: 1px solid #2a3040;
  border-radius: 8px;
  background: #121620;
  padding: 9px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}

.event-card strong {
  font-size: 13px;
}

.event-card p {
  margin: 4px 0 0;
  color: #8f98aa;
  font-size: 12px;
  line-height: 1.45;
}

.legend {
  color: #8f98aa;
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
  display: inline-block;
}

.legend-critical { background: var(--danger-color); }
.legend-warning { background: var(--warning-color); }
.legend-normal { background: var(--success-color); }

.trend-chart {
  min-height: 128px;
  border: 1px solid #2a3040;
  border-radius: 7px;
  background: #121620;
  padding: 10px;
}

.trend-chart line {
  stroke: #2a3040;
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

.table-panel {
  grid-column: 1 / -1;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
}

.table-wrapper {
  min-height: 0;
  overflow: auto;
}

table {
  width: 100%;
  min-width: 860px;
  border-collapse: collapse;
  font-size: 12px;
}

th,
td {
  border-bottom: 1px solid #2a3040;
  padding: 10px;
  text-align: left;
  white-space: nowrap;
}

th {
  color: #8f98aa;
  font-weight: 600;
  background: #151924;
}

td {
  color: #c7ccd8;
}

td strong {
  color: #f3f5fa;
}

.cockpit-empty {
  padding: 24px;
  color: #8f98aa;
  text-align: center;
  font-size: 13px;
}

@media (max-width: 1180px) {
  .cockpit-dashboard {
    grid-template-columns: 1fr 1fr;
    grid-template-rows: auto 520px 340px 260px;
  }

  .health-row {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }

  .hero-card {
    grid-column: 1 / -1;
  }

  .map-panel {
    grid-column: 1 / -1;
    grid-row: 2;
  }

  .trend-panel {
    grid-column: 1 / -1;
  }
}

@media (max-width: 760px) {
  .cockpit-topbar,
  .hero-card,
  .event-card {
    align-items: flex-start;
    flex-direction: column;
  }

  .cockpit-actions {
    flex-wrap: wrap;
  }

  .cockpit-dashboard {
    grid-template-columns: 1fr;
    grid-template-rows: auto 500px auto auto 260px;
  }

  .health-row,
  .coverage-grid {
    grid-template-columns: 1fr;
  }

  .map-panel,
  .coverage-panel,
  .events-panel,
  .trend-panel,
  .table-panel {
    grid-column: 1;
  }

  .map-node {
    width: 112px;
  }

  .node-0 { left: 4%; top: 22%; }
  .node-1 { left: 52%; top: 18%; }
  .node-2 { left: 49%; top: 48%; }
  .node-3 { left: 7%; top: 68%; }
  .node-4 { left: 55%; top: 75%; }
}
</style>
