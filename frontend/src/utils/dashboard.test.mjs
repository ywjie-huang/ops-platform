import assert from 'node:assert/strict'
import test from 'node:test'

const {
  buildDashboardFocusItems,
  buildDashboardMetricCards,
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
      badge: item.badge,
      title: item.title,
      action: item.primaryActionPath,
      tone: item.tone,
    })),
    [
      { badge: '高优告警', title: 'API 网关 5xx 告警', action: '/monitoring/alerts', tone: 'danger' },
      { badge: '待办工单', title: '支付链路工单待确认', action: '/tickets', tone: 'warning' },
      { badge: '资产变更', title: 'db-replica-02 进入维护', action: '/assets/list', tone: 'info' },
    ],
  )
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
