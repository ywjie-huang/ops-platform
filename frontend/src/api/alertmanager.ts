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
export function getAlertManagerSilences() { return request.get('/alertmanager/silences') }
export function createSilence(data: {
  matchers: Array<{ name: string; value: string; is_regex?: boolean }>
  duration_minutes?: number
  comment?: string
  created_by?: string
}) { return request.post('/alertmanager/silences', data) }
export function deleteSilence(id: string) { return request.delete(`/alertmanager/silences/${id}`) }
export function getRuleEvents(ruleName: string) { return request.get(`/alertmanager/rules/${encodeURIComponent(ruleName)}/events`) }
