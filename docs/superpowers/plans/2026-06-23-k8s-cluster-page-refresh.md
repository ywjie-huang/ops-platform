# K8s Cluster Page Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the K8s cluster list and detail pages to match the approved quieter preview while preserving existing cluster operations, dialogs, filters, and data-fetch behavior.

**Architecture:** Extract the risk ranking, summary, and filtering logic into a small `frontend/src/utils/k8sCluster.ts` helper so the list/detail views can stay focused on rendering and event handling. Then reshape `ContainerView.vue` into a fleet-overview page and `ContainerDetailView.vue` into a calmer single-cluster workbench, reusing the current API surface and interaction handlers.

**Tech Stack:** Vue 3 script setup, Element Plus, Vite, TypeScript, Node `node:test` utility tests

---

## File Structure

- Create: `frontend/src/utils/k8sCluster.ts`
  - Pure helpers for cluster summary cards, cluster risk ordering, anomaly summaries, and pod/deployment/service filtering primitives.
- Create: `frontend/src/utils/k8sCluster.test.mjs`
  - Node-based tests for helper behavior before wiring the helpers into the Vue pages.
- Modify: `frontend/src/views/containers/ContainerView.vue`
  - Replace the old CRUD-first cluster list with the quieter fleet-overview layout from preview v2.
- Modify: `frontend/src/views/containers/ContainerDetailView.vue`
  - Rebuild the detail page into the approved workbench layout while preserving existing fetch flows, dialogs, and actions.

### Task 1: Add and verify K8s helper tests

**Files:**
- Create: `frontend/src/utils/k8sCluster.test.mjs`
- Create: `frontend/src/utils/k8sCluster.ts`
- Test: `frontend/src/utils/k8sCluster.test.mjs`

- [ ] **Step 1: Write the failing test**

```javascript
import assert from 'node:assert/strict'
import { test } from 'node:test'

const {
  buildClusterOverview,
  sortClustersByRisk,
  buildClusterAnomalies,
  filterClusterPods,
} = await import('./k8sCluster.ts')

test('builds quiet overview cards from cluster fleet data', () => {
  const cards = buildClusterOverview([
    { status: 'running', node_count: 12, pod_abnormal: 3 },
    { status: 'stopped', node_count: 8, pod_abnormal: 0 },
  ])

  assert.deepEqual(cards, [
    { label: '集群总数', value: 2, foot: '运行中 1，失联 1' },
    { label: '异常集群', value: 1, foot: '优先处理连接中断与副本不足' },
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
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test frontend/src/utils/k8sCluster.test.mjs`

Expected: FAIL with module-not-found or missing export errors for `k8sCluster.ts`

- [ ] **Step 3: Write minimal implementation**

```typescript
type ClusterLike = {
  id?: number
  name?: string
  status?: string
  node_count?: number
  ready_nodes?: number
  abnormal_pod_count?: number
  deployment_gap_count?: number
  pod_abnormal?: number
}

type PodLike = {
  name?: string
  namespace?: string
  status?: string
  reason?: string
  node?: string
}

type DeploymentLike = {
  replicas?: number
  ready_replicas?: number
}

type NodeLike = {
  status?: string
}

export function buildClusterOverview(clusters: ClusterLike[]) {
  const total = clusters.length
  const running = clusters.filter((item) => item.status === 'running').length
  const offline = clusters.filter((item) => item.status !== 'running').length
  const abnormalClusters = clusters.filter((item) => (item.status !== 'running') || (item.abnormal_pod_count ?? item.pod_abnormal ?? 0) > 0 || (item.deployment_gap_count ?? 0) > 0).length
  const abnormalWorkloads = clusters.reduce((sum, item) => sum + (item.abnormal_pod_count ?? item.pod_abnormal ?? 0) + (item.deployment_gap_count ?? 0), 0)
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
  return (cluster.abnormal_pod_count ?? cluster.pod_abnormal ?? 0) * 10 + (cluster.deployment_gap_count ?? 0) * 5 + Math.max((cluster.node_count ?? 0) - (cluster.ready_nodes ?? cluster.node_count ?? 0), 0)
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test frontend/src/utils/k8sCluster.test.mjs`

Expected: PASS for all K8s helper tests

- [ ] **Step 5: Commit**

```bash
git add frontend/src/utils/k8sCluster.ts frontend/src/utils/k8sCluster.test.mjs
git commit -m "test(k8s): add cluster view helper coverage"
```

### Task 2: Refresh the K8s list page

**Files:**
- Modify: `frontend/src/views/containers/ContainerView.vue`
- Modify: `frontend/src/utils/k8sCluster.ts`
- Test: `frontend/src/utils/k8sCluster.test.mjs`

- [ ] **Step 1: Wire the tested helper data into the list page**

Use the existing `getClusters()` fetch but compute enriched rows and overview cards with helper functions. Add local derived types for row rendering:

```typescript
import { buildClusterOverview, sortClustersByRisk } from '@/utils/k8sCluster'

const normalizedClusters = computed(() => sortClustersByRisk((clusters.value || []).map((item: any) => ({
  ...item,
  ready_nodes: item.ready_nodes ?? item.node_count ?? 0,
  abnormal_pod_count: item.abnormal_pod_count ?? item.pod_abnormal ?? 0,
  deployment_gap_count: item.deployment_gap_count ?? 0,
}))))

const overviewCards = computed(() => buildClusterOverview(normalizedClusters.value))
```

- [ ] **Step 2: Replace the template with the quieter fleet layout**

Implement:
- page header title changed to `K8s 集群`
- 4 summary cards
- one compact warning banner shown only when risky clusters exist
- reduced filter row: search, refresh, connect button
- table columns limited to cluster, status, nodes, abnormal workload, owner/description, last sync, actions

Use this table cell pattern for cluster summary:

```vue
<el-table-column label="集群" min-width="220">
  <template #default="{ row }">
    <div class="cluster-cell">
      <div class="cluster-copy">
        <strong>{{ row.name }}</strong>
        <span>{{ row.version || '-' }} · {{ row.description || row.endpoint || '未填写说明' }}</span>
      </div>
    </div>
  </template>
</el-table-column>
```

- [ ] **Step 3: Keep existing create/edit/delete/test dialog behavior unchanged**

Do not remove:
- `handleCreate`
- `handleEdit`
- `handleDelete`
- `handleTest`
- current dialog form fields and validation

Only restyle dialog wrappers if needed; do not change payload shape or submission flow.

- [ ] **Step 4: Add page-scoped styles for the new layout**

Add scoped classes matching the preview direction:

```css
.page-subtitle { margin: 5px 0 0; color: var(--text-secondary); font-size: 13px; }
.summary-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-bottom: 16px; }
.summary-card { padding: 14px 16px; background: var(--surface-color); border: 1px solid var(--border-color); border-radius: var(--border-radius); }
.warning-banner { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 12px 14px; margin-bottom: 16px; background: color-mix(in srgb, var(--warning-color) 10%, white); border: 1px solid color-mix(in srgb, var(--warning-color) 24%, white); border-radius: var(--border-radius); }
.cluster-copy { display: grid; gap: 4px; }
.cluster-copy span { color: var(--text-muted); font-size: 12px; }
```

- [ ] **Step 5: Run build and helper tests**

Run:
- `node --test frontend/src/utils/k8sCluster.test.mjs`
- `npm run build`

Expected:
- helper tests PASS
- Vite build PASS

- [ ] **Step 6: Commit**

```bash
git add frontend/src/views/containers/ContainerView.vue frontend/src/utils/k8sCluster.ts frontend/src/utils/k8sCluster.test.mjs
git commit -m "feat(k8s): refresh cluster fleet overview"
```

### Task 3: Refresh the K8s detail workbench

**Files:**
- Modify: `frontend/src/views/containers/ContainerDetailView.vue`
- Modify: `frontend/src/utils/k8sCluster.ts`
- Test: `frontend/src/utils/k8sCluster.test.mjs`

- [ ] **Step 1: Use helper-driven anomaly summary and preserve current fetch behavior**

Keep:
- `fetchCluster`
- `fetchResources`
- `fetchPods`
- `fetchDeployments`
- `fetchServices`
- dialogs and restart/delete handlers

Replace the local anomaly computation with:

```typescript
import { buildClusterAnomalies, filterClusterPods } from '@/utils/k8sCluster'

const anomalyList = computed(() => buildClusterAnomalies(resources.value))
const filteredPods = computed(() => filterClusterPods(resources.value.pods || [], podSearch.value))
```

- [ ] **Step 2: Rebuild the page header and summary area**

Implement:
- quieter header with back button, cluster name, status tags, version tag, refresh button
- one compact warning banner when anomalies exist
- 4 top summary cards instead of 6 clickable cards

Use:

```typescript
const topSummaryCards = computed(() => [
  { label: '节点', value: resources.value.node_count ?? '-', foot: `NotReady ${Math.max((resources.value.node_count ?? 0) - (resources.value.ready_nodes ?? 0), 0)}` },
  { label: 'Pods', value: resources.value.pod_count ?? '-', foot: `异常 ${anomalyPodCount.value}` },
  { label: 'Deployments', value: resources.value.deployment_count ?? '-', foot: `副本不足 ${deploymentGapCount.value}` },
  { label: '命名空间', value: resources.value.namespace_count ?? '-', foot: resources.value.namespaces?.[0] ? `重点关注 ${resources.value.namespaces[0]}` : '等待资源同步' },
])
```

- [ ] **Step 3: Convert tabs area into one dominant work view**

Keep the existing tabs and data tables, but:
- reduce visible chrome
- keep only one filter row per active section
- make Pods the default tab for workbench triage
- slim Pod columns to: Pod, status, reason, node, restart, actions
- move namespace and deployment context into the Pod subtitle instead of extra columns where possible

Example Pod cell:

```vue
<el-table-column label="Pod" min-width="260">
  <template #default="{ row }">
    <div class="resource-primary">
      <strong>{{ row.name }}</strong>
      <span>{{ row.namespace || '-' }} · {{ row.pod_ip || row.node || '-' }}</span>
    </div>
  </template>
</el-table-column>
```

- [ ] **Step 4: Add the lighter right-side support panel**

Inside the detail page body, add a two-column layout:
- left: active work surface with tabs/tables
- right: `当前异常` and `关联视图` cards

The right side is display-only and uses existing derived state, for example:

```typescript
const sideHighlights = computed(() => [
  anomalyList.value[0],
  anomalyList.value[1],
].filter(Boolean))
```

Do not add new API calls for this panel.

- [ ] **Step 5: Keep all dialogs and destructive actions functional**

Verify the new layout still exposes:
- Pod logs dialog
- Pod events dialog
- Service detail dialog
- Node detail dialog
- Namespace detail dialog
- delete pod
- restart deployment

If a button moves, keep the original handler names and modal logic.

- [ ] **Step 6: Run build and helper tests**

Run:
- `node --test frontend/src/utils/k8sCluster.test.mjs`
- `npm run build`

Expected:
- helper tests PASS
- Vite build PASS

- [ ] **Step 7: Commit**

```bash
git add frontend/src/views/containers/ContainerDetailView.vue frontend/src/utils/k8sCluster.ts frontend/src/utils/k8sCluster.test.mjs
git commit -m "feat(k8s): refresh cluster detail workbench"
```

## Self-Review

- Spec coverage:
  - quieter list page: covered in Task 2
  - quieter detail page: covered in Task 3
  - preserve existing actions/dialogs: covered in Task 2 step 3 and Task 3 step 5
  - helper-driven risk ordering and anomaly summaries: covered in Task 1
- Placeholder scan:
  - no `TODO`, `TBD`, or vague “handle appropriately” steps remain
- Type consistency:
  - helper names are consistently `buildClusterOverview`, `sortClustersByRisk`, `buildClusterAnomalies`, `filterClusterPods`

Plan complete and saved to `docs/superpowers/plans/2026-06-23-k8s-cluster-page-refresh.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
