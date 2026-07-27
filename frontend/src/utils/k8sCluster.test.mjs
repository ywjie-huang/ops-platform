import assert from 'node:assert/strict'
import { test } from 'node:test'

const {
  buildClusterOverview,
  sortClustersByRisk,
  buildClusterAnomalies,
  filterClusterPods,
  summarizeClusterResources,
} = await import('./k8sCluster.ts')

test('builds quiet overview cards from cluster fleet data', () => {
  const cards = buildClusterOverview([
    { status: 'running', node_count: 12, ready_nodes: 12, abnormal_pod_count: 3, deployment_gap_count: 0 },
    { status: 'stopped', node_count: 8, ready_nodes: 8, abnormal_pod_count: 0, deployment_gap_count: 0 },
  ])

  assert.deepEqual(cards, [
    { label: '集群总数', value: 2, foot: '运行中 1，失联 1' },
    { label: '异常集群', value: 2, foot: '优先处理连接中断与副本不足' },
    { label: '异常工作负载', value: 3, foot: '按 Pod 与 Deployment 异常汇总' },
    { label: '节点就绪率', value: '100%', foot: '20 / 20 Ready' },
  ])
})

test('sorts clusters by offline first, then anomaly load, then name', () => {
  const sorted = sortClustersByRisk([
    { id: 1, name: 'healthy', status: 'running', abnormal_pod_count: 0, deployment_gap_count: 0, ready_nodes: 8, node_count: 8 },
    { id: 2, name: 'offline', status: 'stopped', abnormal_pod_count: 0, deployment_gap_count: 0, ready_nodes: 0, node_count: 8 },
    { id: 3, name: 'noisy', status: 'running', abnormal_pod_count: 6, deployment_gap_count: 2, ready_nodes: 10, node_count: 12 },
  ])

  assert.deepEqual(sorted.map((item) => item.name), ['offline', 'noisy', 'healthy'])
})

test('summarizes detail anomalies and filters pods against multiple fields', () => {
  const resources = {
    nodes: [{ status: 'Ready' }, { status: 'NotReady' }],
    pods: [
      { name: 'payment-1', namespace: 'payment', status: 'CrashLoopBackOff', reason: 'BackOff', node: 'worker-a' },
      { name: 'trade-1', namespace: 'trade', status: 'Running', node: 'worker-b' },
    ],
    deployments: [{ name: 'api', replicas: 3, ready_replicas: 1 }],
  }

  assert.deepEqual(buildClusterAnomalies(resources), [
    { key: 'nodes', text: '1 个节点未就绪', count: 1 },
    { key: 'pods', text: '1 个异常 Pod', count: 1 },
    { key: 'deployments', text: '1 个副本不足 Deployment', count: 1 },
  ])

  assert.deepEqual(
    filterClusterPods(resources.pods, 'worker-a').map((item) => item.name),
    ['payment-1'],
  )

  assert.deepEqual(summarizeClusterResources(resources), {
    abnormalPodCount: 1,
    deploymentGapCount: 1,
    notReadyNodeCount: 1,
    hotspotNamespace: 'payment',
  })
})

const {
  isAbnormalPod,
  matchPodQuickFilter,
  parseMemToMi,
  parseCpuCores,
  computeAllocation,
} = await import('./k8sCluster.ts')

test('parses k8s cpu and memory quantities', () => {
  assert.equal(parseCpuCores('100m'), 0.1)
  assert.equal(parseCpuCores('2'), 2)
  assert.equal(parseCpuCores(4), 4)
  assert.equal(parseCpuCores(''), 0)
  assert.equal(parseMemToMi('256Mi'), 256)
  assert.equal(parseMemToMi('1Gi'), 1024)
  assert.equal(parseMemToMi('32768Ki'), 32)
  assert.equal(parseMemToMi(''), 0)
})

test('matches pod quick filters', () => {
  const crash = { status: 'CrashLoopBackOff', reason: 'BackOff', restarts: 27 }
  const pending = { status: 'Pending', reason: 'FailedScheduling', restarts: 0 }
  const oom = { status: 'Running', reason: 'OOMKilled', restarts: 8 }
  const healthy = { status: 'Running', reason: '', restarts: 1 }

  assert.equal(isAbnormalPod(crash), true)
  assert.equal(isAbnormalPod(healthy), false)
  assert.equal(matchPodQuickFilter(crash, 'crash'), true)
  assert.equal(matchPodQuickFilter(pending, 'pending'), true)
  assert.equal(matchPodQuickFilter(oom, 'oom'), true)
  assert.equal(matchPodQuickFilter(crash, 'restarts'), true)
  assert.equal(matchPodQuickFilter(healthy, 'restarts'), false)
  assert.equal(matchPodQuickFilter(healthy, 'abnormal'), false)
  assert.equal(matchPodQuickFilter(healthy, 'all'), true)
})

test('computes cluster allocation percent from requests and capacity', () => {
  const nodes = [
    { name: 'a', status: 'Ready', cpu: '8', memory: '32Gi' },
    { name: 'b', status: 'Ready', cpu: '8', memory: '32768Mi' },
  ]
  const pods = [
    { name: 'p1', cpu_request: 2, mem_request: 8192 },
    { name: 'p2', cpu_request: 2, mem_request: 8192 },
  ]
  const alloc = computeAllocation(nodes, pods)
  assert.equal(alloc.cpuCapacity, 16)
  assert.equal(alloc.memCapacityMi, 65536)
  assert.equal(alloc.cpuPercent, 25)
  assert.equal(alloc.memPercent, 25)
})
