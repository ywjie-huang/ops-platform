# Host Detail Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the host monitoring detail page into an A+C hybrid: a single-host troubleshooting command view with current judgment, compact metrics, recommended actions, trend placeholders, event placeholders, and lighter steady-state details.

**Architecture:** Keep the first implementation frontend-only and reuse the existing `getHostDetail` API. Move host-detail risk, metric, recommendation, trend-placeholder, and display formatting logic into a focused utility module with Node tests, then rebuild `HostDetailView.vue` around those derived view models. Leave real historical metric/event APIs for a later backend plan while rendering stable placeholders now.

**Tech Stack:** Vue 3 `<script setup>`, TypeScript, Element Plus, existing CSS custom properties, Node `node:test`, Vite/Vue build.

---

## Scope

This plan implements the first phase from `docs/superpowers/specs/2026-06-29-host-detail-optimization-design.md`: frontend structure optimization using current host-detail data.

Included:

- Top identity bar with risk state, collection state, host metadata, refresh time, copy IP, and SSH.
- Current judgment area with compact metric cards for CPU, memory, disk, and Load.
- Recommendation panel generated from current metrics.
- Trend section with graceful "暂无历史趋势" placeholders.
- Event/relations panel with clear placeholder state for future data.
- Lighter steady-state details replacing heavy bordered descriptions.
- Loading, API error, Prometheus unavailable, and partial metric missing states.
- Responsive layout.

Excluded:

- Backend trend API.
- Backend event aggregation.
- Real relation counts.
- Ticket creation and copy troubleshooting summary.
- Auto-refresh on the detail page.

## File Structure

- Create `frontend/src/utils/hostDetail.ts`
  - Owns pure view-model logic for the detail page.
  - Derives risk status, collection state, metric cards, current judgment, recommendations, placeholder trend cards, relation cards, uptime formatting, and key-value rows.
  - Exposes small functions that are easy to test and reuse.

- Create `frontend/src/utils/hostDetail.test.mjs`
  - Node tests for risk derivation, metric cards, recommendations, Prometheus unavailable handling, missing metric handling, and uptime formatting.

- Modify `frontend/src/views/monitoring/HostDetailView.vue`
  - Replaces the current circular metric/detail-grid page with the command-view layout.
  - Keeps `onActivated(fetchDetail)` as the data loading pattern.
  - Imports the new host-detail utility functions.
  - Uses existing Element Plus controls and project design tokens.

- Optional modify `frontend/src/api/monitoring.ts`
  - Only if TypeScript build requires narrower optional fields. Keep API shape backward-compatible.

## Task 1: Create Host Detail View-Model Tests

**Files:**

- Create: `frontend/src/utils/hostDetail.test.mjs`
- Create later in Task 2: `frontend/src/utils/hostDetail.ts`

- [ ] **Step 1: Add failing tests for derived host-detail state**

Create `frontend/src/utils/hostDetail.test.mjs` with:

```js
import assert from 'node:assert/strict'
import test from 'node:test'

const {
  buildCollectionState,
  buildCurrentJudgment,
  buildHostMetricCards,
  buildHostRecommendations,
  buildRelationCards,
  buildTrendCards,
  formatHostUptime,
  getHostRiskMeta,
} = await import('./hostDetail.ts')

const healthyHost = {
  id: 1,
  hostname: 'prod-api-01',
  ip: '10.12.3.21',
  owner: '张三',
  status: '使用中',
  uptime_hours: 53,
  prometheus_ok: true,
  cpu: { usage: 42, cores: 8 },
  memory: { usage: 58, total_gb: 16, used_gb: 9.3, available_gb: 6.7 },
  disk: { usage: 52, total_gb: 200, read_mb_s: 12, write_mb_s: 6 },
  network: { in_mbps: 42, out_mbps: 18 },
  load: { '1m': 1.8, '5m': 1.4, '15m': 1.2 },
  tcp_connections: 219,
  processes: { running: 128 },
}

test('classifies healthy, warning, critical, and offline host states', () => {
  assert.deepEqual(getHostRiskMeta(healthyHost), {
    key: 'healthy',
    label: '正常',
    tone: 'success',
    priority: '观察',
  })

  assert.deepEqual(getHostRiskMeta({
    ...healthyHost,
    memory: { ...healthyHost.memory, usage: 78 },
  }), {
    key: 'warning',
    label: '关注',
    tone: 'warning',
    priority: '观察中',
  })

  assert.deepEqual(getHostRiskMeta({
    ...healthyHost,
    cpu: { ...healthyHost.cpu, usage: 94 },
    load: { '1m': 11.2, '5m': 9.8, '15m': 7.4 },
  }), {
    key: 'critical',
    label: '高风险',
    tone: 'danger',
    priority: '需处理',
  })

  assert.deepEqual(getHostRiskMeta({
    ...healthyHost,
    prometheus_ok: false,
  }), {
    key: 'offline',
    label: '采集异常',
    tone: 'muted',
    priority: '需确认',
  })
})

test('builds compact metric cards with load judged against CPU cores', () => {
  const cards = buildHostMetricCards({
    ...healthyHost,
    cpu: { usage: 94, cores: 8 },
    memory: { ...healthyHost.memory, usage: 78 },
    disk: { ...healthyHost.disk, usage: 52 },
    load: { '1m': 11.2, '5m': 9.8, '15m': 7.4 },
  })

  assert.deepEqual(cards.map((card) => ({
    key: card.key,
    label: card.label,
    value: card.value,
    unit: card.unit,
    tone: card.tone,
    statusText: card.statusText,
  })), [
    { key: 'cpu', label: 'CPU', value: 94, unit: '%', tone: 'danger', statusText: '高风险' },
    { key: 'memory', label: '内存', value: 78, unit: '%', tone: 'warning', statusText: '偏高' },
    { key: 'disk', label: '磁盘', value: 52, unit: '%', tone: 'success', statusText: '正常' },
    { key: 'load', label: 'Load', value: 11.2, unit: '', tone: 'danger', statusText: '超过核心数' },
  ])

  assert.equal(cards[3].detail, '1m 11.2 / 8 核')
  assert.equal(cards[3].barPercent, 100)
})

test('summarizes the highest-priority problem and recommendations', () => {
  const host = {
    ...healthyHost,
    cpu: { usage: 94, cores: 8 },
    load: { '1m': 11.2, '5m': 9.8, '15m': 7.4 },
  }

  assert.deepEqual(buildCurrentJudgment(host), {
    title: 'CPU 持续高位，Load 已超过核心数',
    description: '建议优先进入 SSH 查看高 CPU 进程，并核对近期发布或批量任务。',
    tone: 'danger',
  })

  assert.deepEqual(buildHostRecommendations(host).map((item) => ({
    key: item.key,
    title: item.title,
    action: item.action,
  })), [
    { key: 'ssh-cpu', title: 'SSH 查看高 CPU 进程', action: 'ssh' },
    { key: 'check-change', title: '核对最近发布或批量任务', action: 'inspect' },
    { key: 'notify-owner', title: '同步负责人', action: 'copy' },
  ])
})

test('handles Prometheus unavailable without hiding host identity', () => {
  const host = {
    ...healthyHost,
    prometheus_ok: false,
    cpu: undefined,
    memory: undefined,
    disk: undefined,
    load: undefined,
  }

  assert.deepEqual(buildCollectionState(host), {
    label: 'Prometheus 未连接',
    tone: 'danger',
    description: '主机档案可查看，实时指标暂不可用',
  })

  assert.deepEqual(buildCurrentJudgment(host), {
    title: '采集异常，实时指标不可用',
    description: '请先确认 Prometheus、node_exporter 或网络连通性，再判断主机负载。',
    tone: 'muted',
  })

  assert.equal(buildHostMetricCards(host).every((card) => card.isMissing), true)
})

test('provides stable trend and relation placeholders for phase one', () => {
  assert.deepEqual(buildTrendCards(healthyHost).map((card) => ({
    key: card.key,
    label: card.label,
    state: card.state,
  })), [
    { key: 'cpu', label: 'CPU 趋势', state: '暂无历史趋势' },
    { key: 'load', label: 'Load 趋势', state: '暂无历史趋势' },
    { key: 'memory', label: '内存趋势', state: '暂无历史趋势' },
    { key: 'network', label: '网络趋势', state: '暂无历史趋势' },
  ])

  assert.deepEqual(buildRelationCards(healthyHost).map((card) => ({
    key: card.key,
    label: card.label,
    value: card.value,
  })), [
    { key: 'alerts', label: '相关告警', value: '待接入' },
    { key: 'containers', label: '容器', value: '待接入' },
    { key: 'deploys', label: '最近部署', value: '待接入' },
    { key: 'patrols', label: '巡检记录', value: '待接入' },
  ])
})

test('formats uptime in compact Chinese text', () => {
  assert.equal(formatHostUptime(0), '-')
  assert.equal(formatHostUptime(8), '8 小时')
  assert.equal(formatHostUptime(53), '2 天 5 小时')
})
```

- [ ] **Step 2: Run the test and verify it fails because the module does not exist**

Run:

```bash
cd frontend
node --test src/utils/hostDetail.test.mjs
```

Expected:

```text
not ok ... Cannot find module ... hostDetail.ts
```

- [ ] **Step 3: Commit the failing test**

```bash
git add frontend/src/utils/hostDetail.test.mjs
git commit -m "test: add host detail view model coverage"
```

## Task 2: Implement Host Detail View-Model Utilities

**Files:**

- Create: `frontend/src/utils/hostDetail.ts`
- Test: `frontend/src/utils/hostDetail.test.mjs`

- [ ] **Step 1: Implement the utility module**

Create `frontend/src/utils/hostDetail.ts` with:

```ts
type Tone = 'success' | 'warning' | 'danger' | 'muted'
type RiskKey = 'healthy' | 'warning' | 'critical' | 'offline'
type MetricKey = 'cpu' | 'memory' | 'disk' | 'load'

export type HostDetailLike = {
  id?: number
  hostname?: string
  ip?: string
  spec?: string
  os_info?: string
  owner?: string
  status?: string
  uptime_hours?: number
  prometheus_ok?: boolean
  tcp_connections?: number
  cpu?: { usage?: number; cores?: number }
  memory?: { usage?: number; total_gb?: number; used_gb?: number; available_gb?: number }
  disk?: { usage?: number; total_gb?: number; read_mb_s?: number; write_mb_s?: number }
  network?: { in_mbps?: number; out_mbps?: number }
  load?: { '1m'?: number; '5m'?: number; '15m'?: number }
  processes?: { running?: number }
}

export type HostRiskMeta = {
  key: RiskKey
  label: string
  tone: Tone
  priority: string
}

export type HostMetricCard = {
  key: MetricKey
  label: string
  value: number | null
  unit: string
  detail: string
  tone: Tone
  statusText: string
  barPercent: number
  isMissing: boolean
}

export type HostRecommendation = {
  key: string
  title: string
  description: string
  action: 'ssh' | 'inspect' | 'copy'
  tone: Tone
}

function metricTone(value: number | undefined): Tone {
  if (value == null) return 'muted'
  if (value > 90) return 'danger'
  if (value > 70) return 'warning'
  return 'success'
}

function metricStatusText(value: number | undefined): string {
  if (value == null) return '无数据'
  if (value > 90) return '高风险'
  if (value > 70) return '偏高'
  return '正常'
}

function roundMetric(value: number | undefined, digits = 0): number | null {
  if (value == null || Number.isNaN(value)) return null
  const factor = 10 ** digits
  return Math.round(value * factor) / factor
}

function maxMetric(host: HostDetailLike): number {
  return Math.max(
    host.cpu?.usage || 0,
    host.memory?.usage || 0,
    host.disk?.usage || 0,
  )
}

function loadRatio(host: HostDetailLike): number {
  const load1 = host.load?.['1m'] || 0
  const cores = host.cpu?.cores || 0
  if (!cores) return 0
  return load1 / cores
}

function loadTone(host: HostDetailLike): Tone {
  const ratio = loadRatio(host)
  if (ratio >= 1) return 'danger'
  if (ratio >= 0.75) return 'warning'
  return 'success'
}

export function getHostRiskMeta(host: HostDetailLike): HostRiskMeta {
  if (!host.prometheus_ok) {
    return { key: 'offline', label: '采集异常', tone: 'muted', priority: '需确认' }
  }

  if (maxMetric(host) > 90 || loadRatio(host) >= 1) {
    return { key: 'critical', label: '高风险', tone: 'danger', priority: '需处理' }
  }

  if (maxMetric(host) > 70 || loadRatio(host) >= 0.75) {
    return { key: 'warning', label: '关注', tone: 'warning', priority: '观察中' }
  }

  return { key: 'healthy', label: '正常', tone: 'success', priority: '观察' }
}

export function buildCollectionState(host: HostDetailLike) {
  if (host.prometheus_ok) {
    return {
      label: 'Prometheus 已连接',
      tone: 'success' as Tone,
      description: '实时指标采集正常',
    }
  }

  return {
    label: 'Prometheus 未连接',
    tone: 'danger' as Tone,
    description: '主机档案可查看，实时指标暂不可用',
  }
}

export function buildHostMetricCards(host: HostDetailLike): HostMetricCard[] {
  const cpuUsage = roundMetric(host.cpu?.usage)
  const memoryUsage = roundMetric(host.memory?.usage)
  const diskUsage = roundMetric(host.disk?.usage)
  const load1 = roundMetric(host.load?.['1m'], 1)
  const cores = host.cpu?.cores || 0
  const loadStateTone = host.load?.['1m'] == null ? 'muted' : loadTone(host)
  const loadStatusText = host.load?.['1m'] == null
    ? '无数据'
    : loadStateTone === 'danger'
      ? '超过核心数'
      : loadStateTone === 'warning'
        ? '接近核心数'
        : '正常'

  return [
    {
      key: 'cpu',
      label: 'CPU',
      value: cpuUsage,
      unit: '%',
      detail: cores ? `${cores} 核` : '核心数未知',
      tone: metricTone(host.cpu?.usage),
      statusText: metricStatusText(host.cpu?.usage),
      barPercent: cpuUsage || 0,
      isMissing: cpuUsage == null,
    },
    {
      key: 'memory',
      label: '内存',
      value: memoryUsage,
      unit: '%',
      detail: host.memory?.total_gb ? `${host.memory.used_gb || 0}/${host.memory.total_gb} GB` : '容量未知',
      tone: metricTone(host.memory?.usage),
      statusText: metricStatusText(host.memory?.usage),
      barPercent: memoryUsage || 0,
      isMissing: memoryUsage == null,
    },
    {
      key: 'disk',
      label: '磁盘',
      value: diskUsage,
      unit: '%',
      detail: host.disk?.total_gb ? `${host.disk.total_gb} GB` : '容量未知',
      tone: metricTone(host.disk?.usage),
      statusText: metricStatusText(host.disk?.usage),
      barPercent: diskUsage || 0,
      isMissing: diskUsage == null,
    },
    {
      key: 'load',
      label: 'Load',
      value: load1,
      unit: '',
      detail: load1 == null ? '1m 无数据' : `1m ${load1} / ${cores || '-'} 核`,
      tone: loadStateTone,
      statusText: loadStatusText,
      barPercent: Math.min(Math.round(loadRatio(host) * 100), 100),
      isMissing: load1 == null,
    },
  ]
}

export function buildCurrentJudgment(host: HostDetailLike) {
  if (!host.prometheus_ok) {
    return {
      title: '采集异常，实时指标不可用',
      description: '请先确认 Prometheus、node_exporter 或网络连通性，再判断主机负载。',
      tone: 'muted' as Tone,
    }
  }

  const cards = buildHostMetricCards(host)
  const highest = [...cards]
    .filter((card) => !card.isMissing)
    .sort((a, b) => {
      const toneWeight: Record<Tone, number> = { danger: 3, warning: 2, success: 1, muted: 0 }
      return toneWeight[b.tone] - toneWeight[a.tone] || (b.barPercent - a.barPercent)
    })[0]

  if (!highest) {
    return {
      title: '指标数据缺失',
      description: '主机档案可查看，但当前没有足够实时指标用于判断。',
      tone: 'muted' as Tone,
    }
  }

  if (highest.key === 'cpu' && highest.tone === 'danger' && loadTone(host) === 'danger') {
    return {
      title: 'CPU 持续高位，Load 已超过核心数',
      description: '建议优先进入 SSH 查看高 CPU 进程，并核对近期发布或批量任务。',
      tone: 'danger' as Tone,
    }
  }

  if (highest.tone === 'danger') {
    return {
      title: `${highest.label} 已达到高风险阈值`,
      description: '建议优先确认异常指标来源，并根据主机角色选择 SSH 或关联记录排查。',
      tone: 'danger' as Tone,
    }
  }

  if (highest.tone === 'warning') {
    return {
      title: `${highest.label} 偏高，建议持续观察`,
      description: '当前未达到高风险阈值，可结合趋势和最近事件确认是否继续恶化。',
      tone: 'warning' as Tone,
    }
  }

  return {
    title: '主机运行平稳',
    description: '核心指标处于正常范围，可继续观察趋势和关联事件。',
    tone: 'success' as Tone,
  }
}

export function buildHostRecommendations(host: HostDetailLike): HostRecommendation[] {
  if (!host.prometheus_ok) {
    return [
      {
        key: 'check-collector',
        title: '确认采集链路',
        description: '检查 Prometheus、node_exporter 和主机网络连通性。',
        action: 'inspect',
        tone: 'danger',
      },
      {
        key: 'ssh-connectivity',
        title: 'SSH 验证主机状态',
        description: '如 SSH 可达，可先确认主机是否在线。',
        action: 'ssh',
        tone: 'muted',
      },
      {
        key: 'notify-owner',
        title: '同步负责人',
        description: host.owner ? `负责人：${host.owner}` : '负责人未配置，请补充责任人。',
        action: 'copy',
        tone: 'muted',
      },
    ]
  }

  const cards = buildHostMetricCards(host)
  const hasCpuPressure = (host.cpu?.usage || 0) > 90 || loadTone(host) === 'danger'
  const hasDiskPressure = (host.disk?.usage || 0) > 90
  const primaryTitle = hasCpuPressure
    ? 'SSH 查看高 CPU 进程'
    : hasDiskPressure
      ? '确认磁盘空间和写入来源'
      : 'SSH 查看主机现场'

  return [
    {
      key: hasCpuPressure ? 'ssh-cpu' : hasDiskPressure ? 'check-disk' : 'ssh-general',
      title: primaryTitle,
      description: hasCpuPressure ? '建议执行 top、ps 或 systemctl 查看异常进程。' : '进入主机确认服务和资源状态。',
      action: 'ssh',
      tone: hasCpuPressure || hasDiskPressure ? 'danger' : 'success',
    },
    {
      key: 'check-change',
      title: '核对最近发布或批量任务',
      description: '确认异常是否与部署、巡检或批量执行时间重合。',
      action: 'inspect',
      tone: cards.some((card) => card.tone === 'danger') ? 'warning' : 'muted',
    },
    {
      key: 'notify-owner',
      title: '同步负责人',
      description: host.owner ? `负责人：${host.owner}` : '负责人未配置，请补充责任人。',
      action: 'copy',
      tone: 'muted',
    },
  ]
}

export function buildTrendCards(_host: HostDetailLike) {
  return [
    { key: 'cpu', label: 'CPU 趋势', state: '暂无历史趋势' },
    { key: 'load', label: 'Load 趋势', state: '暂无历史趋势' },
    { key: 'memory', label: '内存趋势', state: '暂无历史趋势' },
    { key: 'network', label: '网络趋势', state: '暂无历史趋势' },
  ]
}

export function buildRelationCards(_host: HostDetailLike) {
  return [
    { key: 'alerts', label: '相关告警', value: '待接入' },
    { key: 'containers', label: '容器', value: '待接入' },
    { key: 'deploys', label: '最近部署', value: '待接入' },
    { key: 'patrols', label: '巡检记录', value: '待接入' },
  ]
}

export function formatHostUptime(hours: number | undefined) {
  if (!hours) return '-'
  if (hours < 24) return `${hours} 小时`
  const days = Math.floor(hours / 24)
  const restHours = hours % 24
  return restHours ? `${days} 天 ${restHours} 小时` : `${days} 天`
}

export function buildSteadyDetailGroups(host: HostDetailLike) {
  return [
    {
      key: 'system',
      title: '系统信息',
      rows: [
        { label: '规格', value: host.spec || '-' },
        { label: '系统', value: host.os_info || '-' },
        { label: '运行时间', value: formatHostUptime(host.uptime_hours) },
        { label: '运行进程', value: host.processes?.running ?? '-' },
      ],
    },
    {
      key: 'network',
      title: '网络',
      rows: [
        { label: '入站', value: `${host.network?.in_mbps ?? 0} Mbps` },
        { label: '出站', value: `${host.network?.out_mbps ?? 0} Mbps` },
        { label: 'TCP 连接', value: host.tcp_connections ?? '-' },
      ],
    },
    {
      key: 'diskIo',
      title: '磁盘 IO',
      rows: [
        { label: '容量', value: host.disk?.total_gb ? `${host.disk.total_gb} GB` : '-' },
        { label: '读速率', value: `${host.disk?.read_mb_s ?? 0} MB/s` },
        { label: '写速率', value: `${host.disk?.write_mb_s ?? 0} MB/s` },
      ],
    },
  ]
}
```

- [ ] **Step 2: Run the unit tests**

Run:

```bash
cd frontend
node --test src/utils/hostDetail.test.mjs
```

Expected:

```text
ok ...
```

- [ ] **Step 3: Commit utility implementation**

```bash
git add frontend/src/utils/hostDetail.ts frontend/src/utils/hostDetail.test.mjs
git commit -m "feat(monitoring): derive host detail view state"
```

## Task 3: Rebuild HostDetailView Layout

**Files:**

- Modify: `frontend/src/views/monitoring/HostDetailView.vue`
- Uses: `frontend/src/utils/hostDetail.ts`
- Test: `frontend/src/utils/hostDetail.test.mjs`

- [ ] **Step 1: Replace script logic with derived view models**

In `frontend/src/views/monitoring/HostDetailView.vue`, update the `<script setup lang="ts">` block to:

```ts
import { computed, ref, onActivated } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  ArrowLeft,
  Connection,
  CopyDocument,
  DataLine,
  Monitor,
  Odometer,
  Refresh,
  WarningFilled,
} from '@element-plus/icons-vue'
import { getHostDetail } from '@/api/monitoring'
import type { HostDetail } from '@/api/monitoring'
import {
  buildCollectionState,
  buildCurrentJudgment,
  buildHostMetricCards,
  buildHostRecommendations,
  buildRelationCards,
  buildSteadyDetailGroups,
  buildTrendCards,
  getHostRiskMeta,
} from '@/utils/hostDetail'

const route = useRoute()
const router = useRouter()
const host = ref<HostDetail | null>(null)
const loading = ref(false)
const loadError = ref('')
const lastRefreshTime = ref('')

const riskMeta = computed(() => host.value ? getHostRiskMeta(host.value) : null)
const collectionState = computed(() => host.value ? buildCollectionState(host.value) : null)
const currentJudgment = computed(() => host.value ? buildCurrentJudgment(host.value) : null)
const metricCards = computed(() => host.value ? buildHostMetricCards(host.value) : [])
const recommendations = computed(() => host.value ? buildHostRecommendations(host.value) : [])
const trendCards = computed(() => host.value ? buildTrendCards(host.value) : [])
const relationCards = computed(() => host.value ? buildRelationCards(host.value) : [])
const steadyDetailGroups = computed(() => host.value ? buildSteadyDetailGroups(host.value) : [])

function formatTime(date: Date) {
  return `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}:${date.getSeconds().toString().padStart(2, '0')}`
}

function goSsh() {
  router.push(`/monitoring/hosts/${route.params.id}/ssh`)
}

async function copyIp() {
  if (!host.value?.ip) return
  try {
    await navigator.clipboard.writeText(host.value.ip)
    ElMessage.success('IP 已复制')
  } catch {
    ElMessage.warning('复制失败，请手动复制 IP')
  }
}

function handleRecommendation(action: string) {
  if (action === 'ssh') {
    goSsh()
    return
  }
  if (action === 'copy') {
    copyIp()
  }
}

async function fetchDetail() {
  loading.value = true
  loadError.value = ''
  host.value = null
  try {
    const res: any = await getHostDetail(Number(route.params.id))
    host.value = res.data
    lastRefreshTime.value = formatTime(new Date())
  } catch (e: any) {
    loadError.value = e?.message || '加载主机详情失败，请检查网络或稍后重试'
  } finally {
    loading.value = false
  }
}

onActivated(fetchDetail)
```

- [ ] **Step 2: Replace the template with the command-view structure**

Replace the `<template>` in `HostDetailView.vue` with:

```vue
<template>
  <div class="host-detail">
    <header class="detail-header">
      <div class="identity-block">
        <el-button text class="back-btn" aria-label="返回上一页" @click="$router.back()">
          <el-icon><ArrowLeft /></el-icon>
          <span>返回</span>
        </el-button>
        <div v-if="host" class="identity-main">
          <div class="title-row">
            <h2 class="page-title">{{ host.hostname }}</h2>
            <span v-if="riskMeta" class="state-chip" :class="`tone-${riskMeta.tone}`">{{ riskMeta.label }}</span>
            <span v-if="collectionState" class="state-chip" :class="`tone-${collectionState.tone}`">{{ collectionState.label }}</span>
          </div>
          <p class="host-meta">
            <span>{{ host.ip }}</span>
            <span>{{ host.owner || '未分配负责人' }}</span>
            <span>{{ host.status || '状态未知' }}</span>
            <span v-if="lastRefreshTime">最近刷新 {{ lastRefreshTime }}</span>
          </p>
        </div>
        <div v-else class="identity-main">
          <h2 class="page-title">主机详情</h2>
          <p class="host-meta">正在加载主机信息</p>
        </div>
      </div>
      <div class="header-actions">
        <el-button :loading="loading" @click="fetchDetail">
          <el-icon><Refresh /></el-icon>
          <span>刷新</span>
        </el-button>
        <el-button :disabled="!host?.ip" @click="copyIp">
          <el-icon><CopyDocument /></el-icon>
          <span>复制 IP</span>
        </el-button>
        <el-button type="primary" :disabled="!host" @click="goSsh">
          <el-icon><Monitor /></el-icon>
          <span>SSH 连接</span>
        </el-button>
      </div>
    </header>

    <div v-if="loadError" class="error-state">
      <el-icon :size="48" class="error-icon"><WarningFilled /></el-icon>
      <p class="error-text">{{ loadError }}</p>
      <el-button type="primary" @click="fetchDetail">重新加载</el-button>
    </div>

    <div v-else-if="loading" class="detail-content">
      <div class="hero-grid">
        <section class="panel judgment-panel">
          <el-skeleton :rows="6" animated />
        </section>
        <aside class="panel action-panel">
          <el-skeleton :rows="5" animated />
        </aside>
      </div>
      <div class="diagnostic-grid">
        <section class="panel">
          <el-skeleton :rows="8" animated />
        </section>
        <aside class="panel">
          <el-skeleton :rows="8" animated />
        </aside>
      </div>
    </div>

    <div v-else-if="host" class="detail-content">
      <section v-if="collectionState && !host.prometheus_ok" class="collection-warning" role="status">
        <el-icon><WarningFilled /></el-icon>
        <div>
          <strong>{{ collectionState.label }}</strong>
          <p>{{ collectionState.description }}</p>
        </div>
      </section>

      <div class="hero-grid">
        <section class="panel judgment-panel" :class="currentJudgment ? `tone-${currentJudgment.tone}` : ''">
          <div class="panel-heading">
            <div>
              <span class="section-kicker">当前判断</span>
              <h3>{{ currentJudgment?.title }}</h3>
            </div>
            <span v-if="riskMeta" class="priority-pill" :class="`tone-${riskMeta.tone}`">{{ riskMeta.priority }}</span>
          </div>
          <p class="judgment-copy">{{ currentJudgment?.description }}</p>

          <div class="metric-grid" role="group" aria-label="主机关键指标">
            <article v-for="card in metricCards" :key="card.key" class="metric-card" :class="`tone-${card.tone}`">
              <div class="metric-card-head">
                <span>{{ card.label }}</span>
                <strong>{{ card.statusText }}</strong>
              </div>
              <div class="metric-value">
                <span>{{ card.value ?? '-' }}</span>
                <small>{{ card.unit }}</small>
              </div>
              <div class="metric-track" aria-hidden="true">
                <span :style="{ transform: `scaleX(${card.barPercent / 100})` }" />
              </div>
              <p>{{ card.detail }}</p>
            </article>
          </div>
        </section>

        <aside class="panel action-panel">
          <div class="panel-heading compact">
            <h3>建议动作</h3>
          </div>
          <div class="recommendation-list">
            <button
              v-for="(item, index) in recommendations"
              :key="item.key"
              type="button"
              class="recommendation-item"
              :class="`tone-${item.tone}`"
              @click="handleRecommendation(item.action)"
            >
              <span class="recommendation-index">{{ index + 1 }}</span>
              <span>
                <strong>{{ item.title }}</strong>
                <small>{{ item.description }}</small>
              </span>
            </button>
          </div>
        </aside>
      </div>

      <div class="diagnostic-grid">
        <section class="panel">
          <div class="panel-heading compact">
            <h3>指标趋势</h3>
            <span>最近 1 小时</span>
          </div>
          <div class="trend-grid">
            <article v-for="card in trendCards" :key="card.key" class="trend-card">
              <div class="trend-card-head">
                <strong>{{ card.label }}</strong>
                <span>{{ card.state }}</span>
              </div>
              <div class="trend-placeholder" aria-hidden="true">
                <el-icon><DataLine /></el-icon>
              </div>
            </article>
          </div>
        </section>

        <aside class="side-stack">
          <section class="panel">
            <div class="panel-heading compact">
              <h3>事件时间线</h3>
              <span>最近 24h</span>
            </div>
            <div class="empty-note">
              <el-icon><Connection /></el-icon>
              <span>事件聚合待接入，后续展示告警、部署、巡检和容器变化。</span>
            </div>
          </section>

          <section class="panel">
            <div class="panel-heading compact">
              <h3>关联跳转</h3>
            </div>
            <div class="relation-list">
              <span v-for="card in relationCards" :key="card.key" class="relation-item">
                <strong>{{ card.label }}</strong>
                <small>{{ card.value }}</small>
              </span>
            </div>
          </section>
        </aside>
      </div>

      <section class="steady-section">
        <div class="panel-heading compact">
          <h3>稳态详情</h3>
        </div>
        <div class="steady-grid">
          <article v-for="group in steadyDetailGroups" :key="group.key" class="panel detail-panel">
            <h4>{{ group.title }}</h4>
            <dl class="kv-list">
              <template v-for="row in group.rows" :key="row.label">
                <dt>{{ row.label }}</dt>
                <dd>{{ row.value }}</dd>
              </template>
            </dl>
          </article>
        </div>
      </section>
    </div>
  </div>
</template>
```

- [ ] **Step 3: Replace scoped CSS with the new layout styles**

Replace the `<style scoped>` block in `HostDetailView.vue` with:

```css
<style scoped>
.host-detail {
  min-height: 100%;
}

.detail-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.identity-block {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  min-width: 0;
}

.back-btn {
  flex-shrink: 0;
  gap: 4px;
}

.identity-main {
  min-width: 0;
}

.title-row,
.header-actions,
.metric-card-head,
.panel-heading {
  display: flex;
  align-items: center;
}

.title-row {
  flex-wrap: wrap;
  gap: 8px;
}

.page-title {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
}

.host-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 12px;
  margin-top: 5px;
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.5;
}

.header-actions {
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.state-chip,
.priority-pill {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 0 9px;
  border-radius: 999px;
  border: 1px solid var(--border-color);
  background: var(--surface-color);
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 650;
}

.tone-success {
  --tone-color: var(--success-color);
  --tone-bg: color-mix(in srgb, var(--success-color) 8%, var(--surface-color));
  --tone-border: color-mix(in srgb, var(--success-color) 22%, var(--border-color));
  --tone-text: color-mix(in srgb, var(--success-color) 76%, black);
}

.tone-warning {
  --tone-color: var(--warning-color);
  --tone-bg: color-mix(in srgb, var(--warning-color) 10%, var(--surface-color));
  --tone-border: color-mix(in srgb, var(--warning-color) 24%, var(--border-color));
  --tone-text: color-mix(in srgb, var(--warning-color) 72%, black);
}

.tone-danger {
  --tone-color: var(--danger-color);
  --tone-bg: color-mix(in srgb, var(--danger-color) 8%, var(--surface-color));
  --tone-border: color-mix(in srgb, var(--danger-color) 22%, var(--border-color));
  --tone-text: color-mix(in srgb, var(--danger-color) 80%, black);
}

.tone-muted {
  --tone-color: var(--text-muted);
  --tone-bg: color-mix(in srgb, var(--text-muted) 8%, var(--surface-color));
  --tone-border: color-mix(in srgb, var(--text-muted) 18%, var(--border-color));
  --tone-text: var(--text-secondary);
}

.state-chip,
.priority-pill,
.metric-card,
.recommendation-item {
  border-color: var(--tone-border, var(--border-color));
  background: var(--tone-bg, var(--surface-color));
  color: var(--tone-text, var(--text-secondary));
}

.detail-content {
  display: grid;
  gap: 12px;
}

.hero-grid,
.diagnostic-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 12px;
}

.panel,
.collection-warning {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
}

.panel {
  padding: 14px;
}

.collection-warning {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  padding: 12px 14px;
  color: color-mix(in srgb, var(--danger-color) 82%, black);
  background: color-mix(in srgb, var(--danger-color) 7%, var(--surface-color));
  border-color: color-mix(in srgb, var(--danger-color) 20%, var(--border-color));
}

.collection-warning p {
  margin: 3px 0 0;
  font-size: 12px;
  color: var(--text-secondary);
}

.judgment-panel {
  border-color: var(--tone-border, var(--border-color));
}

.panel-heading {
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.panel-heading.compact {
  align-items: baseline;
}

.panel-heading h3 {
  margin: 0;
  font-size: 15px;
  color: var(--text-primary);
}

.panel-heading span {
  font-size: 12px;
  color: var(--text-muted);
}

.section-kicker {
  display: block;
  margin-bottom: 4px;
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 600;
}

.judgment-copy {
  margin: 0 0 12px;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.6;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.metric-card {
  border: 1px solid var(--tone-border, var(--border-color));
  border-radius: var(--border-radius);
  padding: 10px;
  min-width: 0;
}

.metric-card-head {
  justify-content: space-between;
  gap: 8px;
  color: var(--text-secondary);
  font-size: 12px;
}

.metric-card-head strong {
  color: var(--tone-text, var(--text-secondary));
  font-weight: 700;
}

.metric-value {
  display: flex;
  align-items: baseline;
  gap: 3px;
  margin-top: 6px;
  color: var(--text-primary);
}

.metric-value span {
  font-size: 24px;
  font-weight: 750;
  line-height: 1;
}

.metric-value small {
  color: var(--text-muted);
  font-size: 12px;
}

.metric-track {
  height: 5px;
  margin-top: 8px;
  overflow: hidden;
  border-radius: 999px;
  background: color-mix(in srgb, var(--border-color) 72%, var(--bg-color));
}

.metric-track span {
  display: block;
  width: 100%;
  height: 100%;
  transform-origin: left;
  border-radius: inherit;
  background: var(--tone-color, var(--primary-color));
  transition: transform 180ms ease-out;
}

.metric-card p {
  margin: 7px 0 0;
  color: var(--text-muted);
  font-size: 11px;
}

.recommendation-list,
.side-stack {
  display: grid;
  gap: 8px;
}

.recommendation-item {
  display: grid;
  grid-template-columns: 22px 1fr;
  gap: 8px;
  width: 100%;
  min-width: 0;
  padding: 9px;
  text-align: left;
  border: 1px solid var(--tone-border, var(--border-color));
  border-radius: 7px;
  cursor: pointer;
  transition: border-color 180ms ease-out, background-color 180ms ease-out;
}

.recommendation-item:hover {
  border-color: var(--primary-color);
  background: color-mix(in srgb, var(--primary-color) 5%, var(--surface-color));
}

.recommendation-index {
  font-weight: 750;
}

.recommendation-item strong,
.recommendation-item small {
  display: block;
}

.recommendation-item strong {
  color: var(--text-primary);
  font-size: 12px;
}

.recommendation-item small {
  margin-top: 3px;
  color: var(--text-secondary);
  font-size: 11px;
  line-height: 1.4;
}

.trend-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.trend-card {
  min-width: 0;
  padding: 10px;
  border: 1px solid var(--border-color);
  border-radius: 7px;
}

.trend-card-head {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-size: 12px;
}

.trend-card-head span {
  color: var(--text-muted);
}

.trend-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 56px;
  margin-top: 8px;
  border: 1px dashed var(--border-color);
  border-radius: 6px;
  color: var(--text-muted);
  background: color-mix(in srgb, var(--bg-color) 70%, var(--surface-color));
}

.empty-note {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.5;
}

.relation-list {
  display: grid;
  gap: 7px;
}

.relation-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-secondary);
  font-size: 12px;
}

.relation-item strong {
  color: var(--text-primary);
}

.relation-item small {
  color: var(--text-muted);
}

.steady-section {
  display: grid;
  gap: 10px;
}

.steady-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.detail-panel h4 {
  margin: 0 0 10px;
  color: var(--text-primary);
  font-size: 13px;
}

.kv-list {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 8px 12px;
  margin: 0;
  font-size: 12px;
}

.kv-list dt {
  color: var(--text-muted);
}

.kv-list dd {
  min-width: 0;
  color: var(--text-primary);
  font-weight: 600;
  overflow-wrap: anywhere;
}

.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  text-align: center;
}

.error-icon {
  color: var(--danger-color);
  margin-bottom: 16px;
}

.error-text {
  max-width: 400px;
  margin-bottom: 20px;
  color: var(--text-secondary);
  font-size: 14px;
}

:focus-visible {
  outline: 2px solid var(--primary-color);
  outline-offset: 2px;
  border-radius: 4px;
}

@media (prefers-reduced-motion: reduce) {
  .metric-track span,
  .recommendation-item {
    transition: none;
  }
}

@media (max-width: 1180px) {
  .hero-grid,
  .diagnostic-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 860px) {
  .detail-header {
    flex-direction: column;
  }

  .header-actions {
    justify-content: flex-start;
    width: 100%;
  }

  .metric-grid,
  .trend-grid,
  .steady-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 560px) {
  .identity-block {
    width: 100%;
  }

  .metric-grid,
  .trend-grid,
  .steady-grid {
    grid-template-columns: 1fr;
  }

  .header-actions :deep(.el-button) {
    flex: 1 1 auto;
  }
}
</style>
```

- [ ] **Step 4: Run unit tests**

Run:

```bash
cd frontend
node --test src/utils/hostDetail.test.mjs
```

Expected:

```text
ok ...
```

- [ ] **Step 5: Run type/build check**

Run:

```bash
cd frontend
npm run build
```

Expected:

```text
vite v... building...
✓ built in ...
```

If the build fails because `ElMessage` is not available in type resolution, change the import to:

```ts
import { ElMessage } from 'element-plus'
```

This import is already included in Step 1, so a failure here likely means dependency installation is missing or the local dirty tree has unrelated type errors.

- [ ] **Step 6: Commit the page rebuild**

```bash
git add frontend/src/views/monitoring/HostDetailView.vue frontend/src/utils/hostDetail.ts frontend/src/utils/hostDetail.test.mjs
git commit -m "feat(monitoring): redesign host detail command view"
```

## Task 4: Browser QA and Responsive Polish

**Files:**

- Modify: `frontend/src/views/monitoring/HostDetailView.vue`
- Test: local browser at `/monitoring/hosts/:id`

- [ ] **Step 1: Start the frontend dev server**

Run:

```bash
cd frontend
npm run dev
```

Expected:

```text
Local: http://localhost:3000/
```

If port 3000 is busy, use the URL printed by Vite.

- [ ] **Step 2: Open a real host detail route**

Use an existing host id from the local database and open:

```text
http://localhost:3000/monitoring/hosts/1
```

Expected:

- Header shows host name, IP, status tags, refresh time, and actions.
- Current judgment section appears above steady details.
- Metric cards do not use circular progress.
- Trend and event sections show explicit pending states.

- [ ] **Step 3: Verify desktop layout visually**

At a desktop viewport around `1280x720`, check:

- Header actions stay on the right and wrap only when needed.
- Current judgment is left, recommended actions are right.
- Trend section is left, event/relation stack is right.
- No card is nested inside another card.
- Text does not overflow chips, buttons, metric cards, or relation items.

- [ ] **Step 4: Verify mobile layout visually**

At a mobile viewport around `390x844`, check:

- Header actions wrap without overlapping.
- Metric cards collapse to one column.
- Trend cards collapse to one column.
- Steady detail panels collapse to one column.
- All buttons are reachable without hover.

- [ ] **Step 5: Fix any visual issues found during QA**

Apply only targeted CSS changes. Examples:

```css
.header-actions :deep(.el-button) {
  min-width: 0;
}

.page-title {
  overflow-wrap: anywhere;
}
```

Do not change data or business logic in this polish task unless the QA issue is caused by an obvious binding mistake.

- [ ] **Step 6: Re-run verification**

Run:

```bash
cd frontend
node --test src/utils/hostDetail.test.mjs
npm run build
```

Expected:

```text
ok ...
✓ built in ...
```

- [ ] **Step 7: Commit QA polish**

```bash
git add frontend/src/views/monitoring/HostDetailView.vue
git commit -m "fix(monitoring): polish host detail responsive layout"
```

## Task 5: Final Verification

**Files:**

- Verify: `frontend/src/utils/hostDetail.ts`
- Verify: `frontend/src/utils/hostDetail.test.mjs`
- Verify: `frontend/src/views/monitoring/HostDetailView.vue`

- [ ] **Step 1: Run focused unit tests**

```bash
cd frontend
node --test src/utils/hostDetail.test.mjs
```

Expected:

```text
ok ...
```

- [ ] **Step 2: Run frontend production build**

```bash
cd frontend
npm run build
```

Expected:

```text
vue-tsc -b && vite build
✓ built in ...
```

- [ ] **Step 3: Inspect final diff**

```bash
git diff --stat HEAD
git diff -- frontend/src/views/monitoring/HostDetailView.vue frontend/src/utils/hostDetail.ts frontend/src/utils/hostDetail.test.mjs
```

Expected:

- Only the host detail page and host detail utility/test files are changed since the task commits.
- No unrelated worktree files are staged.

- [ ] **Step 4: Commit any remaining verification fixes**

Only run this if Step 3 shows intentional uncommitted fixes:

```bash
git add frontend/src/views/monitoring/HostDetailView.vue frontend/src/utils/hostDetail.ts frontend/src/utils/hostDetail.test.mjs
git commit -m "fix(monitoring): finalize host detail optimization"
```

## Implementation Notes

- The current repository contains mojibake in several existing Vue files and tests. New code should use normal UTF-8 Chinese text. If the terminal displays mojibake but the browser renders correctly, do not convert unrelated files.
- Keep the detail page on `onActivated(fetchDetail)`. Do not replace it with `onMounted` watchers.
- Keep the first implementation frontend-only. The placeholders for trends, events, and relations are intentional phase-one behavior.
- If the browser QA reveals that `navigator.clipboard` fails on localhost, the warning toast is acceptable for phase one.
- The plan assumes existing dependencies are installed. If `npm run build` fails because dependencies are missing, run `npm install` only after user approval if network access is required.
