<template>
  <div class="rule" :class="[`is-${rule.state}`, { open, 'is-err': isErr, 'is-silenced': silenced }]">
    <!-- 主行 -->
    <div class="rule-main" @click="$emit('toggle')">
      <div class="rname">
        <span v-if="silenced" class="mute-flag" title="已静默">🔕</span>
        <span class="rname-text">{{ rule.name }}</span>
        <span class="fname">{{ rule.file.split('/').pop() }}</span>
      </div>
      <span><span class="pill" :class="`pill-${rule.state}`">{{ rule.state }}</span></span>
      <span><span class="sev" :class="`sev-${severityKey}`">{{ severity }}</span></span>
      <div class="rpromql" :title="rule.query">{{ rule.query }}</div>
      <div class="rdur">{{ formatDuration(rule.duration) }}</div>
      <div class="hits" @click.stop>
        <template v-if="hits.length">
          <span
            v-for="hit in visibleHits"
            :key="hit.id"
            class="hit-tag"
            :class="{ 'firing-hit': rule.state === 'firing' }"
            :title="hit.ip"
            @click="$emit('navigate', hit.id)"
          >{{ hit.name }}<b v-if="hit.value">{{ hit.value }}</b></span>
          <span v-if="hits.length > 3" class="hit-more" @click="hitsExpanded = !hitsExpanded">
            {{ hitsExpanded ? '收起' : `+${hits.length - 3}` }}
          </span>
        </template>
        <span v-else-if="hostsLoading" class="hit-none">加载中…</span>
        <span v-else class="hit-none">无命中</span>
      </div>
      <div class="rhealth">
        <span v-if="rule.health === 'ok'" class="h-ok">OK</span>
        <span v-else-if="isErr" class="h-err">ERR</span>
        <span v-else class="h-other">{{ rule.health || '-' }}</span>
      </div>
      <span class="expand-btn">▼</span>
    </div>

    <!-- 展开详情 -->
    <div v-if="open" class="rule-detail">
      <div class="detail-grid">
        <div class="d-block">
          <div class="d-label">PromQL</div>
          <div class="d-promql">{{ rule.query }}<button class="copy-btn" @click="copyQuery">{{ copied ? '已复制' : '复制' }}</button></div>
          <div class="d-meta">
            <span>持续 <b>{{ formatDuration(rule.duration) }}</b></span>
            <span>评估耗时 <b :class="{ slow: isSlow }">{{ evalTimeLabel }}</b><span v-if="isSlow" class="slow-flag" title="评估耗时超过 1s，PromQL 可能过重，建议优化">🐢</span></span>
            <span>来源 <b>{{ rule.file.split('/').pop() }}</b></span>
          </div>
        </div>
        <div class="d-block">
          <div class="d-label">告警说明</div>
          <div class="d-anno">
            <b>{{ rule.annotations?.summary || rule.name }}</b>
            <template v-if="rule.annotations?.description"><br>{{ rule.annotations.description }}</template>
            <template v-else-if="!rule.annotations?.summary"><span class="hit-none">未配置 annotations</span></template>
          </div>
          <div v-if="isErr && rule.last_error" style="margin-top:10px">
            <div class="d-label">评估报错</div>
            <div class="d-err">{{ rule.last_error }}</div>
          </div>
        </div>
      </div>

      <!-- 正在触发的实例 -->
      <div v-if="firingAlerts.length" class="d-block" style="margin-top:12px">
        <div class="d-label">正在触发的实例（{{ firingAlerts.length }}）</div>
        <div class="firing-list">
          <div v-for="a in firingAlerts" :key="a.instance" class="firing-item">
            <span class="fi-host" @click="navigateInstance(a.instance)">{{ instanceHostName(a.instance) }}</span>
            <span class="fi-val">{{ formatValue(a.value) }}</span>
            <span class="fi-since">{{ activeSinceLabel(a.active_at) }}</span>
          </div>
        </div>
      </div>

      <!-- 静默 -->
      <div class="d-block" style="margin-top:12px">
        <div class="d-label">静默</div>
        <div v-if="silenced" class="silence-row">
          <span class="silence-info">🔕 已静默至 {{ silenceEndLabel }}（{{ silence?.created_by }}：{{ silence?.comment || '无备注' }}）</span>
          <button class="sbtn sbtn-danger" :disabled="silenceBusy" @click="silence && $emit('unsilence', silence.id)">解除静默</button>
        </div>
        <div v-else class="silence-row">
          <input v-model="silenceComment" class="sinput" type="text" placeholder="静默备注（可选）">
          <button class="sbtn" :disabled="!amConnected || silenceBusy" @click="silenceFor(60)">静默 1h</button>
          <button class="sbtn" :disabled="!amConnected || silenceBusy" @click="silenceFor(240)">4h</button>
          <button class="sbtn" :disabled="!amConnected || silenceBusy" @click="silenceFor(1440)">24h</button>
          <span v-if="!amConnected" class="hit-none">Alertmanager 未连接，静默不可用</span>
        </div>
      </div>

      <!-- 事件历史 -->
      <div class="d-block" style="margin-top:12px">
        <div class="d-label">近 7 天事件</div>
        <div v-if="eventsLoading" class="hit-none">加载中…</div>
        <template v-else-if="eventStats">
          <div class="event-chart">
            <div
              v-for="d in eventStats.daily"
              :key="d.date"
              class="bar"
              :class="{ zero: !d.count }"
              :style="{ height: barHeight(d.count) }"
              :title="`${d.date} · ${d.count} 次`"
            ></div>
            <span class="chart-total">共 {{ eventStats.total }} 次</span>
          </div>
          <div v-if="eventStats.recent.length" class="event-recent">
            <div v-for="e in eventStats.recent" :key="e.id" class="event-item">
              <span class="pill" :class="e.status === 'firing' ? 'pill-firing' : 'pill-inactive'">{{ e.status }}</span>
              <span class="ei-inst">{{ e.instance || '-' }}</span>
              <span v-if="e.alert_value" class="ei-val">{{ e.alert_value }}</span>
              <span class="ei-time">{{ formatTime(e.received_at) }}</span>
            </div>
          </div>
          <div v-else class="hit-none">近 7 天无事件记录</div>
          <button class="link-btn" @click="$emit('view-events', rule.name)">查看该规则全部事件 →</button>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { getRuleEvents } from '@/api/alertmanager'

export interface RuleAlert {
  state: string
  value: string
  active_at: string
  instance: string
}

export interface AlertRule {
  name: string
  query: string
  duration: number
  state: string
  labels: Record<string, string>
  annotations: Record<string, string>
  health: string
  last_error: string
  group_name: string
  file: string
  last_evaluation: string
  evaluation_time: number
  alerts: RuleAlert[]
}

export interface RuleHit {
  id: number
  name: string
  ip: string
  value?: string
}

export interface SilenceInfo {
  id: string
  state: string
  ends_at: string
  created_by: string
  comment: string
}

const props = defineProps<{
  rule: AlertRule
  open: boolean
  hits: RuleHit[]
  hostsLoading: boolean
  silence: SilenceInfo | null
  amConnected: boolean
  silenceBusy?: boolean
}>()

const emit = defineEmits<{
  toggle: []
  navigate: [hostId: number]
  silence: [minutes: number, comment: string]
  unsilence: [silenceId: string]
  'view-events': [ruleName: string]
}>()

const hitsExpanded = ref(false)
const copied = ref(false)
const silenceComment = ref('')
const eventsLoading = ref(false)
const eventStats = ref<any>(null)
let eventsLoadedFor = ''

const visibleHits = computed(() => (hitsExpanded.value ? props.hits : props.hits.slice(0, 3)))
const severity = computed(() => props.rule.labels?.severity || 'info')
const severityKey = computed(() => {
  const s = severity.value
  return s === 'critical' ? 'critical' : s === 'warning' || s === 'warn' ? 'warning' : 'info'
})
const isErr = computed(() => props.rule.health === 'err')
const silenced = computed(() => !!props.silence)
const isSlow = computed(() => (props.rule.evaluation_time || 0) > 1)
const evalTimeLabel = computed(() => {
  const t = props.rule.evaluation_time || 0
  return t >= 1 ? `${t.toFixed(2)}s` : `${Math.round(t * 1000)}ms`
})
const firingAlerts = computed(() => props.rule.alerts?.filter((a) => a.state === 'firing') ?? [])
const silenceEndLabel = computed(() => formatTime(props.silence?.ends_at || ''))

function formatDuration(seconds: number) {
  if (!seconds) return '-'
  if (seconds < 60) return `${seconds}s`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`
  return `${Math.floor(seconds / 3600)}h${Math.floor((seconds % 3600) / 60)}m`
}

function formatValue(raw: string) {
  const n = Number(raw)
  if (!Number.isFinite(n)) return raw
  const abs = Math.abs(n)
  const text = abs >= 100 ? n.toFixed(0) : abs >= 1 ? n.toFixed(1) : n.toFixed(2)
  return props.rule.query.includes('* 100') ? `${text}%` : text
}

function formatTime(iso: string) {
  if (!iso) return '-'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  const pad = (v: number) => String(v).padStart(2, '0')
  return `${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function activeSinceLabel(activeAt: string) {
  const start = new Date(activeAt).getTime()
  if (!Number.isFinite(start)) return ''
  const mins = Math.max(0, Math.round((Date.now() - start) / 60000))
  const span = mins < 60 ? `${mins} 分钟` : `${Math.floor(mins / 60)} 小时 ${mins % 60} 分钟`
  return `已持续 ${span} · 起始于 ${formatTime(activeAt)}`
}

function barHeight(count: number) {
  if (!count || !eventStats.value) return '3px'
  const max = Math.max(...eventStats.value.daily.map((d: any) => d.count), 1)
  return `${Math.max(12, Math.round((count / max) * 36))}px`
}

function copyQuery() {
  navigator.clipboard?.writeText(props.rule.query).then(() => {
    copied.value = true
    setTimeout(() => { copied.value = false }, 1500)
  })
}

function silenceFor(minutes: number) {
  emit('silence', minutes, silenceComment.value.trim())
  silenceComment.value = ''
}

function instanceHostName(instance: string) {
  const clean = instance.split(':')[0]
  const host = props.hits.find((h) => h.ip === clean || instance.includes(h.name))
  return host?.name || instance
}

function navigateInstance(instance: string) {
  const clean = instance.split(':')[0]
  const host = props.hits.find((h) => h.ip === clean || instance.includes(h.name))
  if (host) emit('navigate', host.id)
}

watch(() => [props.open, props.rule.name] as const, async ([open]) => {
  if (!open || eventsLoadedFor === props.rule.name) return
  eventsLoadedFor = props.rule.name
  eventsLoading.value = true
  try {
    const res: any = await getRuleEvents(props.rule.name)
    eventStats.value = res?.data ?? null
  } catch {
    eventStats.value = null
  } finally {
    eventsLoading.value = false
  }
}, { immediate: true })
</script>

<style scoped>
/* 与 mockups/alert-rules-v1.html 完全一致 */
.rule{border:1px solid var(--border-color);border-radius:8px;margin-bottom:8px;background:#fff;transition:.15s}
.rule:hover{border-color:#d5d5d5}
.rule.is-firing{border-left:3px solid var(--danger-color);background:linear-gradient(90deg,#fef5f5 0%,#fff 30%)}
.rule.is-pending{border-left:3px solid var(--warning-color)}
.rule.is-err{opacity:.92}
.rule.is-silenced{opacity:.75}
.rule-main{display:grid;grid-template-columns:minmax(200px,1.4fr) 90px 90px minmax(220px,1.6fr) 80px minmax(180px,1.2fr) 70px 32px;gap:12px;align-items:center;padding:10px 16px;cursor:pointer}
.rname{font-weight:600;font-size:13px;display:flex;align-items:center;gap:6px;min-width:0}
.rname-text{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.mute-flag{font-size:12px;flex-shrink:0}
.fname{display:block;font-size:11px;color:var(--text-muted);font-weight:400;margin-left:auto;flex-shrink:0;max-width:45%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.pill{font-size:11px;padding:2px 10px;border-radius:99px;text-align:center;font-weight:600;display:inline-block}
.pill-firing{color:#fff;background:var(--danger-color)}
.pill-pending{color:#fff;background:var(--warning-color)}
.pill-inactive{color:var(--text-secondary);background:#f0f0f0}
.sev{font-size:11px;padding:2px 8px;border-radius:4px;display:inline-block}
.sev-critical{color:#b91c1c;background:#fef2f2;border:1px solid #fecaca}
.sev-warning{color:#b45309;background:#fffbeb;border:1px solid #fde68a}
.sev-info{color:#1d4ed8;background:#eff6ff;border:1px solid #bfdbfe}
.rpromql{font-family:'JetBrains Mono',ui-monospace,Menlo,Consolas,monospace;font-size:11px;color:var(--text-secondary);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.rdur{font-size:12px;color:var(--text-secondary)}
.hits{display:flex;flex-wrap:wrap;gap:4px;align-items:center}
.hit-tag{font-size:11px;padding:1px 8px;border-radius:4px;background:var(--primary-bg);color:var(--primary-color);cursor:pointer;border:1px solid transparent}
.hit-tag:hover{border-color:var(--primary-color)}
.hit-tag b{font-weight:600;margin-left:4px}
.hit-tag.firing-hit{background:#fef2f2;color:#b91c1c}
.hit-tag.firing-hit:hover{border-color:var(--danger-color)}
.hit-more{font-size:11px;color:var(--text-muted);cursor:pointer;align-self:center}
.hit-none{font-size:12px;color:var(--text-muted)}
.h-ok{color:var(--success-color);font-size:12px}
.h-err{color:var(--danger-color);font-size:12px;font-weight:600}
.h-other{color:var(--text-muted);font-size:12px}
.expand-btn{color:var(--text-muted);font-size:12px;text-align:center;transition:transform .15s}
.rule.open .expand-btn{transform:rotate(180deg)}

.rule-detail{border-top:1px dashed var(--border-color);padding:14px 16px;background:#fcfcfd;border-radius:0 0 8px 8px}
.detail-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.d-label{font-size:11px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.4px;margin-bottom:5px}
.d-promql{font-family:'JetBrains Mono',ui-monospace,Menlo,Consolas,monospace;font-size:11.5px;background:#f6f7fb;border:1px solid var(--border-color);border-radius:6px;padding:10px 12px;white-space:pre-wrap;word-break:break-all;color:#333;position:relative}
.copy-btn{position:absolute;top:6px;right:6px;font-size:11px;color:var(--text-muted);border:1px solid var(--border-color);background:#fff;border-radius:4px;padding:1px 8px;cursor:pointer}
.copy-btn:hover{color:var(--primary-color);border-color:var(--primary-color)}
.d-anno{font-size:12px;color:var(--text-secondary)}
.d-anno b{color:var(--text-primary);font-weight:600}
.d-err{font-family:'JetBrains Mono',ui-monospace,Menlo,Consolas,monospace;font-size:11.5px;background:#fef2f2;border:1px solid #fecaca;color:#b91c1c;border-radius:6px;padding:10px 12px;white-space:pre-wrap;word-break:break-all}
.d-meta{display:flex;gap:18px;font-size:12px;color:var(--text-secondary);flex-wrap:wrap;margin-top:10px}
.d-meta span b{color:var(--text-primary);font-weight:600}
.d-meta b.slow{color:var(--warning-color)}
.slow-flag{cursor:default;margin-left:2px}
.firing-list{margin-top:4px}
.firing-item{display:flex;align-items:center;gap:10px;font-size:12px;padding:5px 0;border-bottom:1px solid #f3f3f3}
.firing-item:last-child{border-bottom:none}
.fi-host{font-weight:600;color:var(--primary-color);cursor:pointer}
.fi-val{font-family:'JetBrains Mono',ui-monospace,Menlo,Consolas,monospace;color:var(--danger-color);font-weight:700}
.fi-since{color:var(--text-muted)}
.silence-row{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.silence-info{font-size:12px;color:var(--text-secondary)}
.sinput{border:1px solid var(--border-color);border-radius:6px;padding:5px 12px;font-size:12px;background:#fff;color:var(--text-primary);outline:none;width:220px}
.sinput:focus{border-color:var(--primary-color)}
.sbtn{border:1px solid var(--border-color);background:#fff;border-radius:6px;padding:5px 12px;font-size:12px;color:var(--text-secondary);cursor:pointer}
.sbtn:hover:not(:disabled){color:var(--primary-color);border-color:var(--primary-color)}
.sbtn:disabled{opacity:.5;cursor:not-allowed}
.sbtn-danger{color:var(--danger-color)}
.sbtn-danger:hover:not(:disabled){color:var(--danger-color);border-color:var(--danger-color)}
.event-chart{display:flex;align-items:flex-end;gap:5px;height:40px;margin-bottom:8px}
.event-chart .bar{width:18px;background:var(--primary-color);border-radius:3px 3px 0 0;opacity:.85}
.event-chart .bar.zero{background:#eee}
.chart-total{font-size:11px;color:var(--text-muted);align-self:center;margin-left:8px}
.event-recent{margin-bottom:6px}
.event-item{display:flex;align-items:center;gap:10px;font-size:12px;padding:4px 0;border-bottom:1px solid #f3f3f3}
.event-item:last-child{border-bottom:none}
.ei-inst{color:var(--text-secondary)}
.ei-val{font-family:'JetBrains Mono',ui-monospace,Menlo,Consolas,monospace;color:var(--danger-color)}
.ei-time{color:var(--text-muted);margin-left:auto}
.link-btn{font-size:12px;color:var(--primary-color);background:none;border:none;cursor:pointer;padding:0;margin-top:4px}
.link-btn:hover{text-decoration:underline}
@media(max-width:1100px){
  .rule-main{grid-template-columns:1fr 80px 80px;grid-auto-rows:auto}
  .rpromql,.rdur,.hits,.rhealth{display:none}
  .detail-grid{grid-template-columns:1fr}
}
</style>
