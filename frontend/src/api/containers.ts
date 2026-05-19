import request from './request'

// 集群管理
export function getClusters(params?: { keyword?: string }) { return request.get('/containers/clusters', { params }) }
export function getCluster(id: number) { return request.get(`/containers/clusters/${id}`) }
export function createCluster(data: { name: string; endpoint: string; token?: string; description?: string }) {
  return request.post('/containers/clusters', data)
}
export function updateCluster(id: number, data: { name: string; endpoint: string; token?: string; description?: string }) {
  return request.put(`/containers/clusters/${id}`, data)
}
export function deleteCluster(id: number) { return request.delete(`/containers/clusters/${id}`) }

// 连接测试
export function testConnection(data: { endpoint: string; token?: string }) {
  return request.post('/containers/test-connection', data)
}

// 集群资源（实时从 K8s API 拉取）
export function getClusterResources(id: number) { return request.get(`/containers/clusters/${id}/resources`) }
export function getClusterNodes(id: number) { return request.get(`/containers/clusters/${id}/nodes`) }
export function getClusterPods(id: number, params?: { namespace?: string }) {
  return request.get(`/containers/clusters/${id}/pods`, { params })
}
export function getClusterServices(id: number, params?: { namespace?: string }) {
  return request.get(`/containers/clusters/${id}/services`, { params })
}
export function getClusterDeployments(id: number, params?: { namespace?: string }) {
  return request.get(`/containers/clusters/${id}/deployments`, { params })
}
export function getPodLogs(id: number, namespace: string, podName: string, params?: { tail_lines?: number }) {
  return request.get(`/containers/clusters/${id}/pods/${encodeURIComponent(namespace)}/${encodeURIComponent(podName)}/logs`, { params })
}
export function getPodEvents(id: number, namespace: string, podName: string) {
  return request.get(`/containers/clusters/${id}/pods/${encodeURIComponent(namespace)}/${encodeURIComponent(podName)}/events`)
}
export function deleteClusterPod(id: number, namespace: string, podName: string) {
  return request.delete(`/containers/clusters/${id}/pods/${encodeURIComponent(namespace)}/${encodeURIComponent(podName)}`)
}
export function restartClusterDeployment(id: number, namespace: string, deploymentName: string) {
  return request.post(`/containers/clusters/${id}/deployments/${encodeURIComponent(namespace)}/${encodeURIComponent(deploymentName)}/restart`)
}

// ─── Docker 监控 ──────────────────────────────────────────

// 概览
export function getDockerOverview() { return request.get('/containers/docker/overview') }

// Docker 主机管理
export function getDockerHosts(params?: { keyword?: string }) { return request.get('/containers/docker/hosts', { params }) }
export function getDockerHost(id: number) { return request.get(`/containers/docker/hosts/${id}`) }
export function createDockerHost(data: { name: string; endpoint: string; description?: string }) {
  return request.post('/containers/docker/hosts', data)
}
export function updateDockerHost(id: number, data: { name: string; endpoint?: string; description?: string }) {
  return request.put(`/containers/docker/hosts/${id}`, data)
}
export function deleteDockerHost(id: number) { return request.delete(`/containers/docker/hosts/${id}`) }
export function refreshDockerHost(id: number) { return request.post(`/containers/docker/hosts/${id}/refresh`) }

// Docker 容器查询
export function getDockerContainers(params?: { host_id?: number; keyword?: string; status?: string }) {
  return request.get('/containers/docker/containers', { params })
}
export function getHostContainers(hostId: number, params?: { keyword?: string; status?: string }) {
  return request.get(`/containers/docker/hosts/${hostId}/containers`, { params })
}
