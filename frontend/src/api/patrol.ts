import request from './request'

export function runPatrol() { return request.post('/patrol/run') }
export function getPatrolReports(params?: { status?: string; page?: number; page_size?: number }) {
  return request.get('/patrol/reports', { params })
}
export function getPatrolReportDetail(id: number) { return request.get(`/patrol/reports/${id}`) }
export function deletePatrolReport(id: number) { return request.delete(`/patrol/reports/${id}`) }
export function exportPatrolReport(id: number) { return request.get(`/patrol/reports/${id}/export`, { responseType: 'blob' }) }

// 巡检阈值配置
export function getPatrolThresholds() { return request.get('/patrol/thresholds') }
export function updatePatrolThreshold(key: string, value: string) { return request.put(`/patrol/thresholds/${key}`, { value }) }
export function updatePatrolThresholdsBulk(data: Record<string, string>) { return request.put('/patrol/thresholds', data) }
