export interface DashboardStatsLike {
  asset_total?: number
  online_hosts?: number
  open_alerts?: number
  pending_tickets?: number
  offline_assets?: number
  maintenance_assets?: number
}

export interface DashboardSparklineLike {
  series?: {
    assets?: number[]
    online?: number[]
    alerts?: number[]
    tickets?: number[]
  }
}

export interface DashboardQuickStatLike {
  label?: string
  value?: string
  hint?: string
  tone?: string
}

export interface DashboardSummaryItemLike {
  title?: string
  meta?: string
  detail?: string
  tag?: string
  tone?: string
}

export interface DashboardTypeBreakdownLike {
  label?: string
  value?: number
  color?: string
}

export interface DashboardSummaryLike {
  quick_stats?: DashboardQuickStatLike[]
  recent_asset_changes?: DashboardSummaryItemLike[]
  recent_tickets?: DashboardSummaryItemLike[]
  recent_alerts?: DashboardSummaryItemLike[]
  type_breakdown?: DashboardTypeBreakdownLike[]
  max_type_value?: number
}

export interface DashboardMetricCard {
  key: string
  label: string
  value: number
  delta: string
  deltaType: 'up' | 'down' | 'flat'
  hint: string
  series: number[]
  lineColor: string
  tone: 'danger' | 'warning' | 'success' | 'info'
}

export interface DashboardFocusItem {
  key: string
  badge: string
  title: string
  meta: string
  detail: string
  tone: 'danger' | 'warning' | 'success' | 'info' | 'muted'
  primaryActionLabel: string
  primaryActionPath: string
  secondaryActionLabel?: string
  secondaryActionPath?: string
  summaryTag: string
}

export type DashboardShortcutKey = 'ssh' | 'batch' | 'patrol' | 'tickets'

export interface DashboardShortcutItem {
  key: DashboardShortcutKey
  label: string
  description: string
  path: string
  tone: 'danger' | 'warning' | 'success' | 'info'
  value: string
  valueLabel: string
}

export interface DashboardTypeRow {
  key: string
  label: string
  value: number
  max: number
  tone: 'blue' | 'violet' | 'cyan' | 'amber' | 'slate'
}

function formatDelta(series: number[] | undefined) {
  if (!series || series.length < 2) {
    return { delta: '—', deltaType: 'flat' as const }
  }

  const previous = Number(series[series.length - 2] || 0)
  const current = Number(series[series.length - 1] || 0)

  if (previous <= 0) {
    if (current > 0) {
      return { delta: `+${current}`, deltaType: 'up' as const }
    }
    return { delta: '—', deltaType: 'flat' as const }
  }

  const pct = Math.round(((current - previous) / previous) * 100)
  if (pct > 0) return { delta: `+${pct}%`, deltaType: 'up' as const }
  if (pct < 0) return { delta: `${pct}%`, deltaType: 'down' as const }
  return { delta: '—', deltaType: 'flat' as const }
}

function ratioLabel(numerator: number, denominator: number) {
  if (!denominator) return '0%'
  return `${Math.round((numerator / denominator) * 100)}%`
}

function toneToPriority(tone?: string) {
  switch (tone) {
    case 'red':
      return 40
    case 'orange':
      return 30
    case 'blue':
    case 'primary':
      return 20
    case 'green':
      return 10
    default:
      return 0
  }
}

function mapTone(tone?: string): DashboardFocusItem['tone'] {
  switch (tone) {
    case 'red':
      return 'danger'
    case 'orange':
      return 'warning'
    case 'green':
      return 'success'
    case 'blue':
    case 'primary':
      return 'info'
    default:
      return 'muted'
  }
}

function normalizeText(value?: string, fallback = '暂无信息') {
  return String(value || '').trim() || fallback
}

function buildFocusEntry(
  source: 'alert' | 'ticket' | 'asset',
  item: DashboardSummaryItemLike,
): DashboardFocusItem {
  if (source === 'alert') {
    return {
      key: `alert-${normalizeText(item.title)}`,
      badge: item.tone === 'red' ? '高优告警' : '告警',
      title: normalizeText(item.title),
      meta: normalizeText(item.meta),
      detail: normalizeText(item.detail),
      tone: mapTone(item.tone),
      primaryActionLabel: '查看告警列表',
      primaryActionPath: '/monitoring/alerts',
      secondaryActionLabel: '打开主机监控',
      secondaryActionPath: '/monitoring/hosts',
      summaryTag: normalizeText(item.tag, '告警'),
    }
  }

  if (source === 'ticket') {
    return {
      key: `ticket-${normalizeText(item.title)}`,
      badge: item.tone === 'orange' ? '待办工单' : '工单',
      title: normalizeText(item.title),
      meta: normalizeText(item.meta),
      detail: normalizeText(item.detail),
      tone: mapTone(item.tone),
      primaryActionLabel: '进入工单队列',
      primaryActionPath: '/tickets',
      summaryTag: normalizeText(item.tag, '工单'),
    }
  }

  return {
    key: `asset-${normalizeText(item.title)}`,
    badge: item.tone === 'red' || item.tone === 'orange' ? '资产异常' : '资产变更',
    title: normalizeText(item.title),
    meta: normalizeText(item.meta),
    detail: normalizeText(item.detail),
    tone: mapTone(item.tone),
    primaryActionLabel: '查看资产列表',
    primaryActionPath: '/assets/list',
    secondaryActionLabel: '打开主机监控',
    secondaryActionPath: '/monitoring/hosts',
    summaryTag: normalizeText(item.tag, '资产'),
  }
}

export function buildDashboardMetricCards(
  stats: DashboardStatsLike,
  sparkline: DashboardSparklineLike,
): DashboardMetricCard[] {
  const series = sparkline.series || {}
  const openAlerts = Number(stats.open_alerts || 0)
  const pendingTickets = Number(stats.pending_tickets || 0)
  const onlineHosts = Number(stats.online_hosts || 0)
  const totalAssets = Number(stats.asset_total || 0)
  const maintenanceAssets = Number(stats.maintenance_assets || 0)
  const offlineAssets = Number(stats.offline_assets || 0)

  return [
    {
      key: 'alerts',
      label: '待处理告警',
      value: openAlerts,
      hint: openAlerts ? `${openAlerts} 条待处理告警需要继续跟进` : '当前没有待处理告警',
      series: series.alerts || [],
      lineColor: '#e5484d',
      tone: 'danger',
      ...formatDelta(series.alerts),
    },
    {
      key: 'tickets',
      label: '处理中工单',
      value: pendingTickets,
      hint: pendingTickets ? `${pendingTickets} 个 open / in_progress 工单待推进` : '当前没有阻塞中的工单',
      series: series.tickets || [],
      lineColor: '#f5a623',
      tone: 'warning',
      ...formatDelta(series.tickets),
    },
    {
      key: 'online',
      label: '在线主机',
      value: onlineHosts,
      hint: `总资产 ${totalAssets} 台 · 在线率 ${ratioLabel(onlineHosts, totalAssets)}`,
      series: series.online || [],
      lineColor: '#22c55e',
      tone: 'success',
      ...formatDelta(series.online),
    },
    {
      key: 'maintenance',
      label: '维护资产',
      value: maintenanceAssets,
      hint: offlineAssets ? `另有 ${offlineAssets} 台处于离线或停用状态` : '当前没有额外离线资产',
      series: series.assets || [],
      lineColor: '#5e6ad2',
      tone: 'info',
      ...formatDelta(series.assets),
    },
  ]
}

export function buildDashboardFocusItems(summary: DashboardSummaryLike): DashboardFocusItem[] {
  const alerts = (summary.recent_alerts || []).map((item) => ({ source: 'alert' as const, item, weight: 300 }))
  const tickets = (summary.recent_tickets || []).map((item) => ({ source: 'ticket' as const, item, weight: 200 }))
  const assets = (summary.recent_asset_changes || []).map((item) => ({ source: 'asset' as const, item, weight: 100 }))

  return [...alerts, ...tickets, ...assets]
    .sort((a, b) => {
      const priorityDiff = toneToPriority(b.item.tone) + b.weight - (toneToPriority(a.item.tone) + a.weight)
      if (priorityDiff !== 0) return priorityDiff
      return normalizeText(a.item.title).localeCompare(normalizeText(b.item.title), 'zh-CN')
    })
    .slice(0, 4)
    .map(({ source, item }) => buildFocusEntry(source, item))
}

export function buildDashboardShortcutItems(stats: DashboardStatsLike): DashboardShortcutItem[] {
  const onlineHosts = Number(stats.online_hosts || 0)
  const totalAssets = Number(stats.asset_total || 0)
  const openAlerts = Number(stats.open_alerts || 0)
  const pendingTickets = Number(stats.pending_tickets || 0)
  const maintenanceAssets = Number(stats.maintenance_assets || 0)

  return [
    {
      key: 'ssh',
      label: 'SSH 终端',
      description: '从在线主机直接进入排障，适合作为值班处理的第一跳。',
      path: '/monitoring/hosts',
      tone: 'info',
      value: `${onlineHosts}/${totalAssets || 0}`,
      valueLabel: '在线 / 总资产',
    },
    {
      key: 'batch',
      label: '批量执行',
      description: '适合批量核查告警关联节点，减少重复登录与逐台排查。',
      path: '/batch-exec',
      tone: 'warning',
      value: String(openAlerts),
      valueLabel: '待检查告警',
    },
    {
      key: 'patrol',
      label: '巡检任务',
      description: '巡检回放与维护窗口联动信息集中在这里，适合看整体状态。',
      path: '/patrol',
      tone: 'success',
      value: String(maintenanceAssets),
      valueLabel: '维护资产',
    },
    {
      key: 'tickets',
      label: '工单中心',
      description: '查看阻塞中的协作项和正在推进的处理单，减少跨页切换。',
      path: '/tickets',
      tone: 'danger',
      value: String(pendingTickets),
      valueLabel: '待推进工单',
    },
  ]
}

export function buildDashboardTypeRows(summary: DashboardSummaryLike): DashboardTypeRow[] {
  const max = Number(summary.max_type_value || 1) || 1

  return (summary.type_breakdown || []).map((item) => {
    let tone: DashboardTypeRow['tone'] = 'slate'
    switch (item.color) {
      case '#3b82f6':
        tone = 'blue'
        break
      case '#8b5cf6':
        tone = 'violet'
        break
      case '#06b6d4':
        tone = 'cyan'
        break
      case '#f59e0b':
        tone = 'amber'
        break
      default:
        tone = 'slate'
    }

    return {
      key: `${normalizeText(item.label)}-${item.value || 0}`,
      label: normalizeText(item.label),
      value: Number(item.value || 0),
      max,
      tone,
    }
  })
}
