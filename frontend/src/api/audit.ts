import request from './request'

export interface AuditQuery {
  keyword?: string
  action?: string
  target_type?: string
  days?: number
}

export function getAuditLogs(params?: AuditQuery & { page?: number; page_size?: number }) {
  return request.get('/audit/logs', { params })
}

export function getAuditStats() {
  return request.get('/audit/stats')
}

export function exportAuditLogs(params?: AuditQuery) {
  return request.get('/audit/logs/export', { params, responseType: 'blob' })
}

export function getActionLabels() {
  return request.get('/audit/meta/actions')
}

export function getTargetLabels() {
  return request.get('/audit/meta/target-types')
}
