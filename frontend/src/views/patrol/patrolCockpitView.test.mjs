import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'

const cockpitView = readFileSync(new URL('./PatrolCockpitView.vue', import.meta.url), 'utf8')

test('patrol cockpit uses immersive bigscreen layout vocabulary', () => {
  assert.match(cockpitView, /class="cockpit"/)
  assert.match(cockpitView, /class="main"/)
  assert.match(cockpitView, /class="panel gauge-panel/)
  assert.match(cockpitView, /class="panel trend-panel/)
  assert.match(cockpitView, /class="panel rank-panel/)
})

test('patrol cockpit keeps reduced motion and accessible radar semantics', () => {
  assert.match(cockpitView, /prefers-reduced-motion/)
  assert.match(cockpitView, /aria-label="全局健康指数"/)
  assert.match(cockpitView, /aria-label="健康分走势"/)
  assert.match(cockpitView, /role="alert"/)
})

test('patrol cockpit keeps desktop command layout at 1280 and compresses below it', () => {
  assert.doesNotMatch(cockpitView, /@media \(max-width: 1280px\)/)
  assert.match(cockpitView, /@media \(max-width: 1200px\)[\s\S]*\.main\s*\{[\s\S]*grid-template-columns: 1fr;/)
  assert.match(cockpitView, /@media \(max-width: 1200px\)[\s\S]*\.queue\s*\{[\s\S]*max-height: 420px;/)
})

test('patrol cockpit shell does not create horizontal page overflow', () => {
  assert.doesNotMatch(cockpitView, /margin:\s*-4px;/)
})
