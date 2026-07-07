export type PatrolStatus = 'normal' | 'warning' | 'critical' | string
export type PatrolCategory = 'host' | 'k8s' | 'asset' | string
export type PatrolTone = 'success' | 'warning' | 'danger' | 'info'

export interface PatrolReportLike {
  id?: number
  title?: string
  status?: PatrolStatus
  total_checks?: number
  normal_count?: number
  warning_count?: number
  critical_count?: number
  summary?: string
  operator?: string
  created_at?: string
}

export interface PatrolItemLike {
  id?: number
  category?: PatrolCategory
  target_name?: string
  target_ip?: string
  check_name?: string
  status?: PatrolStatus
  value?: string
  threshold?: string
  detail?: string
}

export interface PatrolOverview {
  total: number
  normal: number
  warning: number
  critical: number
  abnormal: number
  healthScore: number
  priority: string
  priorityLabel: string
  status: PatrolStatus
}

export interface RiskObject {
  key: string
  category: PatrolCategory
  categoryLabel: string
  targetName: string
  targetIp: string
  status: PatrolStatus
  tone: PatrolTone
  priority: string
  normal: number
  warning: number
  critical: number
  total: number
  headline: string
  impact: string
  items: PatrolItemLike[]
}

export interface RiskObjectCountBadge {
  tone: Exclude<PatrolTone, 'info'>
  value: number
  label: string
}

export interface RiskObjectPage<T = RiskObject> {
  items: T[]
  page: number
  pageSize: number
  total: number
  totalPages: number
}

export interface CockpitStat {
  key: string
  label: string
  value: string
  helper: string
  tone: PatrolTone
}

export interface RadarObject extends RiskObject {
  ring: number
  angle: number
  size: number
}

export interface TickerItem {
  key: string
  title: string
  detail: string
  meta: string
  tone: PatrolTone
}

export interface PagerMeta {
  page: number
  pageSize: number
  total: number
  totalPages: number
}

export interface PatrolRouteLocation {
  path: string
  query?: Record<string, string>
}

const CATEGORY_ORDER: Record<string, number> = {
  host: 1,
  k8s: 2,
  asset: 3,
}

const CATEGORY_LABELS: Record<string, string> = {
  host: '主机',
  k8s: 'K8s',
  asset: '资产',
}

export function statusLabel(status: PatrolStatus = '') {
  if (status === 'normal') return '正常'
  if (status === 'warning') return '警告'
  if (status === 'critical') return '严重'
  return status || '-'
}

export function statusTone(status: PatrolStatus = ''): PatrolTone {
  if (status === 'normal') return 'success'
  if (status === 'warning') return 'warning'
  if (status === 'critical') return 'danger'
  return 'info'
}

export function categoryLabel(category: PatrolCategory = '') {
  return CATEGORY_LABELS[category] || category || '其他'
}

export function buildObjectCounts(counts: Pick<RiskObject, 'critical' | 'warning' | 'normal'>): RiskObjectCountBadge[] {
  const badges = [
    { tone: 'danger', value: counts.critical, label: '严重' },
    { tone: 'warning', value: counts.warning, label: '警告' },
    { tone: 'success', value: counts.normal, label: '正常' },
  ] satisfies RiskObjectCountBadge[]

  const visibleBadges = badges.filter((item) => item.value > 0)
  return visibleBadges.length ? visibleBadges : [{ tone: 'success', value: 0, label: '正常' }]
}

export function buildCockpitRouteLocation(report?: PatrolReportLike | null): PatrolRouteLocation {
  if (report?.id != null) {
    return {
      path: '/patrol/cockpit',
      query: { reportId: String(report.id) },
    }
  }

  return { path: '/patrol/cockpit' }
}

export function getPatrolPriority(report?: PatrolReportLike | null) {
  if (!report) return '-'
  if ((report.critical_count || 0) > 0 || report.status === 'critical') return 'P1'
  if ((report.warning_count || 0) > 0 || report.status === 'warning') return 'P2'
  return '正常'
}

export function buildPatrolOverview(report?: PatrolReportLike | null): PatrolOverview {
  const normal = report?.normal_count || 0
  const warning = report?.warning_count || 0
  const critical = report?.critical_count || 0
  const total = report?.total_checks || normal + warning + critical
  const abnormal = warning + critical
  const healthScore = total > 0 ? Math.max(0, Math.round(((normal + warning * 0.2) / total) * 100)) : 100
  const priority = getPatrolPriority(report)

  return {
    total,
    normal,
    warning,
    critical,
    abnormal,
    healthScore,
    priority,
    priorityLabel: priority === 'P1' ? '需处置' : priority === 'P2' ? '需观察' : '正常',
    status: report?.status || 'normal',
  }
}

export function buildCockpitStats(report: PatrolReportLike | null | undefined, coverageCount = 0, updatedText = '-'): CockpitStat[] {
  const overview = buildPatrolOverview(report)
  const healthTone: PatrolTone = overview.critical > 0 ? 'danger' : overview.warning > 0 ? 'warning' : 'success'

  return [
    {
      key: 'health',
      label: '健康分',
      value: String(overview.healthScore),
      helper: overview.priorityLabel,
      tone: healthTone,
    },
    {
      key: 'critical',
      label: '严重项',
      value: String(overview.critical),
      helper: `${overview.priority} 优先级`,
      tone: overview.critical > 0 ? 'danger' : 'success',
    },
    {
      key: 'warning',
      label: '警告项',
      value: String(overview.warning),
      helper: `${overview.abnormal} 个异常项`,
      tone: overview.warning > 0 ? 'warning' : 'success',
    },
    {
      key: 'coverage',
      label: '覆盖对象',
      value: String(coverageCount),
      helper: '主机 / K8s / 资产',
      tone: 'info',
    },
    {
      key: 'updated',
      label: '最近巡检',
      value: updatedText,
      helper: report?.operator || '系统任务',
      tone: 'success',
    },
  ]
}

export function buildRiskObjects(items: PatrolItemLike[] = []): RiskObject[] {
  const groups = new Map<string, RiskObject>()

  for (const item of items) {
    const category = item.category || 'other'
    const targetName = item.target_name || '未知对象'
    const key = `${category}::${targetName}`
    const current = groups.get(key) || {
      key,
      category,
      categoryLabel: categoryLabel(category),
      targetName,
      targetIp: item.target_ip || '',
      status: 'normal',
      tone: 'success' as PatrolTone,
      priority: '正常',
      normal: 0,
      warning: 0,
      critical: 0,
      total: 0,
      headline: '',
      impact: '',
      items: [],
    }

    current.items.push(item)
    current.total += 1
    if (item.status === 'critical') current.critical += 1
    else if (item.status === 'warning') current.warning += 1
    else current.normal += 1

    if (!current.targetIp && item.target_ip) current.targetIp = item.target_ip
    groups.set(key, current)
  }

  return Array.from(groups.values())
    .map((object) => {
      const status = object.critical > 0 ? 'critical' : object.warning > 0 ? 'warning' : 'normal'
      const priority = status === 'critical' ? 'P1' : status === 'warning' ? 'P2' : '正常'
      const lead = object.items.find((item) => item.status === 'critical')
        || object.items.find((item) => item.status === 'warning')
        || object.items[0]

      return {
        ...object,
        status,
        tone: statusTone(status),
        priority,
        headline: lead ? `${lead.check_name || '检查项'} ${lead.value || '-'}` : '暂无检查项',
        impact: buildObjectImpact(object.category, status),
      }
    })
    .sort((a, b) => {
      if (a.critical !== b.critical) return b.critical - a.critical
      if (a.warning !== b.warning) return b.warning - a.warning
      const categoryDelta = (CATEGORY_ORDER[a.category] || 99) - (CATEGORY_ORDER[b.category] || 99)
      if (categoryDelta !== 0) return categoryDelta
      return a.targetName.localeCompare(b.targetName)
    })
}

export function buildRadarObjects(objects: RiskObject[] = []): RadarObject[] {
  const categoryBase: Record<string, { ring: number; angle: number }> = {
    host: { ring: 34, angle: -34 },
    k8s: { ring: 56, angle: 86 },
    asset: { ring: 64, angle: 164 },
  }

  const seenByCategory: Record<string, number> = {}

  return objects.slice(0, 10).map((object) => {
    const seen = seenByCategory[object.category] || 0
    seenByCategory[object.category] = seen + 1
    const base = categoryBase[object.category] || { ring: 62, angle: 220 }

    return {
      ...object,
      ring: Math.min(72, base.ring + seen * 9),
      angle: base.angle + seen * 52,
      size: object.status === 'critical' ? 18 : object.status === 'warning' ? 14 : 10,
    }
  })
}

export function buildTickerItems(priorityObjects: RiskObject[] = [], reports: PatrolReportLike[] = []): TickerItem[] {
  const riskItems = priorityObjects.slice(0, 4).map((object) => ({
    key: `risk-${object.key}`,
    title: object.targetName,
    detail: `${object.headline}，${object.impact}`,
    meta: `${object.categoryLabel} · ${object.priority}`,
    tone: object.tone,
  }))

  const reportItems = reports.slice(0, 3).map((report, index) => ({
    key: `report-${index}`,
    title: report.title || `巡检批次 ${index + 1}`,
    detail: `${report.critical_count || 0} 严重 / ${report.warning_count || 0} 警告`,
    meta: getPatrolPriority(report),
    tone: statusTone(report.status),
  }))

  return [...riskItems, ...reportItems]
}

export function groupRiskObjectsByCategory(objects: RiskObject[] = []) {
  return [
    { key: 'host', label: '主机', objects: objects.filter((item) => item.category === 'host') },
    { key: 'k8s', label: 'K8s 集群', objects: objects.filter((item) => item.category === 'k8s') },
    { key: 'asset', label: '资产状态', objects: objects.filter((item) => item.category === 'asset') },
  ]
}

export function paginateRiskObjects<T>(objects: T[] = [], page = 1, pageSize = 5): RiskObjectPage<T> {
  const pager = buildPager(objects.length, page, pageSize)
  const start = (pager.page - 1) * pager.pageSize

  return {
    items: objects.slice(start, start + pager.pageSize),
    ...pager,
  }
}

export function buildPager(total = 0, page = 1, pageSize = 5): PagerMeta {
  const normalizedTotal = Math.max(0, total)
  const normalizedPageSize = Math.max(1, pageSize)
  const totalPages = Math.max(1, Math.ceil(normalizedTotal / normalizedPageSize))
  const currentPage = Math.min(Math.max(1, page), totalPages)

  return {
    page: currentPage,
    pageSize: normalizedPageSize,
    total: normalizedTotal,
    totalPages,
  }
}

export function pickPrimaryRiskObject(objects: RiskObject[] = []) {
  return objects.find((item) => item.status !== 'normal') || objects[0] || null
}

function buildObjectImpact(category: PatrolCategory, status: PatrolStatus) {
  if (status === 'normal') return '无明显影响'
  if (category === 'host') return '可能影响主机承载服务'
  if (category === 'k8s') return '可能影响集群工作负载'
  if (category === 'asset') return '可能影响资产可用性'
  return '需要进一步确认影响范围'
}
