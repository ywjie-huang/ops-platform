import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'

const cockpitView = readFileSync(new URL('./PatrolCockpitView.vue', import.meta.url), 'utf8')

test('patrol cockpit uses immersive bigscreen layout vocabulary', () => {
  assert.match(cockpitView, /class="patrol-cockpit bigscreen-shell"/)
  assert.match(cockpitView, /class="metric-rail"/)
  assert.match(cockpitView, /class="bigscreen-panel radar-stage"/)
  assert.match(cockpitView, /class="bigscreen-panel risk-queue"/)
  assert.match(cockpitView, /class="battle-ticker"/)
})

test('patrol cockpit keeps reduced motion and accessible radar semantics', () => {
  assert.match(cockpitView, /prefers-reduced-motion/)
  assert.match(cockpitView, /role="img"/)
  assert.match(cockpitView, /aria-label=/)
})

test('patrol cockpit keeps desktop command layout at 1280 and compresses below it', () => {
  assert.doesNotMatch(cockpitView, /@media \(max-width: 1280px\)/)
  assert.match(cockpitView, /@media \(max-width: 1180px\)[\s\S]*\.metric-rail[\s\S]*repeat\(3, minmax\(0, 1fr\)\)/)
})

test('patrol cockpit shell does not create horizontal page overflow', () => {
  assert.doesNotMatch(cockpitView, /margin:\s*-4px;/)
})
