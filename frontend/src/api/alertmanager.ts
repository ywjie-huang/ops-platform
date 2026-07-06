import request from './request'

export function getAlertManagerStatus() { return request.get('/alertmanager/status') }
export function getAlertManagerAlerts() { return request.get('/alertmanager/alerts') }
export function getAlertManagerRules() { return request.get('/alertmanager/rules') }
export function getAlertManagerRulesHosts(params?: { names?: string[] }) {
  if (!params?.names?.length) return request.get('/alertmanager/rules/hosts')

  const searchParams = new URLSearchParams()
  params.names.forEach((name) => searchParams.append('names', name))
  return request.get('/alertmanager/rules/hosts', { params: searchParams })
}
export function getAlertManagerEvents(params?: { keyword?: string; severity?: string; status?: string; page?: number; page_size?: number }) { return request.get('/alertmanager/events', { params }) }
