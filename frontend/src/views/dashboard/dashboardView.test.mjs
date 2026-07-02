import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'

const dashboardView = readFileSync(new URL('./DashboardView.vue', import.meta.url), 'utf8')

test('dashboard view promotes duty-first sections instead of a generic welcome summary', () => {
  assert.match(dashboardView, /今日关注/)
  assert.match(dashboardView, /值班视角摘要/)
  assert.match(dashboardView, /处置入口/)
  assert.doesNotMatch(dashboardView, /\{\{\s*greeting\s*\}\}/)
})

test('dashboard view consumes summary alert and ticket data for focus content', () => {
  assert.match(dashboardView, /getDashboardSummary/)
  assert.match(dashboardView, /const summary = ref<DashboardSummaryLike>\(\{\}\)/)
  assert.match(dashboardView, /buildDashboardFocusItems/)
  assert.match(dashboardView, /const focusItems = computed\(\(\) => buildDashboardFocusItems\(summary\.value\)\)/)
  assert.match(dashboardView, /filteredFocusItems/)
})

test('dashboard view now uses the preview layout vocabulary directly', () => {
  assert.match(dashboardView, /class="risk-strip"/)
  assert.match(dashboardView, /class="main-grid"/)
  assert.match(dashboardView, /class="mini-grid"/)
  assert.match(dashboardView, /class="segmented"/)
  assert.match(dashboardView, /class="duty-card"/)
  assert.match(dashboardView, /class="asset-list"/)
})
