<template>
  <div class="alert-events">
    <header class="page-header">
      <div>
        <h2 class="page-title">告警事件</h2>
        <p class="page-subtitle">值班视角的告警事实流，firing 优先，点击事件行展开排障面板。</p>
      </div>
      <div class="header-actions">
        <span v-if="lastRefresh" class="last-refresh">最近刷新 {{ lastRefresh }}</span>
        <span class="firing-pill" :class="{ hot: stats.firing > 0 }">
          <span class="dot"></span>{{ stats.firing }} firing
        </span>
        <el-button :type="autoRefresh ? 'primary' : 'default'" size="small" @click="toggleAutoRefresh">
          {{ autoRefresh ? '自动刷新中' : '自动刷新' }}
        </el-button>
        <el-button size="small" :loading="loading" @click="refreshAll">
          <el-icon><Refresh /></el-icon>
          立即刷新
        </el-button>
      </div>
    </header>

    <el-alert v-if="loadError" type="warning" :closable="false" class="load-error" show-icon>
      <template #title>告警事件加载失败，请检查网络或稍后重试；数据来自 Alertmanager Webhook 落库。</template>
    </el-alert>

    <!-- 概览统计条（点击即筛选） -->
    <div class="stat-row">
      <button type="button" class="stat-card" :class="{ active: filterStatus === 'firing' && !filterSeverity, hot: stats.firing > 0 }"
              @click="clickFiringCard">
        <div class="stat-num">{{ stats.firing }}</div>
        <div class="stat-label"><span class="dot"></span>Firing</div>
      </button>
      <button type="button" class="stat-card critical" :class="{ active: filterSeverity === 'critical', hot: stats.criticalFiring > 0 }"
              @click="clickCriticalCard">
        <div class="stat-num">{{ stats.criticalFiring }}</div>
        <div class="stat-label"><span class="dot"></span>Critical（firing）</div>
      </button>
      <button type="button" class="stat-card" :class="{ active: filterStatus === 'resolved' }"
              @click="clickResolvedCard">
        <div class="stat-num">{{ stats.resolved }}</div>
        <div class="stat-label">已恢复</div>
      </button>
      <button type="button" class="stat-card" :class="{ active: !filterStatus && !filterSeverity }"
              @click="clearFilters">
        <div class="stat-num">{{ stats.total }}</div>
        <div class="stat-label">全部事件</div>
      </button>
    </div>

    <div class="data-card">
      <div class="toolbar">
        <el-input
          v-model="keyword"
          placeholder="搜索告警名称 / 实例"
          clearable
          size="small"
          style="width: 220px"
          @keyup.enter="applyFilters"
        />
        <el-select v-model="filterSeverity" placeholder="严重程度" clearable size="small" style="width: 130px" @change="applyFilters">
          <el-option label="critical" value="critical" />
          <el-option label="warn" value="warn" />
          <el-option label="warning" value="warning" />
          <el-option label="info" value="info" />
        </el-select>
        <el-select v-model="filterStatus" placeholder="状态" clearable size="small" style="width: 130px" @change="applyFilters">
          <el-option label="firing" value="firing" />
          <el-option label="resolved" value="resolved" />
        </el-select>
        <el-button type="primary" size="small" @click="applyFilters">查询</el-button>
      </div>

      <div class="table-wrapper">
        <el-table ref="tableRef" :data="items" stripe v-loading="loading" @row-click="onRowClick">
          <el-table-column type="expand" width="36">
            <template #default="{ row }">
              <div class="detail-panel">
                <div class="dp-grid">
                  <div class="dp-block">
                    <div class="dp-title">Labels</div>
                    <div class="label-chips">
                      <span v-for="chip in labelChips(row)" :key="chip" class="label-chip mono"
                            :title="'点击复制 ' + chip" @click="copyText(chip)">{{ chip }}</span>
                      <span v-if="!labelChips(row).length" class="no-data">无</span>
                    </div>
                  </div>
                  <div class="dp-block">
                    <div class="dp-title">Annotations</div>
                    <div v-if="annotationEntries(row).length" class="anno-list">
                      <div v-for="[k, v] in annotationEntries(row)" :key="k" class="anno-row">
                        <span class="dp-ck">{{ k }}</span>
                        <a v-if="isUrl(v)" :href="v" target="_blank" rel="noopener" class="anno-link">{{ v }}</a>
                        <span v-else class="anno-val">{{ v }}</span>
                      </div>
                    </div>
                    <span v-else class="no-data">无</span>
                  </div>
                </div>
                <div class="dp-meta">
                  <span class="mono">fingerprint: {{ row.fingerprint || '-' }}</span>
                  <span>接收时间 {{ fullTime(row.received_at) }}</span>
                  <a v-if="row.generator_url" :href="row.generator_url" target="_blank" rel="noopener" class="anno-link">Prometheus 表达式 ↗</a>
                </div>
                <div class="dp-actions">
                  <el-tooltip content="在日志检索中查看该告警时间窗 ±15 分钟的相关日志" placement="top">
                    <el-button size="small" type="primary" plain @click.stop="goRelatedLogs(row)">关联日志（±15 分钟）</el-button>
                  </el-tooltip>
                  <el-button v-if="canCreateTicket" size="small" plain @click.stop="openTicketDialog(row)">转为工单</el-button>
                </div>
              </div>
            </template>
          </el-table-column>

          <el-table-column label="严重程度" width="96">
            <template #default="{ row }">
              <el-tag :type="severityType(row.severity)" size="small"
                      :effect="row.severity === 'critical' && row.status === 'firing' ? 'dark' : 'plain'">
                {{ row.severity }}
              </el-tag>
            </template>
          </el-table-column>

          <el-table-column label="状态" width="110">
            <template #default="{ row }">
              <el-tag :type="row.status === 'firing' ? 'danger' : 'success'" size="small"
                      :effect="row.status === 'firing' ? 'dark' : 'plain'" class="status-tag">
                <span v-if="row.status === 'firing'" class="tag-dot"></span>{{ row.status }}
              </el-tag>
              <div v-if="row.status === 'firing' && row.alert_value" class="alert-value mono">{{ row.alert_value }}</div>
            </template>
          </el-table-column>

          <el-table-column label="告警" min-width="280">
            <template #default="{ row }">
              <div class="alert-cell">
                <div class="alert-name">{{ row.alert_name }}</div>
                <div class="alert-summary">{{ row.summary || row.description || '-' }}</div>
              </div>
            </template>
          </el-table-column>

          <el-table-column label="来源" min-width="180" show-overflow-tooltip>
            <template #default="{ row }">
              <span class="mono source-text">{{ sourceText(row) }}</span>
            </template>
          </el-table-column>

          <el-table-column label="触发 / 持续" width="150">
            <template #default="{ row }">
              <div class="time-cell">
                <div class="t-rel" :title="fullTime(row.starts_at)">{{ relTime(row.starts_at) }}</div>
                <div class="t-dur" :class="{ firing: row.status === 'firing' }">{{ durationText(row) }}</div>
              </div>
            </template>
          </el-table-column>

          <el-table-column label="次数" width="70" align="center">
            <template #default="{ row }">
              <span v-if="row.firing_count >= 3" class="count-badge" title="连续触发次数">×{{ row.firing_count }}</span>
              <span v-else class="no-data">—</span>
            </template>
          </el-table-column>

          <template #empty>
            <div class="empty-state">
              <div class="empty-icon">{{ filterStatus === 'firing' ? '✅' : '🔍' }}</div>
              <div class="empty-text">{{ filterStatus === 'firing' ? '当前没有 firing 的告警' : '没有匹配的告警事件' }}</div>
              <div class="empty-sub">{{ filterStatus === 'firing' ? '系统运行平稳。点击「全部事件」查看历史' : '调整筛选条件后重试' }}</div>
            </div>
          </template>
        </el-table>
      </div>

      <div class="pagination" v-if="total > pageSize">
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="fetchData"
        />
      </div>
    </div>

    <!-- 转为工单 -->
    <el-dialog v-model="ticketVisible" title="转为工单" width="min(560px, 90vw)">
      <el-form label-position="top">
        <el-form-item label="标题">
          <el-input v-model="ticketForm.title" maxlength="120" show-word-limit />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="ticketForm.description" type="textarea" :rows="6" />
        </el-form-item>
        <el-form-item label="优先级">
          <el-select v-model="ticketForm.priority" style="width: 160px">
            <el-option label="低" value="low" />
            <el-option label="中" value="normal" />
            <el-option label="高" value="high" />
            <el-option label="紧急" value="critical" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="ticketVisible = false">取消</el-button>
        <el-button type="primary" :loading="ticketSaving" @click="submitTicket">创建工单</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onActivated, onDeactivated, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { getAlertManagerEvents } from '@/api/alertmanager'
import { createTicket } from '@/api/tickets'
import { useAuthStore } from '@/stores/modules/auth'
import { formatRelativeTime } from '@/utils/time'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

interface AlertEvent {
  id: number
  fingerprint: string
  alert_name: string
  severity: string
  status: string
  alert_value: string
  summary: string
  description: string
  instance: string
  job: string
  firing_count: number
  generator_url: string
  starts_at: string | null
  ends_at: string | null
  received_at: string | null
  raw_labels: string
  raw_annotations: string
}

const loading = ref(false)
const loadError = ref(false)
const items = ref<AlertEvent[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const keyword = ref(typeof route.query.keyword === 'string' ? route.query.keyword : '')
const filterSeverity = ref('')
// 值班语义：默认只看 firing；带关键字跳入（如仪表盘链接）时查全部
const filterStatus = ref(keyword.value ? '' : 'firing')
const tableRef = ref()
const lastRefresh = ref('')

const stats = reactive({ firing: 0, criticalFiring: 0, resolved: 0, total: 0 })

const canCreateTicket = computed(() => authStore.hasPermission('tickets.create'))

// ── 数据加载 ──

async function fetchData() {
  loading.value = true
  loadError.value = false
  try {
    const res: any = await getAlertManagerEvents({
      keyword: keyword.value,
      severity: filterSeverity.value,
      status: filterStatus.value,
      page: page.value,
      page_size: pageSize,
    })
    items.value = res?.data?.items ?? []
    total.value = res?.data?.total ?? 0
  } catch {
    items.value = []
    total.value = 0
    loadError.value = true
  } finally {
    loading.value = false
  }
}

/** 统计卡数字不受关键字/分页影响，只按状态与级别聚合计数 */
async function fetchStats() {
  try {
    const [firing, criticalFiring, resolved, all] = await Promise.all([
      getAlertManagerEvents({ status: 'firing', page_size: 1 }),
      getAlertManagerEvents({ status: 'firing', severity: 'critical', page_size: 1 }),
      getAlertManagerEvents({ status: 'resolved', page_size: 1 }),
      getAlertManagerEvents({ page_size: 1 }),
    ]) as any[]
    stats.firing = firing?.data?.total ?? 0
    stats.criticalFiring = criticalFiring?.data?.total ?? 0
    stats.resolved = resolved?.data?.total ?? 0
    stats.total = all?.data?.total ?? 0
  } catch { /* 保留旧值 */ }
}

function refreshAll() {
  fetchData()
  fetchStats()
  lastRefresh.value = new Date().toTimeString().slice(0, 8)
}

function applyFilters() {
  page.value = 1
  fetchData()
}

// ── 统计卡点击筛选 ──

function clickFiringCard() {
  filterStatus.value = filterStatus.value === 'firing' && !filterSeverity.value ? '' : 'firing'
  filterSeverity.value = ''
  applyFilters()
}

function clickCriticalCard() {
  if (filterSeverity.value === 'critical') {
    filterSeverity.value = ''
  } else {
    filterSeverity.value = 'critical'
    filterStatus.value = 'firing'
  }
  applyFilters()
}

function clickResolvedCard() {
  filterStatus.value = filterStatus.value === 'resolved' ? '' : 'resolved'
  filterSeverity.value = ''
  applyFilters()
}

function clearFilters() {
  filterStatus.value = ''
  filterSeverity.value = ''
  applyFilters()
}

// ── 自动刷新（keep-alive 感知：离开页面停表） ──

const autoRefresh = ref(false)
let refreshTimer: ReturnType<typeof setInterval> | undefined

function startTimer() {
  stopTimer()
  refreshTimer = setInterval(refreshAll, 30_000)
}

function stopTimer() {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = undefined
  }
}

function toggleAutoRefresh() {
  autoRefresh.value = !autoRefresh.value
  if (autoRefresh.value) startTimer()
  else stopTimer()
}

onDeactivated(stopTimer)
// keep-alive 组件首次挂载会同时触发 onMounted 与 onActivated，跳过一次避免重复查询
let firstActivation = true
onActivated(() => {
  if (firstActivation) {
    firstActivation = false
    return
  }
  refreshAll()
  if (autoRefresh.value) startTimer()
})

// ── 行展开 ──

function onRowClick(row: AlertEvent) {
  tableRef.value?.toggleRowExpansion(row)
}

function parseJsonMap(raw: string): Record<string, string> {
  try {
    const obj = JSON.parse(raw || '{}')
    return obj && typeof obj === 'object' ? obj : {}
  } catch {
    return {}
  }
}

function labelChips(row: AlertEvent): string[] {
  return Object.entries(parseJsonMap(row.raw_labels)).map(([k, v]) => `${k}="${v}"`)
}

function annotationEntries(row: AlertEvent): [string, string][] {
  return Object.entries(parseJsonMap(row.raw_annotations)).map(([k, v]) => [k, String(v)])
}

function isUrl(v: string) {
  return /^https?:\/\//.test(v)
}

async function copyText(text: string) {
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制')
  } catch {
    ElMessage.error('复制失败')
  }
}

// ── 展示辅助 ──

function severityType(severity: string) {
  if (severity === 'critical') return 'danger'
  if (severity === 'warning' || severity === 'warn') return 'warning'
  return 'info'
}

function validDate(iso: string | null): Date | null {
  if (!iso) return null
  const d = new Date(iso)
  if (isNaN(d.getTime()) || d.getFullYear() < 2000) return null
  return d
}

function fullTime(iso: string | null) {
  const d = validDate(iso)
  if (!d) return '-'
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`
}

function relTime(iso: string | null) {
  const d = validDate(iso)
  return d ? formatRelativeTime(d.toISOString()) : '-'
}

function fmtDuration(ms: number): string {
  const s = Math.max(0, Math.round(ms / 1000))
  if (s < 60) return `${s} 秒`
  const m = Math.floor(s / 60)
  if (m < 60) return `${m} 分钟`
  const h = Math.floor(m / 60)
  if (h < 24) return m % 60 ? `${h} 小时 ${m % 60} 分` : `${h} 小时`
  const dd = Math.floor(h / 24)
  return h % 24 ? `${dd} 天 ${h % 24} 时` : `${dd} 天`
}

function durationText(row: AlertEvent): string {
  const start = validDate(row.starts_at)
  if (!start) return ''
  if (row.status === 'firing') return `已持续 ${fmtDuration(Date.now() - start.getTime())}`
  const end = validDate(row.ends_at)
  if (!end) return ''
  return `持续 ${fmtDuration(end.getTime() - start.getTime())}`
}

function sourceText(row: AlertEvent): string {
  const labels = parseJsonMap(row.raw_labels)
  const pod = (labels.pod || labels.pod_name || '').trim()
  if (pod) {
    const ns = (labels.namespace || '').trim()
    return ns ? `${ns}/${pod}` : pod
  }
  if (row.instance) return row.instance
  if (labels.node) return labels.node
  if (row.job) return row.job
  return '-'
}

// ── 关联日志跳转 ──

function goRelatedLogs(row: AlertEvent) {
  const query: Record<string, string> = {}
  const start = validDate(row.starts_at)
  if (start) {
    query.start = new Date(start.getTime() - 15 * 60e3).toISOString()
    query.end = new Date(start.getTime() + 15 * 60e3).toISOString()
  }
  const labels = parseJsonMap(row.raw_labels)
  const namespace = (labels.namespace || '').trim()
  const pod = (labels.pod || labels.pod_name || '').trim()
  const container = (labels.container || labels.container_name || '').trim()
  if (namespace) query.namespace = namespace
  if (pod) query.pod = pod
  if (container) query.container = container
  if (!pod && !namespace) {
    const host = (labels.node || row.instance || labels.instance || '').trim()
    if (host) query.host = host.replace(/:\d+$/, '')
  }
  router.push({ path: '/monitoring/logs', query })
}

// ── 转为工单 ──

const ticketVisible = ref(false)
const ticketSaving = ref(false)
const ticketForm = reactive({ title: '', description: '', priority: 'normal' })

function openTicketDialog(row: AlertEvent) {
  const src = sourceText(row)
  ticketForm.title = `【告警】${row.alert_name}${src !== '-' ? ` · ${src}` : ''}`.slice(0, 120)
  const lines = [row.summary, row.description].filter(Boolean)
  lines.push(`级别: ${row.severity} / 状态: ${row.status} / 触发时间: ${fullTime(row.starts_at)}`)
  if (row.instance) lines.push(`实例: ${row.instance}`)
  lines.push(`连续触发: ${row.firing_count} 次`)
  ticketForm.description = lines.join('\n')
  ticketForm.priority = ({ critical: 'critical', warning: 'high', warn: 'high', info: 'normal' } as Record<string, string>)[row.severity] || 'normal'
  ticketVisible.value = true
}

async function submitTicket() {
  if (!ticketForm.title.trim()) {
    ElMessage.warning('请填写标题')
    return
  }
  ticketSaving.value = true
  try {
    await createTicket({
      title: ticketForm.title.trim(),
      description: ticketForm.description.trim(),
      priority: ticketForm.priority,
    })
    ElMessage.success('工单已创建，可到「工单协作」查看')
    ticketVisible.value = false
  } catch { /* 拦截器已提示 */ } finally {
    ticketSaving.value = false
  }
}

onMounted(() => {
  refreshAll()
})
</script>

<style scoped>
.mono { font-family: "SF Mono", "JetBrains Mono", Consolas, "Courier New", monospace; }

.page-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 16px;
}
.page-title { font-size: 18px; font-weight: 700; margin: 0; }
.page-subtitle { font-size: 12px; color: var(--text-muted); margin: 4px 0 0; }
.header-actions { display: flex; align-items: center; gap: 10px; }
.last-refresh { font-size: 11px; color: var(--text-muted); }

.firing-pill {
  display: inline-flex; align-items: center; gap: 7px;
  font-size: 12px; font-weight: 600; padding: 5px 12px; border-radius: 20px;
  background: rgba(34, 197, 94, .10); color: #15803d;
}
.firing-pill .dot { width: 7px; height: 7px; border-radius: 50%; background: var(--success-color); }
.firing-pill.hot { background: rgba(229, 72, 77, .10); color: #c2282d; }
.firing-pill.hot .dot { background: var(--danger-color); animation: breathe 1.4s infinite; }

.load-error { margin-bottom: 14px; }

/* ── 概览统计条 ── */
.stat-row {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 14px;
}
.stat-card {
  background: var(--surface-color); border: 1px solid var(--border-color);
  border-radius: var(--border-radius); padding: 14px 18px; cursor: pointer;
  text-align: left; font-family: inherit;
  transition: border-color .15s, box-shadow .15s, transform .15s;
}
.stat-card:hover { border-color: var(--primary-color); transform: translateY(-1px); }
.stat-card.active {
  border-color: var(--primary-color); background: var(--primary-bg);
  box-shadow: 0 0 0 1px var(--primary-color) inset;
}
.stat-num { font-size: 24px; font-weight: 700; line-height: 1.1; color: var(--text-primary); }
.stat-card.hot .stat-num { color: var(--danger-color); }
.stat-label {
  display: flex; align-items: center; gap: 6px;
  font-size: 12px; color: var(--text-muted); margin-top: 4px;
}
.stat-label .dot { width: 6px; height: 6px; border-radius: 50%; background: var(--border-color); }
.stat-card.hot .stat-label .dot { background: var(--danger-color); animation: breathe 1.4s infinite; }

@keyframes breathe {
  0%, 100% { box-shadow: 0 0 0 0 rgba(229, 72, 77, .35); opacity: 1; }
  50% { box-shadow: 0 0 0 4px rgba(229, 72, 77, 0); opacity: .55; }
}

/* ── 表格区 ── */
.data-card {
  background: var(--surface-color); border: 1px solid var(--border-color);
  border-radius: var(--border-radius); padding: 14px 16px;
}
.toolbar { display: flex; gap: 10px; margin-bottom: 12px; align-items: center; }
.table-wrapper { overflow-x: auto; }

.status-tag .tag-dot {
  display: inline-block; width: 6px; height: 6px; border-radius: 50%;
  background: #fff; margin-right: 4px; animation: breathe 1.4s infinite;
}
.alert-value { font-size: 11px; color: var(--danger-color); margin-top: 3px; }

.alert-cell { line-height: 1.5; }
.alert-name { font-weight: 600; font-size: 13px; }
.alert-summary {
  font-size: 12px; color: var(--text-secondary);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 460px;
}

.source-text { font-size: 12px; color: var(--text-secondary); }

.time-cell { line-height: 1.5; }
.t-rel { font-size: 12px; color: var(--text-primary); }
.t-dur { font-size: 11px; color: var(--text-muted); }
.t-dur.firing { color: var(--danger-color); }

.count-badge {
  display: inline-block; font-size: 11px; font-weight: 700;
  color: var(--danger-color); background: rgba(229, 72, 77, .10);
  border-radius: 10px; padding: 2px 8px;
}

.no-data { color: var(--text-muted); }

.empty-state { padding: 48px 0; text-align: center; }
.empty-icon { font-size: 26px; margin-bottom: 8px; opacity: .6; }
.empty-text { font-size: 14px; font-weight: 600; color: var(--text-secondary); }
.empty-sub { font-size: 12px; color: var(--text-muted); margin-top: 4px; }

/* ── 排障面板 ── */
.detail-panel { padding: 4px 8px 10px 36px; }
.dp-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.dp-block { min-width: 0; }
.dp-title {
  font-size: 11px; font-weight: 700; color: var(--text-muted);
  letter-spacing: .06em; text-transform: uppercase; margin-bottom: 8px;
}
.label-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.label-chip {
  font-size: 11px; padding: 3px 8px; border-radius: 6px; cursor: copy;
  background: var(--bg-color); border: 1px solid var(--border-color); color: var(--text-secondary);
  transition: border-color .15s, color .15s;
}
.label-chip:hover { border-color: var(--primary-color); color: var(--primary-color); }

.anno-list { display: flex; flex-direction: column; gap: 6px; }
.anno-row { font-size: 12px; line-height: 1.6; }
.dp-ck {
  display: inline-block; min-width: 92px; margin-right: 8px;
  color: var(--text-muted); font-weight: 600;
}
.anno-val { color: var(--text-primary); word-break: break-all; white-space: pre-wrap; }
.anno-link { color: var(--primary-color); text-decoration: none; word-break: break-all; }
.anno-link:hover { text-decoration: underline; }

.dp-meta {
  display: flex; flex-wrap: wrap; gap: 18px; margin-top: 12px; padding-top: 10px;
  border-top: 1px dashed var(--border-color);
  font-size: 11px; color: var(--text-muted);
}
.dp-actions { display: flex; gap: 10px; margin-top: 12px; }

.pagination { display: flex; justify-content: flex-end; margin-top: 12px; }

@media (max-width: 900px) {
  .stat-row { grid-template-columns: 1fr 1fr; }
  .dp-grid { grid-template-columns: 1fr; }
  .page-header { flex-direction: column; align-items: flex-start; gap: 10px; }
}
</style>

