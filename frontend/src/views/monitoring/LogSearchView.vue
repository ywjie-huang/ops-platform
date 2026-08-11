<template>
  <div class="log-search">
    <header class="page-header">
      <div>
        <h2 class="page-title">日志检索</h2>
        <p class="page-subtitle">跨命名空间、Pod 与主机的统一日志查询，数据来自 Elasticsearch。</p>
      </div>
      <div class="header-actions">
        <span v-if="searchedAt" class="last-refresh">最近查询 {{ searchedAt }}</span>
        <el-button :loading="loading" @click="doSearch">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </header>

    <!-- 错误提示（未配置 / 连接失败） -->
    <el-alert v-if="errorMsg" type="warning" :closable="false" class="error-alert">
      <template #title>
        <span>{{ errorMsg }}</span>
        <el-button v-if="errorMsg.includes('未配置')" size="small" type="warning" plain
                   class="error-action" @click="router.push('/system/settings')">
          前往集成中心配置
        </el-button>
      </template>
    </el-alert>

    <!-- 筛选区 -->
    <div class="filter-card">
      <div class="filter-row">
        <el-input v-model="filters.keyword" class="keyword-input" clearable
                  placeholder="搜索日志内容，如 OutOfMemory / 订单号 / traceId（短语精确匹配）"
                  @keyup.enter="doSearch">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-button type="primary" :loading="loading" @click="doSearch">搜索</el-button>
        <el-button @click="resetFilters">重置</el-button>
      </div>
      <div class="filter-row filter-row-dim">
        <el-select v-model="filters.namespace" placeholder="命名空间" clearable filterable class="dim-ns">
          <el-option v-for="ns in options.namespaces" :key="ns" :label="ns" :value="ns" />
        </el-select>
        <el-input v-model="filters.pod" placeholder="Pod 名称" clearable class="dim-pod" @keyup.enter="doSearch" />
        <el-input v-model="filters.container" placeholder="容器名称" clearable class="dim-container" @keyup.enter="doSearch" />
        <el-select v-model="filters.host" placeholder="主机" clearable filterable class="dim-host">
          <el-option v-for="h in options.hosts" :key="h" :label="h" :value="h" />
        </el-select>
        <el-select v-model="filters.level" placeholder="级别" clearable class="dim-level">
          <el-option v-for="lv in mergedLevels" :key="lv" :label="lv.toUpperCase()" :value="lv" />
        </el-select>
        <el-date-picker v-model="timeRange" type="datetimerange" class="dim-time"
                        start-placeholder="开始时间" end-placeholder="结束时间"
                        unlink-panels @change="onCustomTime" />
        <div class="quick-ranges">
          <button v-for="q in quickRanges" :key="q.key" class="quick-btn"
                  :class="{ active: quick === q.key }" @click="applyQuick(q.key)">
            {{ q.label }}
          </button>
        </div>
      </div>
    </div>

    <!-- 日志量直方图 -->
    <div v-if="buckets.length" class="histo-card">
      <div class="histo-head">
        <span class="histo-title">日志量分布</span>
        <span class="histo-sub">粒度 {{ intervalText }} · 点击柱条缩放到该时间段</span>
      </div>
      <div class="histo-body">
        <div v-for="b in buckets" :key="b.key" class="histo-bar"
             :class="{ empty: b.count === 0 }"
             :style="{ height: barHeight(b.count) }"
             :title="`${formatBarTime(b.key)} · ${b.count.toLocaleString()} 条`"
             @click="zoomBucket(b)"></div>
      </div>
    </div>

    <!-- 结果列表 -->
    <div class="result-card">
      <div class="result-head">
        <span class="result-total">
          共 <b>{{ total.toLocaleString() }}</b> 条日志
          <template v-if="items.length && items.length < total">，已加载 {{ items.length.toLocaleString() }} 条</template>
        </span>
        <span v-if="loadingMore" class="result-loading">加载中…</span>
      </div>

      <div v-if="!loading && !items.length && !errorMsg" class="empty-state">
        <div class="empty-icon">🔍</div>
        <div class="empty-text">没有匹配的日志</div>
        <div class="empty-sub">调整关键字、筛选维度或扩大时间范围后重试</div>
      </div>

      <ul v-else class="log-list">
        <li v-for="item in items" :key="item.id + item.index" class="log-line">
          <span class="ts mono" :title="item.timestamp">{{ formatTs(item.timestamp) }}</span>
          <span class="lv" :class="levelClass(item.level)">{{ levelText(item.level) }}</span>
          <span class="meta mono" :title="metaText(item)">{{ metaText(item) }}</span>
          <span class="msg" v-html="highlight(item.message)"></span>
        </li>
      </ul>

      <div v-if="items.length && items.length < total" class="load-more">
        <el-button :loading="loadingMore" @click="loadMore">
          加载更多（剩余 {{ (total - items.length).toLocaleString() }} 条）
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Refresh, Search } from '@element-plus/icons-vue'
import {
  getLogFilterOptions,
  getLogHistogram,
  searchLogs,
  type LogHistogramBucket,
  type LogItem,
  type LogSearchParams,
} from '@/api/logs'

const route = useRoute()
const router = useRouter()

const PAGE_SIZE = 100

const filters = reactive({
  keyword: '',
  namespace: '',
  pod: '',
  container: '',
  host: '',
  level: '',
})

const quickRanges = [
  { key: '15m', label: '15分钟', ms: 15 * 60e3 },
  { key: '1h', label: '1小时', ms: 3600e3 },
  { key: '6h', label: '6小时', ms: 6 * 3600e3 },
  { key: '24h', label: '24小时', ms: 24 * 3600e3 },
  { key: '7d', label: '7天', ms: 7 * 86400e3 },
] as const

const quick = ref<string>('24h')
const timeRange = ref<[Date, Date] | null>(null)

const items = ref<LogItem[]>([])
const total = ref(0)
const buckets = ref<LogHistogramBucket[]>([])
const interval = ref('')
const loading = ref(false)
const loadingMore = ref(false)
const errorMsg = ref('')
const searchedAt = ref('')

const options = reactive<{ namespaces: string[]; hosts: string[]; levels: string[] }>({
  namespaces: [],
  hosts: [],
  levels: [],
})

const DEFAULT_LEVELS = ['error', 'warn', 'warning', 'info', 'debug']
const mergedLevels = computed(() => {
  const seen = new Set<string>()
  const out: string[] = []
  for (const lv of [...options.levels, ...DEFAULT_LEVELS]) {
    const k = lv.toLowerCase()
    if (!seen.has(k)) {
      seen.add(k)
      out.push(lv)
    }
  }
  return out
})

const intervalText = computed(() => {
  const map: Record<string, string> = {
    '10s': '10 秒', '30s': '30 秒', '1m': '1 分钟', '5m': '5 分钟', '10m': '10 分钟',
    '30m': '30 分钟', '1h': '1 小时', '3h': '3 小时', '6h': '6 小时', '12h': '12 小时',
    '1d': '1 天', '7d': '7 天',
  }
  return map[interval.value] || interval.value
})

function applyQuick(key: string, search = true) {
  quick.value = key
  const q = quickRanges.find(r => r.key === key)
  if (!q) return
  const now = new Date()
  timeRange.value = [new Date(now.getTime() - q.ms), now]
  if (search) doSearch()
}

function onCustomTime() {
  // 手动选择时间后取消快捷区间高亮
  if (timeRange.value) quick.value = ''
}

function buildParams(offset = 0): LogSearchParams {
  const p: LogSearchParams = { offset, size: PAGE_SIZE }
  if (filters.keyword.trim()) p.keyword = filters.keyword.trim()
  if (filters.namespace) p.namespace = filters.namespace
  if (filters.pod.trim()) p.pod = filters.pod.trim()
  if (filters.container.trim()) p.container = filters.container.trim()
  if (filters.host) p.host = filters.host
  if (filters.level) p.level = filters.level
  if (timeRange.value) {
    p.start = timeRange.value[0].toISOString()
    p.end = timeRange.value[1].toISOString()
  }
  return p
}

async function doSearch() {
  // 快捷区间相对"现在"滚动
  if (quick.value) applyQuick(quick.value, false)
  loading.value = true
  errorMsg.value = ''
  try {
    const res = await searchLogs(buildParams(0))
    items.value = res.data.items
    total.value = res.data.total
    searchedAt.value = new Date().toTimeString().slice(0, 8)
    syncRoute()
    // 直方图与筛选项联动刷新（失败不影响主结果）
    fetchHistogram()
    fetchOptions()
  } catch (e: any) {
    errorMsg.value = e?.message || '查询失败'
    items.value = []
    total.value = 0
    buckets.value = []
  } finally {
    loading.value = false
  }
}

async function loadMore() {
  loadingMore.value = true
  try {
    const res = await searchLogs(buildParams(items.value.length))
    items.value = [...items.value, ...res.data.items]
    total.value = res.data.total
  } catch { /* 拦截器已提示 */ } finally {
    loadingMore.value = false
  }
}

async function fetchHistogram() {
  try {
    const res = await getLogHistogram(buildParams(0))
    buckets.value = res.data.buckets
    interval.value = res.data.interval
  } catch { buckets.value = [] }
}

async function fetchOptions() {
  try {
    const res = await getLogFilterOptions(buildParams(0))
    options.namespaces = res.data.namespaces
    options.hosts = res.data.hosts
    options.levels = res.data.levels
  } catch { /* 筛选项失败可忽略 */ }
}

function resetFilters() {
  filters.keyword = ''
  filters.namespace = ''
  filters.pod = ''
  filters.container = ''
  filters.host = ''
  filters.level = ''
  applyQuick('24h')
}

// ── 直方图交互 ──

const maxCount = computed(() => Math.max(1, ...buckets.value.map(b => b.count)))

function barHeight(count: number) {
  if (count === 0) return '2px'
  return `${Math.max(6, Math.round((count / maxCount.value) * 72))}px`
}

function intervalMs(): number {
  const m = /^(\d+)(s|m|h|d)$/.exec(interval.value)
  if (!m) return 60e3
  const n = Number(m[1])
  const unit = { s: 1e3, m: 60e3, h: 3600e3, d: 86400e3 }[m[2] as 's' | 'm' | 'h' | 'd']
  return n * unit
}

function zoomBucket(b: LogHistogramBucket) {
  const start = new Date(b.key)
  if (Number.isNaN(start.getTime())) return
  timeRange.value = [start, new Date(start.getTime() + intervalMs())]
  quick.value = ''
  doSearch()
}

function formatBarTime(key: string) {
  const d = new Date(key)
  return Number.isNaN(d.getTime()) ? key : formatTs(d.toISOString())
}

// ── 展示辅助 ──

function pad(n: number, len = 2) {
  return String(n).padStart(len, '0')
}

function formatTs(iso: string) {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return `${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}.${pad(d.getMilliseconds(), 3)}`
}

function levelText(level: string | null) {
  return (level || '—').toUpperCase().slice(0, 5)
}

function levelClass(level: string | null) {
  const lv = (level || '').toLowerCase()
  if (['error', 'fatal', 'crit', 'critical', 'alert', 'emerg'].includes(lv)) return 'lv-error'
  if (['warn', 'warning'].includes(lv)) return 'lv-warn'
  if (['info', 'notice', 'information'].includes(lv)) return 'lv-info'
  if (['debug', 'trace', 'fine', 'finer', 'finest'].includes(lv)) return 'lv-debug'
  return 'lv-na'
}

function metaText(item: LogItem) {
  if (item.namespace || item.pod) {
    return [item.namespace, item.pod, item.container].filter(Boolean).join('/')
  }
  return item.host || '—'
}

function escapeHtml(s: string) {
  return s.replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[c] as string))
}

function highlight(message: string) {
  const escaped = escapeHtml(message || '')
  const kw = filters.keyword.trim()
  if (!kw) return escaped
  const kwSafe = escapeHtml(kw).replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  return escaped.replace(new RegExp(kwSafe, 'gi'), m => `<mark>${m}</mark>`)
}

// ── 路由联动（分享 / Pod 抽屉跳转） ──

function syncRoute() {
  const query: Record<string, string> = {}
  for (const [k, v] of Object.entries(filters)) {
    const val = (v || '').trim()
    if (val) query[k] = val
  }
  if (timeRange.value) {
    query.start = timeRange.value[0].toISOString()
    query.end = timeRange.value[1].toISOString()
  }
  router.replace({ query })
}

function initFromRoute() {
  const q = route.query
  for (const k of Object.keys(filters) as (keyof typeof filters)[]) {
    const v = q[k]
    if (typeof v === 'string') filters[k] = v
  }
  const start = typeof q.start === 'string' ? new Date(q.start) : null
  const end = typeof q.end === 'string' ? new Date(q.end) : null
  if (start && end && !Number.isNaN(start.getTime()) && !Number.isNaN(end.getTime())) {
    timeRange.value = [start, end]
    quick.value = ''
  } else {
    applyQuick(quick.value, false)
  }
}

onMounted(() => {
  initFromRoute()
  doSearch()
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

.error-alert { margin-bottom: 14px; }
.error-action { margin-left: 12px; }

/* ── 筛选区 ── */
.filter-card {
  background: var(--surface-color); border: 1px solid var(--border-color);
  border-radius: var(--border-radius); padding: 14px 16px;
  display: flex; flex-direction: column; gap: 10px; margin-bottom: 14px;
}
.filter-row { display: flex; gap: 10px; align-items: center; }
.keyword-input { flex: 1; }
.filter-row-dim { flex-wrap: wrap; }
.dim-ns { width: 150px; }
.dim-pod { width: 190px; }
.dim-container { width: 140px; }
.dim-host { width: 150px; }
.dim-level { width: 110px; }
.dim-time { width: 330px; }

.quick-ranges {
  display: flex; border: 1px solid var(--border-color); border-radius: 6px; overflow: hidden;
}
.quick-btn {
  border: none; background: var(--surface-color); color: var(--text-secondary);
  font-size: 12px; padding: 7px 12px; cursor: pointer; font-family: inherit;
  border-right: 1px solid var(--border-color); transition: background .15s;
}
.quick-btn:last-child { border-right: none; }
.quick-btn:hover { background: var(--bg-color); }
.quick-btn.active { background: var(--primary-bg); color: var(--primary-color); font-weight: 600; }

/* ── 直方图 ── */
.histo-card {
  background: var(--surface-color); border: 1px solid var(--border-color);
  border-radius: var(--border-radius); padding: 12px 16px 10px; margin-bottom: 14px;
}
.histo-head { display: flex; align-items: baseline; gap: 10px; margin-bottom: 8px; }
.histo-title { font-size: 13px; font-weight: 600; }
.histo-sub { font-size: 11px; color: var(--text-muted); }
.histo-body {
  display: flex; align-items: flex-end; gap: 2px; height: 76px;
  padding-bottom: 2px; border-bottom: 1px solid var(--border-color);
}
.histo-bar {
  flex: 1; min-width: 3px; border-radius: 2px 2px 0 0;
  background: var(--primary-color); opacity: .75; cursor: pointer;
  transition: opacity .12s, background .12s;
}
.histo-bar:hover { opacity: 1; background: var(--primary-hover); }
.histo-bar.empty { background: var(--border-color); opacity: .6; }

/* ── 结果 ── */
.result-card {
  background: var(--surface-color); border: 1px solid var(--border-color);
  border-radius: var(--border-radius); overflow: hidden;
}
.result-head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 16px; border-bottom: 1px solid var(--border-color);
  font-size: 12px; color: var(--text-secondary);
}
.result-total b { color: var(--text-primary); font-size: 14px; }
.result-loading { font-size: 11px; color: var(--text-muted); }

.empty-state { padding: 56px 0; text-align: center; }
.empty-icon { font-size: 28px; margin-bottom: 10px; opacity: .5; }
.empty-text { font-size: 14px; font-weight: 600; color: var(--text-secondary); }
.empty-sub { font-size: 12px; color: var(--text-muted); margin-top: 4px; }

.log-list { list-style: none; margin: 0; padding: 0; }
.log-line {
  display: grid;
  grid-template-columns: 148px 50px minmax(160px, 260px) 1fr;
  gap: 10px; padding: 5px 16px; font-size: 12px; line-height: 1.6;
  border-bottom: 1px solid var(--bg-color);
}
.log-line:hover { background: var(--bg-color); }
.log-line:last-child { border-bottom: none; }
.ts { color: var(--text-muted); white-space: nowrap; }
.lv { font-weight: 700; font-size: 11px; letter-spacing: .03em; white-space: nowrap; }
.lv-error { color: var(--danger-color); }
.lv-warn { color: var(--warning-color); }
.lv-info { color: var(--primary-color); }
.lv-debug, .lv-na { color: var(--text-muted); }
.meta {
  color: var(--text-secondary); overflow: hidden;
  text-overflow: ellipsis; white-space: nowrap;
}
.msg {
  color: var(--text-primary); font-family: "SF Mono", "JetBrains Mono", Consolas, monospace;
  white-space: pre-wrap; word-break: break-all;
}
.msg :deep(mark) {
  background: rgba(245, 166, 35, .28); color: inherit;
  border-radius: 2px; padding: 0 1px;
}

.load-more {
  display: flex; justify-content: center; padding: 14px;
  border-top: 1px solid var(--border-color);
}

@media (max-width: 900px) {
  .log-line { grid-template-columns: 130px 46px 1fr; }
  .log-line .meta { display: none; }
  .dim-time { width: 100%; }
}
</style>

