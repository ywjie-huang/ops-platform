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
}

export type DeploymentLike = {
  replicas?: number
  ready_replicas?: number
}

export type NodeLike = {
  status?: string
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
