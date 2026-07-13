import request from './request'

export interface LLMProfile {
  id: string
  name: string
  provider: string
  icon: string
  base_url: string
  api_key: string
  model: string
  api_mode?: 'chat_completions' | 'responses'
  reasoning_effort?: '' | 'low' | 'medium' | 'high'
  temperature: number
  max_tokens: number
  top_p: number
  system_prompt: string
  is_active: boolean
}

export function getSettings() {
  return request.get('/settings/')
}

export function getSetting(key: string) {
  return request.get(`/settings/${key}`)
}

export function updateSetting(key: string, value: string) {
  return request.put(`/settings/${key}`, { value })
}

export function testConnection(service: string, url: string, credentials?: { username?: string; token?: string }) {
  return request.post(`/settings/test-connection/${service}`, {
    url,
    ...credentials,
  })
}

export function testLLMConnection(data: {
  base_url: string
  api_key: string
  model: string
  api_mode: 'chat_completions' | 'responses'
  reasoning_effort: '' | 'low' | 'medium' | 'high'
}) {
  return request.post('/settings/test-connection/llm', data)
}

export function getLLMProfiles() {
  return request.get('/settings/llm/profiles')
}

export function updateLLMProfiles(profiles: LLMProfile[]) {
  return request.put('/settings/llm/profiles', { profiles })
}
