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

export function testLLMConnection(data: { base_url: string; api_key: string; model: string }) {
  return request.post('/settings/test-connection/llm', data)
}
