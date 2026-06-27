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
