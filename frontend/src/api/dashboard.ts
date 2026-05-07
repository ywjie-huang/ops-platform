import request from './request'

export function getDashboardStats() {
  return request.get('/dashboard/stats')
}

export function getDashboardSummary() {
  return request.get('/dashboard/summary')
}
