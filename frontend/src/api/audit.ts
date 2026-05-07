import request from './request'

export function getAuditLogs(params?: { keyword?: string; action?: string; target_type?: string; days?: number }) {
  return request.get('/audit/logs', { params })
}
export function getActionLabels() { return request.get('/audit/meta/actions') }
export function getTargetLabels() { return request.get('/audit/meta/target-types') }
