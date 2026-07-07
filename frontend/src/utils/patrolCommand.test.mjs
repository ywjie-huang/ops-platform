import assert from 'node:assert/strict'
import { test } from 'node:test'

const {
  buildObjectCounts,
  buildCockpitRouteLocation,
  buildCockpitStats,
  buildPager,
  buildPatrolOverview,
  buildRadarObjects,
  buildRiskObjects,
  buildTickerItems,
  getPatrolPriority,
  paginateRiskObjects,
  statusLabel,
  statusTone,
} = await import('./patrolCommand.ts')

const report = {
  status: 'critical',
  total_checks: 8,
  normal_count: 4,
  warning_count: 2,
  critical_count: 2,
}

const items = [
  { category: 'host', target_name: 'web-01', target_ip: '10.0.0.1', check_name: '磁盘使用率', status: 'critical', value: '92%', threshold: '严重 90%', detail: '/data 分区过高' },
  { category: 'host', target_name: 'web-01', target_ip: '10.0.0.1', check_name: 'CPU 使用率', status: 'warning', value: '86%', threshold: '警告 80%', detail: '持续 10 分钟' },
  { category: 'host', target_name: 'db-02', target_ip: '10.0.0.2', check_name: '系统负载', status: 'critical', value: '12.8', threshold: '严重 10', detail: '数据库负载过高' },
  { category: 'k8s', target_name: 'k8s-prod', target_ip: '', check_name: 'Pod 重启', status: 'warning', value: '6 次', threshold: '警告 3 次', detail: 'payment-worker 重启频繁' },
  { category: 'asset', target_name: 'cert-api', target_ip: '', check_name: '证书有效期', status: 'normal', value: '120 天', threshold: '警告 15 天', detail: '证书有效' },
]

test('summarizes patrol report counts and priority state', () => {
  assert.deepEqual(buildPatrolOverview(report), {
    total: 8,
    normal: 4,
    warning: 2,
    critical: 2,
    abnormal: 4,
    healthScore: 55,
    priority: 'P1',
    priorityLabel: '需处置',
    status: 'critical',
  })

  assert.equal(getPatrolPriority(report), 'P1')
  assert.equal(statusLabel('warning'), '警告')
  assert.equal(statusTone('critical'), 'danger')
})

test('groups patrol items into risk objects ordered by severity and category', () => {
  const objects = buildRiskObjects(items)

  assert.deepEqual(objects.map((item) => ({
    key: item.key,
    category: item.category,
    targetName: item.targetName,
    critical: item.critical,
    warning: item.warning,
    status: item.status,
    priority: item.priority,
    headline: item.headline,
  })), [
    {
      key: 'host::web-01',
      category: 'host',
      targetName: 'web-01',
      critical: 1,
      warning: 1,
      status: 'critical',
      priority: 'P1',
      headline: '磁盘使用率 92%',
    },
    {
      key: 'host::db-02',
      category: 'host',
      targetName: 'db-02',
      critical: 1,
      warning: 0,
      status: 'critical',
      priority: 'P1',
      headline: '系统负载 12.8',
    },
    {
      key: 'k8s::k8s-prod',
      category: 'k8s',
      targetName: 'k8s-prod',
      critical: 0,
      warning: 1,
      status: 'warning',
      priority: 'P2',
      headline: 'Pod 重启 6 次',
    },
    {
      key: 'asset::cert-api',
      category: 'asset',
      targetName: 'cert-api',
      critical: 0,
      warning: 0,
      status: 'normal',
      priority: '正常',
      headline: '证书有效期 120 天',
    },
  ])
})

test('builds compact count badges that only keep non-zero states', () => {
  assert.deepEqual(buildObjectCounts({ critical: 0, warning: 1, normal: 0 }), [
    { tone: 'warning', value: 1, label: '警告' },
  ])

  assert.deepEqual(buildObjectCounts({ critical: 2, warning: 0, normal: 4 }), [
    { tone: 'danger', value: 2, label: '严重' },
    { tone: 'success', value: 4, label: '正常' },
  ])

  assert.deepEqual(buildObjectCounts({ critical: 0, warning: 0, normal: 0 }), [
    { tone: 'success', value: 0, label: '正常' },
  ])
})

test('builds cockpit route location with selected report id when available', () => {
  assert.deepEqual(buildCockpitRouteLocation({ id: 42, title: '巡检报告 A' }), {
    path: '/patrol/cockpit',
    query: { reportId: '42' },
  })

  assert.deepEqual(buildCockpitRouteLocation(null), {
    path: '/patrol/cockpit',
  })
})

test('paginates risk objects with five records per page and clamps invalid pages', () => {
  const objects = Array.from({ length: 12 }, (_, index) => ({
    key: `host::node-${index + 1}`,
    targetName: `node-${index + 1}`,
  }))

  assert.deepEqual(paginateRiskObjects(objects, 1).items.map((item) => item.targetName), [
    'node-1',
    'node-2',
    'node-3',
    'node-4',
    'node-5',
  ])

  assert.deepEqual(paginateRiskObjects(objects, 3), {
    items: [
      { key: 'host::node-11', targetName: 'node-11' },
      { key: 'host::node-12', targetName: 'node-12' },
    ],
    page: 3,
    pageSize: 5,
    total: 12,
    totalPages: 3,
  })

  assert.equal(paginateRiskObjects(objects, 99).page, 3)
  assert.equal(paginateRiskObjects(objects, -1).page, 1)
})

test('builds pager metadata for server-paginated lists and clamps invalid pages', () => {
  assert.deepEqual(buildPager(12, 2, 5), {
    page: 2,
    pageSize: 5,
    total: 12,
    totalPages: 3,
  })

  assert.deepEqual(buildPager(0, 0, 5), {
    page: 1,
    pageSize: 5,
    total: 0,
    totalPages: 1,
  })

  assert.equal(buildPager(12, 99, 5).page, 3)
  assert.equal(buildPager(12, -1, 5).page, 1)
})

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
