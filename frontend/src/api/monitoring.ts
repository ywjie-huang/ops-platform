import request from './request'

export function getMetrics(params?: { keyword?: string; category?: string }) { return request.get('/monitoring/metrics', { params }) }
export function getMetricCategories() { return request.get('/monitoring/metrics/categories') }
export function createMetric(data: any) { return request.post('/monitoring/metrics', data) }
export function updateMetric(id: number, data: any) { return request.put(`/monitoring/metrics/${id}`, data) }
export function deleteMetric(id: number) { return request.delete(`/monitoring/metrics/${id}`) }
export function getHosts() { return request.get('/monitoring/hosts') }
export function getHostDetail(id: number) { return request.get(`/monitoring/hosts/${id}`) }
