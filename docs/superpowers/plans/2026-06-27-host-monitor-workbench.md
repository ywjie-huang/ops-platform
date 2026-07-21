# Host Monitor Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the host monitoring page into the approved workbench layout so operators can judge risk quickly, focus on the most important hosts first, and complete detail or SSH jumps from a denser work list.

**Architecture:** Keep the existing `getHosts()` API and page route, but extract the new risk-summary, priority-host, and row-presentation logic into a small `frontend/src/utils/hostMonitor.ts` helper so `HostListView.vue` stays focused on rendering and interactions. Then reshape `HostListView.vue` into a three-layer workbench: compact header, compressed risk summary with a thin priority band, and a dominant host work list with improved row context and state expression.

**Tech Stack:** Vue 3 script setup, Element Plus, Vite, TypeScript, Node `node:test` utility tests

---

## File Structure

- Create: `frontend/src/utils/hostMonitor.ts`
  - Pure helpers for host risk scoring, overview summary, priority-host extraction, and row state metadata.
- Create: `frontend/src/utils/hostMonitor.test.mjs`
  - Node-based regression tests for the helper behavior before wiring it into the Vue page.
- Modify: `frontend/src/views/monitoring/HostListView.vue`
  - Replace the current list page structure with the approved workbench layout while preserving fetch behavior, routing, filtering, pagination, and auto-refresh.
- Modify: `frontend/src/utils/autoRefresh.js`
  - Only if needed to support richer refresh-status presentation without duplicating timer state in the page.
- Modify: `frontend/src/utils/autoRefresh.d.ts`
  - Keep declarations aligned if the helper interface changes.

## Task 1: Add and verify host monitor helper tests

**Files:**
- Create: `frontend/src/utils/hostMonitor.test.mjs`
- Create: `frontend/src/utils/hostMonitor.ts`
- Test: `frontend/src/utils/hostMonitor.test.mjs`

- [ ] **Step 1: Write the failing test**

```javascript
import assert from 'node:assert/strict'
import test from 'node:test'

const {
  buildHostOverview,
  sortHostsByRisk,
  buildPriorityHosts,
  getHostStateMeta,
} = await import('./hostMonitor.ts')

test('builds workbench overview cards from host list data', () => {
  const cards = buildHostOverview([
    { id: 1, name: 'prod-app-01', prometheus_ok: true, cpu: 97, memory: 84, disk: 61 },
    { id: 2, name: 'cache-node-03', prometheus_ok: false, cpu: 0, memory: 0, disk: 0 },
    { id: 3, name: 'gateway-07', prometheus_ok: true, cpu: 51, memory: 48, disk: 43 },
    { id: 4, name: 'db-replica-02', prometheus_ok: true, cpu: 58, memory: 63, disk: 91 },
  ])

  assert.deepEqual(cards, [
    { key: 'critical', label: '高危主机', value: 2, tone: 'danger' },
    { key: 'offline', label: '离线主机', value: 1, tone: 'muted' },
    { key: 'warning', label: '指标异常', value: 3, tone: 'warning' },
    { key: 'healthy', label: '运行正常', value: 1, tone: 'success' },
  ])
})

test('sorts hosts by offline first, then severity, then host name', () => {
  const sorted = sortHostsByRisk([
    { id: 1, name: 'healthy', prometheus_ok: true, cpu: 30, memory: 35, disk: 40 },
    { id: 2, name: 'offline', prometheus_ok: false, cpu: 0, memory: 0, disk: 0 },
    { id: 3, name: 'critical', prometheus_ok: true, cpu: 98, memory: 81, disk: 50 },
    { id: 4, name: 'warning', prometheus_ok: true, cpu: 55, memory: 73, disk: 52 },
  ])

  assert.deepEqual(sorted.map((item) => item.name), ['offline', 'critical', 'warning', 'healthy'])
})

test('extracts priority hosts and descriptive state metadata', () => {
  const hosts = [
    { id: 1, name: 'prod-app-01', ip_address: '10.10.3.21', owner: '应用组', prometheus_ok: true, cpu: 97, memory: 84, disk: 61, load: '22.3' },
    { id: 2, name: 'cache-node-03', ip_address: '10.10.5.9', owner: '平台组', prometheus_ok: false, cpu: 0, memory: 0, disk: 0, load: '-' },
    { id: 3, name: 'db-replica-02', ip_address: '10.10.4.18', owner: '数据组', prometheus_ok: true, cpu: 58, memory: 63, disk: 91, load: '5.6' },
  ]

  assert.deepEqual(
    buildPriorityHosts(hosts).map((item) => ({
      name: item.name,
      headline: item.headline,
      action: item.action,
    })),
    [
      { name: 'cache-node-03', headline: '主机离线，指标不可用', action: 'SSH' },
      { name: 'prod-app-01', headline: 'CPU 97% · Load 22.3', action: '详情' },
      { name: 'db-replica-02', headline: '磁盘 91% · 需尽快清理', action: '详情' },
    ],
  )

  assert.deepEqual(getHostStateMeta(hosts[0]), {
    key: 'critical',
    label: '高危',
    tone: 'danger',
    summary: 'CPU 97% · Load 22.3',
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test frontend/src/utils/hostMonitor.test.mjs`

Expected: FAIL with module-not-found or missing export errors for `hostMonitor.ts`

- [ ] **Step 3: Write minimal implementation**

```typescript
export type HostLike = {
  id?: number
  name?: string
  ip_address?: string
  owner?: string
  prometheus_ok?: boolean
  cpu?: number
  memory?: number
  disk?: number
  load?: string | number
}

function metricMax(host: HostLike) {
  return Math.max(host.cpu || 0, host.memory || 0, host.disk || 0)
}

export function getHostStateMeta(host: HostLike) {
  if (!host.prometheus_ok) {
    return { key: 'offline', label: '离线', tone: 'muted', summary: '主机离线，指标不可用' }
  }
  if ((host.cpu || 0) > 90 || (host.memory || 0) > 90 || (host.disk || 0) > 90) {
    const cpu = host.cpu || 0
    const disk = host.disk || 0
    if (cpu >= disk) {
      return { key: 'critical', label: '高危', tone: 'danger', summary: `CPU ${cpu}% · Load ${host.load || '-'}` }
    }
    return { key: 'critical', label: '高危', tone: 'danger', summary: `磁盘 ${disk}% · 需尽快清理` }
  }
  if ((host.cpu || 0) > 70 || (host.memory || 0) > 70 || (host.disk || 0) > 70) {
    return { key: 'warning', label: '告警', tone: 'warning', summary: `峰值指标 ${metricMax(host)}%` }
  }
  return { key: 'healthy', label: '在线', tone: 'success', summary: `负载 ${host.load || '-'} · 运行平稳` }
}

export function hostRiskScore(host: HostLike) {
  if (!host.prometheus_ok) return 1000
  const max = metricMax(host)
  if (max > 90) return 700 + max
  if (max > 70) return 400 + max
  return max
}

export function sortHostsByRisk<T extends HostLike>(hosts: T[]) {
  return [...hosts].sort((a, b) => {
    const scoreDiff = hostRiskScore(b) - hostRiskScore(a)
    if (scoreDiff !== 0) return scoreDiff
    return String(a.name || '').localeCompare(String(b.name || ''), 'zh-CN')
  })
}

export function buildHostOverview(hosts: HostLike[]) {
  const critical = hosts.filter((item) => getHostStateMeta(item).key === 'critical').length
  const offline = hosts.filter((item) => getHostStateMeta(item).key === 'offline').length
  const warning = hosts.filter((item) => ['critical', 'warning'].includes(getHostStateMeta(item).key)).length
  const healthy = hosts.filter((item) => getHostStateMeta(item).key === 'healthy').length

  return [
    { key: 'critical', label: '高危主机', value: critical, tone: 'danger' },
    { key: 'offline', label: '离线主机', value: offline, tone: 'muted' },
    { key: 'warning', label: '指标异常', value: warning, tone: 'warning' },
    { key: 'healthy', label: '运行正常', value: healthy, tone: 'success' },
  ]
}

export function buildPriorityHosts<T extends HostLike>(hosts: T[]) {
  return sortHostsByRisk(hosts).slice(0, 5).map((item) => {
    const state = getHostStateMeta(item)
    return {
      ...item,
      headline: state.summary,
      action: state.key === 'offline' ? 'SSH' : '详情',
      tone: state.tone,
      label: state.label,
    }
  })
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test frontend/src/utils/hostMonitor.test.mjs`

Expected: PASS for all host monitor helper tests

- [ ] **Step 5: Commit**

```bash
git add frontend/src/utils/hostMonitor.ts frontend/src/utils/hostMonitor.test.mjs
git commit -m "test(monitoring): add host workbench helper coverage"
```

## Task 2: Reshape the page script state around the workbench

**Files:**
- Modify: `frontend/src/views/monitoring/HostListView.vue`
- Modify: `frontend/src/utils/hostMonitor.ts`
- Test: `frontend/src/utils/hostMonitor.test.mjs`

- [ ] **Step 1: Import the tested helpers and replace local risk logic**

In `frontend/src/views/monitoring/HostListView.vue`, replace the page-local danger and status helpers with imports from `hostMonitor.ts`:

```typescript
import {
  buildHostOverview,
  buildPriorityHosts,
  getHostStateMeta,
  sortHostsByRisk,
} from '@/utils/hostMonitor'

const overviewCards = computed(() => buildHostOverview(items.value))
const priorityHosts = computed(() => buildPriorityHosts(items.value))
```

Keep `filteredItems` local to the page, but make its default sorting branch reuse `sortHostsByRisk(result)` instead of duplicating ranking rules in the view.

- [ ] **Step 2: Add richer refresh state without changing fetch behavior**

Keep `fetchData()` and the existing auto-refresh toggle flow, but add page-local derived state:

```typescript
const refreshStatusText = computed(() => autoRefresh.value ? '自动刷新中' : '手动刷新')
const dataHealthText = computed(() => loadError.value ? '采集异常' : '数据正常')
const partialFailureCount = computed(() => items.value.filter((item) => !item.prometheus_ok).length)
```

Do not change the `getHosts()` call shape. Continue updating `lastRefreshTime` only after successful fetches.

- [ ] **Step 3: Add a filter for operator context**

Extend the page state with an owner keyword filter to support the approved “运维台账” direction:

```typescript
const ownerFilter = ref('')

watch([keyword, statusFilter, sortBy, ownerFilter], () => { currentPage.value = 1 })
```

Apply it inside `filteredItems`:

```typescript
if (ownerFilter.value) {
  const owner = ownerFilter.value.toLowerCase()
  result = result.filter((item) => String(item.owner || '').toLowerCase().includes(owner))
}
```

- [ ] **Step 4: Run helper tests**

Run: `node --test frontend/src/utils/hostMonitor.test.mjs`

Expected: PASS while `HostListView.vue` still compiles with the new helper imports

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/monitoring/HostListView.vue frontend/src/utils/hostMonitor.ts frontend/src/utils/hostMonitor.test.mjs
git commit -m "refactor(monitoring): prepare host page workbench state"
```

## Task 3: Rebuild the template into the approved workbench layout

**Files:**
- Modify: `frontend/src/views/monitoring/HostListView.vue`
- Test: `frontend/src/utils/hostMonitor.test.mjs`

- [ ] **Step 1: Replace the header with the compact workbench header**

Implement a compact header with:
- left: title and one-line task-oriented subtitle
- right: last refresh, auto-refresh button, manual refresh button, data health badge

Use this template block:

```vue
<header class="page-header workbench-header">
  <div>
    <h2 class="page-title">主机监控</h2>
    <p class="page-subtitle">按风险优先展示主机，支持快速筛查、详情定位与 SSH 进入处理。</p>
  </div>
  <div class="header-actions">
    <span v-if="lastRefreshTime" class="last-refresh">最近刷新 {{ lastRefreshTime }}</span>
    <span class="health-pill" :class="loadError ? 'is-danger' : 'is-success'">{{ dataHealthText }}</span>
    <el-button :type="autoRefresh ? 'primary' : 'default'" @click="toggleAutoRefresh">
      <el-icon><Refresh /></el-icon>
      {{ autoRefresh ? '自动刷新中' : '自动刷新' }}
    </el-button>
    <el-button :loading="loading" @click="fetchData">
      <el-icon><Refresh /></el-icon>
      立即刷新
    </el-button>
  </div>
</header>
```

- [ ] **Step 2: Replace the current stat pills with compressed risk summary cards**

Render the helper-driven overview summary:

```vue
<section class="risk-summary" aria-label="主机风险摘要">
  <div v-for="card in overviewCards" :key="card.key" class="summary-card" :class="`tone-${card.tone}`">
    <span class="summary-label">{{ card.label }}</span>
    <strong class="summary-value">{{ card.value }}</strong>
  </div>
</section>
```

Do not add decorative chart content. Keep the cards shallow and dense.

- [ ] **Step 3: Add the thin priority-host band**

Place a thin, scroll-safe priority band below the summary:

```vue
<section class="priority-strip" aria-label="优先处理主机">
  <div class="strip-header">
    <h3>优先处理</h3>
    <span>当前最值得先看的 {{ Math.min(priorityHosts.length, 5) }} 台主机</span>
  </div>
  <div class="priority-list">
    <button
      v-for="host in priorityHosts"
      :key="host.id"
      type="button"
      class="priority-item"
      :class="`tone-${host.tone}`"
      @click="goDetail(host)"
    >
      <span class="priority-name">{{ host.name }}</span>
      <span class="priority-summary">{{ host.headline }}</span>
      <span class="priority-owner">{{ host.owner || '未分配负责人' }}</span>
    </button>
  </div>
</section>
```

Keep the interaction simple: click goes to detail; secondary actions stay in the main table.

- [ ] **Step 4: Rebuild the filter bar into a work-list toolbar**

Replace the current toolbar with search, status, owner, and sort controls only:

```vue
<div class="filter-bar worklist-toolbar">
  <el-input v-model="keyword" placeholder="搜索主机名或 IP" clearable :prefix-icon="Search" class="filter-search" />
  <el-select v-model="statusFilter" placeholder="状态" clearable class="filter-status">
    <el-option label="在线" value="online" />
    <el-option label="离线" value="offline" />
    <el-option label="高危" value="danger" />
  </el-select>
  <el-input v-model="ownerFilter" placeholder="负责人" clearable class="filter-owner" />
  <el-select v-model="sortBy" placeholder="排序" class="filter-sort">
    <el-option label="风险优先" value="risk" />
    <el-option label="按 CPU 降序" value="cpu_desc" />
    <el-option label="按内存降序" value="mem_desc" />
    <el-option label="按磁盘降序" value="disk_desc" />
    <el-option label="按主机名" value="name" />
  </el-select>
</div>
```

- [ ] **Step 5: Upgrade the table into the dominant work list**

Keep the existing `el-table`, pagination, and row-click behavior, but change the columns to emphasize context:
- 主机
- 状态
- CPU
- 内存
- 磁盘
- 负责人
- 采集状态
- 动作

Use this host cell pattern:

```vue
<el-table-column label="主机" min-width="220">
  <template #default="{ row }">
    <div class="host-primary">
      <span class="host-name">{{ row.name }}</span>
      <span class="host-meta">{{ row.ip_address }} · {{ row.owner || '未分配负责人' }}</span>
    </div>
  </template>
</el-table-column>
```

Use this status cell pattern:

```vue
<el-table-column label="状态" min-width="100" align="center">
  <template #default="{ row }">
    <span class="status-chip" :class="`tone-${getHostStateMeta(row).tone}`">
      {{ getHostStateMeta(row).label }}
    </span>
  </template>
</el-table-column>
```

Add a compact “采集状态” column:

```vue
<el-table-column label="采集状态" min-width="180">
  <template #default="{ row }">
    <span class="collection-state">{{ getHostStateMeta(row).summary }}</span>
  </template>
</el-table-column>
```

Keep only `详情` and `SSH` in the action column.

- [ ] **Step 6: Preserve existing empty and error states, but sharpen copy**

Keep the current branches for `loadError` and empty state, but update copy to distinguish:
- list fetch failure
- no host data
- no filter matches

Use:

```typescript
const emptyDescription = computed(() => {
  if (keyword.value || statusFilter.value || ownerFilter.value) return '当前筛选条件下没有匹配的主机'
  return '当前没有可展示的主机监控数据'
})
```

- [ ] **Step 7: Run helper tests**

Run: `node --test frontend/src/utils/hostMonitor.test.mjs`

Expected: PASS after the template rewrite

- [ ] **Step 8: Commit**

```bash
git add frontend/src/views/monitoring/HostListView.vue frontend/src/utils/hostMonitor.test.mjs
git commit -m "feat(monitoring): rebuild host page into workbench layout"
```

## Task 4: Add page-scoped styling and responsive behavior

**Files:**
- Modify: `frontend/src/views/monitoring/HostListView.vue`
- Test: `frontend/src/utils/hostMonitor.test.mjs`

- [ ] **Step 1: Add scoped styles for the new header, summary, and priority strip**

Append scoped CSS for the new layout:

```css
.workbench-header {
  align-items: flex-start;
}

.page-subtitle {
  margin: 5px 0 0;
  color: var(--text-secondary);
  font-size: 13px;
}

.risk-summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 12px;
}

.summary-card {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: 12px 14px;
  display: grid;
  gap: 4px;
}

.priority-strip {
  margin-bottom: 12px;
  padding: 12px 14px;
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
}
```

- [ ] **Step 2: Add work-list and table styles**

Add focused styles for the dominant list:

```css
.worklist-toolbar {
  margin-bottom: 12px;
}

.host-primary {
  display: grid;
  gap: 4px;
}

.host-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.host-meta,
.collection-state {
  font-size: 12px;
  color: var(--text-secondary);
}

.status-chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 56px;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
}
```

Use project tokens and `color-mix()` for tone variations instead of hard-coded rgba values.

- [ ] **Step 3: Add responsive collapse rules**

At `max-width: 768px`, stack the summary cards and priority strip, and reduce nonessential columns:

```css
@media (max-width: 768px) {
  .risk-summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .header-actions {
    width: 100%;
    justify-content: flex-start;
  }

  .priority-list {
    grid-template-columns: 1fr;
  }
}
```

Keep the page usable without a separate right rail or floating cards.

- [ ] **Step 4: Run helper tests and build**

Run:
- `node --test frontend/src/utils/hostMonitor.test.mjs`
- `npm run build`

Expected:
- helper tests PASS
- build PASS, or if unrelated pre-existing TypeScript errors remain, capture them verbatim and confirm no new host-monitor-specific errors were introduced

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/monitoring/HostListView.vue frontend/src/utils/hostMonitor.ts frontend/src/utils/autoRefresh.js frontend/src/utils/autoRefresh.d.ts frontend/src/utils/hostMonitor.test.mjs
git commit -m "style(monitoring): polish host workbench presentation"
```

## Task 5: Verify behavior in the browser

**Files:**
- Modify: `frontend/src/views/monitoring/HostListView.vue` (only if bugs are found during verification)
- Test: `frontend/src/utils/hostMonitor.test.mjs`

- [ ] **Step 1: Start the frontend and open the host monitoring page**

Run:

```bash
cd frontend
npm run dev
```

Then open the host monitoring route in the browser and verify the page loads.

- [ ] **Step 2: Verify the approved workbench behaviors**

Check:
- top header shows recent refresh, refresh controls, and data-health feedback
- compressed risk summary renders four cards
- priority band renders only 3-5 hosts and clicks through to detail
- main table is visually dominant
- action column contains only `详情` and `SSH`
- no standalone right rail exists
- no standalone quick-action block exists

- [ ] **Step 3: Verify filtering, paging, and refresh still work**

Check:
- keyword search filters by host name or IP
- owner filter narrows rows by owner
- status filter narrows online / offline / high-risk rows
- sort toggle switches between risk, metric, and name ordering
- pagination still works after filtering
- auto-refresh still updates the last refresh time after 15 seconds

- [ ] **Step 4: Re-run helper tests after any browser fixes**

Run: `node --test frontend/src/utils/hostMonitor.test.mjs`

Expected: PASS after any final adjustments

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/monitoring/HostListView.vue frontend/src/utils/hostMonitor.ts frontend/src/utils/hostMonitor.test.mjs
git commit -m "fix(monitoring): verify host workbench interactions"
```

## Self-Review

- Spec coverage:
  - compact header with refresh and data health: covered in Task 3 step 1 and Task 2 step 2
  - compressed risk summary: covered in Task 1 and Task 3 step 2
  - thin priority-host band: covered in Task 1 and Task 3 step 3
  - dominant host work list with denser context: covered in Task 2 step 3 and Task 3 steps 4-5
  - remove right rail and quick-action block: enforced in Task 3 structure and Task 5 verification
  - improve refresh and data-health expression: covered in Task 2 step 2 and Task 5 verification
- Placeholder scan:
  - no `TODO`, `TBD`, or vague “handle later” language remains
- Type consistency:
  - helper names are consistently `buildHostOverview`, `sortHostsByRisk`, `buildPriorityHosts`, and `getHostStateMeta`

Plan complete and saved to `docs/superpowers/plans/2026-06-27-host-monitor-workbench.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
