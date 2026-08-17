<template>
  <div>
    <!-- ═══ 页头 ═══ -->
    <div class="page-header">
      <div>
        <h2 class="page-title">审计日志</h2>
        <p class="page-subtitle">平台关键操作留痕，点击任意一行查看完整记录。</p>
      </div>
      <div class="header-actions">
        <el-button size="small" :loading="loading" aria-label="刷新审计日志" @click="handleRefresh">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
        <el-button size="small" :loading="exporting" aria-label="按当前筛选条件导出 CSV" @click="handleExport">
          <el-icon><Download /></el-icon>
          导出 CSV
        </el-button>
      </div>
    </div>

    <!-- ═══ 统计卡 ═══ -->
    <div class="stats" role="region" aria-label="审计概览">
      <div class="stat">
        <div class="lbl"><span class="dot dot-p" aria-hidden="true"></span>今日事件</div>
        <div class="num">{{ stats?.today_events ?? '-' }}</div>
        <div class="foot">{{ todayTrendText }}</div>
      </div>
      <div class="stat">
        <div class="lbl"><span class="dot dot-s" aria-hidden="true"></span>今日登录</div>
        <div class="num">{{ stats?.today_logins ?? '-' }}</div>
        <div class="foot">{{ stats ? `失败 ${stats.today_login_failed} 次` : '' }}</div>
      </div>
      <div
        class="stat clickable"
        role="button"
        tabindex="0"
        aria-label="筛选删除操作"
        @click="filterDeletes"
        @keyup.enter="filterDeletes"
      >
        <div class="lbl"><span class="dot dot-d" aria-hidden="true"></span>删除操作</div>
        <div class="num" :class="{ danger: (stats?.deletes_7d ?? 0) > 0 }">{{ stats?.deletes_7d ?? '-' }}</div>
        <div class="foot">近 7 天 · 点击筛选</div>
      </div>
      <div class="stat">
        <div class="lbl"><span class="dot dot-w" aria-hidden="true"></span>活跃操作人</div>
        <div class="num">{{ stats?.active_users_7d ?? '-' }}</div>
        <div class="foot">近 7 天有操作记录的用户</div>
      </div>
    </div>

    <div class="table-card">
      <!-- ═══ 工具栏 ═══ -->
      <div class="toolbar">
        <el-input
          v-model="filters.keyword"
          placeholder="搜索操作人 / 对象名称 / 详情…"
          clearable
          class="search-input"
          :prefix-icon="Search"
          aria-label="搜索审计日志"
          @keyup.enter="applyFilters"
          @clear="applyFilters"
        />
        <el-select v-model="filters.action" class="filter-select" aria-label="按操作类型筛选" @change="applyFilters">
          <el-option value="" label="操作类型：全部" />
          <el-option v-for="opt in actionOptions" :key="opt.value" :value="opt.value" :label="opt.label" />
        </el-select>
        <el-select v-model="filters.target_type" class="filter-select" aria-label="按对象类型筛选" @change="applyFilters">
          <el-option value="" label="对象类型：全部" />
          <el-option v-for="opt in targetOptions" :key="opt.value" :value="opt.value" :label="opt.label" />
        </el-select>
        <el-select v-model="filters.days" class="filter-select days" aria-label="按时间范围筛选" @change="applyFilters">
          <el-option :value="1" label="时间：今天" />
          <el-option :value="7" label="时间：近 7 天" />
          <el-option :value="30" label="时间：近 30 天" />
          <el-option :value="0" label="时间：全部" />
        </el-select>
        <el-button link type="primary" aria-label="重置筛选条件" @click="resetFilters">重置</el-button>
        <span class="spacer"></span>
        <span class="meta">共 {{ total.toLocaleString() }} 条</span>
      </div>
      <!-- ═══ 表格 ═══ -->
      <el-table
        :data="items"
        v-loading="loading"
        :row-class-name="rowClassName"
        class="audit-table"
        @row-click="openDetail"
      >
        <el-table-column label="操作人" width="140">
          <template #default="{ row }">
            <div class="user-cell">
              <span class="avatar" :style="{ background: avatarColor(row.user) }" aria-hidden="true">{{ avatarChar(row.user) }}</span>
              <span class="user-name">{{ row.user || '-' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <span class="tag" :class="actionTagClass(row.action)">{{ actionLabel(row.action) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="对象" min-width="210">
          <template #default="{ row }">
            <div class="obj-cell">
              <strong>{{ row.target_name || '-' }}</strong>
              <span>{{ targetLabel(row.target_type) }}<template v-if="row.target_id"> · #{{ row.target_id }}</template></span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="详情" min-width="240" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="detail-cell">{{ row.detail || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="IP" width="130">
          <template #default="{ row }">
            <span class="mono">{{ row.ip_address || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="时间" width="130">
          <template #default="{ row }">
            <div class="time-cell">
              {{ relativeTime(row.created_at) }}
              <span>{{ absoluteTime(row.created_at) }}</span>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <!-- ═══ 分页 ═══ -->
      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50]"
          :total="total"
          :layout="paginationLayout"
          small
          @current-change="handleCurrentChange"
          @size-change="handleSizeChange"
        />
      </div>
    </div>

    <!-- ═══ 详情抽屉 ═══ -->
    <el-drawer v-model="drawerVisible" size="720px" :with-header="false" destroy-on-close>
      <template v-if="current">
        <div class="d-head">
          <div class="d-head-copy">
            <div class="d-hero">
              <span class="tag" :class="actionTagClass(current.action)">{{ actionLabel(current.action) }}</span>
              <span class="tag info">{{ targetLabel(current.target_type) }}</span>
            </div>
            <div class="d-title">{{ current.target_name || '审计详情' }}</div>
            <div class="d-chips">
              <span class="d-chip"><span class="k">操作人</span>{{ current.user || '-' }}</span>
              <span class="d-chip"><span class="k">IP</span><span class="mono">{{ current.ip_address || '-' }}</span></span>
              <span class="d-chip"><span class="k">时间</span>{{ fullTime(current.created_at) }}</span>
            </div>
          </div>
          <button type="button" class="d-close" aria-label="关闭" @click="drawerVisible = false">✕</button>
        </div>
        <div class="d-body">
          <div class="d-sec-k">基本信息</div>
          <dl class="kv-grid">
            <div class="kv"><dt>操作人</dt><dd>{{ current.user || '-' }}</dd></div>
            <div class="kv"><dt>操作</dt><dd>{{ actionLabel(current.action) }}（{{ current.action }}）</dd></div>
            <div class="kv"><dt>对象类型</dt><dd>{{ targetLabel(current.target_type) }}（{{ current.target_type }}）</dd></div>
            <div class="kv"><dt>对象 ID</dt><dd class="mono">{{ current.target_id ? `#${current.target_id}` : '-' }}</dd></div>
            <div class="kv"><dt>来源 IP</dt><dd class="mono">{{ current.ip_address || '-' }}</dd></div>
            <div class="kv"><dt>发生时间</dt><dd>{{ fullTime(current.created_at) }}</dd></div>
          </dl>
          <div class="d-sec-k">操作详情</div>
          <div class="d-detail">{{ current.detail || '无详情' }}</div>
          <div class="d-sec-k">原始记录</div>
          <div class="d-raw">{{ rawJson }}</div>
        </div>
      </template>
    </el-drawer>
  </div>
</template>
<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, Download, Search } from '@element-plus/icons-vue'
import { getAuditLogs, getAuditStats, exportAuditLogs, getActionLabels, getTargetLabels } from '@/api/audit'
import { usePagination } from '@/hooks/usePagination'

// ─── 数据 ────────────────────────────────────────────────
const loading = ref(false)
const exporting = ref(false)
const items = ref<any[]>([])
const stats = ref<any | null>(null)
const actionLabels = ref<Record<string, string>>({})
const targetLabels = ref<Record<string, string>>({})

const { currentPage, pageSize, total, paginationLayout, handleCurrentChange, handleSizeChange, resetPagination } = usePagination(fetchData)
const filters = reactive({ keyword: '', action: '', target_type: '', days: 7 })

// 下拉选项按固定顺序展示，后端新增类型时自动附带在末尾
const ACTION_ORDER = ['login', 'login_failed', 'logout', 'create', 'update', 'delete']
const TARGET_ORDER = ['asset', 'user', 'role', 'ticket', 'alert', 'auth', 'settings']

const actionOptions = computed(() => orderedOptions(actionLabels.value, ACTION_ORDER))
const targetOptions = computed(() => orderedOptions(targetLabels.value, TARGET_ORDER))

function orderedOptions(labels: Record<string, string>, order: string[]) {
  const keys = Object.keys(labels)
  const sorted = [...order.filter((k) => keys.includes(k)), ...keys.filter((k) => !order.includes(k))]
  return sorted.map((value) => ({ value, label: labels[value] }))
}

function actionLabel(a: string) { return actionLabels.value[a] || a }
function targetLabel(t: string) { return targetLabels.value[t] || t }

const ACTION_TAG: Record<string, string> = {
  login: 'ok',
  login_failed: 'danger',
  logout: 'info',
  create: 'primary',
  update: 'warn',
  delete: 'danger',
}
function actionTagClass(a: string) { return ACTION_TAG[a] || 'info' }

// ─── 查询 ────────────────────────────────────────────────
async function fetchData(extra?: any) {
  loading.value = true
  try {
    const params = {
      ...filters,
      page: extra?.page || currentPage.value,
      page_size: extra?.page_size || pageSize.value,
    }
    const res: any = await getAuditLogs(params)
    items.value = res.data.items
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}

async function fetchStats() {
  try {
    const res: any = await getAuditStats()
    stats.value = res.data
  } catch {
    stats.value = null
  }
}

async function fetchMeta() {
  try {
    const [a, t]: any[] = await Promise.all([getActionLabels(), getTargetLabels()])
    actionLabels.value = a.data || {}
    targetLabels.value = t.data || {}
  } catch { /* 标签加载失败时兜底显示英文原文 */ }
}

function applyFilters() {
  resetPagination()
  fetchData({ page: 1 })
}

function resetFilters() {
  Object.assign(filters, { keyword: '', action: '', target_type: '', days: 7 })
  applyFilters()
}

function filterDeletes() {
  filters.action = 'delete'
  applyFilters()
}

function handleRefresh() {
  fetchData()
  fetchStats()
}

async function handleExport() {
  exporting.value = true
  try {
    const res: any = await exportAuditLogs({ ...filters })
    const url = URL.createObjectURL(res.data)
    const a = document.createElement('a')
    const disposition: string = res.headers?.['content-disposition'] || ''
    const match = disposition.match(/filename=([^;]+)/)
    a.href = url
    a.download = match ? match[1].trim() : `audit_logs_${Date.now()}.csv`
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch {
    ElMessage.error('导出失败')
  } finally {
    exporting.value = false
  }
}

// ─── 表格辅助 ────────────────────────────────────────────
function rowClassName({ row }: { row: any }) {
  return row.action === 'login_failed' ? 'alert-row' : ''
}

const AVATAR_PALETTE = ['#5e6ad2', '#0e9f6e', '#b7791f', '#718096', '#c2410c', '#0369a1']
function avatarColor(name: string) {
  if (!name) return AVATAR_PALETTE[0]
  let hash = 0
  for (const ch of name) hash = (hash * 31 + (ch.codePointAt(0) || 0)) >>> 0
  return AVATAR_PALETTE[hash % AVATAR_PALETTE.length]
}
function avatarChar(name: string) {
  if (!name) return '?'
  const ch = [...name][0] || '?'
  return /[a-z]/.test(ch) ? ch.toUpperCase() : ch
}

// ─── 时间格式化 ──────────────────────────────────────────
function parseTime(ts: string): Date | null {
  if (!ts) return null
  const d = new Date(ts)
  return isNaN(d.getTime()) ? null : d
}
function pad(n: number) { return String(n).padStart(2, '0') }
function isSameDay(a: Date, b: Date) {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate()
}
function relativeTime(ts: string) {
  const d = parseTime(ts)
  if (!d) return '-'
  const now = new Date()
  const s = Math.floor((now.getTime() - d.getTime()) / 1000)
  if (s < 0) return fullTime(ts)
  if (s < 60) return '刚刚'
  const m = Math.floor(s / 60)
  if (m < 60) return `${m} 分钟前`
  if (isSameDay(d, now)) return `${Math.floor(m / 60)} 小时前`
  const yesterday = new Date(now)
  yesterday.setDate(now.getDate() - 1)
  if (isSameDay(d, yesterday)) return `昨天 ${pad(d.getHours())}:${pad(d.getMinutes())}`
  const days = Math.floor(s / 86400)
  if (days < 7) return `${days} 天前`
  return `${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}
function absoluteTime(ts: string) {
  const d = parseTime(ts)
  if (!d) return ''
  const hms = `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
  return isSameDay(d, new Date()) ? hms : `${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${hms}`
}
function fullTime(ts: string) {
  const d = parseTime(ts)
  if (!d) return '-'
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

const todayTrendText = computed(() => {
  if (!stats.value) return ''
  const { today_events: today, yesterday_events: yesterday } = stats.value
  if (!yesterday) return '昨日同期 0'
  const pct = Math.round(((today - yesterday) / yesterday) * 100)
  const arrow = pct >= 0 ? '↑' : '↓'
  return `昨日同期 ${yesterday} · ${arrow} ${Math.abs(pct)}%`
})

// ─── 详情抽屉 ────────────────────────────────────────────
const drawerVisible = ref(false)
const current = ref<any | null>(null)

function openDetail(row: any) {
  current.value = row
  drawerVisible.value = true
}

const rawJson = computed(() => {
  if (!current.value) return ''
  const { id, user, action, target_type, target_id, target_name, ip_address, created_at } = current.value
  return JSON.stringify({ id, user, action, target_type, target_id, target_name, ip_address, created_at }, null, 2)
})

onMounted(() => {
  fetchData()
  fetchStats()
  fetchMeta()
})
</script>
<style scoped>
.page-subtitle {
  margin: 3px 0 0;
  font-size: 12px;
  color: var(--text-secondary);
}
.header-actions {
  display: flex;
  gap: 8px;
}

/* ═══ 统计卡 ═══ */
.stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 14px;
}
.stat {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: 12px 14px;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.stat.clickable {
  cursor: pointer;
}
.stat.clickable:hover {
  border-color: var(--primary-color);
  box-shadow: 0 2px 8px rgba(94, 106, 210, 0.1);
}
.stat .lbl {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-secondary);
}
.stat .num {
  margin-top: 3px;
  font-size: 17px;
  font-weight: 750;
  font-variant-numeric: tabular-nums;
  color: var(--text-primary);
}
.stat .num.danger {
  color: var(--danger-color);
}
.stat .foot {
  margin-top: 4px;
  font-size: 11.5px;
  color: var(--text-muted);
}
.dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex: none;
}
.dot-p { background: var(--primary-color); }
.dot-s { background: var(--success-color); }
.dot-w { background: var(--warning-color); }
.dot-d { background: var(--danger-color); }

/* ═══ 卡片 + 工具栏 ═══ */
.table-card {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  overflow: hidden;
}
.toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  border-bottom: 1px solid var(--border-color);
  flex-wrap: wrap;
}
.search-input {
  width: 260px;
}
.filter-select {
  width: 150px;
}
.filter-select.days {
  width: 130px;
}
.spacer {
  flex: 1;
}
.meta {
  font-size: 12px;
  color: var(--text-muted);
}

/* ═══ 表格 ═══ */
.audit-table {
  --el-table-row-hover-bg-color: var(--primary-bg);
}
.audit-table :deep(.el-table__header th) {
  background: #f7f7f9;
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 600;
}
.audit-table :deep(.el-table__row) {
  cursor: pointer;
}
.audit-table :deep(.el-table__body tr.alert-row > td.el-table__cell) {
  background: rgba(239, 68, 68, 0.045);
}
.audit-table :deep(.el-table__body tr.alert-row:hover > td.el-table__cell) {
  background: rgba(239, 68, 68, 0.09);
}
.user-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}
.avatar {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  flex: none;
  display: grid;
  place-items: center;
  font-size: 11px;
  font-weight: 700;
  color: #fff;
}
.user-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.obj-cell {
  display: grid;
  gap: 1px;
  min-width: 0;
}
.obj-cell strong {
  font-weight: 650;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.obj-cell span {
  font-size: 11.5px;
  color: var(--text-muted);
}
.detail-cell {
  color: var(--text-secondary);
}
.time-cell {
  white-space: nowrap;
  color: var(--text-secondary);
}
.time-cell span {
  display: block;
  font-size: 11px;
  color: var(--text-muted);
}
.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
}

/* 操作 tag */
.tag {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11.5px;
  font-weight: 600;
  padding: 2px 9px;
  border-radius: 999px;
  white-space: nowrap;
}
.tag::before {
  content: '';
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: currentColor;
}
.tag.ok { color: #16a34a; background: rgba(34, 197, 94, 0.11); }
.tag.primary { color: var(--primary-color); background: var(--primary-bg); }
.tag.warn { color: #d97706; background: rgba(245, 158, 11, 0.13); }
.tag.danger { color: #dc2626; background: rgba(239, 68, 68, 0.09); }
.tag.info { color: var(--text-secondary); background: rgba(140, 140, 140, 0.12); }

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  padding: 11px 12px;
}

/* ═══ 详情抽屉 ═══ */
:deep(.el-drawer__body) {
  padding: 0;
  overflow-y: auto;
}
.d-head {
  padding: 16px 20px 14px;
  border-bottom: 1px solid var(--border-color);
  background: linear-gradient(180deg, #fbfbfc 0%, var(--surface-color) 100%);
  display: flex;
  justify-content: space-between;
  gap: 12px;
}
.d-head-copy {
  min-width: 0;
}
.d-hero {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 7px;
  flex-wrap: wrap;
}
.d-title {
  font-size: 16px;
  font-weight: 700;
  word-break: break-all;
}
.d-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 9px;
}
.d-chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11.5px;
  color: var(--text-secondary);
  background: var(--bg-color);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  padding: 2px 8px;
}
.d-chip .k {
  color: var(--text-muted);
}
.d-close {
  border: 0;
  cursor: pointer;
  width: 28px;
  height: 28px;
  border-radius: 7px;
  background: var(--bg-color);
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1;
  flex: none;
  transition: all 0.15s;
}
.d-close:hover {
  background: rgba(239, 68, 68, 0.09);
  color: #dc2626;
}
.d-body {
  padding: 16px 20px 22px;
}
.d-sec-k {
  font-size: 11px;
  font-weight: 700;
  color: var(--text-muted);
  letter-spacing: 0.4px;
  margin: 14px 0 8px;
}
.d-sec-k:first-child {
  margin-top: 0;
}
.kv-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 24px;
  background: var(--bg-color);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 12px 14px;
  margin: 0;
}
.kv {
  display: flex;
  align-items: baseline;
  gap: 10px;
  font-size: 12.5px;
  min-width: 0;
}
.kv dt {
  flex: none;
  width: 64px;
  color: var(--text-muted);
}
.kv dd {
  margin: 0;
  flex: 1;
  min-width: 0;
  color: var(--text-primary);
  word-break: break-all;
}
.d-detail {
  background: var(--bg-color);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 12px 14px;
  font-size: 12.5px;
  line-height: 1.7;
  word-break: break-all;
}
.d-raw {
  background: #1c1c22;
  color: #d5d5de;
  border-radius: 10px;
  padding: 12px 14px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 11.5px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-all;
}

@media (max-width: 900px) {
  .stats {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .kv-grid {
    grid-template-columns: 1fr;
  }
  .search-input,
  .filter-select,
  .filter-select.days {
    width: 100%;
  }
}
</style>
