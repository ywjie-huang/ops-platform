export type HostLike = {
  id?: number
  name?: string
  ip_address?: string
  owner?: string
  prometheus_ok?: boolean
  cpu?: number
  memory?: number
  disk?: number
  load?: string | number
}

function metricMax(host: HostLike) {
  return Math.max(host.cpu || 0, host.memory || 0, host.disk || 0)
}

export function getHostStateMeta(host: HostLike) {
  if (!host.prometheus_ok) {
    return { key: 'offline', label: '离线', tone: 'muted', summary: '主机离线，指标不可用' }
  }
  if ((host.cpu || 0) > 90 || (host.memory || 0) > 90 || (host.disk || 0) > 90) {
    const cpu = host.cpu || 0
    const disk = host.disk || 0
    if (cpu >= disk) {
      return { key: 'critical', label: '高危', tone: 'danger', summary: `CPU ${cpu}% · Load ${host.load || '-'}` }
    }
    return { key: 'critical', label: '高危', tone: 'danger', summary: `磁盘 ${disk}% · 需尽快清理` }
  }
  if ((host.cpu || 0) > 70 || (host.memory || 0) > 70 || (host.disk || 0) > 70) {
    return { key: 'warning', label: '告警', tone: 'warning', summary: `峰值指标 ${metricMax(host)}%` }
  }
  return { key: 'healthy', label: '在线', tone: 'success', summary: `负载 ${host.load || '-'} · 运行平稳` }
}

export function hostRiskScore(host: HostLike) {
  if (!host.prometheus_ok) return 1000
  const max = metricMax(host)
  if (max > 90) return 700 + max
  if (max > 70) return 400 + max
  return max
}

export function sortHostsByRisk<T extends HostLike>(hosts: T[]) {
  return [...hosts].sort((a, b) => {
    const scoreDiff = hostRiskScore(b) - hostRiskScore(a)
    if (scoreDiff !== 0) return scoreDiff
    return String(a.name || '').localeCompare(String(b.name || ''), 'zh-CN')
  })
}

export function buildHostOverview(hosts: HostLike[]) {
  const critical = hosts.filter((item) => getHostStateMeta(item).key === 'critical').length
  const offline = hosts.filter((item) => getHostStateMeta(item).key === 'offline').length
  const warning = hosts.filter((item) => getHostStateMeta(item).key !== 'healthy').length
  const healthy = hosts.filter((item) => getHostStateMeta(item).key === 'healthy').length

  return [
    { key: 'critical', label: '高危主机', value: critical, tone: 'danger' },
    { key: 'offline', label: '离线主机', value: offline, tone: 'muted' },
    { key: 'warning', label: '指标异常', value: warning, tone: 'warning' },
    { key: 'healthy', label: '运行正常', value: healthy, tone: 'success' },
  ]
}

export function buildPriorityHosts<T extends HostLike>(hosts: T[]) {
  return sortHostsByRisk(hosts).slice(0, 5).map((item) => {
    const state = getHostStateMeta(item)
    return {
      ...item,
      headline: state.summary,
      action: state.key === 'offline' ? 'SSH' : '详情',
      tone: state.tone,
      label: state.label,
    }
  })
}
