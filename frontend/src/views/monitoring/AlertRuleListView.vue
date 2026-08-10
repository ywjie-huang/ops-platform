<template>
  <div class="alert-rules-page">
    <!-- ═══ 页头 ═══ -->
    <div class="page-header">
      <h2 class="page-title">告警规则</h2>
      <div class="header-right">
        <span v-if="lastUpdated" class="updated">最后更新 {{ lastUpdated }} · 30s 自动刷新</span>
        <span class="conn-tag" :class="promConnected === true ? 'conn-ok' : promConnected === false ? 'conn-err' : 'conn-checking'">
          Prometheus {{ promConnected === true ? '已连接' : promConnected === false ? '未连接' : '检测中' }}
        </span>
        <span class="conn-tag" :class="amConnected === true ? 'conn-ok' : amConnected === false ? 'conn-err' : 'conn-checking'">
          Alertmanager {{ amConnected === true ? '已连接' : amConnected === false ? '未连接' : '检测中' }}
        </span>
        <button class="refresh-btn" :disabled="loading" @click="refreshAll(true)">↻ 刷新</button>
      </div>
    </div>

    <!-- Prometheus 未连接引导 -->
    <div v-if="promConnected === false" class="card empty-state">
      <div class="empty-icon">📡</div>
      <h3>Prometheus 未连接</h3>
      <p>告警规则来源于 Prometheus，请先在「系统设置」中配置 Prometheus 地址并确认服务可达。</p>
    </div>

    <template v-else>
      <!-- ═══ 概览统计（点击即筛选） ═══ -->
      <div class="stats">
        <div class="stat s-firing" :class="{ active: statFilter === 'firing' }" @click="toggleStatFilter('firing')">
          <div class="num"><span v-if="firingCount" class="dot"></span>{{ firingCount }}</div>
          <div class="lbl">正在告警</div>
          <div class="sub">{{ firingSeveritySummary }}</div>
        </div>
        <div class="stat s-pending" :class="{ active: statFilter === 'pending' }" @click="toggleStatFilter('pending')">
          <div class="num">{{ pendingCount }}</div>
          <div class="lbl">待触发 Pending</div>
          <div class="sub">等待持续时间满足</div>
        </div>
        <div class="stat s-err" :class="{ active: statFilter === 'err' }" @click="toggleStatFilter('err')">
          <div class="num">{{ errCount }}</div>
          <div class="lbl">异常规则</div>
          <div class="sub">PromQL 评估失败</div>
        </div>
        <div class="stat" @click="clearStatFilter">
          <div class="num">{{ rules.length }}</div>
          <div class="lbl">规则总数</div>
          <div class="sub">{{ groupCount }} 个分组</div>
        </div>
      </div>

      <!-- Alertmanager 降级提示 -->
      <div v-if="amConnected === false" class="am-banner">
        ⚠ Alertmanager 未连接 — 规则可正常查看，但静默功能不可用，告警通知可能中断。
      </div>

      <div class="card">
        <!-- ═══ 工具栏 ═══ -->
        <div class="toolbar">
          <input v-model="keyword" type="text" placeholder="🔍 搜索规则名 / PromQL…" class="t-input">
          <select v-model="filterSeverity" class="t-select">
            <option value="">严重程度：全部</option>
            <option value="critical">critical</option>
            <option value="warning">warning</option>
            <option value="warn">warn</option>
            <option value="info">info</option>
          </select>
          <select v-model="filterState" class="t-select">
            <option value="">状态：全部</option>
            <option value="firing">firing</option>
            <option value="pending">pending</option>
            <option value="inactive">inactive</option>
          </select>
          <select v-model="filterGroup" class="t-select">
            <option value="">分组：全部</option>
            <option v-for="g in allGroupNames" :key="g" :value="g">{{ g }}</option>
          </select>
          <span class="spacer"></span>
          <span class="count-hint">匹配 {{ filteredRules.length }} 条 / 共 {{ rules.length }} 条</span>
        </div>

        <!-- ═══ 规则分组列表 ═══ -->
        <div class="rules-area">
          <div v-if="loading && !rules.length" class="loading-hint">加载中…</div>
          <div v-else-if="!groupedRules.length" class="empty-rules">
            <template v-if="rules.length">当前筛选条件下没有匹配的规则</template>
            <template v-else>未发现告警规则 — 请在 Prometheus 的 rule_files 中配置告警规则。</template>
          </div>

          <div v-for="group in groupedRules" :key="group.name" class="group" :class="{ collapsed: isCollapsed(group.name) }">
            <div class="group-head" @click="toggleGroup(group.name)">
              <span class="arrow">▼</span>
              <span class="group-name">{{ group.name }}</span>
              <span class="group-meta">{{ group.rules.length }} 条规则</span>
              <span v-if="group.firingCount" class="group-firing">firing {{ group.firingCount }}</span>
              <span v-if="group.errCount" class="group-err">err {{ group.errCount }}</span>
            </div>
            <div class="group-body">
              <AlertRuleItem
                v-for="rule in group.rules"
                :key="rule.name"
                :rule="rule"
                :open="openRules.has(rule.name)"
                :hits="hitsOf(rule)"
                :hosts-loading="hostsLoading"
                :silence="silenceOf(rule.name)"
                :am-connected="amConnected === true"
                :silence-busy="silenceBusy"
                @toggle="toggleRule(rule.name)"
                @navigate="goToHost"
                @silence="(mins: number, comment: string) => handleSilence(rule.name, mins, comment)"
                @unsilence="handleUnsilence"
                @view-events="goToEvents"
              />
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onActivated, onDeactivated, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  createSilence,
  deleteSilence,
  getAlertManagerRules,
  getAlertManagerRulesHosts,
  getAlertManagerSilences,
  getAlertManagerStatus,
} from '@/api/alertmanager'
import { getPrometheusHealth } from '@/api/monitoring'
import { useAuthStore } from '@/stores/modules/auth'
import AlertRuleItem, { type AlertRule, type RuleHit, type SilenceInfo } from './AlertRuleItem.vue'

interface Silence extends SilenceInfo {
  matchers: Array<{ name: string; value: string; is_regex: boolean }>
}

const router = useRouter()
const authStore = useAuthStore()

const loading = ref(false)
const hostsLoading = ref(false)
const silenceBusy = ref(false)
const promConnected = ref<boolean | null>(null)
const amConnected = ref<boolean | null>(null)
const rules = ref<AlertRule[]>([])
const rulesHosts = ref<Record<string, Array<{ id: number; name: string; ip: string }>>>({})
const silences = ref<Silence[]>([])
const keyword = ref('')
const filterSeverity = ref('')
const filterState = ref('')
const filterGroup = ref('')
const statFilter = ref('')
const openRules = ref<Set<string>>(new Set())
const lastUpdated = ref('')
let refreshTimer: ReturnType<typeof setInterval> | undefined
// 用户手动折叠/展开过的分组（刷新时保持），key: 组名 value: 是否折叠
const groupToggleOverride = new Map<string, boolean>()

const SEVERITY_ORDER: Record<string, number> = { critical: 0, warning: 1, warn: 1, info: 2 }
const STATE_ORDER: Record<string, number> = { firing: 0, pending: 1, inactive: 2 }

const firingCount = computed(() => rules.value.filter((r) => r.state === 'firing').length)
const pendingCount = computed(() => rules.value.filter((r) => r.state === 'pending').length)
const errCount = computed(() => rules.value.filter((r) => r.health === 'err').length)
const groupCount = computed(() => new Set(rules.value.map((r) => r.group_name)).size)
const firingSeveritySummary = computed(() => {
  const firing = rules.value.filter((r) => r.state === 'firing')
  if (!firing.length) return '一切正常'
  const parts: string[] = []
  for (const sev of ['critical', 'warning', 'warn', 'info']) {
    const n = firing.filter((r) => r.labels?.severity === sev).length
    if (n) parts.push(`${sev} ${n}`)
  }
  return parts.join(' · ')
})

const allGroupNames = computed(() =>
  [...new Set(rules.value.map((r) => r.group_name).filter(Boolean))].sort()
)

const filteredRules = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  return rules.value.filter((r) => {
    if (statFilter.value === 'err') {
      if (r.health !== 'err') return false
    } else if (statFilter.value && r.state !== statFilter.value) {
      return false
    }
    if (filterSeverity.value && r.labels?.severity !== filterSeverity.value) return false
    if (filterState.value && r.state !== filterState.value) return false
    if (filterGroup.value && r.group_name !== filterGroup.value) return false
    if (kw && !r.name.toLowerCase().includes(kw) && !r.query.toLowerCase().includes(kw)) return false
    return true
  })
})

const groupedRules = computed(() => {
  const map = new Map<string, AlertRule[]>()
  for (const rule of filteredRules.value) {
    const name = rule.group_name || '未分组'
    if (!map.has(name)) map.set(name, [])
    map.get(name)!.push(rule)
  }
  const groups = [...map.entries()].map(([name, list]) => ({
    name,
    rules: [...list].sort(compareRules),
    firingCount: list.filter((r) => r.state === 'firing').length,
    errCount: list.filter((r) => r.health === 'err').length,
  }))
  // 有 firing 的分组置顶
  return groups.sort((a, b) => b.firingCount - a.firingCount || a.name.localeCompare(b.name))
})

function compareRules(a: AlertRule, b: AlertRule) {
  const sd = (STATE_ORDER[a.state] ?? 3) - (STATE_ORDER[b.state] ?? 3)
  if (sd) return sd
  return (SEVERITY_ORDER[a.labels?.severity] ?? 4) - (SEVERITY_ORDER[b.labels?.severity] ?? 4)
}

function isCollapsed(groupName: string) {
  const override = groupToggleOverride.get(groupName)
  if (override !== undefined) return override
  // 默认：有 firing/pending 的组展开，其余折叠
  const group = groupedRules.value.find((g) => g.name === groupName)
  return !(group?.firingCount || group?.rules.some((r) => r.state === 'pending'))
}

function toggleGroup(groupName: string) {
  groupToggleOverride.set(groupName, !isCollapsed(groupName))
  // 触发响应式（Map 非响应式，借 openRules 的引用更新驱动）
  openRules.value = new Set(openRules.value)
}

function toggleRule(name: string) {
  const set = new Set(openRules.value)
  if (set.has(name)) set.delete(name)
  else set.add(name)
  openRules.value = set
}

function toggleStatFilter(state: string) {
  statFilter.value = statFilter.value === state ? '' : state
}

function clearStatFilter() {
  statFilter.value = ''
}

// ── 命中主机（firing/pending 规则才查） ──
function hitsOf(rule: AlertRule): RuleHit[] {
  const hosts = rulesHosts.value[rule.name] || []
  return hosts.map((h) => {
    const alert = rule.alerts?.find((a) => {
      const clean = a.instance.split(':')[0]
      return clean === h.ip || a.instance.includes(h.name)
    })
    return { ...h, value: alert ? formatHitValue(rule, alert.value) : undefined }
  })
}

function formatHitValue(rule: AlertRule, raw: string) {
  const n = Number(raw)
  if (!Number.isFinite(n)) return raw
  const abs = Math.abs(n)
  const text = abs >= 100 ? n.toFixed(0) : abs >= 1 ? n.toFixed(1) : n.toFixed(2)
  return rule.query.includes('* 100') ? `${text}%` : text
}

function silenceOf(ruleName: string): Silence | null {
  return silences.value.find((s) =>
    (s.state === 'active' || s.state === 'pending') &&
    s.matchers.some((m) => m.name === 'alertname' && m.value === ruleName && !m.is_regex)
  ) ?? null
}

function goToHost(hostId: number) {
  router.push(`/monitoring/hosts/${hostId}`)
}

function goToEvents(ruleName: string) {
  router.push({ path: '/monitoring/events', query: { keyword: ruleName } })
}

// ── 数据加载 ──
async function fetchStatus() {
  const [prom, am] = await Promise.allSettled([
    getPrometheusHealth(),
    getAlertManagerStatus(),
  ])
  promConnected.value = prom.status === 'fulfilled' ? !!(prom.value as any)?.data?.connected : false
  amConnected.value = am.status === 'fulfilled' ? !!(am.value as any)?.data?.connected : false
}

async function fetchRules() {
  const res: any = await getAlertManagerRules()
  rules.value = res?.data ?? []
}

async function fetchSilences() {
  if (amConnected.value !== true) {
    silences.value = []
    return
  }
  try {
    const res: any = await getAlertManagerSilences()
    silences.value = res?.data ?? []
  } catch {
    silences.value = []
  }
}

async function fetchHosts() {
  // 只查 firing/pending 规则的命中主机，inactive 不消耗 PromQL 查询
  const names = rules.value
    .filter((r) => r.state === 'firing' || r.state === 'pending')
    .map((r) => r.name)
  if (!names.length) {
    rulesHosts.value = {}
    return
  }
  hostsLoading.value = true
  try {
    const res: any = await getAlertManagerRulesHosts({ names })
    const data = res?.data ?? {}
    const next: Record<string, any[]> = {}
    names.forEach((n) => { next[n] = data[n] ?? [] })
    rulesHosts.value = next
  } catch {
    // 保留旧数据
  } finally {
    hostsLoading.value = false
  }
}

async function refreshAll(manual = false) {
  if (manual) loading.value = true
  try {
    await fetchStatus()
    if (promConnected.value === true) {
      await fetchRules()
      await Promise.all([fetchHosts(), fetchSilences()])
      lastUpdated.value = new Date().toLocaleTimeString('zh-CN', { hour12: false })
    } else {
      rules.value = []
      rulesHosts.value = {}
    }
  } catch {
    if (manual) ElMessage.error('刷新失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

// ── 静默操作 ──
async function handleSilence(ruleName: string, minutes: number, comment: string) {
  silenceBusy.value = true
  try {
    await createSilence({
      matchers: [{ name: 'alertname', value: ruleName }],
      duration_minutes: minutes,
      comment: comment || `规则 ${ruleName} 临时静默`,
      created_by: authStore.username || 'ops-platform',
    })
    ElMessage.success(`已静默 ${ruleName}（${minutes >= 60 ? `${minutes / 60}h` : `${minutes}m`}）`)
    await fetchSilences()
  } catch {
    ElMessage.error('静默创建失败')
  } finally {
    silenceBusy.value = false
  }
}

async function handleUnsilence(silenceId: string) {
  silenceBusy.value = true
  try {
    await deleteSilence(silenceId)
    ElMessage.success('已解除静默')
    await fetchSilences()
  } catch {
    ElMessage.error('解除静默失败')
  } finally {
    silenceBusy.value = false
  }
}

// ── 30s 自动刷新（页面不可见时暂停） ──
function startTimer() {
  stopTimer()
  refreshTimer = setInterval(() => {
    if (!document.hidden) void refreshAll()
  }, 30_000)
}

function stopTimer() {
  if (refreshTimer) clearInterval(refreshTimer)
  refreshTimer = undefined
}

onMounted(startTimer)
onActivated(() => { void refreshAll(); startTimer() })
onDeactivated(stopTimer)
onUnmounted(stopTimer)
</script>

<style scoped>
/* 与 mockups/alert-rules-v1.html 完全一致 */
.alert-rules-page{font-size:13px}
.page-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px}
.page-title{margin:0;font-size:20px;font-weight:700}
.header-right{display:flex;gap:8px;align-items:center}
.updated{font-size:12px;color:var(--text-muted)}
.conn-tag{font-size:12px;padding:2px 10px;border-radius:99px;border:1px solid}
.conn-ok{color:#15803d;border-color:#bbf7d0;background:#f0fdf4}
.conn-err{color:#b91c1c;border-color:#fecaca;background:#fef2f2}
.conn-checking{color:var(--text-secondary);border-color:var(--border-color);background:#f5f5f5}
.refresh-btn{border:1px solid var(--border-color);background:var(--surface-color);border-radius:6px;padding:4px 12px;font-size:12px;color:var(--text-secondary);cursor:pointer}
.refresh-btn:hover:not(:disabled){color:var(--primary-color);border-color:var(--primary-color)}
.refresh-btn:disabled{opacity:.5;cursor:not-allowed}

.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:16px}
.stat{background:var(--surface-color);border:1px solid var(--border-color);border-radius:8px;padding:14px 18px;cursor:pointer;transition:.15s;position:relative;overflow:hidden}
.stat:hover{border-color:#d0d0d0;box-shadow:0 2px 8px rgba(0,0,0,.04)}
.stat.active{border-color:var(--primary-color);box-shadow:0 0 0 1px var(--primary-color)}
.stat .num{font-size:26px;font-weight:700;line-height:1.2}
.stat .lbl{font-size:12px;color:var(--text-secondary)}
.stat .sub{font-size:11px;color:var(--text-muted);margin-top:2px}
.stat.s-firing .num{color:var(--danger-color)}
.stat.s-pending .num{color:var(--warning-color)}
.stat.s-err .num{color:var(--danger-color)}
.dot{display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--danger-color);margin-right:8px;animation:pulse 1.6s infinite}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(229,72,77,.4)}70%{box-shadow:0 0 0 8px rgba(229,72,77,0)}100%{box-shadow:0 0 0 0 rgba(229,72,77,0)}}

.am-banner{font-size:12px;color:#b45309;background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:9px 14px;margin-bottom:12px}

.card{background:var(--surface-color);border:1px solid var(--border-color);border-radius:8px;padding:16px 20px}
.toolbar{display:flex;gap:10px;margin-bottom:14px;flex-wrap:wrap}
.t-input,.t-select{border:1px solid var(--border-color);border-radius:6px;padding:6px 12px;font-size:13px;background:#fff;color:var(--text-primary);outline:none;height:auto;line-height:1.6}
.t-input{width:260px}
.t-select{color:var(--text-secondary)}
.t-input:focus,.t-select:focus{border-color:var(--primary-color)}
.spacer{flex:1}
.count-hint{font-size:12px;color:var(--text-muted);align-self:center}

.rules-area{min-height:120px;position:relative}
.loading-hint{text-align:center;color:var(--text-muted);font-size:13px;padding:32px 0}
.empty-state{text-align:center;padding:56px 20px}
.empty-icon{font-size:36px;margin-bottom:10px}
.empty-state h3{margin:0 0 8px;font-size:15px}
.empty-state p{margin:0;color:var(--text-secondary);font-size:13px}
.empty-rules{text-align:center;color:var(--text-muted);font-size:13px;padding:32px 0}

.group{margin-bottom:6px}
.group-head{display:flex;align-items:center;gap:10px;padding:8px 4px;cursor:pointer;user-select:none}
.group-head .arrow{color:var(--text-muted);font-size:11px;transition:transform .15s;width:14px}
.group.collapsed .group-head .arrow{transform:rotate(-90deg)}
.group-name{font-weight:600;font-size:13px}
.group-meta{font-size:12px;color:var(--text-muted)}
.group-firing{font-size:11px;color:var(--danger-color);background:#fef2f2;border-radius:99px;padding:1px 8px;font-weight:600}
.group-err{font-size:11px;color:#b45309;background:#fffbeb;border-radius:99px;padding:1px 8px;font-weight:600}
.group-body{padding-left:4px}
.group.collapsed .group-body{display:none}

@media(max-width:1100px){
  .stats{grid-template-columns:repeat(2,1fr)}
}
</style>
