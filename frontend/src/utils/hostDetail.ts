type Tone = 'success' | 'warning' | 'danger' | 'muted'
type RiskKey = 'healthy' | 'warning' | 'critical' | 'offline'
type MetricKey = 'cpu' | 'memory' | 'disk' | 'load'

export type HostDetailLike = {
  id?: number
  hostname?: string
  ip?: string
  spec?: string
  os_info?: string
  owner?: string
  status?: string
  uptime_hours?: number
  prometheus_ok?: boolean
  tcp_connections?: number
  cpu?: { usage?: number; cores?: number }
  memory?: { usage?: number; total_gb?: number; used_gb?: number; available_gb?: number }
  disk?: { usage?: number; total_gb?: number; used_gb?: number; available_gb?: number; read_mb_s?: number; write_mb_s?: number }
  network?: { in_mbps?: number; out_mbps?: number }
  load?: { '1m'?: number; '5m'?: number; '15m'?: number }
  processes?: { running?: number }
}

export type HostRiskMeta = {
  key: RiskKey
  label: string
  tone: Tone
  priority: string
}

export type HostMetricCard = {
  key: MetricKey
  label: string
  value: number | null
  unit: string
  detail: string
  tone: Tone
  statusText: string
  barPercent: number
  isMissing: boolean
}

export type HostRecommendation = {
  key: string
  title: string
  description: string
  action: 'ssh' | 'inspect' | 'copy'
  tone: Tone
}

export type HostTrendPointLike = {
  timestamp: number
  value: number
}

export type TrendChartTick = {
  label: string
  y: number
}

export type TrendChartGeometry = {
  viewBox: string
  linePoints: string
  areaPoints: string
  yTicks: TrendChartTick[]
  gridLines: { x1: number; x2: number; y: number }[]
  xLabels: { label: string; x: number; y: number; anchor: 'start' | 'end' }[]
}

function metricTone(value: number | undefined): Tone {
  if (value == null) return 'muted'
  if (value > 90) return 'danger'
  if (value > 70) return 'warning'
  return 'success'
}

function metricStatusText(value: number | undefined): string {
  if (value == null) return '无数据'
  if (value > 90) return '高风险'
  if (value > 70) return '偏高'
  return '正常'
}

function roundMetric(value: number | undefined, digits = 0): number | null {
  if (value == null || Number.isNaN(value)) return null
  const factor = 10 ** digits
  return Math.round(value * factor) / factor
}

function formatGb(value: number): string {
  return Number.isInteger(value) ? `${value}` : `${roundMetric(value, 1)}`
}

function formatCapacityUsage(totalGb?: number, usagePercent?: number, usedGb?: number): string {
  if (!totalGb) return '容量未知'
  const currentUsedGb = usedGb ?? (usagePercent == null ? undefined : (totalGb * usagePercent) / 100)
  if (currentUsedGb == null) return `${formatGb(totalGb)} GB`
  return `${formatGb(currentUsedGb)}/${formatGb(totalGb)} GB`
}

function maxMetric(host: HostDetailLike): number {
  return Math.max(
    host.cpu?.usage || 0,
    host.memory?.usage || 0,
    host.disk?.usage || 0,
  )
}

function hasAnyMetric(host: HostDetailLike): boolean {
  if (!hasMetricEvidence(host)) return false
  return host.cpu?.usage != null
    || host.memory?.usage != null
    || host.disk?.usage != null
    || (host.load?.['1m'] != null && (host.cpu?.cores || 0) > 0)
}

function hasMetricEvidence(host: HostDetailLike): boolean {
  return (host.cpu?.cores || 0) > 0
    || (host.memory?.total_gb || 0) > 0
    || (host.disk?.total_gb || 0) > 0
    || (host.cpu?.usage || 0) > 0
    || (host.memory?.usage || 0) > 0
    || (host.disk?.usage || 0) > 0
    || (host.load?.['1m'] || 0) > 0
    || (host.network?.in_mbps || 0) > 0
    || (host.network?.out_mbps || 0) > 0
}

function loadRatio(host: HostDetailLike): number | null {
  const load1 = host.load?.['1m'] || 0
  const cores = host.cpu?.cores || 0
  if (!cores) return null
  return load1 / cores
}

function loadTone(host: HostDetailLike): Tone {
  const ratio = loadRatio(host)
  if (ratio == null) return 'muted'
  if (ratio >= 1) return 'danger'
  if (ratio >= 0.75) return 'warning'
  return 'success'
}

export function getHostRiskMeta(host: HostDetailLike): HostRiskMeta {
  if (!host.prometheus_ok) {
    return { key: 'offline', label: '采集异常', tone: 'muted', priority: '需确认' }
  }

  if (!hasAnyMetric(host)) {
    return { key: 'offline', label: '指标缺失', tone: 'muted', priority: '需确认' }
  }

  const ratio = loadRatio(host)
  if (maxMetric(host) > 90 || (ratio != null && ratio >= 1)) {
    return { key: 'critical', label: '高风险', tone: 'danger', priority: '需处理' }
  }

  if (maxMetric(host) > 70 || (ratio != null && ratio >= 0.75)) {
    return { key: 'warning', label: '关注', tone: 'warning', priority: '观察中' }
  }

  return { key: 'healthy', label: '正常', tone: 'success', priority: '观察' }
}

export function buildCollectionState(host: HostDetailLike) {
  if (host.prometheus_ok) {
    return {
      label: 'Prometheus 已连接',
      tone: 'success' as Tone,
      description: '实时指标采集正常',
    }
  }

  return {
    label: 'Prometheus 未连接',
    tone: 'danger' as Tone,
    description: '主机档案可查看，实时指标暂不可用',
  }
}

export function buildHostMetricCards(host: HostDetailLike): HostMetricCard[] {
  const metricsAvailable = host.prometheus_ok !== false && hasMetricEvidence(host)
  const cpuUsage = metricsAvailable ? roundMetric(host.cpu?.usage) : null
  const memoryUsage = metricsAvailable ? roundMetric(host.memory?.usage) : null
  const diskUsage = metricsAvailable ? roundMetric(host.disk?.usage) : null
  const load1 = metricsAvailable ? roundMetric(host.load?.['1m'], 1) : null
  const cores = host.cpu?.cores || 0
  const loadStateTone = !metricsAvailable || host.load?.['1m'] == null ? 'muted' : loadTone(host)
  const loadStatusText = !metricsAvailable || host.load?.['1m'] == null
    ? '无数据'
    : !cores
      ? '核心数未知'
    : loadStateTone === 'danger'
      ? '超过核心数'
      : loadStateTone === 'warning'
        ? '接近核心数'
        : '正常'

  return [
    {
      key: 'cpu',
      label: 'CPU',
      value: cpuUsage,
      unit: '%',
      detail: cores ? `${cores} 核` : '核心数未知',
      tone: metricTone(cpuUsage ?? undefined),
      statusText: metricStatusText(cpuUsage ?? undefined),
      barPercent: cpuUsage || 0,
      isMissing: cpuUsage == null,
    },
    {
      key: 'memory',
      label: '内存',
      value: memoryUsage,
      unit: '%',
      detail: host.memory?.total_gb ? `${host.memory.used_gb || 0}/${host.memory.total_gb} GB` : '容量未知',
      tone: metricTone(memoryUsage ?? undefined),
      statusText: metricStatusText(memoryUsage ?? undefined),
      barPercent: memoryUsage || 0,
      isMissing: memoryUsage == null,
    },
    {
      key: 'disk',
      label: '磁盘',
      value: diskUsage,
      unit: '%',
      detail: formatCapacityUsage(host.disk?.total_gb, host.disk?.usage, host.disk?.used_gb),
      tone: metricTone(diskUsage ?? undefined),
      statusText: metricStatusText(diskUsage ?? undefined),
      barPercent: diskUsage || 0,
      isMissing: diskUsage == null,
    },
    {
      key: 'load',
      label: 'Load',
      value: load1,
      unit: '',
      detail: load1 == null ? '1m 无数据' : `1m ${load1} / ${cores || '-'} 核`,
      tone: loadStateTone,
      statusText: loadStatusText,
      barPercent: Math.min(Math.round((loadRatio(host) || 0) * 100), 100),
      isMissing: load1 == null,
    },
  ]
}

export function buildCurrentJudgment(host: HostDetailLike) {
  if (!host.prometheus_ok) {
    return {
      title: '采集异常，实时指标不可用',
      description: '请先确认 Prometheus、node_exporter 或网络连通性，再判断主机负载。',
      tone: 'muted' as Tone,
    }
  }

  const cards = buildHostMetricCards(host)
  const highest = [...cards]
    .filter((card) => !card.isMissing)
    .sort((a, b) => {
      const toneWeight: Record<Tone, number> = { danger: 3, warning: 2, success: 1, muted: 0 }
      return toneWeight[b.tone] - toneWeight[a.tone] || (b.barPercent - a.barPercent)
    })[0]

  if (!highest) {
    return {
      title: '指标数据缺失',
      description: '主机档案可查看，但当前没有足够实时指标用于判断。',
      tone: 'muted' as Tone,
    }
  }

  if ((host.cpu?.usage || 0) > 90 && loadTone(host) === 'danger') {
    return {
      title: 'CPU 持续高位，Load 已超过核心数',
      description: '建议优先进入 SSH 查看高 CPU 进程，并核对近期发布或批量任务。',
      tone: 'danger' as Tone,
    }
  }

  if (highest.tone === 'danger') {
    return {
      title: `${highest.label} 已达到高风险阈值`,
      description: '建议优先确认异常指标来源，并根据主机角色选择 SSH 或关联记录排查。',
      tone: 'danger' as Tone,
    }
  }

  if (highest.tone === 'warning') {
    return {
      title: `${highest.label} 偏高，建议持续观察`,
      description: '当前未达到高风险阈值，可结合趋势和最近事件确认是否继续恶化。',
      tone: 'warning' as Tone,
    }
  }

  return {
    title: '主机运行平稳',
    description: '核心指标处于正常范围，可继续观察趋势和关联事件。',
    tone: 'success' as Tone,
  }
}

export function buildHostRecommendations(host: HostDetailLike): HostRecommendation[] {
  if (!host.prometheus_ok) {
    return [
      {
        key: 'check-collector',
        title: '确认采集链路',
        description: '检查 Prometheus、node_exporter 和主机网络连通性。',
        action: 'inspect',
        tone: 'danger',
      },
      {
        key: 'ssh-connectivity',
        title: 'SSH 验证主机状态',
        description: '如 SSH 可达，可先确认主机是否在线。',
        action: 'ssh',
        tone: 'muted',
      },
      {
        key: 'notify-owner',
        title: '同步负责人',
        description: host.owner ? `负责人：${host.owner}` : '负责人未配置，请补充责任人。',
        action: 'copy',
        tone: 'muted',
      },
    ]
  }

  const cards = buildHostMetricCards(host)
  const hasCpuPressure = (host.cpu?.usage || 0) > 90 || loadTone(host) === 'danger'
  const hasDiskPressure = (host.disk?.usage || 0) > 90
  const primaryTitle = hasCpuPressure
    ? 'SSH 查看高 CPU 进程'
    : hasDiskPressure
      ? '确认磁盘空间和写入来源'
      : 'SSH 查看主机现场'

  return [
    {
      key: hasCpuPressure ? 'ssh-cpu' : hasDiskPressure ? 'check-disk' : 'ssh-general',
      title: primaryTitle,
      description: hasCpuPressure ? '建议执行 top、ps 或 systemctl 查看异常进程。' : '进入主机确认服务和资源状态。',
      action: 'ssh',
      tone: hasCpuPressure || hasDiskPressure ? 'danger' : 'success',
    },
    {
      key: 'check-change',
      title: '核对最近发布或批量任务',
      description: '确认异常是否与部署、巡检或批量执行时间重合。',
      action: 'inspect',
      tone: cards.some((card) => card.tone === 'danger') ? 'warning' : 'muted',
    },
    {
      key: 'notify-owner',
      title: '同步负责人',
      description: host.owner ? `负责人：${host.owner}` : '负责人未配置，请补充责任人。',
      action: 'copy',
      tone: 'muted',
    },
  ]
}

export function buildTrendCards(_host: HostDetailLike) {
  return [
    { key: 'cpu', label: 'CPU 趋势', state: '暂无历史趋势', unit: '%', points: [] },
    { key: 'load', label: 'Load 趋势', state: '暂无历史趋势', unit: '', points: [] },
    { key: 'memory', label: '内存趋势', state: '暂无历史趋势', unit: '%', points: [] },
    { key: 'network_in', label: '网络趋势', state: '暂无历史趋势', unit: 'Mbps', points: [] },
  ]
}

function formatTrendAxisValue(value: number, unit = '') {
  const rounded = Number.isInteger(value) ? `${value}` : `${Math.round(value * 10) / 10}`
  return `${rounded}${unit}`
}

export function buildTrendChartGeometry(points: HostTrendPointLike[], unit = ''): TrendChartGeometry {
  const width = 180
  const height = 72
  const plotLeft = 34
  const plotRight = 176
  const plotTop = 8
  const plotBottom = 52
  const values = points.map((point) => point.value)
  const min = values.length ? Math.min(...values) : 0
  const max = values.length ? Math.max(...values) : 0
  const isFlat = max === min
  const range = max - min || 1
  const step = (plotRight - plotLeft) / (points.length - 1 || 1)
  const yForValue = (value: number) => (
    isFlat ? (plotTop + plotBottom) / 2 : plotBottom - ((value - min) / range) * (plotBottom - plotTop)
  )
  const linePoints = points.map((point, index) => (
    `${plotLeft + index * step},${yForValue(point.value)}`
  )).join(' ')
  const tickValues = [max, min + (max - min) / 2, min]
  const flatTickY = [plotTop, (plotTop + plotBottom) / 2, plotBottom]
  const yTicks = tickValues.map((value, index) => ({
    label: formatTrendAxisValue(value, unit),
    y: isFlat ? flatTickY[index] : yForValue(value),
  }))

  return {
    viewBox: `0 0 ${width} ${height}`,
    linePoints,
    areaPoints: linePoints ? `${linePoints} ${plotRight},${plotBottom} ${plotLeft},${plotBottom}` : '',
    yTicks,
    gridLines: yTicks.map((tick) => ({ x1: plotLeft, x2: plotRight, y: tick.y })),
    xLabels: [
      { label: '-60m', x: plotLeft, y: 68, anchor: 'start' },
      { label: 'now', x: plotRight, y: 68, anchor: 'end' },
    ],
  }
}

export function buildRelationCards(_host: HostDetailLike) {
  return [
    { key: 'alerts', label: '相关告警', value: '待接入' },
    { key: 'containers', label: '容器', value: '待接入' },
    { key: 'deploys', label: '最近部署', value: '待接入' },
    { key: 'patrols', label: '巡检记录', value: '待接入' },
  ]
}

export function formatHostUptime(hours: number | undefined) {
  if (!hours) return '-'
  if (hours < 24) return `${hours} 小时`
  const days = Math.floor(hours / 24)
  const restHours = hours % 24
  return restHours ? `${days} 天 ${restHours} 小时` : `${days} 天`
}

export function buildSteadyDetailGroups(host: HostDetailLike) {
  return [
    {
      key: 'system',
      title: '系统信息',
      rows: [
        { label: '规格', value: host.spec || '-' },
        { label: '系统', value: host.os_info || '-' },
        { label: '运行时间', value: formatHostUptime(host.uptime_hours) },
        { label: '运行进程', value: host.processes?.running ?? '-' },
      ],
    },
    {
      key: 'network',
      title: '网络',
      rows: [
        { label: '入站', value: `${host.network?.in_mbps ?? 0} Mbps` },
        { label: '出站', value: `${host.network?.out_mbps ?? 0} Mbps` },
        { label: 'TCP 连接', value: host.tcp_connections ?? '-' },
      ],
    },
    {
      key: 'diskIo',
      title: '磁盘 IO',
      rows: [
        { label: '容量', value: host.disk?.total_gb ? formatCapacityUsage(host.disk.total_gb, host.disk.usage, host.disk.used_gb) : '-' },
        { label: '读速率', value: `${host.disk?.read_mb_s ?? 0} MB/s` },
        { label: '写速率', value: `${host.disk?.write_mb_s ?? 0} MB/s` },
      ],
    },
  ]
}
