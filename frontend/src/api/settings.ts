import request from './request'

export interface LLMProfile {
  id: string
  name: string
  provider: string
  icon: string
  base_url: string
  api_key: string
  api_key_masked?: string
  has_api_key?: boolean
  model: string
  api_mode?: 'chat_completions' | 'responses' | 'anthropic'
  reasoning_effort?: '' | 'low' | 'medium' | 'high'
  temperature: number
  max_tokens: number
  top_p: number
  system_prompt: string
  is_active: boolean
  /** 复制配置时沿用源 profile 密钥 */
  copy_api_key_from?: string
}

export type LLMErrorCode =
  | 'validation'
  | 'auth'
  | 'model_not_found'
  | 'timeout'
  | 'connect'
  | 'protocol'
  | 'unknown'

export interface LLMTestResult {
  ok: boolean
  latency_ms?: number | null
  status_code?: number | null
  model?: string | null
  error_code?: LLMErrorCode | string | null
  content?: string
  msg?: string
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
  api_key?: string
  model: string
  api_mode?: 'chat_completions' | 'responses' | 'anthropic'
  reasoning_effort?: '' | 'low' | 'medium' | 'high'
  provider?: string
  profile_id?: string
}) {
  return request.post('/settings/test-connection/llm', data)
}

export function testLLMChat(data: {
  base_url: string
  api_key?: string
  model: string
  api_mode?: 'chat_completions' | 'responses' | 'anthropic'
  reasoning_effort?: '' | 'low' | 'medium' | 'high'
  temperature?: number
  max_tokens?: number
  top_p?: number
  system_prompt?: string
  message: string
  provider?: string
  profile_id?: string
}) {
  return request.post('/settings/llm/test-chat', data, { timeout: 35000 })
}


export function listLLMModels(data: {
  base_url: string
  api_key?: string
  provider?: string
  api_mode?: string
  profile_id?: string
}) {
  return request.post('/settings/llm/models', data)
}

export function getLLMProfiles() {
  return request.get('/settings/llm/profiles')
}

export function updateLLMProfiles(profiles: LLMProfile[]) {
  return request.put('/settings/llm/profiles', { profiles })
}

/** 保存前规范化：空 key 表示不修改；去掉纯展示字段 */
export function toLLMProfileWritePayload(profiles: LLMProfile[]): LLMProfile[] {
  return profiles.map((p) => ({
    id: p.id,
    name: p.name,
    provider: p.provider,
    icon: p.icon,
    base_url: p.base_url,
    api_key: (p.api_key || '').trim(),
    model: p.model,
    api_mode: p.api_mode || 'chat_completions',
    reasoning_effort: p.reasoning_effort || '',
    temperature: p.temperature,
    max_tokens: p.max_tokens,
    top_p: p.top_p,
    system_prompt: p.system_prompt || '',
    is_active: !!p.is_active,
    ...(p.copy_api_key_from ? { copy_api_key_from: p.copy_api_key_from } : {}),
  }))
}

export function formatLLMTestMessage(data: LLMTestResult | null | undefined, fallback = ''): string {
  if (!data) return fallback
  const parts: string[] = []
  if (data.ok) {
    parts.push('连接成功')
  } else {
    const guide: Record<string, string> = {
      validation: '请检查必填项',
      auth: '请检查 API Key',
      model_not_found: '请检查模型名称',
      timeout: '连接超时，请检查网络或地址',
      connect: '无法连接，请检查 API 地址',
      protocol: '接口响应异常，请检查接口模式',
      unknown: '未知错误',
    }
    const code = data.error_code ? String(data.error_code) : ''
    parts.push(code && guide[code] ? guide[code] : (fallback || '连接失败'))
  }
  if (data.latency_ms != null) parts.push(`${data.latency_ms}ms`)
  if (data.model) parts.push(`model=${data.model}`)
  return parts.join(' · ')
}
