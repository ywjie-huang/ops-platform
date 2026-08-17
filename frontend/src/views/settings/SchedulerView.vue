<template>
  <div>
    <!-- ═══ 页头 ═══ -->
    <div class="page-header">
      <div>
        <h2 class="page-title">任务调度中心</h2>
        <p class="page-subtitle">平台周期性任务的统一调度与执行观测。</p>
      </div>
      <el-button type="primary" size="small" @click="showDialog()">
        <el-icon><Plus /></el-icon>新建任务
      </el-button>
    </div>

    <!-- ═══ 统计卡 ═══ -->
    <div class="stats" role="region" aria-label="调度概览">
      <div class="stat">
        <div class="lbl"><span class="dot dot-p" aria-hidden="true"></span>任务总数</div>
        <div class="num">{{ stats?.total_tasks ?? '-' }}</div>
        <div class="foot">{{ stats ? `启用中 ${stats.enabled_count} · 已禁用 ${stats.total_tasks - stats.enabled_count}` : '' }}</div>
      </div>
      <div class="stat">
        <div class="lbl"><span class="dot dot-s" aria-hidden="true"></span>今日执行</div>
        <div class="num">{{ stats?.today_runs ?? '-' }}</div>
        <div class="foot">{{ stats ? `累计耗时 ${fmtDurationSpaced(stats.today_duration_sec)}` : '' }}</div>
      </div>
      <div class="stat">
        <div class="lbl"><span class="dot dot-w" aria-hidden="true"></span>今日成功率</div>
        <div class="num">{{ stats?.success_rate != null ? `${stats.success_rate}%` : '-' }}</div>
        <div class="foot">{{ successRateFoot }}</div>
      </div>
      <div class="stat">
        <div class="lbl"><span class="dot dot-d" aria-hidden="true"></span>最近失败</div>
        <div class="num" :class="{ danger: (stats?.today_failed ?? 0) > 0 }">{{ stats?.today_failed ?? '-' }}</div>
        <div class="foot">{{ latestFailureFoot }}</div>
      </div>
    </div>

    <div class="table-card">
      <!-- ═══ 工具栏 ═══ -->
      <div class="toolbar">
        <el-input
          v-model="filters.keyword"
          placeholder="搜索任务名称…"
          clearable
          class="search-input"
          :prefix-icon="Search"
          aria-label="搜索任务"
          @keyup.enter="applyFilters"
          @clear="applyFilters"
        />
        <el-select v-model="filters.task_type" class="filter-select" aria-label="按类型筛选" @change="applyFilters">
          <el-option value="" label="类型：全部" />
          <el-option v-for="t in taskTypes" :key="t.key" :value="t.key" :label="t.label" />
        </el-select>
        <el-select v-model="filters.status" class="filter-select" aria-label="按状态筛选" @change="applyFilters">
          <el-option value="" label="状态：全部" />
          <el-option value="enabled" label="启用中" />
          <el-option value="disabled" label="已禁用" />
          <el-option value="running" label="执行中" />
          <el-option value="failed" label="上次失败" />
        </el-select>
        <span class="spacer"></span>
        <span class="meta">共 {{ total }} 个任务</span>
      </div>
      <!-- ═══ 任务表格 ═══ -->
      <el-table
        :data="items"
        v-loading="loading"
        :row-class-name="rowClassName"
        class="sched-table"
      >
        <el-table-column label="任务" min-width="220">
          <template #default="{ row }">
            <div class="task-name">
              <strong>{{ row.name }}</strong>
              <span>{{ row.description || '暂无描述' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="类型" width="100">
          <template #default="{ row }">
            <span class="tag" :class="row.enabled ? 'primary' : 'info'">{{ typeLabel(row.task_type) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="执行周期" width="175">
          <template #default="{ row }">
            <div class="cron-cell">
              <strong>{{ humanizeCron(row.cron_expr) }}</strong>
              <span class="mono">{{ row.cron_expr }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="启用" width="64" align="center">
          <template #default="{ row }">
            <el-switch
              v-model="row.enabled"
              size="small"
              :aria-label="row.enabled ? `禁用任务 ${row.name}` : `启用任务 ${row.name}`"
              @change="handleToggle(row)"
            />
          </template>
        </el-table-column>
        <el-table-column label="上次执行" width="185">
          <template #default="{ row }">
            <div v-if="row.last_run_at" class="run-cell">
              <span class="tag" :class="statusTagClass(row.last_status)">{{ statusLabel(row.last_status) }}</span>
              <span class="sub">{{ lastRunText(row) }}</span>
            </div>
            <span v-else class="none">未执行</span>
          </template>
        </el-table-column>
        <el-table-column label="下次执行" width="155">
          <template #default="{ row }">
            <div v-if="row.enabled && row.next_run_at" class="next-cell">
              {{ nextRunMain(row.next_run_at) }}
              <span class="cd">{{ countdownText(row.next_run_at) }}</span>
            </div>
            <span v-else-if="!row.enabled" class="none">已禁用</span>
            <span v-else class="none">-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="195" align="center">
          <template #default="{ row }">
            <div class="action-cell">
              <el-button size="small" type="primary" link :aria-label="`立即执行 ${row.name}`" @click="handleRunNow(row)">立即执行</el-button>
              <el-button size="small" type="primary" link :aria-label="`查看 ${row.name} 执行日志`" @click="showLogs(row)">日志</el-button>
              <el-button size="small" type="primary" link :aria-label="`编辑 ${row.name}`" @click="showDialog(row)">编辑</el-button>
              <el-dropdown trigger="click" placement="bottom-end" :aria-label="`${row.name} 更多操作`" @command="() => handleDelete(row)">
                <el-button size="small" link class="action-more">
                  更多<el-icon class="action-more-icon"><ArrowDown /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="delete">
                      <span class="text-danger">删除</span>
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <!-- ═══ 分页 ═══ -->
      <div class="pagination-wrap" v-if="total > 0">
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
    <!-- ═══ 新建/编辑弹窗 ═══ -->
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑任务' : '新建任务'" width="560px" :close-on-click-modal="false" destroy-on-close>
      <div class="dlg-body">
        <div class="fld">
          <div class="fld-k"><em>*</em> 任务名称</div>
          <el-input v-model="form.name" placeholder="如：每日凌晨巡检" />
        </div>
        <div class="fld">
          <div class="fld-k"><em>*</em> 任务类型</div>
          <div class="freq-grid two">
            <div
              v-for="t in taskTypes"
              :key="t.key"
              class="freq"
              :class="{ on: form.task_type === t.key }"
              role="button"
              tabindex="0"
              @click="form.task_type = t.key"
              @keyup.enter="form.task_type = t.key"
            >
              <strong>{{ t.label }}</strong>
              <span>{{ typeDesc(t.key) }}</span>
            </div>
            <div v-if="!hasBackupType" class="freq disabled" aria-disabled="true">
              <strong>定时备份（规划中）</strong>
              <span>数据库与配置备份</span>
            </div>
          </div>
        </div>
        <div class="fld">
          <div class="fld-k"><em>*</em> 执行周期</div>
          <div class="freq-grid">
            <div
              v-for="m in FREQ_MODES"
              :key="m.key"
              class="freq"
              :class="{ on: form.freqMode === m.key }"
              role="button"
              tabindex="0"
              @click="form.freqMode = m.key"
              @keyup.enter="form.freqMode = m.key"
            >
              <strong>{{ m.label }}</strong>
              <span>{{ m.desc }}</span>
            </div>
          </div>
          <div class="freq-sub">
            <template v-if="form.freqMode === 'hourly'">
              <span>每小时的第</span>
              <el-input-number v-model="form.minute" :min="0" :max="59" size="small" controls-position="right" class="num-input" />
              <span>分执行</span>
            </template>
            <template v-else-if="form.freqMode === 'daily'">
              <span>每天</span>
              <el-time-picker v-model="form.time" format="HH:mm" value-format="HH:mm" :clearable="false" class="time-input" />
              <span>执行</span>
            </template>
            <template v-else-if="form.freqMode === 'weekly'">
              <span>每</span>
              <el-select v-model="form.weekday" class="weekday-input">
                <el-option v-for="(w, i) in ['周日', '周一', '周二', '周三', '周四', '周五', '周六']" :key="i" :value="i" :label="w" />
              </el-select>
              <el-time-picker v-model="form.time" format="HH:mm" value-format="HH:mm" :clearable="false" class="time-input" />
              <span>执行</span>
            </template>
            <template v-else-if="form.freqMode === 'monthly'">
              <span>每月</span>
              <el-input-number v-model="form.monthDay" :min="1" :max="31" size="small" controls-position="right" class="num-input" />
              <span>日</span>
              <el-time-picker v-model="form.time" format="HH:mm" value-format="HH:mm" :clearable="false" class="time-input" />
              <span>执行</span>
            </template>
            <template v-else-if="form.freqMode === 'interval'">
              <span>每</span>
              <el-input-number v-model="form.intervalValue" :min="1" :max="59" size="small" controls-position="right" class="num-input" />
              <el-select v-model="form.intervalUnit" class="weekday-input">
                <el-option value="minute" label="分钟" />
                <el-option value="hour" label="小时" />
              </el-select>
              <span>执行</span>
            </template>
            <template v-else>
              <el-input v-model="form.customCron" placeholder="如：0 2 * * *" class="cron-input" />
            </template>
          </div>
          <div class="cron-preview">
            生成表达式 <span class="mono">{{ buildCron() || '（待填写）' }}</span>
            <template v-if="form.freqMode !== 'custom' && buildCron()"> · 下次执行：{{ previewNextRunText }}</template>
            <template v-else-if="form.freqMode === 'custom'"> · 格式：分 时 日 月 星期（下次执行保存后可见）</template>
          </div>
        </div>
        <div class="fld">
          <div class="fld-k">备注</div>
          <el-input v-model="form.description" placeholder="可选" />
        </div>
      </div>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
    <!-- ═══ 执行日志抽屉（时间线） ═══ -->
    <el-drawer v-model="logsVisible" size="620px" :with-header="false" destroy-on-close>
      <div class="d-head">
        <div>
          <div class="d-title">{{ logsTask?.name || '执行日志' }}</div>
          <div class="d-sub" v-if="logsTask">{{ humanizeCron(logsTask.cron_expr) }} · <span class="mono">{{ logsTask.cron_expr }}</span></div>
        </div>
        <button type="button" class="d-close" aria-label="关闭" @click="logsVisible = false">✕</button>
      </div>
      <div class="d-summary">
        <div>
          <div class="k">近 7 天执行</div>
          <div class="v">{{ logsSummary ? `${logsSummary.total_7d} 次` : '-' }}</div>
        </div>
        <div>
          <div class="k">成功率</div>
          <div class="v">{{ logsSummary?.success_rate_7d != null ? `${logsSummary.success_rate_7d}%` : '-' }}</div>
        </div>
        <div>
          <div class="k">平均耗时</div>
          <div class="v">{{ logsSummary?.avg_duration_sec_7d != null ? fmtDuration(logsSummary.avg_duration_sec_7d) : '-' }}</div>
        </div>
      </div>
      <div class="timeline" v-loading="logsLoading">
        <div v-for="log in logs" :key="log.id" class="tl-item">
          <span class="tl-dot" :class="tlDotClass(log.status)" aria-hidden="true"></span>
          <div class="tl-head">
            <span class="tl-time">{{ logTimeText(log.started_at) }}</span>
            <span class="tl-dur">{{ logDuration(log) }}</span>
            <span class="tag tl-tag" :class="statusTagClass(log.status)">{{ statusLabel(log.status) }}</span>
          </div>
          <div v-if="log.result" class="tl-result">{{ log.result }}</div>
          <div v-if="log.error" class="tl-err">{{ log.error }}</div>
        </div>
        <el-empty v-if="!logsLoading && !logs.length" description="暂无执行记录" :image-size="80" />
      </div>
      <div class="pagination-wrap drawer-pager" v-if="logsTotal > logsPageSize">
        <el-pagination
          v-model:current-page="logsPage"
          :page-size="logsPageSize"
          :total="logsTotal"
          layout="total, prev, pager, next"
          small
          @current-change="fetchLogs"
        />
      </div>
    </el-drawer>
  </div>
</template>
<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, ArrowDown, Search } from '@element-plus/icons-vue'
import {
  getSchedulerTasks, getTaskTypes, getSchedulerStats, createSchedulerTask, updateSchedulerTask,
  deleteSchedulerTask, toggleSchedulerTask, runSchedulerTaskNow, getTaskExecutionLogs,
  type ScheduledTask, type TaskExecutionLog,
} from '@/api/scheduler'
import { usePagination } from '@/hooks/usePagination'

// ─── 列表 ────────────────────────────────────────────────
const loading = ref(false)
const items = ref<ScheduledTask[]>([])
const stats = ref<any | null>(null)
const taskTypes = ref<{ key: string; label: string }[]>([])
const filters = reactive({ keyword: '', task_type: '', status: '' })

const { currentPage, pageSize, total, paginationLayout, handleCurrentChange, handleSizeChange, resetPagination } = usePagination(fetchData)

async function fetchData(extra?: any) {
  loading.value = true
  try {
    const res: any = await getSchedulerTasks({
      ...filters,
      page: extra?.page || currentPage.value,
      page_size: extra?.page_size || pageSize.value,
    })
    items.value = res.data?.items || []
    total.value = res.data?.total || 0
  } finally {
    loading.value = false
  }
}

async function fetchStats() {
  try {
    const res: any = await getSchedulerStats()
    stats.value = res.data
  } catch {
    stats.value = null
  }
}

async function fetchTaskTypes() {
  try {
    const res: any = await getTaskTypes()
    taskTypes.value = res.data?.items || []
  } catch { /* 类型加载失败时仅影响筛选项 */ }
}

function applyFilters() {
  resetPagination()
  fetchData({ page: 1 })
}

const hasBackupType = computed(() => taskTypes.value.some((t) => t.key === 'backup'))

function typeLabel(key: string) {
  return taskTypes.value.find((t) => t.key === key)?.label || key
}
function typeDesc(key: string) {
  const map: Record<string, string> = { patrol: '按周期执行主机巡检', backup: '数据库与配置备份' }
  return map[key] || '周期性任务'
}

const successRateFoot = computed(() => {
  if (!stats.value) return ''
  if (!stats.value.today_runs) return '今日暂无执行'
  return stats.value.today_failed > 0 ? `失败 ${stats.value.today_failed} 次` : '今日全部成功'
})
const latestFailureFoot = computed(() => {
  const f = stats.value?.latest_failure
  if (!f) return '暂无失败记录'
  const d = new Date(f.started_at)
  return `${pad(d.getHours())}:${pad(d.getMinutes())} · ${f.task_name}`
})

// ─── cron 翻译 / 时间格式化 ──────────────────────────────
const WEEKDAYS = ['日', '一', '二', '三', '四', '五', '六']
function humanizeCron(cron: string): string {
  const p = (cron || '').trim().split(/\s+/)
  if (p.length !== 5) return '自定义周期'
  const [mi, hh, dd, , wd] = p
  const hm = /^\d{1,2}$/.test(mi) && /^\d{1,2}$/.test(hh)
    ? `${hh.padStart(2, '0')}:${mi.padStart(2, '0')}` : ''
  const hourStep = hh.match(/^(\d{1,2})-(\d{1,2})\/(\d{1,2})$/)
  if (dd === '*' && wd === '*') {
    if (hh === '*' && mi.startsWith('*/')) return `每 ${mi.slice(2)} 分钟`
    if (hh === '*' && /^\d{1,2}$/.test(mi)) return `每小时第 ${mi} 分`
    if (hh.startsWith('*/') && mi === '0') return `每 ${hh.slice(2)} 小时`
    if (hourStep) return `每天 ${hourStep[1]}-${hourStep[2]} 点每 ${hourStep[3]} 小时`
    if (hm) return `每天 ${hm}`
  }
  if (dd === '*' && wd === '1-5') {
    if (hourStep) return hourStep[3] === '1' ? '工作日每小时' : `工作日每 ${hourStep[3]} 小时`
    if (hm) return `工作日 ${hm}`
  }
  if (dd === '*' && /^\d$/.test(wd) && hm) return `每周${WEEKDAYS[Number(wd)]} ${hm}`
  if (/^\d{1,2}$/.test(dd) && wd === '*' && hm) return `每月 ${Number(dd)} 日 ${hm}`
  return '自定义周期'
}

function pad(n: number) { return String(n).padStart(2, '0') }
function isSameDay(a: Date, b: Date) {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate()
}
function nextRunMain(iso: string): string {
  const d = new Date(iso)
  const now = new Date()
  const hm = `${pad(d.getHours())}:${pad(d.getMinutes())}`
  if (isSameDay(d, now)) return `今天 ${hm}`
  const tomorrow = new Date(now); tomorrow.setDate(now.getDate() + 1)
  if (isSameDay(d, tomorrow)) return `明天 ${hm}`
  return `${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${hm}`
}
function countdownText(iso: string): string {
  const ms = new Date(iso).getTime() - Date.now()
  if (ms <= 0) return '即将执行'
  const min = Math.floor(ms / 60000)
  if (min < 60) return `${min} 分钟后`
  const h = Math.floor(min / 60)
  if (h < 24) return min % 60 ? `${h} 小时 ${min % 60} 分后` : `${h} 小时后`
  return `${Math.floor(h / 24)} 天后`
}
function lastRunText(row: ScheduledTask): string {
  if (!row.last_run_at) return ''
  const d = new Date(row.last_run_at)
  const now = new Date()
  const hm = `${pad(d.getHours())}:${pad(d.getMinutes())}`
  let dayLabel: string
  if (isSameDay(d, now)) dayLabel = '今天'
  else {
    const yesterday = new Date(now); yesterday.setDate(now.getDate() - 1)
    if (isSameDay(d, yesterday)) dayLabel = '昨天'
    else if (now.getTime() - d.getTime() < 7 * 86400000) dayLabel = `周${WEEKDAYS[d.getDay()]}`
    else dayLabel = `${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
  }
  const dur = row.last_duration_sec != null ? ` · 耗时 ${fmtDuration(row.last_duration_sec)}` : ''
  return `${dayLabel} ${hm}${dur}`
}
function fmtDuration(sec: number): string {
  if (sec < 60) return `${Math.max(sec, 0)}s`
  const m = Math.floor(sec / 60)
  if (m < 60) return sec % 60 ? `${m}m${sec % 60}s` : `${m}m`
  const h = Math.floor(m / 60)
  return m % 60 ? `${h}h${m % 60}m` : `${h}h`
}
function fmtDurationSpaced(sec: number): string {
  const m = Math.floor(sec / 60)
  const s = sec % 60
  if (m === 0) return `${s}s`
  return s ? `${m}m ${s}s` : `${m}m`
}

// ─── 状态 ────────────────────────────────────────────────
function statusTagClass(status: string) {
  if (status === 'success') return 'ok'
  if (status === 'failed') return 'danger'
  if (status === 'running') return 'warn'
  return 'info'
}
function statusLabel(status: string) {
  const map: Record<string, string> = { success: '成功', failed: '失败', running: '执行中' }
  return map[status] || status || '未知'
}
function rowClassName({ row }: { row: ScheduledTask }) {
  return row.enabled ? '' : 'disabled-row'
}

// ─── 新建 / 编辑弹窗 ──────────────────────────────────────
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)

const FREQ_MODES = [
  { key: 'hourly', label: '每小时', desc: '整点执行' },
  { key: 'daily', label: '每天', desc: '指定时间执行' },
  { key: 'weekly', label: '每周', desc: '指定星期与时间' },
  { key: 'monthly', label: '每月', desc: '指定日期与时间' },
  { key: 'interval', label: '间隔', desc: '每 N 分钟/小时' },
  { key: 'custom', label: '自定义', desc: '手写 cron 表达式' },
] as const

const defaultForm = () => ({
  name: '',
  task_type: 'patrol',
  description: '',
  freqMode: 'daily' as string,
  time: '02:00',
  minute: 0,
  weekday: 1,
  monthDay: 1,
  intervalValue: 30,
  intervalUnit: 'minute' as string,
  customCron: '',
})
const form = reactive(defaultForm())

function buildCron(): string {
  const [h, m] = (form.time || '02:00').split(':').map(Number)
  switch (form.freqMode) {
    case 'hourly': return `${form.minute} * * * *`
    case 'daily': return `${m} ${h} * * *`
    case 'weekly': return `${m} ${h} * * ${form.weekday}`
    case 'monthly': return `${m} ${h} ${form.monthDay} * *`
    case 'interval':
      return form.intervalUnit === 'minute'
        ? `*/${form.intervalValue} * * * *`
        : `0 */${form.intervalValue} * * *`
    case 'custom': return form.customCron.trim()
    default: return ''
  }
}

/** 本地按标准 cron 语义（周日=0）计算下次执行时间，与后端口径一致。 */
function nextCronFire(cron: string): Date | null {
  const p = cron.trim().split(/\s+/)
  if (p.length !== 5) return null
  const match = (field: string, v: number, max: number): boolean => {
    if (field === '*') return true
    return field.split(',').some((part) => {
      const [base, stepS] = part.split('/')
      const step = stepS ? Number(stepS) : 1
      let lo = 0
      let hi = max
      if (base !== '*') {
        if (base.includes('-')) {
          const [a, b] = base.split('-').map(Number)
          lo = a; hi = b
        } else {
          lo = Number(base)
          if (Number.isNaN(lo)) return false
          if (!stepS) return v === lo
          hi = max
        }
      }
      return v >= lo && v <= hi && (v - lo) % step === 0
    })
  }
  const d = new Date()
  d.setSeconds(0, 0)
  d.setMinutes(d.getMinutes() + 1)
  // 逐分钟探测，上限一年；周期模板生成的表达式几步内即命中
  for (let i = 0; i < 527040; i++) {
    if (match(p[0], d.getMinutes(), 59) && match(p[1], d.getHours(), 23)
      && match(p[2], d.getDate(), 31) && match(p[3], d.getMonth() + 1, 12)
      && match(p[4], d.getDay(), 7)) return d
    d.setMinutes(d.getMinutes() + 1)
  }
  return null
}

const previewNextRunText = computed(() => {
  const d = nextCronFire(buildCron())
  return d ? nextRunMain(d.toISOString()) : '无法计算'
})

/** 编辑时把 cron 反向映射回周期模板。 */
function parseCronToForm(cron: string) {
  const p = (cron || '').trim().split(/\s+/)
  if (p.length !== 5) {
    form.freqMode = 'custom'; form.customCron = cron
    return
  }
  const [mi, hh, dd, mm, wd] = p
  const hm = `${hh.padStart(2, '0')}:${mi.padStart(2, '0')}`
  if (/^\d{1,2}$/.test(mi) && hh === '*' && dd === '*' && mm === '*' && wd === '*') {
    form.freqMode = 'hourly'; form.minute = Number(mi)
  } else if (mi.startsWith('*/') && hh === '*' && dd === '*' && wd === '*') {
    form.freqMode = 'interval'; form.intervalUnit = 'minute'; form.intervalValue = Number(mi.slice(2))
  } else if (mi === '0' && hh.startsWith('*/') && dd === '*' && wd === '*') {
    form.freqMode = 'interval'; form.intervalUnit = 'hour'; form.intervalValue = Number(hh.slice(2))
  } else if (/^\d{1,2}$/.test(mi) && /^\d{1,2}$/.test(hh) && mm === '*') {
    form.time = hm
    if (dd === '*' && wd === '*') form.freqMode = 'daily'
    else if (dd === '*' && /^\d$/.test(wd)) { form.freqMode = 'weekly'; form.weekday = Number(wd) }
    else if (/^\d{1,2}$/.test(dd) && wd === '*') { form.freqMode = 'monthly'; form.monthDay = Number(dd) }
    else { form.freqMode = 'custom'; form.customCron = cron }
  } else {
    form.freqMode = 'custom'; form.customCron = cron
  }
}

function showDialog(task?: ScheduledTask) {
  if (task) {
    editingId.value = task.id
    Object.assign(form, defaultForm(), {
      name: task.name,
      task_type: task.task_type,
      description: task.description || '',
    })
    parseCronToForm(task.cron_expr)
  } else {
    editingId.value = null
    Object.assign(form, defaultForm(), { task_type: taskTypes.value[0]?.key || 'patrol' })
  }
  dialogVisible.value = true
}

async function handleSave() {
  if (!form.name.trim()) {
    ElMessage.warning('请填写任务名称')
    return
  }
  const cron = buildCron()
  if (!cron) {
    ElMessage.warning('请填写 cron 表达式')
    return
  }
  saving.value = true
  try {
    const payload = {
      name: form.name.trim(),
      task_type: form.task_type,
      cron_expr: cron,
      description: form.description.trim(),
    }
    if (editingId.value) {
      await updateSchedulerTask(editingId.value, payload)
      ElMessage.success('任务已更新')
    } else {
      await createSchedulerTask(payload)
      ElMessage.success('任务已创建')
    }
    dialogVisible.value = false
    await Promise.all([fetchData(), fetchStats()])
  } finally {
    saving.value = false
  }
}

// ─── 行操作 ──────────────────────────────────────────────
async function handleToggle(row: ScheduledTask) {
  try {
    await toggleSchedulerTask(row.id)
    ElMessage.success(row.enabled ? `已启用「${row.name}」` : `已禁用「${row.name}」`)
    await Promise.all([fetchData(), fetchStats()])
  } catch {
    row.enabled = !row.enabled // 失败回滚开关
  }
}

async function handleRunNow(row: ScheduledTask) {
  await runSchedulerTaskNow(row.id)
  ElMessage.success(`已触发「${row.name}」执行，稍后可查看日志`)
  setTimeout(() => {
    fetchData()
    fetchStats()
  }, 1500)
}

async function handleDelete(row: ScheduledTask) {
  try {
    await ElMessageBox.confirm(
      `确认删除任务「${row.name}」？执行日志将一并清除，此操作不可恢复。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  await deleteSchedulerTask(row.id)
  ElMessage.success('任务已删除')
  await Promise.all([fetchData(), fetchStats()])
}

// ─── 执行日志抽屉 ─────────────────────────────────────────
const logsVisible = ref(false)
const logsTask = ref<ScheduledTask | null>(null)
const logs = ref<TaskExecutionLog[]>([])
const logsLoading = ref(false)
const logsTotal = ref(0)
const logsPage = ref(1)
const logsPageSize = 10
const logsSummary = ref<{ total_7d: number; success_rate_7d: number | null; avg_duration_sec_7d: number | null } | null>(null)

function showLogs(row: ScheduledTask) {
  logsTask.value = row
  logsPage.value = 1
  logsVisible.value = true
  fetchLogs(1)
}

async function fetchLogs(page?: number) {
  if (!logsTask.value) return
  if (page) logsPage.value = page
  logsLoading.value = true
  try {
    const res: any = await getTaskExecutionLogs(logsTask.value.id, { page: logsPage.value, page_size: logsPageSize })
    logs.value = res.data?.items || []
    logsTotal.value = res.data?.total || 0
    logsSummary.value = res.data?.summary || null
  } finally {
    logsLoading.value = false
  }
}

function tlDotClass(status: string) {
  if (status === 'success') return 'ok'
  if (status === 'failed') return 'bad'
  if (status === 'running') return 'run'
  return ''
}
function logTimeText(iso: string | null): string {
  if (!iso) return '-'
  const d = new Date(iso)
  const now = new Date()
  const hm = `${pad(d.getHours())}:${pad(d.getMinutes())}`
  if (isSameDay(d, now)) return `今天 ${hm}`
  const yesterday = new Date(now); yesterday.setDate(now.getDate() - 1)
  if (isSameDay(d, yesterday)) return `昨天 ${hm}`
  return `${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${hm}`
}
function logDuration(log: TaskExecutionLog): string {
  if (!log.started_at) return '-'
  if (!log.finished_at) return log.status === 'running' ? '执行中…' : '-'
  const sec = Math.max(0, Math.round((new Date(log.finished_at).getTime() - new Date(log.started_at).getTime()) / 1000))
  return `耗时 ${fmtDuration(sec)}`
}

onMounted(() => {
  fetchData()
  fetchStats()
  fetchTaskTypes()
})
</script>

<style scoped>
.page-subtitle {
  margin: 3px 0 0;
  font-size: 12px;
  color: var(--text-secondary);
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
  width: 220px;
}
.filter-select {
  width: 140px;
}
.spacer {
  flex: 1;
}
.meta {
  font-size: 12px;
  color: var(--text-muted);
}

/* ═══ 表格 ═══ */
.sched-table {
  --el-table-row-hover-bg-color: var(--primary-bg);
}
.sched-table :deep(.el-table__header th) {
  background: #f7f7f9;
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 600;
}
.sched-table :deep(.el-table__body tr.disabled-row .task-name strong),
.sched-table :deep(.el-table__body tr.disabled-row .cron-cell strong) {
  color: var(--text-muted);
  font-weight: 500;
}
.task-name strong {
  display: block;
  font-weight: 650;
  color: var(--text-primary);
}
.task-name span {
  font-size: 11.5px;
  color: var(--text-muted);
}
.cron-cell strong {
  display: block;
  font-weight: 650;
  color: var(--text-primary);
}
.cron-cell .mono {
  color: var(--text-muted);
  font-size: 11px;
}
.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
}
.run-cell {
  white-space: nowrap;
}
.run-cell .sub {
  display: block;
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 1px;
}
.next-cell {
  white-space: nowrap;
  color: var(--text-primary);
}
.next-cell .cd {
  display: block;
  font-size: 11px;
  color: var(--primary-color);
  margin-top: 1px;
  font-weight: 600;
}
.none {
  color: var(--text-muted);
}

/* 状态 tag */
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

/* 操作列 */
.action-cell {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
}
.action-cell :deep(.el-button + .el-button) {
  margin-left: 0;
}
.action-cell :deep(.el-dropdown) {
  margin-left: 0;
}
.action-more {
  color: var(--text-secondary);
}
.action-more-icon {
  margin-left: 2px;
  font-size: 12px;
}
.text-danger {
  color: #dc2626;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  padding: 11px 12px;
}

/* ═══ 新建/编辑弹窗 ═══ */
.dlg-body {
  padding: 2px 0;
}
.fld {
  margin-bottom: 14px;
}
.fld:last-child {
  margin-bottom: 0;
}
.fld-k {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 6px;
}
.fld-k em {
  color: var(--danger-color);
  font-style: normal;
}
.freq-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}
.freq-grid.two {
  grid-template-columns: 1fr 1fr;
}
.freq {
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 9px 10px;
  cursor: pointer;
  transition: all 0.12s;
}
.freq:hover {
  border-color: var(--primary-color);
}
.freq.on {
  border-color: var(--primary-color);
  background: var(--primary-bg);
}
.freq.disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.freq.disabled:hover {
  border-color: var(--border-color);
}
.freq strong {
  display: block;
  font-size: 12.5px;
  color: var(--text-primary);
}
.freq span {
  font-size: 11px;
  color: var(--text-muted);
}
.freq-sub {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  flex-wrap: wrap;
  font-size: 12px;
  color: var(--text-secondary);
}
.num-input {
  width: 90px;
}
.time-input {
  width: 110px;
}
.weekday-input {
  width: 100px;
}
.cron-input {
  flex: 1;
}
.cron-preview {
  margin-top: 10px;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  background: #f7f7f9;
  border: 1px dashed var(--border-color);
  border-radius: 7px;
  padding: 7px 10px;
  font-size: 12px;
  color: var(--text-secondary);
}
.cron-preview .mono {
  color: var(--primary-color);
  font-weight: 700;
}

/* ═══ 执行日志抽屉 ═══ */
:deep(.el-drawer__body) {
  padding: 0;
  overflow-y: auto;
}
.d-head {
  padding: 15px 20px;
  border-bottom: 1px solid var(--border-color);
  background: linear-gradient(180deg, #fbfbfc 0%, var(--surface-color) 100%);
  display: flex;
  justify-content: space-between;
  gap: 12px;
}
.d-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
  word-break: break-all;
}
.d-sub {
  margin-top: 3px;
  font-size: 12px;
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
.d-summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  border-bottom: 1px solid var(--border-color);
}
.d-summary > div {
  padding: 10px 14px;
  border-right: 1px solid var(--border-color);
}
.d-summary > div:last-child {
  border-right: none;
}
.d-summary .k {
  font-size: 11px;
  color: var(--text-muted);
}
.d-summary .v {
  margin-top: 2px;
  font-size: 15px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: var(--text-primary);
}
.timeline {
  padding: 16px 20px 20px;
}
.tl-item {
  position: relative;
  padding: 0 0 16px 22px;
}
.tl-item::before {
  content: '';
  position: absolute;
  left: 5px;
  top: 14px;
  bottom: -2px;
  width: 1px;
  background: var(--border-color);
}
.tl-item:last-child::before {
  display: none;
}
.tl-dot {
  position: absolute;
  left: 0;
  top: 4px;
  width: 11px;
  height: 11px;
  border-radius: 50%;
  border: 2px solid var(--surface-color);
  box-shadow: 0 0 0 1px var(--border-color);
  background: var(--text-muted);
}
.tl-dot.ok {
  background: #16a34a;
  box-shadow: 0 0 0 1px rgba(34, 197, 94, 0.4);
}
.tl-dot.bad {
  background: #dc2626;
  box-shadow: 0 0 0 1px rgba(239, 68, 68, 0.4);
}
.tl-dot.run {
  background: #d97706;
  box-shadow: 0 0 0 1px rgba(245, 158, 11, 0.4);
}
.tl-head {
  display: flex;
  align-items: baseline;
  gap: 8px;
  flex-wrap: wrap;
}
.tl-time {
  font-size: 12.5px;
  font-weight: 650;
  color: var(--text-primary);
}
.tl-dur {
  font-size: 11px;
  color: var(--text-muted);
}
.tl-tag {
  margin-left: auto;
}
.tl-result {
  margin-top: 3px;
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.6;
  word-break: break-all;
}
.tl-err {
  margin-top: 5px;
  font-size: 11.5px;
  color: #dc2626;
  background: rgba(239, 68, 68, 0.09);
  border-radius: 6px;
  padding: 6px 9px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  line-height: 1.6;
  word-break: break-all;
}
.drawer-pager {
  border-top: 1px solid var(--border-color);
}

@media (max-width: 900px) {
  .stats {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .search-input,
  .filter-select {
    width: 100%;
  }
  .freq-grid,
  .freq-grid.two {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
