import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'

const dashboardView = readFileSync(new URL('./DashboardView.vue', import.meta.url), 'utf8')

test('dashboard view uses the approved event-command-center hierarchy', () => {
  assert.match(dashboardView, /事件指挥台/)
  assert.match(dashboardView, /优先事件队列/)
  assert.match(dashboardView, /影响与处置/)
  assert.match(dashboardView, /资源健康/)
  assert.match(dashboardView, /值班动作/)
  assert.match(dashboardView, /最近活动/)
  assert.match(dashboardView, /10 秒发现异常/)
  assert.doesNotMatch(dashboardView, /Dashboard Preview \/ Duty First/)
  assert.doesNotMatch(dashboardView, /这个首页直接按预览稿的逻辑展开/)
})

test('dashboard view consumes the resource-health endpoint without blocking core data', () => {
  assert.match(dashboardView, /getDashboardResourceHealth/)
  assert.match(dashboardView, /buildDashboardResourceRows/)
  assert.match(dashboardView, /CPU（容量加权）/)
  assert.match(dashboardView, /内存（总体使用）/)
  assert.match(dashboardView, /P95/)
  assert.match(dashboardView, /resourceError/)
  assert.match(dashboardView, /Promise\.allSettled/)
})

test('dashboard view provides truthful incident inspection and navigation actions', () => {
  assert.match(dashboardView, /eventDrawerOpen/)
  assert.match(dashboardView, /事件详情/)
  assert.match(dashboardView, /查看告警事件/)
  assert.match(dashboardView, /进入工单队列/)
  assert.doesNotMatch(dashboardView, /认领事件/)
})

test('dashboard lifecycle refresh follows keep-alive conventions', () => {
  assert.match(dashboardView, /onActivated/)
  assert.match(dashboardView, /onDeactivated/)
  assert.match(dashboardView, /refreshDashboard/)
})
