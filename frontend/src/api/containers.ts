import request from './request'
import { getToken } from '@/utils/auth'

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
export function downloadClusterKubeconfig(name: string) {
  return request.get(`/containers/clusters/${encodeURIComponent(name)}/kubeconfig`, { responseType: 'blob' })
}
export function testSavedClusterConnection(name: string) {
  return request.post(`/containers/clusters/${encodeURIComponent(name)}/test-connection`)
}

// 连接测试
export function testConnection(data: { endpoint: string; token?: string }) {
  return request.post('/containers/test-connection', data)
}

// 集群资源（实时从 K8s API 拉取）
export function getClusterResources(name: string) { return request.get(`/containers/clusters/${encodeURIComponent(name)}/resources`) }
export function getClusterNodes(name: string) { return request.get(`/containers/clusters/${encodeURIComponent(name)}/nodes`) }
export function getNodeMaintenancePreview(name: string, nodeName: string) {
  return request.get(`/containers/clusters/${encodeURIComponent(name)}/nodes/${encodeURIComponent(nodeName)}/maintenance-preview`)
}
export function cordonClusterNode(name: string, nodeName: string, data: { confirm_node: string; unschedulable: boolean }) {
  return request.post(`/containers/clusters/${encodeURIComponent(name)}/nodes/${encodeURIComponent(nodeName)}/cordon`, data)
}
export function drainClusterNode(name: string, nodeName: string, data: { confirm_node: string; grace_period_seconds?: number }) {
  return request.post(`/containers/clusters/${encodeURIComponent(name)}/nodes/${encodeURIComponent(nodeName)}/drain`, data)
}
export function getClusterPods(name: string, params?: { namespace?: string }) {
  return request.get(`/containers/clusters/${encodeURIComponent(name)}/pods`, { params })
}
export function getClusterServices(name: string, params?: { namespace?: string }) {
  return request.get(`/containers/clusters/${encodeURIComponent(name)}/services`, { params })
}
export function getClusterDeployments(name: string, params?: { namespace?: string }) {
  return request.get(`/containers/clusters/${encodeURIComponent(name)}/deployments`, { params })
}
export function getPodLogs(
  name: string,
  namespace: string,
  podName: string,
  params?: { tail_lines?: number; since?: number; until?: number },
) {
  return request.get(`/containers/clusters/${encodeURIComponent(name)}/pods/${encodeURIComponent(namespace)}/${encodeURIComponent(podName)}/logs`, { params })
}

// EventSource 无法使用 axios 实例（不能自定义请求头），单独拼全 URL + token
export function buildPodLogStreamUrl(name: string, namespace: string, podName: string, sinceUnix: number): string {
  const base = (import.meta.env.VITE_API_BASE_URL as string) || '/api/v1'
  const token = getToken() || ''
  const params = new URLSearchParams({
    token,
    since: String(sinceUnix),
    interval: '2',
  })
  return `${base}/containers/clusters/${encodeURIComponent(name)}/pods/${encodeURIComponent(namespace)}/${encodeURIComponent(podName)}/logs/stream?${params.toString()}`
}
export function getPodEvents(name: string, namespace: string, podName: string) {
  return request.get(`/containers/clusters/${encodeURIComponent(name)}/pods/${encodeURIComponent(namespace)}/${encodeURIComponent(podName)}/events`)
}
export function getPodDetail(name: string, namespace: string, podName: string) {
  return request.get(`/containers/clusters/${encodeURIComponent(name)}/pods/${encodeURIComponent(namespace)}/${encodeURIComponent(podName)}`)
}
export function getClusterEvents(name: string) {
  return request.get(`/containers/clusters/${encodeURIComponent(name)}/events`)
}
export function deleteClusterPod(name: string, namespace: string, podName: string) {
  return request.delete(`/containers/clusters/${encodeURIComponent(name)}/pods/${encodeURIComponent(namespace)}/${encodeURIComponent(podName)}`)
}
export function restartClusterDeployment(name: string, namespace: string, deploymentName: string) {
  return request.post(`/containers/clusters/${encodeURIComponent(name)}/deployments/${encodeURIComponent(namespace)}/${encodeURIComponent(deploymentName)}/restart`)
}
export function scaleClusterDeployment(name: string, namespace: string, deploymentName: string, replicas: number) {
  return request.post(
    `/containers/clusters/${encodeURIComponent(name)}/deployments/${encodeURIComponent(namespace)}/${encodeURIComponent(deploymentName)}/scale`,
    { replicas },
  )
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
export function getDockerContainerLogs(
  hostName: string,
  containerId: string,
  params?: { tail_lines?: number; since?: number; until?: number },
) {
  return request.get(`/containers/docker/hosts/${encodeURIComponent(hostName)}/containers/${encodeURIComponent(containerId)}/logs`, { params })
}
export function getDockerContainerInspect(hostName: string, containerId: string) {
  return request.get(`/containers/docker/hosts/${encodeURIComponent(hostName)}/containers/${encodeURIComponent(containerId)}/inspect`)
}

// EventSource 无法使用 axios 实例（不能自定义请求头），单独拼全 URL + token
export function buildDockerLogStreamUrl(hostName: string, containerId: string, sinceUnix: number): string {
  const base = (import.meta.env.VITE_API_BASE_URL as string) || '/api/v1'
  const token = getToken() || ''
  const params = new URLSearchParams({
    token,
    since: String(sinceUnix),
    interval: '2',
  })
  return `${base}/containers/docker/hosts/${encodeURIComponent(hostName)}/containers/${encodeURIComponent(containerId)}/logs/stream?${params.toString()}`
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
