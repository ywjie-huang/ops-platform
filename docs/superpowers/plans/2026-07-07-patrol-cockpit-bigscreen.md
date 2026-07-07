# Patrol Cockpit Bigscreen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild `/patrol/cockpit` as an immersive B2-style patrol situation screen with a metric top rail, central radar, side context panels, and bottom battle ticker.

**Architecture:** Keep the implementation frontend-only. Add small deterministic view-model helpers to `frontend/src/utils/patrolCommand.ts`, cover them with `node:test`, then refactor `frontend/src/views/patrol/PatrolCockpitView.vue` to consume those helpers and render the new layout.

**Tech Stack:** Vue 3 `<script setup>`, TypeScript, scoped SCSS/CSS, Element Plus buttons/icons, Node `node:test` for utility tests.

---

## Baseline Notes

- Worktree: `D:\my-project\.worktrees\codex-patrol-cockpit-bigscreen`
- Branch: `codex/patrol-cockpit-bigscreen`
- Baseline passing command: `node --test frontend/src/utils/patrolCommand.test.mjs` passes 6/6.
- Baseline failing command: `npm run build` fails before this implementation on unrelated project type errors, including missing `@/utils/time`, batch execution HTMLElement fields, deploy approval indexing, role checkbox typing, and scheduler tag typing.

## File Structure

- Modify: `frontend/src/utils/patrolCommand.ts`
  - Add display-only helpers for radar point placement, ticker item generation, and cockpit stat metadata.
- Modify: `frontend/src/utils/patrolCommand.test.mjs`
  - Add failing tests for the new helpers before implementation.
- Modify: `frontend/src/views/patrol/PatrolCockpitView.vue`
  - Replace the current card-grid cockpit with the approved immersive B2 layout.
- Keep: `docs/superpowers/specs/2026-07-07-patrol-cockpit-design.md`
  - Source design requirements; no code changes needed.

---

### Task 1: Add Cockpit Display View-Model Helpers

**Files:**
- Modify: `frontend/src/utils/patrolCommand.test.mjs`
- Modify: `frontend/src/utils/patrolCommand.ts`

- [ ] **Step 1: Write failing tests**

Add imports for `buildCockpitStats`, `buildRadarObjects`, and `buildTickerItems`, then append tests:

```js
test('builds cockpit stats for the immersive top rail', () => {
  const stats = buildCockpitStats(report, 4, '刚刚')

  assert.deepEqual(stats.map((item) => ({
    key: item.key,
    label: item.label,
    value: item.value,
    tone: item.tone,
  })), [
    { key: 'health', label: '健康分', value: '55', tone: 'danger' },
    { key: 'critical', label: '严重项', value: '2', tone: 'danger' },
    { key: 'warning', label: '警告项', value: '2', tone: 'warning' },
    { key: 'coverage', label: '覆盖对象', value: '4', tone: 'info' },
    { key: 'updated', label: '最近巡检', value: '刚刚', tone: 'success' },
  ])
})

test('maps risk objects into stable radar positions by category and severity', () => {
  const radar = buildRadarObjects(buildRiskObjects(items))

  assert.deepEqual(radar.map((item) => ({
    key: item.key,
    targetName: item.targetName,
    ring: item.ring,
    angle: item.angle,
    size: item.size,
    tone: item.tone,
  })), [
    { key: 'host::web-01', targetName: 'web-01', ring: 34, angle: -34, size: 18, tone: 'danger' },
    { key: 'host::db-02', targetName: 'db-02', ring: 43, angle: 18, size: 18, tone: 'danger' },
    { key: 'k8s::k8s-prod', targetName: 'k8s-prod', ring: 56, angle: 86, size: 14, tone: 'warning' },
    { key: 'asset::cert-api', targetName: 'cert-api', ring: 64, angle: 164, size: 10, tone: 'success' },
  ])
})

test('builds ticker items from priority objects and recent reports', () => {
  const priority = buildRiskObjects(items).filter((item) => item.status !== 'normal')
  const ticker = buildTickerItems(priority, [
    { title: '巡检报告 A', status: 'critical', critical_count: 2, warning_count: 1 },
    { title: '巡检报告 B', status: 'normal', critical_count: 0, warning_count: 0 },
  ])

  assert.deepEqual(ticker.map((item) => ({
    key: item.key,
    title: item.title,
    tone: item.tone,
  })), [
    { key: 'risk-host::web-01', title: 'web-01', tone: 'danger' },
    { key: 'risk-host::db-02', title: 'db-02', tone: 'danger' },
    { key: 'risk-k8s::k8s-prod', title: 'k8s-prod', tone: 'warning' },
    { key: 'report-0', title: '巡检报告 A', tone: 'danger' },
    { key: 'report-1', title: '巡检报告 B', tone: 'success' },
  ])
})
```

- [ ] **Step 2: Run tests and verify RED**

Run: `node --test frontend/src/utils/patrolCommand.test.mjs`

Expected: FAIL because `buildCockpitStats`, `buildRadarObjects`, and `buildTickerItems` are not exported.

- [ ] **Step 3: Implement minimal helpers**

In `frontend/src/utils/patrolCommand.ts`, add exported interfaces and functions:

```ts
export interface CockpitStat {
  key: string
  label: string
  value: string
  helper: string
  tone: PatrolTone
}

export interface RadarObject extends RiskObject {
  ring: number
  angle: number
  size: number
}

export interface TickerItem {
  key: string
  title: string
  detail: string
  meta: string
  tone: PatrolTone
}

export function buildCockpitStats(report: PatrolReportLike | null | undefined, coverageCount = 0, updatedText = '-'): CockpitStat[] {
  const overview = buildPatrolOverview(report)
  const healthTone: PatrolTone = overview.critical > 0 ? 'danger' : overview.warning > 0 ? 'warning' : 'success'
  return [
    { key: 'health', label: '健康分', value: String(overview.healthScore), helper: overview.priorityLabel, tone: healthTone },
    { key: 'critical', label: '严重项', value: String(overview.critical), helper: `${overview.priority} 优先级`, tone: overview.critical > 0 ? 'danger' : 'success' },
    { key: 'warning', label: '警告项', value: String(overview.warning), helper: `${overview.abnormal} 个异常项`, tone: overview.warning > 0 ? 'warning' : 'success' },
    { key: 'coverage', label: '覆盖对象', value: String(coverageCount), helper: '主机 / K8s / 资产', tone: 'info' },
    { key: 'updated', label: '最近巡检', value: updatedText, helper: report?.operator || '系统任务', tone: 'success' },
  ]
}

export function buildRadarObjects(objects: RiskObject[] = []): RadarObject[] {
  const categoryBase: Record<string, { ring: number; angle: number }> = {
    host: { ring: 34, angle: -34 },
    k8s: { ring: 56, angle: 86 },
    asset: { ring: 64, angle: 164 },
  }

  const seenByCategory: Record<string, number> = {}
  return objects.slice(0, 10).map((object) => {
    const seen = seenByCategory[object.category] || 0
    seenByCategory[object.category] = seen + 1
    const base = categoryBase[object.category] || { ring: 62, angle: 220 }
    return {
      ...object,
      ring: Math.min(72, base.ring + seen * 9),
      angle: base.angle + seen * 52,
      size: object.status === 'critical' ? 18 : object.status === 'warning' ? 14 : 10,
    }
  })
}

export function buildTickerItems(priorityObjects: RiskObject[] = [], reports: PatrolReportLike[] = []): TickerItem[] {
  const riskItems = priorityObjects.slice(0, 4).map((object) => ({
    key: `risk-${object.key}`,
    title: object.targetName,
    detail: `${object.headline}，${object.impact}`,
    meta: `${object.categoryLabel} · ${object.priority}`,
    tone: object.tone,
  }))

  const reportItems = reports.slice(0, 3).map((report, index) => ({
    key: `report-${index}`,
    title: report.title || `巡检批次 ${index + 1}`,
    detail: `${report.critical_count || 0} 严重 / ${report.warning_count || 0} 警告`,
    meta: getPatrolPriority(report),
    tone: statusTone(report.status),
  }))

  return [...riskItems, ...reportItems]
}
```

- [ ] **Step 4: Run tests and verify GREEN**

Run: `node --test frontend/src/utils/patrolCommand.test.mjs`

Expected: PASS.

---

### Task 2: Rebuild PatrolCockpitView Template and Computed Data

**Files:**
- Modify: `frontend/src/views/patrol/PatrolCockpitView.vue`

- [ ] **Step 1: Add markup smoke test before implementation**

Create or update a lightweight test `frontend/src/views/patrol/patrolCockpitView.test.mjs` that reads the SFC and asserts the new layout vocabulary:

```js
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'

const cockpitView = readFileSync(new URL('./PatrolCockpitView.vue', import.meta.url), 'utf8')

test('patrol cockpit uses immersive bigscreen layout vocabulary', () => {
  assert.match(cockpitView, /class="bigscreen-shell"/)
  assert.match(cockpitView, /class="metric-rail"/)
  assert.match(cockpitView, /class="radar-stage"/)
  assert.match(cockpitView, /class="risk-queue"/)
  assert.match(cockpitView, /class="battle-ticker"/)
})

test('patrol cockpit keeps reduced motion and accessible radar semantics', () => {
  assert.match(cockpitView, /prefers-reduced-motion/)
  assert.match(cockpitView, /role="img"/)
  assert.match(cockpitView, /aria-label="巡检风险雷达"/)
})
```

- [ ] **Step 2: Run smoke test and verify RED**

Run: `node --test frontend/src/views/patrol/patrolCockpitView.test.mjs`

Expected: FAIL because the new classes and radar semantics are absent.

- [ ] **Step 3: Replace template structure**

Replace the current template with:

```vue
<template>
  <div class="patrol-cockpit bigscreen-shell">
    <header class="bigscreen-topbar">...</header>
    <main v-loading="loading" class="bigscreen-dashboard">
      <section class="metric-rail">...</section>
      <section class="risk-queue">...</section>
      <section class="radar-stage" role="img" aria-label="巡检风险雷达">...</section>
      <section class="distribution-panel">...</section>
      <section class="trend-panel">...</section>
      <section class="battle-ticker">...</section>
    </main>
  </div>
</template>
```

Keep `返回指挥台` and `立即巡检`. Replace the bottom table with ticker cards.

- [ ] **Step 4: Wire computed state**

Import the new helpers:

```ts
import {
  buildCockpitStats,
  buildPatrolOverview,
  buildRadarObjects,
  buildRiskObjects,
  buildTickerItems,
  groupRiskObjectsByCategory,
  statusTone,
  type PatrolItemLike,
  type PatrolReportLike,
} from '@/utils/patrolCommand'
```

Add computed values:

```ts
const cockpitStats = computed(() => buildCockpitStats(latestReport.value, riskObjects.value.length, relativeTime(latestReport.value?.created_at)))
const priorityObjects = computed(() => riskObjects.value.filter((item) => item.status !== 'normal').slice(0, 6))
const radarObjects = computed(() => buildRadarObjects(riskObjects.value))
const tickerItems = computed(() => buildTickerItems(priorityObjects.value, reports.value))
```

- [ ] **Step 5: Run smoke test and utility tests**

Run:

```bash
node --test frontend/src/views/patrol/patrolCockpitView.test.mjs
node --test frontend/src/utils/patrolCommand.test.mjs
```

Expected: PASS.

---

### Task 3: Add Immersive Bigscreen Styling and Motion

**Files:**
- Modify: `frontend/src/views/patrol/PatrolCockpitView.vue`

- [ ] **Step 1: Implement scoped styles**

Replace the old cockpit styles with a B2 layout:

```css
.bigscreen-shell {
  min-height: calc(100vh - var(--header-height));
  margin: -4px;
  padding: 12px;
  color: #eef5ff;
  background:
    radial-gradient(circle at 50% 36%, color-mix(in srgb, var(--primary-color) 22%, transparent), transparent 38%),
    radial-gradient(circle at 78% 18%, color-mix(in srgb, #06b6d4 15%, transparent), transparent 28%),
    linear-gradient(180deg, #07101c 0%, #080b13 100%);
}

.bigscreen-dashboard {
  display: grid;
  grid-template-columns: minmax(230px, 0.82fr) minmax(420px, 1.55fr) minmax(230px, 0.82fr);
  grid-template-rows: auto minmax(410px, 1fr) 156px;
  grid-template-areas:
    "metrics metrics metrics"
    "queue radar side"
    "ticker ticker ticker";
  gap: 12px;
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

Use full borders, glow only for active/semantic states, and no nested card styling.

- [ ] **Step 2: Add radar and ticker motion**

Add keyframes for radar sweep and risk pulse. Keep animations bounded to pseudo-elements and small dots:

```css
@keyframes radar-sweep {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@keyframes risk-pulse {
  0%, 100% { transform: translate(-50%, -50%) scale(1); opacity: 0.82; }
  50% { transform: translate(-50%, -50%) scale(1.18); opacity: 1; }
}
```

- [ ] **Step 3: Run smoke tests**

Run: `node --test frontend/src/views/patrol/patrolCockpitView.test.mjs`

Expected: PASS.

---

### Task 4: Visual Verification and Final Checks

**Files:**
- Verify: `frontend/src/views/patrol/PatrolCockpitView.vue`
- Verify: `frontend/src/utils/patrolCommand.ts`

- [ ] **Step 1: Run focused automated checks**

Run:

```bash
node --test frontend/src/utils/patrolCommand.test.mjs
node --test frontend/src/views/patrol/patrolCockpitView.test.mjs
```

Expected: PASS.

- [ ] **Step 2: Run build and document baseline failures**

Run: `npm run build` from `frontend`.

Expected: It may still fail on baseline project errors unrelated to this change. If it fails, capture the first several errors and state that the same baseline class of failures existed before implementation.

- [ ] **Step 3: Start dev server for visual check**

Run: `npm run dev -- --host 127.0.0.1 --port 3000`.

Expected: Vite serves the app.

- [ ] **Step 4: Inspect with browser**

Open `/patrol/cockpit` in the browser. Verify:

1. Center radar is the strongest visual focus.
2. Top metric rail is readable.
3. Left queue and right distribution/trend explain the radar.
4. Bottom ticker replaces the old table.
5. Reduced-motion CSS exists.
6. No text overlaps at desktop and narrow widths.

- [ ] **Step 5: Commit**

Stage only implementation files:

```bash
git add docs/superpowers/plans/2026-07-07-patrol-cockpit-bigscreen.md frontend/src/utils/patrolCommand.ts frontend/src/utils/patrolCommand.test.mjs frontend/src/views/patrol/PatrolCockpitView.vue frontend/src/views/patrol/patrolCockpitView.test.mjs
git commit -m "feat(patrol): redesign cockpit as immersive bigscreen"
```
