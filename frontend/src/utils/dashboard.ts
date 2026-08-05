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
  merged_count?: number
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

export type DashboardFocusSource = 'alert' | 'ticket' | 'asset'
export type DashboardFocusFilterKey = 'all' | 'high' | 'ticket' | 'asset'

export interface DashboardFocusItem {
  key: string
  source: DashboardFocusSource
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
  mergedCount?: number
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
  source: DashboardFocusSource,
  item: DashboardSummaryItemLike,
): DashboardFocusItem {
  if (source === 'alert') {
    const isResolved = item.tag === 'resolved'
    const mergedCount = Number(item.merged_count || 1)
    return {
      key: `alert-${normalizeText(item.title)}`,
      source,
      badge: isResolved ? '已恢复' : item.tone === 'red' ? '高优告警' : '告警',
      title: normalizeText(item.title),
      meta: normalizeText(item.meta),
      detail: normalizeText(item.detail),
      tone: isResolved ? 'muted' : mapTone(item.tone),
      primaryActionLabel: '查看告警事件',
      primaryActionPath: '/monitoring/events',
      secondaryActionLabel: '打开主机监控',
      secondaryActionPath: '/monitoring/hosts',
      summaryTag: isResolved ? '已恢复' : normalizeText(item.tag, '告警'),
      mergedCount: mergedCount > 1 ? mergedCount : undefined,
    }
  }

  if (source === 'ticket') {
    return {
      key: `ticket-${normalizeText(item.title)}`,
      source,
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
    source,
    badge: item.tone === 'red' || item.tone === 'orange' ? '资产异常' : '资产变更',
    title: normalizeText(item.title),
    meta: normalizeText(item.meta),
    detail: normalizeText(item.detail),
    tone: mapTone(item.tone),
    primaryActionLabel: '查看资产列表',
    primaryActionPath: '/assets/hosts',
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
  const alerts = (summary.recent_alerts || []).map((item) => ({
    source: 'alert' as const,
    item,
    // 已恢复告警不再占用优先槽位，降级置底展示
    weight: item.tag === 'resolved' ? 0 : 300,
  }))
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

export function filterDashboardFocusItems(
  items: DashboardFocusItem[],
  key: DashboardFocusFilterKey,
): DashboardFocusItem[] {
  if (key === 'all') return items
  if (key === 'high') return items.filter((item) => item.tone === 'danger')
  return items.filter((item) => item.source === key)
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

export interface DashboardHostPoolLike {
  total?: number
  monitored?: number
  unmonitored?: number
  coverage?: number
  status?: 'healthy' | 'warning' | 'critical' | 'unknown'
  cpu_usage?: number | null
  cpu_p95?: number | null
  cpu_hot_hosts?: number
  cpu_cores?: number
  memory_usage?: number | null
  memory_p95?: number | null
  memory_hot_hosts?: number
  memory_total_gb?: number
  disk_usage?: number | null
  disk_p95?: number | null
  disk_hot_hosts?: number
  disk_total_gb?: number
}

export interface DashboardResourceHealthLike {
  host_pool?: DashboardHostPoolLike
}

export interface DashboardResourceRow {
  key: 'cpu' | 'memory' | 'disk'
  label: string
  value: number | null
  valueLabel: string
  p95: number | null
  p95Label: string
  hotHosts: number
  hotHostLabel: string
  threshold: number
  detail: string
  tone: 'danger' | 'warning' | 'success' | 'muted'
}

export interface DashboardHealthMetric {
  key: 'health' | 'alerts' | 'tickets' | 'degraded' | 'online'
  label: string
  value: string
  unit?: string
  hint: string
  tone: 'danger' | 'warning' | 'success' | 'info'
}

function optionalNumber(value: unknown): number | null {
  if (value === null || value === undefined || value === '') return null
  const number = Number(value)
  return Number.isFinite(number) ? number : null
}

function formatPercent(value: number | null) {
  return value === null ? '—' : `${value.toFixed(1)}%`
}

function formatCapacity(totalGb: number | null) {
  if (totalGb === null || totalGb <= 0) return '容量数据不可用'
  if (totalGb >= 1024) return `总容量 ${(totalGb / 1024).toFixed(1)} TiB`
  return `总容量 ${totalGb.toFixed(1)} GiB`
}

function resourceTone(
  value: number | null,
  p95: number | null,
  hotHosts: number,
  warningThreshold: number,
): DashboardResourceRow['tone'] {
  if (value === null && p95 === null) return 'muted'
  if ((value ?? 0) >= 90 || (p95 ?? 0) >= 95) return 'danger'
  if ((value ?? 0) >= warningThreshold || hotHosts > 0) return 'warning'
  return 'success'
}

export function buildDashboardResourceRows(
  resourceHealth?: DashboardResourceHealthLike,
): DashboardResourceRow[] {
  const pool = resourceHealth?.host_pool
  const cpuUsage = optionalNumber(pool?.cpu_usage)
  const cpuP95 = optionalNumber(pool?.cpu_p95)
  const cpuHotHosts = Number(pool?.cpu_hot_hosts || 0)
  const memoryUsage = optionalNumber(pool?.memory_usage)
  const memoryP95 = optionalNumber(pool?.memory_p95)
  const memoryHotHosts = Number(pool?.memory_hot_hosts || 0)
  const diskUsage = optionalNumber(pool?.disk_usage)
  const diskP95 = optionalNumber(pool?.disk_p95)
  const diskHotHosts = Number(pool?.disk_hot_hosts || 0)

  return [
    {
      key: 'cpu',
      label: 'CPU（容量加权）',
      value: cpuUsage,
      valueLabel: formatPercent(cpuUsage),
      p95: cpuP95,
      p95Label: formatPercent(cpuP95),
      hotHosts: cpuHotHosts,
      hotHostLabel: `${cpuHotHosts} 台 ≥ 80%`,
      threshold: 80,
      detail: pool?.cpu_cores
        ? `按 ${Number(pool.cpu_cores).toLocaleString('en-US')} 核容量加权`
        : '核心容量数据不可用',
      tone: resourceTone(cpuUsage, cpuP95, cpuHotHosts, 80),
    },
    {
      key: 'memory',
      label: '内存（总体使用）',
      value: memoryUsage,
      valueLabel: formatPercent(memoryUsage),
      p95: memoryP95,
      p95Label: formatPercent(memoryP95),
      hotHosts: memoryHotHosts,
      hotHostLabel: `${memoryHotHosts} 台 ≥ 85%`,
      threshold: 85,
      detail: formatCapacity(optionalNumber(pool?.memory_total_gb)),
      tone: resourceTone(memoryUsage, memoryP95, memoryHotHosts, 85),
    },
    {
      key: 'disk',
      label: '根分区（总体使用）',
      value: diskUsage,
      valueLabel: formatPercent(diskUsage),
      p95: diskP95,
      p95Label: formatPercent(diskP95),
      hotHosts: diskHotHosts,
      hotHostLabel: `${diskHotHosts} 台 ≥ 85%`,
      threshold: 85,
      detail: formatCapacity(optionalNumber(pool?.disk_total_gb)),
      tone: resourceTone(diskUsage, diskP95, diskHotHosts, 85),
    },
  ]
}

export function buildDashboardHealthMetrics(
  stats: DashboardStatsLike,
  resourceHealth?: DashboardResourceHealthLike,
): DashboardHealthMetric[] {
  const total = Number(stats.asset_total || 0)
  const online = Number(stats.online_hosts || 0)
  const alerts = Number(stats.open_alerts || 0)
  const tickets = Number(stats.pending_tickets || 0)
  const offline = Number(stats.offline_assets || 0)
  const maintenance = Number(stats.maintenance_assets || 0)
  const degraded = offline + maintenance
  const pool = resourceHealth?.host_pool
  const hasResourceData = Boolean(pool)
  const hotspotPenalty = Math.min(10,
    Number(pool?.cpu_hot_hosts || 0)
      + Number(pool?.memory_hot_hosts || 0)
      + Number(pool?.disk_hot_hosts || 0),
  )
  const coveragePenalty = pool && Number(pool.coverage || 0) < 90 ? 5 : 0
  const score = Math.max(0, Math.min(100,
    100
      - Math.min(32, alerts * 4)
      - Math.min(16, tickets)
      - Math.min(24, degraded * 4)
      - hotspotPenalty
      - coveragePenalty,
  ))
  const onlineRate = total > 0 ? Math.round((online / total) * 100) : 0

  return [
    {
      key: 'health',
      label: '运行健康度',
      value: String(score),
      unit: '/100',
      hint: hasResourceData
        ? '综合告警、工单、资产与资源热点'
        : '资源数据不可用，当前仅综合告警、工单与资产状态',
      tone: score >= 90 ? 'success' : score >= 70 ? 'warning' : 'danger',
    },
    {
      key: 'alerts',
      label: '待处理告警',
      value: String(alerts),
      hint: '待确认与已确认告警',
      tone: alerts > 0 ? 'danger' : 'success',
    },
    {
      key: 'tickets',
      label: '待办工单',
      value: String(tickets),
      hint: '待处理与处理中工单',
      tone: tickets > 0 ? 'warning' : 'success',
    },
    {
      key: 'degraded',
      label: '降级资产',
      value: String(degraded),
      hint: `已删除 ${offline} · 已关机 ${maintenance}`,
      tone: degraded > 0 ? 'warning' : 'success',
    },
    {
      key: 'online',
      label: '资产在线率',
      value: `${onlineRate}%`,
      hint: total > 0 ? `${online}/${total} 资产使用中` : '暂无资产',
      tone: total === 0 ? 'info' : onlineRate >= 95 ? 'success' : onlineRate >= 80 ? 'info' : 'danger',
    },
  ]
}
