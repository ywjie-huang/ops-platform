import request from './request'

export function getSettings() {
  return request.get('/settings/')
}

export function getSetting(key: string) {
  return request.get(`/settings/${key}`)
}

export function updateSetting(key: string, value: string) {
  return request.put(`/settings/${key}`, { value })
}

export function testConnection(service: string, url: string) {
  return request.post(`/settings/test-connection/${service}`, { url })
}
