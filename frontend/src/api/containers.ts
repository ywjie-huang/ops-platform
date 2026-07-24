import request from './request'

// 集群管理
export function getClusters(params?: { keyword?: string }) { return request.get('/containers/clusters', { params }) }
export function getCluster(name: string) { return request.get(`/containers/clusters/${encodeURIComponent(name)}`) }
export function createCluster(data: { name: string; endpoint: string; token?: string; description?: string }) {
  return request.post('/containers/clusters', data)
}
export function updateCluster(name: string, data: { name: string; endpoint: string; token?: string; description?: string }) {
  return request.put(`/containers/clusters/${encodeURIComponent(name)}`, data)
}
export function deleteCluster(name: string) { return request.delete(`/containers/clusters/${encodeURIComponent(name)}`) }

// 连接测试
export function testConnection(data: { endpoint: string; token?: string }) {
  return request.post('/containers/test-connection', data)
}

// 集群资源（实时从 K8s API 拉取）
export function getClusterResources(name: string) { return request.get(`/containers/clusters/${encodeURIComponent(name)}/resources`) }
export function getClusterNodes(name: string) { return request.get(`/containers/clusters/${encodeURIComponent(name)}/nodes`) }
export function getClusterPods(name: string, params?: { namespace?: string }) {
  return request.get(`/containers/clusters/${encodeURIComponent(name)}/pods`, { params })
}
export function getClusterServices(name: string, params?: { namespace?: string }) {
  return request.get(`/containers/clusters/${encodeURIComponent(name)}/services`, { params })
}
export function getClusterDeployments(name: string, params?: { namespace?: string }) {
  return request.get(`/containers/clusters/${encodeURIComponent(name)}/deployments`, { params })
}
export function getPodLogs(name: string, namespace: string, podName: string, params?: { tail_lines?: number }) {
  return request.get(`/containers/clusters/${encodeURIComponent(name)}/pods/${encodeURIComponent(namespace)}/${encodeURIComponent(podName)}/logs`, { params })
}
export function getPodEvents(name: string, namespace: string, podName: string) {
  return request.get(`/containers/clusters/${encodeURIComponent(name)}/pods/${encodeURIComponent(namespace)}/${encodeURIComponent(podName)}/events`)
}
export function deleteClusterPod(name: string, namespace: string, podName: string) {
  return request.delete(`/containers/clusters/${encodeURIComponent(name)}/pods/${encodeURIComponent(namespace)}/${encodeURIComponent(podName)}`)
}
export function restartClusterDeployment(name: string, namespace: string, deploymentName: string) {
  return request.post(`/containers/clusters/${encodeURIComponent(name)}/deployments/${encodeURIComponent(namespace)}/${encodeURIComponent(deploymentName)}/restart`)
}

// ─── Docker 监控 ──────────────────────────────────────────

// 概览
export function getDockerOverview() { return request.get('/containers/docker/overview') }

// Docker 主机管理
export function getDockerHosts(params?: { keyword?: string }) { return request.get('/containers/docker/hosts', { params }) }
export function getDockerHost(name: string) { return request.get(`/containers/docker/hosts/${encodeURIComponent(name)}`) }
export function createDockerHost(data: { name: string; endpoint: string; description?: string }) {
  return request.post('/containers/docker/hosts', data)
}
export function updateDockerHost(name: string, data: { name: string; endpoint?: string; description?: string }) {
  return request.put(`/containers/docker/hosts/${encodeURIComponent(name)}`, data)
}
export function deleteDockerHost(name: string) { return request.delete(`/containers/docker/hosts/${encodeURIComponent(name)}`) }
export function refreshDockerHost(name: string) { return request.post(`/containers/docker/hosts/${encodeURIComponent(name)}/refresh`) }

// Docker 容器查询
export function getDockerContainers(params?: { keyword?: string; status?: string }) {
  return request.get('/containers/docker/containers', { params })
}
export function getHostContainers(hostName: string, params?: { keyword?: string; status?: string }) {
  return request.get(`/containers/docker/hosts/${encodeURIComponent(hostName)}/containers`, { params })
}
export function getDockerContainerLogs(hostName: string, containerId: string, params?: { tail_lines?: number }) {
  return request.get(`/containers/docker/hosts/${encodeURIComponent(hostName)}/containers/${encodeURIComponent(containerId)}/logs`, { params })
}

// Docker 容器操作
export function startDockerContainer(hostName: string, containerId: string) {
  return request.post(`/containers/docker/hosts/${encodeURIComponent(hostName)}/containers/${encodeURIComponent(containerId)}/start`)
}
export function stopDockerContainer(hostName: string, containerId: string) {
  return request.post(`/containers/docker/hosts/${encodeURIComponent(hostName)}/containers/${encodeURIComponent(containerId)}/stop`)
}
export function restartDockerContainer(hostName: string, containerId: string) {
  return request.post(`/containers/docker/hosts/${encodeURIComponent(hostName)}/containers/${encodeURIComponent(containerId)}/restart`)
}
export function deleteDockerContainer(hostName: string, containerId: string) {
  return request.post(`/containers/docker/hosts/${encodeURIComponent(hostName)}/containers/${encodeURIComponent(containerId)}/delete`)
}
