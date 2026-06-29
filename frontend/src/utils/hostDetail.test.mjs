import assert from 'node:assert/strict'
import test from 'node:test'

const {
  buildCollectionState,
  buildCurrentJudgment,
  buildHostMetricCards,
  buildHostRecommendations,
  buildRelationCards,
  buildSteadyDetailGroups,
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

  assert.equal(cards[2].detail, '104/200 GB')
  assert.equal(cards[3].detail, '1m 11.2 / 8 核')
  assert.equal(cards[3].barPercent, 100)
})

test('shows disk used capacity alongside total capacity', () => {
  const cards = buildHostMetricCards({
    ...healthyHost,
    disk: { usage: 15, total_gb: 96.5, read_mb_s: 0, write_mb_s: 0.1 },
  })
  const disk = cards.find((card) => card.key === 'disk')

  assert.equal(disk?.detail, '14.5/96.5 GB')

  const explicitUsedCards = buildHostMetricCards({
    ...healthyHost,
    disk: { usage: 15, total_gb: 96.5, used_gb: 13.8, read_mb_s: 0, write_mb_s: 0.1 },
  })
  assert.equal(explicitUsedCards.find((card) => card.key === 'disk')?.detail, '13.8/96.5 GB')
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
    cpu: { usage: 0, cores: 8 },
    memory: { usage: 0, total_gb: 0, used_gb: 0, available_gb: 0 },
    disk: { usage: 0, total_gb: 0, read_mb_s: 0, write_mb_s: 0 },
    network: { in_mbps: 0, out_mbps: 0 },
    load: { '1m': 0, '5m': 0, '15m': 0 },
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

  assert.equal(
    buildHostRecommendations(host).find((item) => item.key === 'notify-owner')?.description,
    '负责人：张三',
  )
  assert.equal(buildHostMetricCards(host).every((card) => (
    card.isMissing && card.tone === 'muted' && card.statusText === '无数据'
  )), true)
})

test('does not report missing metrics as healthy', () => {
  const host = {
    ...healthyHost,
    cpu: undefined,
    memory: undefined,
    disk: undefined,
    load: undefined,
  }

  assert.deepEqual(getHostRiskMeta(host), {
    key: 'offline',
    label: '指标缺失',
    tone: 'muted',
    priority: '需确认',
  })
  assert.deepEqual(buildCurrentJudgment(host), {
    title: '指标数据缺失',
    description: '主机档案可查看，但当前没有足够实时指标用于判断。',
    tone: 'muted',
  })
})

test('treats backend all-zero fallback metrics as missing', () => {
  const host = {
    ...healthyHost,
    cpu: { usage: 0, cores: 0 },
    memory: { usage: 0, total_gb: 0, used_gb: 0, available_gb: 0 },
    disk: { usage: 0, total_gb: 0, read_mb_s: 0, write_mb_s: 0 },
    network: { in_mbps: 0, out_mbps: 0 },
    load: { '1m': 0, '5m': 0, '15m': 0 },
  }

  assert.deepEqual(getHostRiskMeta(host), {
    key: 'offline',
    label: '指标缺失',
    tone: 'muted',
    priority: '需确认',
  })
  assert.equal(buildHostMetricCards(host).every((card) => (
    card.isMissing && card.tone === 'muted' && card.statusText === '无数据'
  )), true)
})

test('marks load as unknown when CPU cores are missing', () => {
  const cards = buildHostMetricCards({
    ...healthyHost,
    cpu: { usage: 42, cores: 0 },
    load: { '1m': 20, '5m': 18, '15m': 15 },
  })
  const load = cards.find((card) => card.key === 'load')

  assert.deepEqual({
    tone: load?.tone,
    statusText: load?.statusText,
    barPercent: load?.barPercent,
    detail: load?.detail,
  }, {
    tone: 'muted',
    statusText: '核心数未知',
    barPercent: 0,
    detail: '1m 20 / - 核',
  })
})

test('does not treat load-only data without cores as healthy', () => {
  const host = {
    ...healthyHost,
    cpu: undefined,
    memory: undefined,
    disk: undefined,
    load: { '1m': 20, '5m': 18, '15m': 15 },
  }

  assert.deepEqual(getHostRiskMeta(host), {
    key: 'offline',
    label: '指标缺失',
    tone: 'muted',
    priority: '需确认',
  })
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

test('shows disk used capacity in steady detail groups', () => {
  const diskGroup = buildSteadyDetailGroups({
    ...healthyHost,
    disk: { usage: 15, total_gb: 96.5, read_mb_s: 0, write_mb_s: 0.1 },
  }).find((group) => group.key === 'diskIo')

  assert.equal(diskGroup?.rows.find((row) => row.label === '容量')?.value, '14.5/96.5 GB')
})

test('formats uptime in compact Chinese text', () => {
  assert.equal(formatHostUptime(0), '-')
  assert.equal(formatHostUptime(8), '8 小时')
  assert.equal(formatHostUptime(53), '2 天 5 小时')
})
