<template>
  <div class="patrol-page">
    <!-- 页头 -->
    <div class="page-header rise rise-1">
      <div class="title-row">
        <div class="title-badge">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
        </div>
        <div>
          <h2 class="page-title">巡检指挥台</h2>
          <p class="page-subtitle">异常对象优先 · 趋势对比 · 右侧直接进入处置路径</p>
        </div>
      </div>
      <div class="header-actions">
        <el-button @click="goCockpit">
          <el-icon><DataAnalysis /></el-icon> 态势大屏
        </el-button>
        <el-button @click="thresholdDrawerOpen = true">
          <el-icon><Setting /></el-icon> 校准阈值
        </el-button>
        <el-button type="primary" class="btn-run" :loading="running" @click="handleRun">
          <el-icon><VideoPlay /></el-icon> 立即巡检
        </el-button>
      </div>
    </div>

    <!-- 批次趋势条 -->
    <div class="trend-strip rise rise-2" v-loading="loading && !trendItems.length">
      <div class="trend-label">
        <b>巡检趋势</b>
        <span>近 {{ trendItems.length }} 次 · 点击切换</span>
      </div>
      <div v-if="trendItems.length" class="trend-bars">
        <div v-for="t in trendItems" :key="t.report.id" class="trend-bar"
             :class="{ active: selectedReport?.id === t.report.id }"
             :title="`${t.report.title || '巡检报告'} · ${t.fullTime} · 健康分 ${t.score} · 异常 ${t.issues} 项`"
             @click="selectReport(t.report)">
          <div class="bar" :class="'tone-' + t.tone" :style="{ height: Math.max(t.score * 0.52, 4) + 'px' }"></div>
          <span class="bar-score">{{ t.score }}</span>
          <span class="bar-time">{{ t.timeLabel }}</span>
        </div>
      </div>
      <div v-else class="trend-empty">
        暂无巡检报告，点击右上角「立即巡检」生成第一份
      </div>
      <div v-if="trendItems.length" class="trend-compare">
        <div>较上次异常项</div>
        <b :class="issueDelta > 0 ? 'delta-up' : 'delta-down'">
          {{ issueDelta > 0 ? '▲ +' + issueDelta : '▼ ' + issueDelta }}
        </b>
        <div class="compare-time">本批次 {{ selectedFullTime }}</div>
      </div>
    </div>

    <div class="main-grid">
      <!-- 左：概览 + 对象 -->
      <div v-loading="detailLoading">
        <div class="overview-band rise rise-3" :style="{ '--ring-glow': ringGlow }">
          <div class="health-ring">
            <svg width="92" height="92" viewBox="0 0 92 92">
              <defs>
                <linearGradient id="patrolRingGrad" x1="0" y1="0" x2="1" y2="1">
                  <stop offset="0%" :stop-color="ringGradFrom" />
                  <stop offset="100%" :stop-color="ringGradTo" />
                </linearGradient>
              </defs>
              <circle class="ring-track" cx="46" cy="46" r="38" fill="none" stroke-width="8" />
              <circle class="ring-value" cx="46" cy="46" r="38" fill="none" stroke-width="8"
                      stroke="url(#patrolRingGrad)" :stroke-dasharray="ringC" :stroke-dashoffset="ringOffset" />
            </svg>
            <div class="health-ring-text">
              <b>{{ overview.healthScore }}</b>
              <span>健康分</span>
            </div>
          </div>
          <div class="overview-counts">
            <div class="ov-count c-crit"><b>{{ overview.critical }}</b><span>严重项</span></div>
            <div class="ov-count c-warn"><b>{{ overview.warning }}</b><span>警告项</span></div>
            <div class="ov-count c-ok"><b>{{ overview.normal }}</b><span>正常项</span></div>
          </div>
          <div class="issue-chips">
            <div class="issue-chips-title">异常类型分布（点击过滤）</div>
            <div class="chip-row">
              <span v-for="chip in issueChips" :key="chip.type" class="issue-chip"
                    :class="{ active: typeFilter === chip.type }"
                    @click="typeFilter = typeFilter === chip.type ? '' : chip.type">
                <span class="cdot" :style="{ background: chip.color, color: chip.color }"></span>
                {{ chip.type }} <b>{{ chip.count }}</b>
              </span>
              <span v-if="!issueChips.length" class="chips-empty">
                {{ selectedReport ? '本次巡检无异常 🎉' : '等待选择巡检批次' }}
              </span>
            </div>
          </div>
        </div>

        <div class="object-zone rise rise-4">
          <div class="zone-tabs">
            <el-tabs v-model="laneTab">
              <el-tab-pane :label="`全部 (${laneCounts.all})`" name="all" />
              <el-tab-pane :label="`主机 (${laneCounts.host})`" name="host" />
              <el-tab-pane :label="`K8s (${laneCounts.k8s})`" name="k8s" />
              <el-tab-pane :label="`资产 (${laneCounts.asset})`" name="asset" />
            </el-tabs>
            <label class="only-abnormal">
              <el-switch v-model="onlyAbnormal" size="small" /> 只看异常
            </label>
          </div>

          <div class="object-grid">
            <button v-for="obj in visibleObjects" :key="obj.key"
                    class="object-card" :class="['tone-' + toneKey(obj.tone), { selected: selectedObject?.key === obj.key }]"
                    type="button"
                    @click="selectedObjectKey = obj.key">
              <span class="obj-top">
                <span class="obj-name">
                  <b>{{ obj.targetName }}</b>
                  <span class="mono">{{ obj.targetIp || obj.impact }}</span>
                </span>
                <span class="status-pill" :class="'tone-' + toneKey(obj.tone)">{{ obj.priority }}</span>
              </span>
              <div class="obj-headline">{{ obj.headline }}</div>
              <div v-if="worstMetricOf(obj)" class="worst-metric">
                <div class="wm-label">
                  <span>最差：{{ worstMetricOf(obj)!.name }}</span>
                  <b>{{ worstMetricOf(obj)!.value }} / 阈值 {{ worstMetricOf(obj)!.threshold }}</b>
                </div>
                <div v-if="worstMetricOf(obj)!.bar" class="wm-track">
                  <div class="wm-fill" :class="fillClass(worstMetricOf(obj)!.bar!.over)"
                       :style="{ width: worstMetricOf(obj)!.bar!.pct + '%' }"></div>
                  <div class="wm-threshold" :style="{ left: worstMetricOf(obj)!.bar!.thresholdPct + '%' }"></div>
                </div>
              </div>
              <span class="obj-counts">
                <span v-if="obj.critical" class="count-badge crit">{{ obj.critical }} 严重</span>
                <span v-if="obj.warning" class="count-badge warn">{{ obj.warning }} 警告</span>
                <span v-if="!obj.critical && !obj.warning" class="count-badge ok">全部正常</span>
              </span>
            </button>
          </div>
          <div v-if="!visibleObjects.length" class="zone-empty">
            {{ selectedReport ? '当前过滤条件下没有对象' : '请选择巡检批次查看对象' }}
          </div>
        </div>
      </div>

      <!-- 右：处置面板 -->
      <aside class="action-panel rise rise-3">
        <div class="panel-head">
          <span class="panel-title">处置面板</span>
          <div v-if="selectedReport">
            <el-button link type="primary" size="small" @click="handleExport(selectedReport)">导出 Excel</el-button>
            <el-button link type="danger" size="small" @click="handleDelete(selectedReport)">删除</el-button>
          </div>
        </div>

        <template v-if="selectedObject">
          <div class="target-block">
            <div class="target-main">
              <div>
                <h3>{{ selectedObject.targetName }}</h3>
                <p>{{ selectedObject.categoryLabel }} · <span class="mono">{{ selectedObject.targetIp || selectedObject.impact }}</span></p>
              </div>
              <span class="status-pill" :class="'tone-' + toneKey(selectedObject.tone)">{{ selectedObject.priority }}</span>
            </div>
            <div class="target-meta">
              <div><span>巡检结论</span><b>{{ selectedObject.critical }} 严重 / {{ selectedObject.warning }} 警告</b></div>
              <div><span>检查项</span><b>{{ selectedObject.total }}</b></div>
              <div><span>影响范围</span><b>{{ selectedObject.impact }}</b></div>
              <div><span>报告时间</span><b>{{ relativeTime(selectedReport?.created_at) }}</b></div>
            </div>
          </div>

          <template v-if="abnormalFindings.length">
            <div class="sec-title">关键发现</div>
            <div v-for="f in abnormalFindings" :key="f.item.id || `${f.item.check_name}-${f.item.value}`" class="finding">
              <div class="finding-top">
                <strong>{{ f.item.check_name }}</strong>
                <span class="status-pill" :class="'tone-' + toneKey(statusTone(f.item.status))">{{ statusLabel(f.item.status) }}</span>
              </div>
              <p>{{ f.item.detail || '暂无详情' }}</p>
              <div class="worst-metric" style="margin-bottom:6px">
                <div class="wm-label"><span>当前值 <b>{{ f.item.value || '-' }}</b></span><span>阈值 {{ f.item.threshold || '-' }}</span></div>
                <div v-if="f.bar" class="wm-track">
                  <div class="wm-fill" :class="fillClass(f.bar.over)" :style="{ width: f.bar.pct + '%' }"></div>
                  <div class="wm-threshold" :style="{ left: f.bar.thresholdPct + '%' }"></div>
                </div>
              </div>
            </div>
          </template>

          <div class="sec-title">处置建议 · 按异常类型生成</div>
          <ol class="playbook-steps">
            <li v-for="(step, i) in playbook" :key="i" v-html="step"></li>
          </ol>

          <div class="sec-title">快捷动作</div>
          <div class="action-list">
            <button v-if="selectedObject.category === 'host'" class="action-row primary" type="button" @click="goTerminal">
              <span class="action-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 17l6-6-6-6"/><path d="M12 19h8"/></svg></span>
              <span><strong>打开 Web 终端</strong><small>直连 {{ selectedObject.targetName }} 处理异常</small></span>
            </button>
            <button class="action-row" type="button" @click="goTickets">
              <span class="action-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a4 4 0 0 1-4 4H7l-4 4V7a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4z"/></svg></span>
              <span><strong>创建工单</strong><small>自动附带巡检项、阈值与当前值</small></span>
            </button>
            <button class="action-row" type="button" @click="goHostDetail">
              <span class="action-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-3 3"/></svg></span>
              <span><strong>查看对象详情</strong><small>跳转主机 / 集群 / 资产详情页</small></span>
            </button>
          </div>
        </template>

        <div v-else class="panel-empty">
          <div class="big">🎯</div>
          <p>从左侧选择一个对象<br />查看关键发现与处置建议</p>
        </div>
      </aside>
    </div>

    <PatrolThresholdDrawer v-model="thresholdDrawerOpen" />
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onActivated, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { DataAnalysis, Setting, VideoPlay } from '@element-plus/icons-vue'
import { deletePatrolReport, exportPatrolReport, getPatrolReportDetail, getPatrolReports, runPatrol } from '@/api/patrol'
import PatrolThresholdDrawer from './components/PatrolThresholdDrawer.vue'
import { formatRelativeTime } from '@/utils/time'
import {
  buildCockpitRouteLocation,
  buildPatrolOverview,
  buildRiskObjects,
  pickPrimaryRiskObject,
  statusLabel,
  statusTone,
  type PatrolItemLike,
  type PatrolReportLike,
  type PatrolTone,
  type RiskObject,
} from '@/utils/patrolCommand'

const router = useRouter()
const thresholdDrawerOpen = ref(false)
const running = ref(false)
const loading = ref(false)
const detailLoading = ref(false)
const reports = ref<PatrolReportLike[]>([])
const selectedReport = ref<PatrolReportLike | null>(null)
const detailItems = ref<PatrolItemLike[]>([])
const selectedObjectKey = ref('')
const laneTab = ref('all')
const typeFilter = ref('')
const onlyAbnormal = ref(false)

// ── 批次趋势 ──
const TREND_SIZE = 12

interface TrendItem {
  report: PatrolReportLike
  score: number
  issues: number
  tone: 'ok' | 'warn' | 'crit'
  timeLabel: string
  fullTime: string
}

function scoreTone(score: number): 'ok' | 'warn' | 'crit' {
  if (score >= 95) return 'ok'
  if (score >= 90) return 'warn'
  return 'crit'
}

function pad2(n: number) {
  return String(n).padStart(2, '0')
}

function barTime(value?: string): { label: string; full: string } {
  if (!value) return { label: '', full: '-' }
  const d = new Date(value)
  if (isNaN(d.getTime())) return { label: '', full: '-' }
  const hm = `${pad2(d.getHours())}:${pad2(d.getMinutes())}`
  const md = `${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`
  const sameDay = d.toDateString() === new Date().toDateString()
  return { label: sameDay ? hm : md, full: `${md} ${hm}` }
}

const trendItems = computed<TrendItem[]>(() => reports.value.map((report) => {
  const overview = buildPatrolOverview(report)
  const time = barTime(report.created_at)
  return {
    report,
    score: overview.healthScore,
    issues: overview.abnormal,
    tone: scoreTone(overview.healthScore),
    timeLabel: time.label,
    fullTime: time.full,
  }
}))

const selectedFullTime = computed(() => barTime(selectedReport.value?.created_at).full)

const issueDelta = computed(() => {
  const idx = trendItems.value.findIndex(t => t.report.id === selectedReport.value?.id)
  const prev = trendItems.value[idx + 1]
  if (idx < 0 || !prev) return 0
  return trendItems.value[idx].issues - prev.issues
})

// ── 概览 ──
const overview = computed(() => buildPatrolOverview(selectedReport.value))

const ringC = 2 * Math.PI * 38
const ringOffset = computed(() => ringC * (1 - overview.value.healthScore / 100))
const ringGradFrom = computed(() => overview.value.healthScore >= 95 ? '#4ade80' : overview.value.healthScore >= 90 ? '#fbbf24' : '#f87171')
const ringGradTo = computed(() => overview.value.healthScore >= 95 ? '#22c55e' : overview.value.healthScore >= 90 ? '#f59e0b' : '#e5484d')
const ringGlow = computed(() => overview.value.healthScore >= 95 ? 'rgba(34,197,94,.16)' : overview.value.healthScore >= 90 ? 'rgba(245,166,35,.16)' : 'rgba(229,72,77,.16)')

// ── 异常类型聚合 ──
const TYPE_COLORS: Record<string, string> = {
  磁盘: '#e5484d', 内存: '#f5a623', CPU: '#f5a623', 负载: '#f47c48',
  Pod: '#8b5cf6', 集群: '#5e6ad2', 证书: '#22c55e', 连接: '#0ea5e9', 其他: '#9aa0b0',
}

function issueType(checkName = ''): string {
  if (checkName.includes('磁盘')) return '磁盘'
  if (checkName.includes('内存')) return '内存'
  if (/cpu/i.test(checkName)) return 'CPU'
  if (checkName.includes('负载')) return '负载'
  if (checkName.includes('Pod')) return 'Pod'
  if (checkName.includes('节点') || checkName.includes('集群')) return '集群'
  if (checkName.includes('证书')) return '证书'
  if (checkName.includes('连接')) return '连接'
  return '其他'
}

const abnormalItems = computed(() => detailItems.value.filter(i => i.status === 'critical' || i.status === 'warning'))

const issueChips = computed(() => {
  const counter: Record<string, number> = {}
  for (const item of abnormalItems.value) {
    const type = issueType(item.check_name)
    counter[type] = (counter[type] || 0) + 1
  }
  return Object.entries(counter)
    .map(([type, count]) => ({ type, count, color: TYPE_COLORS[type] || '#5e6ad2' }))
    .sort((a, b) => b.count - a.count)
})

// ── 对象列表 ──
const riskObjects = computed(() => buildRiskObjects(detailItems.value))

const laneCounts = computed(() => ({
  all: riskObjects.value.length,
  host: riskObjects.value.filter(o => o.category === 'host').length,
  k8s: riskObjects.value.filter(o => o.category === 'k8s').length,
  asset: riskObjects.value.filter(o => o.category === 'asset').length,
}))

const visibleObjects = computed(() => {
  let list = riskObjects.value
  if (laneTab.value !== 'all') list = list.filter(o => o.category === laneTab.value)
  if (typeFilter.value) list = list.filter(o => o.items.some(i => (i.status === 'critical' || i.status === 'warning') && issueType(i.check_name) === typeFilter.value))
  if (onlyAbnormal.value) list = list.filter(o => o.critical || o.warning)
  return list
})

const selectedObject = computed(() =>
  riskObjects.value.find(item => item.key === selectedObjectKey.value) || pickPrimaryRiskObject(riskObjects.value),
)

watch(riskObjects, (objects) => {
  if (!objects.length) {
    selectedObjectKey.value = ''
    return
  }
  if (!objects.some(item => item.key === selectedObjectKey.value)) {
    selectedObjectKey.value = pickPrimaryRiskObject(objects)?.key || objects[0].key
  }
})

// ── 指标进度条 ──
interface MetricBar { pct: number; thresholdPct: number; over: number }

function parseNum(s?: string): number | null {
  const m = (s || '').match(/-?\d+(\.\d+)?/)
  return m ? parseFloat(m[0]) : null
}

function metricBar(value?: string, threshold?: string): MetricBar | null {
  const v = parseNum(value)
  if (v === null) return null
  const t = parseNum(threshold) ?? 0
  const scale = Math.max(v, t, 1) * 1.15
  return {
    pct: Math.min(100, (v / scale) * 100),
    thresholdPct: t > 0 ? Math.min(100, (t / scale) * 100) : 5,
    over: t > 0 ? v / t : (v > 0 ? 2 : 0),
  }
}

function fillClass(over: number) {
  return over >= 1 ? 'over' : over >= 0.85 ? 'warn' : 'ok'
}

interface WorstMetric {
  name: string
  value: string
  threshold: string
  bar: MetricBar | null
}

function worstMetricOf(obj: RiskObject): WorstMetric | null {
  const lead = obj.items.find(i => i.status === 'critical') || obj.items.find(i => i.status === 'warning')
  if (!lead) return null
  return {
    name: lead.check_name || '检查项',
    value: lead.value || '-',
    threshold: lead.threshold || '-',
    bar: metricBar(lead.value, lead.threshold),
  }
}

const abnormalFindings = computed(() => {
  if (!selectedObject.value) return []
  const items = [...selectedObject.value.items]
    .filter(i => i.status === 'critical' || i.status === 'warning')
    .sort((a, b) => (a.status === b.status ? 0 : a.status === 'critical' ? -1 : 1))
    .slice(0, 5)
  return items.map(item => ({ item, bar: metricBar(item.value, item.threshold) }))
})

// ── 动态处置建议 ──
function buildPlaybook(object: RiskObject | null): string[] {
  if (!object) return []
  const abnormal = object.items.filter(i => i.status === 'critical' || i.status === 'warning')
  if (!abnormal.length) return ['本次巡检未发现异常，保持常规观察。']

  const names = abnormal.map(i => i.check_name || '').join(' ')
  const steps: string[] = []

  if (object.category === 'host') {
    if (names.includes('磁盘')) {
      steps.push(
        '通过 <b>Web 终端</b> 登录主机，执行 <code>du -xh / 2>/dev/null | sort -h | tail -20</code> 定位大文件',
        '清理或归档历史日志：<code>journalctl --vacuum-time=3d</code>',
      )
    }
    if (names.includes('内存')) {
      steps.push(
        '查看内存占用 Top 进程：<code>ps aux --sort=-%mem | head</code>',
        '确认是否存在内存泄漏或缓存膨胀，必要时低峰重启对应服务',
      )
    }
    if (/cpu/i.test(names)) {
      steps.push('定位高 CPU 进程：<code>top -b -n 1 | head -20</code>，评估是否限流或扩容')
    }
    if (names.includes('负载')) {
      steps.push('检查负载来源：<code>uptime</code> 结合 <code>iostat -x 1 3</code> 判断是 CPU 还是 IO 瓶颈')
    }
    if (names.includes('连接') || names.includes('Prometheus')) {
      steps.push(
        '确认采集 agent 是否运行：<code>systemctl status node_exporter</code>',
        '检查 Prometheus 目标配置与网络连通性',
      )
    }
  } else if (object.category === 'k8s') {
    steps.push(
      '查看异常 Pod 详情：<code>kubectl describe pod &lt;名称&gt;</code> 确认重启 / Pending 原因',
      'OOMKilled 则调高 limits 或排查内存泄漏；资源不足则检查节点容量与亲和性',
      '处理后在容器页观察重启计数是否停止增长',
    )
  } else {
    steps.push(
      '打开资产详情确认证书 / 状态信息',
      '需要变更时创建工单并转交对应负责人',
    )
  }

  if (!steps.length) {
    steps.push(
      '打开对象详情，确认影响范围与最近变更',
      '处理后观察 30 分钟关键指标是否回落',
    )
  }
  steps.push('无法短期恢复时 <b>创建工单</b> 并转交对应负责人')
  return steps.slice(0, 4)
}

const playbook = computed(() => buildPlaybook(selectedObject.value))

// ── 工具 ──
function toneKey(tone: PatrolTone): 'ok' | 'warn' | 'crit' {
  if (tone === 'danger') return 'crit'
  if (tone === 'warning') return 'warn'
  return 'ok'
}

function relativeTime(value?: string) {
  return value ? formatRelativeTime(value) : '-'
}

// ── 数据加载 ──
async function fetchReports() {
  loading.value = true
  try {
    const res: any = await getPatrolReports({ page: 1, page_size: TREND_SIZE })
    reports.value = res.data.items
    if (!selectedReport.value && reports.value.length) {
      await selectReport(reports.value[0])
    } else if (selectedReport.value) {
      const current = reports.value.find(item => item.id === selectedReport.value?.id)
      if (current) selectedReport.value = current
    }
  } finally {
    loading.value = false
  }
}

async function selectReport(report: PatrolReportLike) {
  if (selectedReport.value?.id === report.id && detailItems.value.length) return
  selectedReport.value = report
  selectedObjectKey.value = ''
  typeFilter.value = ''
  detailLoading.value = true
  try {
    const res: any = await getPatrolReportDetail(report.id as number)
    selectedReport.value = res.data.report
    detailItems.value = res.data.items
    await nextTick()
  } catch (e: any) {
    detailItems.value = []
    ElMessage.error(e?.response?.data?.detail || '加载巡检详情失败')
  } finally {
    detailLoading.value = false
  }
}

async function handleRun() {
  running.value = true
  try {
    const res: any = await runPatrol()
    ElMessage.success(`巡检完成：${res.data.summary}`)
    selectedReport.value = null
    await fetchReports()
  } finally {
    running.value = false
  }
}

async function handleExport(row: PatrolReportLike | null) {
  if (!row?.id) return
  try {
    const res: any = await exportPatrolReport(row.id)
    const blob = new Blob([res.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${row.title || '巡检报告'}.xlsx`
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch {
    ElMessage.error('导出失败')
  }
}

async function handleDelete(row: PatrolReportLike | null) {
  if (!row?.id) return
  await ElMessageBox.confirm(`确定删除巡检报告「${row.title}」？此操作不可恢复。`, '删除确认', {
    type: 'warning',
    confirmButtonText: '确认删除',
    cancelButtonText: '取消',
  })
  await deletePatrolReport(row.id)
  ElMessage.success('删除成功')
  selectedReport.value = null
  detailItems.value = []
  await fetchReports()
}

function goHostDetail() {
  const object = selectedObject.value
  if (!object) return
  if (object.category === 'host') router.push('/monitoring/hosts')
  else if (object.category === 'k8s') router.push('/assets/containers')
  else router.push('/assets/list')
}

function goTerminal() {
  router.push('/monitoring/hosts')
}

function goTickets() {
  router.push('/tickets')
}

function goCockpit() {
  router.push(buildCockpitRouteLocation(selectedReport.value))
}

onActivated(fetchReports)
</script>

<style scoped>
.patrol-page { min-width: 0; }
.mono { font-family: "SF Mono", "JetBrains Mono", Consolas, monospace; }

/* ═══ 入场动画 ═══ */
@keyframes rise {
  from { opacity: 0; transform: translateY(14px); }
  to { opacity: 1; transform: translateY(0); }
}
.rise { animation: rise .5s cubic-bezier(.22, .8, .36, 1) both; }
.rise-1 { animation-delay: .03s; }
.rise-2 { animation-delay: .09s; }
.rise-3 { animation-delay: .15s; }
.rise-4 { animation-delay: .21s; }

/* ═══ 页头 ═══ */
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 18px; }
.title-row { display: flex; align-items: center; gap: 12px; }
.title-badge {
  width: 38px; height: 38px; border-radius: 11px;
  background: linear-gradient(135deg, #5e6ad2, #8b5cf6);
  box-shadow: 0 6px 16px -4px rgba(94, 106, 210, .5), inset 0 1px 0 rgba(255, 255, 255, .25);
  display: flex; align-items: center; justify-content: center; color: #fff;
}
.title-badge svg { width: 20px; height: 20px; }
.page-title { font-size: 21px; font-weight: 800; letter-spacing: .01em; }
.page-subtitle { font-size: 12px; color: var(--text-muted); margin-top: 3px; }
.header-actions { display: flex; gap: 8px; }
.btn-run { box-shadow: 0 6px 16px -4px rgba(94, 106, 210, .45) !important; }

/* ═══ 批次趋势条 ═══ */
.trend-strip {
  background: var(--surface-color); border: 1px solid var(--border-color);
  border-radius: 14px; box-shadow: 0 1px 2px rgba(21, 22, 26, .03), 0 2px 6px rgba(21, 22, 26, .05);
  padding: 16px 20px; margin-bottom: 16px;
  display: flex; align-items: center; gap: 22px;
  position: relative; overflow: hidden; min-height: 92px;
}
.trend-label { flex-shrink: 0; }
.trend-label b { font-size: 13px; display: block; letter-spacing: .01em; }
.trend-label span { font-size: 11px; color: var(--text-muted); }
.trend-empty { flex: 1; text-align: center; font-size: 12px; color: var(--text-muted); }
.trend-bars { display: flex; align-items: flex-end; gap: 7px; flex: 1; min-width: 0; }
.trend-bar {
  flex: 1; max-width: 46px; cursor: pointer; text-align: center;
  display: flex; flex-direction: column; align-items: center; gap: 5px;
}
.trend-bar .bar {
  width: 100%; border-radius: 5px 5px 3px 3px; min-height: 4px;
  transition: height .35s cubic-bezier(.22, .8, .36, 1), opacity .2s, transform .18s, box-shadow .2s;
  opacity: .45; position: relative;
}
.trend-bar:hover .bar { opacity: .8; transform: translateY(-2px); }
.trend-bar.active .bar {
  opacity: 1; transform: translateY(-2px);
  box-shadow: 0 4px 12px -2px currentColor;
}
.trend-bar .bar-score { font-size: 10px; color: var(--text-muted); transition: color .2s; }
.trend-bar.active .bar-score { color: var(--text-primary); font-weight: 800; }
.trend-bar .bar-time { font-size: 9px; color: var(--text-muted); opacity: .8; line-height: 1; }
.compare-time { font-size: 10px; color: var(--text-muted); margin-top: 3px; }
.bar.tone-ok { background: linear-gradient(180deg, #4ade80, #22c55e); color: rgba(34, 197, 94, .5); }
.bar.tone-warn { background: linear-gradient(180deg, #fbbf24, #f59e0b); color: rgba(245, 166, 35, .5); }
.bar.tone-crit { background: linear-gradient(180deg, #f87171, #e5484d); color: rgba(229, 72, 77, .5); }
.trend-compare {
  flex-shrink: 0; text-align: right; font-size: 12px; color: var(--text-secondary);
  border-left: 1px solid var(--border-color); padding-left: 22px;
}
.trend-compare b { font-size: 16px; font-weight: 800; }
.delta-up { color: var(--danger-color); }
.delta-down { color: var(--success-color); }

/* ═══ 主区两栏 ═══ */
.main-grid { display: grid; grid-template-columns: minmax(0, 1fr) 368px; gap: 16px; align-items: start; }

/* ── 概览带 ── */
.overview-band {
  background: var(--surface-color); border: 1px solid var(--border-color);
  border-radius: 14px; box-shadow: 0 1px 2px rgba(21, 22, 26, .03), 0 2px 6px rgba(21, 22, 26, .05);
  padding: 20px 24px; margin-bottom: 16px;
  display: flex; align-items: center; gap: 26px;
  position: relative; overflow: hidden;
}
.overview-band::after {
  content: ''; position: absolute; left: -40px; top: -60px;
  width: 220px; height: 220px; border-radius: 50%;
  background: radial-gradient(circle, var(--ring-glow, rgba(34, 197, 94, .14)), transparent 70%);
  pointer-events: none; transition: background .5s;
}
.health-ring { position: relative; width: 92px; height: 92px; flex-shrink: 0; z-index: 1; }
.health-ring svg { transform: rotate(-90deg); }
.ring-track { stroke: #eef0f6; }
.ring-value { stroke-linecap: round; transition: stroke-dashoffset .9s cubic-bezier(.4, 0, .2, 1); }
.health-ring-text { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; }
.health-ring-text b { font-size: 24px; font-weight: 800; line-height: 1; letter-spacing: -.02em; }
.health-ring-text span { font-size: 10px; color: var(--text-muted); margin-top: 3px; }

.overview-counts { display: flex; gap: 26px; z-index: 1; }
.ov-count { text-align: center; position: relative; }
.ov-count b { font-size: 26px; font-weight: 800; display: block; line-height: 1.1; letter-spacing: -.02em; }
.ov-count span { font-size: 11px; color: var(--text-muted); }
.ov-count.c-crit b { color: var(--danger-color); text-shadow: 0 0 24px rgba(229, 72, 77, .35); }
.ov-count.c-warn b { color: #d48806; text-shadow: 0 0 24px rgba(245, 166, 35, .35); }
.ov-count.c-ok b { color: var(--success-color); text-shadow: 0 0 24px rgba(34, 197, 94, .3); }

.issue-chips { flex: 1; min-width: 0; border-left: 1px solid var(--border-color); padding-left: 24px; z-index: 1; }
.issue-chips-title { font-size: 11px; color: var(--text-muted); margin-bottom: 9px; }
.chips-empty { font-size: 12px; color: var(--text-muted); }
.chip-row { display: flex; gap: 8px; flex-wrap: wrap; }
.issue-chip {
  display: inline-flex; align-items: center; gap: 7px;
  border: 1px solid var(--border-color); background: #fafbfd;
  border-radius: 18px; padding: 5px 12px; font-size: 12px; cursor: pointer;
  transition: all .18s; color: var(--text-secondary); font-weight: 500;
}
.issue-chip b { font-weight: 800; }
.issue-chip:hover { border-color: var(--primary-color); color: var(--primary-color); transform: translateY(-1px); box-shadow: 0 4px 10px -3px rgba(94, 106, 210, .3); }
.issue-chip.active {
  background: linear-gradient(135deg, #5e6ad2, #7c5cd6); border-color: transparent; color: #fff;
  box-shadow: 0 6px 14px -4px rgba(94, 106, 210, .5);
}
.issue-chip .cdot { width: 7px; height: 7px; border-radius: 50%; box-shadow: 0 0 6px currentColor; }

/* ── 对象区 ── */
.object-zone {
  background: var(--surface-color); border: 1px solid var(--border-color);
  border-radius: 14px; box-shadow: 0 1px 2px rgba(21, 22, 26, .03), 0 2px 6px rgba(21, 22, 26, .05);
  padding: 4px 20px 20px;
}
.zone-tabs { display: flex; align-items: center; justify-content: space-between; }
.only-abnormal { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--text-secondary); white-space: nowrap; }

.object-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(284px, 1fr)); gap: 13px; margin-top: 2px; }
.object-card {
  border: 1px solid var(--border-color); border-radius: 12px; padding: 15px 17px;
  cursor: pointer; transition: all .2s cubic-bezier(.22, .8, .36, 1); background: var(--surface-color);
  position: relative; overflow: hidden; text-align: left; font-family: inherit;
}
.object-card::before {
  content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 3.5px;
  background: linear-gradient(180deg, var(--tone-from, #d3d7e0), var(--tone-to, #b9bfcc));
}
.object-card::after {
  content: ''; position: absolute; right: -30px; top: -30px;
  width: 110px; height: 110px; border-radius: 50%;
  background: radial-gradient(circle, var(--tone-glow, transparent), transparent 70%);
  opacity: 0; transition: opacity .25s; pointer-events: none;
}
.object-card:hover { border-color: #d4d9e8; box-shadow: 0 6px 16px -4px rgba(21, 22, 26, .08), 0 16px 40px -8px rgba(21, 22, 26, .1); transform: translateY(-3px); }
.object-card:hover::after { opacity: 1; }
.object-card.selected {
  border-color: var(--primary-color);
  box-shadow: 0 0 0 1.5px var(--primary-color), 0 12px 28px -8px rgba(94, 106, 210, .3);
}
.object-card.tone-crit { --tone-from: #f87171; --tone-to: #e5484d; --tone-glow: rgba(229, 72, 77, .12); }
.object-card.tone-warn { --tone-from: #fbbf24; --tone-to: #f59e0b; --tone-glow: rgba(245, 166, 35, .12); }
.object-card.tone-ok { --tone-from: #4ade80; --tone-to: #22c55e; --tone-glow: rgba(34, 197, 94, .12); }

.obj-top { display: flex; align-items: flex-start; justify-content: space-between; gap: 8px; }
.obj-name b { font-size: 13px; font-weight: 700; display: block; }
.obj-name span { font-size: 11px; color: var(--text-muted); }
.obj-headline { font-size: 12px; color: var(--text-secondary); margin: 8px 0 11px; line-height: 1.5; }

.worst-metric { margin-bottom: 11px; }
.worst-metric .wm-label { display: flex; justify-content: space-between; font-size: 11px; color: var(--text-muted); margin-bottom: 5px; }
.worst-metric .wm-label b { color: var(--text-primary); }
.wm-track { height: 7px; border-radius: 4px; background: #eef0f6; position: relative; overflow: visible; margin-top: 14px; }
.wm-fill { height: 100%; border-radius: 4px; transition: width .6s cubic-bezier(.22, .8, .36, 1); position: relative; }
.wm-fill.over { background: linear-gradient(90deg, #f5a623, var(--danger-color)); box-shadow: 0 0 10px rgba(229, 72, 77, .4); }
.wm-fill.warn { background: linear-gradient(90deg, #fbbf24, #f59e0b); box-shadow: 0 0 8px rgba(245, 166, 35, .35); }
.wm-fill.ok { background: linear-gradient(90deg, #4ade80, #22c55e); }
.wm-threshold {
  position: absolute; top: -3px; bottom: -3px; width: 2px; background: var(--text-primary);
  opacity: .4; border-radius: 1px;
}
.wm-threshold::after {
  content: '阈值'; position: absolute; top: -14px; left: 50%; transform: translateX(-50%);
  font-size: 9px; color: var(--text-muted); white-space: nowrap;
}

.obj-counts { display: flex; gap: 6px; }
.count-badge { font-size: 11px; font-weight: 600; padding: 2px 9px; border-radius: 11px; }
.count-badge.crit { background: rgba(229, 72, 77, .1); color: #c2282d; }
.count-badge.warn { background: rgba(245, 166, 35, .12); color: #92600a; }
.count-badge.ok { background: rgba(34, 197, 94, .1); color: #15803d; }

.status-pill {
  font-size: 11px; font-weight: 700; padding: 3px 10px; border-radius: 13px; flex-shrink: 0;
  display: inline-flex; align-items: center; gap: 5px;
}
.status-pill::before { content: ''; width: 5px; height: 5px; border-radius: 50%; background: currentColor; }
.status-pill.tone-crit { background: rgba(229, 72, 77, .1); color: #c2282d; }
.status-pill.tone-warn { background: rgba(245, 166, 35, .12); color: #92600a; }
.status-pill.tone-ok { background: rgba(34, 197, 94, .1); color: #15803d; }

.zone-empty { text-align: center; color: var(--text-muted); font-size: 12px; padding: 40px 0; }

/* ── 处置面板 ── */
.action-panel {
  background: var(--surface-color); border: 1px solid var(--border-color);
  border-radius: 14px; box-shadow: 0 1px 2px rgba(21, 22, 26, .03), 0 2px 6px rgba(21, 22, 26, .05);
  padding: 18px 20px; position: sticky; top: 16px;
  overflow: hidden;
}
.panel-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.panel-title { font-size: 14px; font-weight: 800; display: flex; align-items: center; gap: 8px; letter-spacing: .01em; }

.target-block {
  background: linear-gradient(135deg, #f7f8fc, #f2f4fb);
  border: 1px solid var(--border-color);
  border-radius: 11px; padding: 15px; margin-bottom: 6px;
}
.target-main { display: flex; align-items: flex-start; justify-content: space-between; gap: 8px; }
.target-main h3 { font-size: 14px; font-weight: 800; }
.target-main p { font-size: 11px; color: var(--text-muted); margin-top: 3px; }
.target-meta { display: grid; grid-template-columns: 1fr 1fr; gap: 10px 8px; margin-top: 13px; }
.target-meta div span { font-size: 10px; color: var(--text-muted); display: block; margin-bottom: 2px; }
.target-meta div b { font-size: 12px; }

.sec-title {
  font-size: 11px; font-weight: 800; margin: 18px 0 10px; color: var(--text-muted);
  letter-spacing: .08em;
  display: flex; align-items: center; gap: 8px;
}
.sec-title::after { content: ''; flex: 1; height: 1px; background: var(--border-color); }

.finding {
  border: 1px solid var(--border-color); border-radius: 10px;
  padding: 11px 13px; margin-bottom: 9px;
  transition: border-color .15s, box-shadow .15s;
}
.finding:hover { border-color: #d4d9e8; box-shadow: 0 1px 2px rgba(21, 22, 26, .03), 0 2px 6px rgba(21, 22, 26, .05); }
.finding-top { display: flex; justify-content: space-between; align-items: center; }
.finding-top strong { font-size: 12px; }
.finding p { font-size: 11px; color: var(--text-secondary); margin: 7px 0 8px; line-height: 1.55; }
.finding .wm-label { font-size: 10px; }

.playbook-steps { padding-left: 0; list-style: none; counter-reset: step; }
.playbook-steps li {
  counter-increment: step; position: relative;
  padding: 9px 0 9px 36px; font-size: 12px; color: var(--text-secondary); line-height: 1.55;
}
.playbook-steps li::before {
  content: counter(step); position: absolute; left: 0; top: 9px;
  width: 23px; height: 23px; border-radius: 8px;
  background: linear-gradient(135deg, var(--primary-bg), rgba(139, 92, 246, .12));
  border: 1px solid rgba(94, 106, 210, .2);
  color: var(--primary-color);
  font-size: 11px; font-weight: 800;
  display: flex; align-items: center; justify-content: center;
}
.playbook-steps li:not(:last-child)::after {
  content: ''; position: absolute; left: 11px; top: 36px; bottom: -2px;
  width: 1.5px; background: linear-gradient(180deg, rgba(94, 106, 210, .25), transparent);
}
.playbook-steps li b { color: var(--text-primary); }
.playbook-steps li :deep(code) {
  font-family: "SF Mono", Consolas, monospace; font-size: 11px;
  background: #f2f3fa; border: 1px solid var(--border-color);
  padding: 1px 6px; border-radius: 5px; color: var(--primary-hover); font-weight: 600;
}

.action-list { display: flex; flex-direction: column; gap: 9px; }
.action-row {
  display: flex; align-items: center; gap: 12px; width: 100%;
  border: 1px solid var(--border-color); border-radius: 10px;
  padding: 11px 13px; cursor: pointer; background: var(--surface-color);
  transition: all .18s; text-align: left; font-family: inherit;
}
.action-row:hover { border-color: var(--primary-color); background: var(--primary-bg); transform: translateX(2px); }
.action-row.primary {
  background: linear-gradient(135deg, #5e6ad2, #7c5cd6); border-color: transparent; color: #fff;
  box-shadow: 0 8px 18px -6px rgba(94, 106, 210, .55);
}
.action-row.primary:hover { transform: translateX(2px); box-shadow: 0 10px 22px -6px rgba(94, 106, 210, .65); }
.action-row.primary small { color: rgba(255, 255, 255, .78); }
.action-icon {
  width: 32px; height: 32px; border-radius: 9px; flex-shrink: 0;
  background: var(--primary-bg); color: var(--primary-color);
  display: flex; align-items: center; justify-content: center;
}
.action-row.primary .action-icon { background: rgba(255, 255, 255, .18); color: #fff; }
.action-icon svg { width: 16px; height: 16px; }
.action-row strong { font-size: 12px; display: block; font-weight: 700; }
.action-row small { font-size: 11px; color: var(--text-muted); }

.panel-empty { text-align: center; padding: 52px 0; color: var(--text-muted); }
.panel-empty .big { font-size: 34px; margin-bottom: 12px; }
.panel-empty p { font-size: 12px; line-height: 1.7; }

@media (max-width: 1100px) {
  .main-grid { grid-template-columns: 1fr; }
  .action-panel { position: static; }
}
</style>
