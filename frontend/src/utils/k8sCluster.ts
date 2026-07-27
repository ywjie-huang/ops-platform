export type ClusterLike = {
  id?: number
  name?: string
  status?: string
  node_count?: number
  ready_nodes?: number
  abnormal_pod_count?: number
  deployment_gap_count?: number
  pod_abnormal?: number
}

export type PodLike = {
  name?: string
  namespace?: string
  status?: string
  reason?: string
  node?: string
  restarts?: number
  cpu_request?: number
  mem_request?: number
}

export type DeploymentLike = {
  replicas?: number
  ready_replicas?: number
}

export type NodeLike = {
  name?: string
  status?: string
  cpu?: string | number
  memory?: string
}

export function buildClusterOverview(clusters: ClusterLike[]) {
  const total = clusters.length
  const running = clusters.filter((item) => item.status === 'running').length
  const offline = clusters.filter((item) => item.status !== 'running').length
  const abnormalClusters = clusters.filter((item) => {
    const abnormalPods = item.abnormal_pod_count ?? item.pod_abnormal ?? 0
    const deploymentGaps = item.deployment_gap_count ?? 0
    return item.status !== 'running' || abnormalPods > 0 || deploymentGaps > 0
  }).length
  const abnormalWorkloads = clusters.reduce((sum, item) => {
    return sum + (item.abnormal_pod_count ?? item.pod_abnormal ?? 0) + (item.deployment_gap_count ?? 0)
  }, 0)
  const readyNodes = clusters.reduce((sum, item) => sum + (item.ready_nodes ?? item.node_count ?? 0), 0)
  const totalNodes = clusters.reduce((sum, item) => sum + (item.node_count ?? 0), 0)
  const readyPercent = totalNodes ? `${Math.round((readyNodes / totalNodes) * 100)}%` : '-'

  return [
    { label: '集群总数', value: total, foot: `运行中 ${running}，失联 ${offline}` },
    { label: '异常集群', value: abnormalClusters, foot: '优先处理连接中断与副本不足' },
    { label: '异常工作负载', value: abnormalWorkloads, foot: '按 Pod 与 Deployment 异常汇总' },
    { label: '节点就绪率', value: readyPercent, foot: `${readyNodes} / ${totalNodes} Ready` },
  ]
}

export function clusterRiskScore(cluster: ClusterLike) {
  if (cluster.status !== 'running') return 1000
  const abnormalPods = cluster.abnormal_pod_count ?? cluster.pod_abnormal ?? 0
  const deploymentGaps = cluster.deployment_gap_count ?? 0
  const notReadyNodes = Math.max((cluster.node_count ?? 0) - (cluster.ready_nodes ?? cluster.node_count ?? 0), 0)
  return abnormalPods * 10 + deploymentGaps * 5 + notReadyNodes
}

export function sortClustersByRisk<T extends ClusterLike>(clusters: T[]) {
  return [...clusters].sort((a, b) => {
    const scoreDiff = clusterRiskScore(b) - clusterRiskScore(a)
    if (scoreDiff !== 0) return scoreDiff
    return String(a.name || '').localeCompare(String(b.name || ''), 'zh-CN')
  })
}

export function buildClusterAnomalies(resources: { nodes?: NodeLike[]; pods?: PodLike[]; deployments?: DeploymentLike[] }) {
  const items: { key: string; text: string; count: number }[] = []
  const notReadyNodes = (resources.nodes || []).filter((item) => item.status && item.status !== 'Ready').length
  const abnormalPods = (resources.pods || []).filter((item) => !['Running', 'Succeeded'].includes(item.status || '')).length
  const gapDeployments = (resources.deployments || []).filter((item) => (item.ready_replicas ?? 0) < (item.replicas ?? 0)).length

  if (notReadyNodes) items.push({ key: 'nodes', text: `${notReadyNodes} 个节点未就绪`, count: notReadyNodes })
  if (abnormalPods) items.push({ key: 'pods', text: `${abnormalPods} 个异常 Pod`, count: abnormalPods })
  if (gapDeployments) items.push({ key: 'deployments', text: `${gapDeployments} 个副本不足 Deployment`, count: gapDeployments })

  return items
}

export function filterClusterPods<T extends PodLike>(pods: T[], keyword: string) {
  const normalized = keyword.trim().toLowerCase()
  if (!normalized) return pods
  return pods.filter((item) =>
    [item.name, item.namespace, item.status, item.reason, item.node]
      .some((value) => String(value || '').toLowerCase().includes(normalized)),
  )
}

const ABNORMAL_STATUSES = ['Running', 'Succeeded']

export function isAbnormalPod(pod: PodLike) {
  return !ABNORMAL_STATUSES.includes(pod.status || '')
}

export type PodQuickFilter = 'all' | 'abnormal' | 'crash' | 'pending' | 'oom' | 'restarts'

export function matchPodQuickFilter(pod: PodLike, filter: PodQuickFilter) {
  const status = pod.status || ''
  const reason = pod.reason || ''
  switch (filter) {
    case 'abnormal':
      return isAbnormalPod(pod)
    case 'crash':
      return /crashloopbackoff|error/i.test(status) || /crashloopbackoff/i.test(reason)
    case 'pending':
      return status === 'Pending'
    case 'oom':
      return /oomkilled/i.test(status) || /oomkilled/i.test(reason)
    case 'restarts':
      return (pod.restarts ?? 0) > 5
    default:
      return true
  }
}

const MEM_UNIT_TO_MI: Record<string, number> = {
  Ki: 1 / 1024,
  Mi: 1,
  Gi: 1024,
  Ti: 1024 * 1024,
  K: 1000 / 1048576,
  M: 1e6 / 1048576,
  G: 1e9 / 1048576,
}

export function parseMemToMi(value?: string | number): number {
  if (value === undefined || value === null || value === '') return 0
  if (typeof value === 'number') return value / 1048576
  const v = String(value).trim()
  for (const [suffix, factor] of Object.entries(MEM_UNIT_TO_MI)) {
    if (v.endsWith(suffix)) {
      const num = parseFloat(v.slice(0, -suffix.length))
      return Number.isFinite(num) ? num * factor : 0
    }
  }
  const num = parseFloat(v)
  return Number.isFinite(num) ? num / 1048576 : 0
}

export function parseCpuCores(value?: string | number): number {
  if (value === undefined || value === null || value === '') return 0
  if (typeof value === 'number') return value
  const v = String(value).trim()
  if (v.endsWith('m')) {
    const num = parseFloat(v.slice(0, -1))
    return Number.isFinite(num) ? num / 1000 : 0
  }
  const num = parseFloat(v)
  return Number.isFinite(num) ? num : 0
}

export type ResourceAllocation = {
  cpuRequest: number
  cpuCapacity: number
  cpuPercent: number
  memRequestMi: number
  memCapacityMi: number
  memPercent: number
}

/** 汇总一组 Pod 的 requests 与一组 Node 的 capacity，得出申请率。 */
export function computeAllocation(nodes: NodeLike[], pods: PodLike[]): ResourceAllocation {
  const cpuCapacity = nodes.reduce((sum, n) => sum + parseCpuCores(n.cpu), 0)
  const memCapacityMi = nodes.reduce((sum, n) => sum + parseMemToMi(n.memory), 0)
  const cpuRequest = pods.reduce((sum, p) => sum + (p.cpu_request ?? 0), 0)
  const memRequestMi = pods.reduce((sum, p) => sum + (p.mem_request ?? 0), 0)
  return {
    cpuRequest,
    cpuCapacity,
    cpuPercent: cpuCapacity ? Math.round((cpuRequest / cpuCapacity) * 100) : 0,
    memRequestMi,
    memCapacityMi,
    memPercent: memCapacityMi ? Math.round((memRequestMi / memCapacityMi) * 100) : 0,
  }
}

export function summarizeClusterResources(resources: {
  nodes?: NodeLike[]
  pods?: PodLike[]
  deployments?: DeploymentLike[]
}) {
  const abnormalPodCount = (resources.pods || []).filter((item) => !['Running', 'Succeeded'].includes(item.status || '')).length
  const deploymentGapCount = (resources.deployments || []).filter((item) => (item.ready_replicas ?? 0) < (item.replicas ?? 0)).length
  const notReadyNodeCount = (resources.nodes || []).filter((item) => item.status && item.status !== 'Ready').length

  const namespaceCounts = new Map<string, number>()
  for (const pod of resources.pods || []) {
    if (['Running', 'Succeeded'].includes(pod.status || '')) continue
    const namespace = pod.namespace || 'default'
    namespaceCounts.set(namespace, (namespaceCounts.get(namespace) || 0) + 1)
  }

  let hotspotNamespace = ''
  let hotspotCount = -1
  for (const [namespace, count] of namespaceCounts.entries()) {
    if (count > hotspotCount) {
      hotspotNamespace = namespace
      hotspotCount = count
    }
  }

  return {
    abnormalPodCount,
    deploymentGapCount,
    notReadyNodeCount,
    hotspotNamespace,
  }
}
