import request from './request'

export function getDashboardStats() {
  return request.get('/dashboard/stats')
}

export function getDashboardSummary() {
  return request.get('/dashboard/summary')
}

export function getSparkline() {
  return request.get('/dashboard/sparkline')
}

export function getActivities(limit = 20, type?: string) {
  const params: any = { limit }
  if (type && type !== 'all') params.type = type
  return request.get('/dashboard/activities', { params })
}

export function getAlertTrend() {
  return request.get('/dashboard/alert-trend')
}
