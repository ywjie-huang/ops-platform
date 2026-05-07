import request from './request'

export function getContainerOverview() { return request.get('/containers/overview') }
export function getClusters() { return request.get('/containers/clusters') }
export function createCluster(data: any) { return request.post('/containers/clusters', data) }
export function updateCluster(id: number, data: any) { return request.put(`/containers/clusters/${id}`, data) }
export function deleteCluster(id: number) { return request.delete(`/containers/clusters/${id}`) }
export function getPods(params?: { cluster_id?: number; status?: string }) { return request.get('/containers/pods', { params }) }
export function deletePod(id: number) { return request.delete(`/containers/pods/${id}`) }
export function getServices(params?: { cluster_id?: number }) { return request.get('/containers/services', { params }) }
export function deleteService(id: number) { return request.delete(`/containers/services/${id}`) }
export function getDeployments(params?: { cluster_id?: number }) { return request.get('/containers/deployments', { params }) }
