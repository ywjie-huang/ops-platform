import type { LLMProfile } from '@/api/settings'

/** 稳定序列化，用于 dirty 对比（忽略纯展示字段） */
export function serializeProfiles(profiles: LLMProfile[]): string {
  return JSON.stringify(
    profiles.map((p) => ({
      id: p.id,
      name: p.name,
      provider: p.provider,
      icon: p.icon,
      base_url: p.base_url,
      // 仅比较用户新输入的 key；已保存密钥用 has_api_key 表达
      api_key: (p.api_key || '').trim(),
      has_api_key: !!p.has_api_key,
      model: p.model,
      api_mode: p.api_mode || 'chat_completions',
      reasoning_effort: p.reasoning_effort || '',
      temperature: p.temperature,
      max_tokens: p.max_tokens,
      top_p: p.top_p,
      system_prompt: p.system_prompt || '',
      is_active: !!p.is_active,
      copy_api_key_from: p.copy_api_key_from || '',
    })),
  )
}

export function normalizeLoadedProfiles(items: LLMProfile[]): LLMProfile[] {
  return (items || []).map((p) => ({
    ...p,
    api_key: '', // 读接口不回显明文；输入框留空表示不修改
    api_key_masked: p.api_key_masked || '',
    has_api_key: !!p.has_api_key,
    api_mode: p.api_mode || 'chat_completions',
    reasoning_effort: p.reasoning_effort || '',
    system_prompt: p.system_prompt || '',
  }))
}

export function isLocalProvider(profile: Pick<LLMProfile, 'provider' | 'base_url'>): boolean {
  const provider = (profile.provider || '').toLowerCase()
  const url = (profile.base_url || '').toLowerCase()
  if (provider === 'ollama') return true
  return (
    url.includes('localhost') ||
    url.includes('127.0.0.1') ||
    url.includes('0.0.0.0') ||
    url.includes(':11434') ||
    url.includes('host.docker.internal')
  )
}
