import assert from 'node:assert/strict'
import test from 'node:test'

const {
  buildDashboardFocusItems,
  filterDashboardFocusItems,
  buildDashboardHealthMetrics,
  buildDashboardMetricCards,
  buildDashboardResourceRows,
  buildDashboardShortcutItems,
  buildDashboardTypeRows,
} = await import('./dashboard.ts')

test('builds duty-first focus items from summary alerts, tickets, and asset changes', () => {
  const items = buildDashboardFocusItems({
    recent_alerts: [
      {
        title: 'API 网关 5xx 告警',
        meta: 'prod-gateway-01',
        detail: '错误率持续上升，需要先确认入口流量与后端依赖。',
        tag: 'P1',
        tone: 'red',
      },
    ],
    recent_tickets: [
      {
        title: '支付链路工单待确认',
        meta: '创建于 10:24',
        detail: '业务方催办，需要同步当前恢复进度。',
        tag: '阻塞',
        tone: 'orange',
      },
    ],
    recent_asset_changes: [
      {
        title: 'db-replica-02 进入维护',
        meta: '维护窗口 11:00 - 12:00',
        detail: '值班期间留意主从切换和备份任务状态。',
        tag: '维护',
        tone: 'blue',
      },
    ],
  })

  assert.deepEqual(
    items.map((item) => ({
      source: item.source,
      badge: item.badge,
      title: item.title,
      action: item.primaryActionPath,
      tone: item.tone,
    })),
    [
      { source: 'alert', badge: '高优告警', title: 'API 网关 5xx 告警', action: '/monitoring/events', tone: 'danger' },
      { source: 'ticket', badge: '待办工单', title: '支付链路工单待确认', action: '/tickets', tone: 'warning' },
      { source: 'asset', badge: '资产变更', title: 'db-replica-02 进入维护', action: '/assets/hosts', tone: 'info' },
    ],
  )
})

test('filters focus items by priority or event source instead of display tone', () => {
  const items = buildDashboardFocusItems({
    recent_alerts: [
      { title: '普通告警', tone: 'orange' },
      { title: '高优告警', tone: 'red' },
    ],
    recent_tickets: [
      { title: '普通工单', tone: 'blue' },
    ],
    recent_asset_changes: [
      { title: '异常资产', tone: 'red' },
    ],
  })

  assert.deepEqual(filterDashboardFocusItems(items, 'ticket').map((item) => item.title), ['普通工单'])
  assert.deepEqual(filterDashboardFocusItems(items, 'asset').map((item) => item.title), ['异常资产'])
  assert.deepEqual(
    filterDashboardFocusItems(items, 'high').map((item) => item.title),
    ['高优告警', '异常资产'],
  )
  assert.equal(filterDashboardFocusItems(items, 'all').length, 4)
})

test('builds metric cards, shortcuts, and type rows from dashboard aggregates', () => {
  const metricCards = buildDashboardMetricCards(
    {
      asset_total: 24,
      online_hosts: 22,
      open_alerts: 3,
      pending_tickets: 5,
      offline_assets: 1,
      maintenance_assets: 2,
    },
    {
      series: {
        assets: [1, 2],
        online: [21, 22],
        alerts: [5, 3],
        tickets: [4, 5],
      },
    },
  )

  assert.deepEqual(
    metricCards.map((item) => ({
      key: item.key,
      value: item.value,
      delta: item.delta,
      tone: item.tone,
    })),
    [
      { key: 'alerts', value: 3, delta: '-40%', tone: 'danger' },
      { key: 'tickets', value: 5, delta: '+25%', tone: 'warning' },
      { key: 'online', value: 22, delta: '+5%', tone: 'success' },
      { key: 'maintenance', value: 2, delta: '+100%', tone: 'info' },
    ],
  )

  assert.deepEqual(
    buildDashboardShortcutItems({
      asset_total: 24,
      online_hosts: 22,
      open_alerts: 3,
      pending_tickets: 5,
      maintenance_assets: 2,
    }).map((item) => ({
      key: item.key,
      path: item.path,
      value: item.value,
    })),
    [
      { key: 'ssh', path: '/monitoring/hosts', value: '22/24' },
      { key: 'batch', path: '/batch-exec', value: '3' },
      { key: 'patrol', path: '/patrol', value: '2' },
      { key: 'tickets', path: '/tickets', value: '5' },
    ],
  )

  assert.deepEqual(
    buildDashboardTypeRows({
      max_type_value: 10,
      type_breakdown: [
        { label: 'Linux', value: 10, color: '#3b82f6' },
        { label: 'Kubernetes', value: 6, color: '#06b6d4' },
        { label: 'Other', value: 2, color: '#000000' },
      ],
    }).map((item) => ({
      label: item.label,
      value: item.value,
      max: item.max,
      tone: item.tone,
    })),
    [
      { label: 'Linux', value: 10, max: 10, tone: 'blue' },
      { label: 'Kubernetes', value: 6, max: 10, tone: 'cyan' },
      { label: 'Other', value: 2, max: 10, tone: 'slate' },
    ],
  )
})

test('builds explicit weighted resource rows with P95 and hotspot counts', () => {
  const rows = buildDashboardResourceRows({
    host_pool: {
      total: 128,
      monitored: 124,
      unmonitored: 4,
      coverage: 96.9,
      cpu_usage: 61,
      cpu_p95: 84,
      cpu_hot_hosts: 6,
      cpu_cores: 1024,
      memory_usage: 68,
      memory_p95: 89,
      memory_hot_hosts: 4,
      memory_total_gb: 4096,
      disk_usage: 52,
      disk_p95: 82,
      disk_hot_hosts: 2,
      disk_total_gb: 80000,
    },
  })

  assert.deepEqual(
    rows.map((row) => ({
      key: row.key,
      label: row.label,
      valueLabel: row.valueLabel,
      p95Label: row.p95Label,
      hotHostLabel: row.hotHostLabel,
      detail: row.detail,
    })),
    [
      {
        key: 'cpu',
        label: 'CPU（容量加权）',
        valueLabel: '61.0%',
        p95Label: '84.0%',
        hotHostLabel: '6 台 ≥ 80%',
        detail: '按 1,024 核容量加权',
      },
      {
        key: 'memory',
        label: '内存（总体使用）',
        valueLabel: '68.0%',
        p95Label: '89.0%',
        hotHostLabel: '4 台 ≥ 85%',
        detail: '总容量 4.0 TiB',
      },
      {
        key: 'disk',
        label: '根分区（总体使用）',
        valueLabel: '52.0%',
        p95Label: '82.0%',
        hotHostLabel: '2 台 ≥ 85%',
        detail: '总容量 78.1 TiB',
      },
    ],
  )
})

test('surfaces merge-count badge and degrades resolved alerts to the bottom', () => {
  const items = buildDashboardFocusItems({
    recent_alerts: [
      { title: 'k8s CPU 告警', tone: 'red', tag: 'firing', merged_count: 2 },
      { title: 'db-slave 主从延迟', tone: 'green', tag: 'resolved' },
    ],
    recent_tickets: [
      { title: '生产环境磁盘扩容', tone: 'orange' },
    ],
  })

  // firing 告警置顶，带合并角标
  assert.equal(items[0].title, 'k8s CPU 告警')
  assert.equal(items[0].badge, '高优告警')
  assert.equal(items[0].tone, 'danger')
  assert.equal(items[0].mergedCount, 2)

  // resolved 告警降级为 muted、无角标，并排在工单之后
  const resolved = items.find((item) => item.title === 'db-slave 主从延迟')
  assert.equal(resolved.badge, '已恢复')
  assert.equal(resolved.tone, 'muted')
  assert.equal(resolved.mergedCount, undefined)

  const ticketIndex = items.findIndex((item) => item.source === 'ticket')
  const resolvedIndex = items.findIndex((item) => item === resolved)
  assert.ok(resolvedIndex > ticketIndex, '已恢复告警应排在工单之后')
})

test('resource rows and health metrics degrade truthfully when aggregate data is unavailable', () => {
  const rows = buildDashboardResourceRows(undefined)
  assert.equal(rows.length, 3)
  assert.ok(rows.every((row) => row.value === null && row.valueLabel === '—'))

  const metrics = buildDashboardHealthMetrics(
    {
      asset_total: 20,
      online_hosts: 17,
      open_alerts: 2,
      pending_tickets: 4,
      offline_assets: 1,
      maintenance_assets: 2,
    },
    undefined,
  )

  assert.equal(metrics[0].label, '运行健康度')
  assert.equal(metrics[0].value, '76')
  assert.equal(metrics[1].value, '2')
  assert.equal(metrics[3].value, '3')
  assert.equal(metrics[4].value, '85%')
})
