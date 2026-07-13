export interface ProviderDraft {
  base_url: string
  model: string
  api_mode: 'chat_completions' | 'responses'
  reasoning_effort: '' | 'low' | 'medium' | 'high'
}

export interface ProviderPreset {
  id: string
  name: string
  icon: string
  hint: string
  base_url: string
  model: string
  api_mode?: 'chat_completions' | 'responses'
  reasoning_effort?: '' | 'low' | 'medium' | 'high'
}

export function snapshotProviderDraft(profile: Partial<ProviderDraft>): ProviderDraft {
  return {
    base_url: profile.base_url || '',
    model: profile.model || '',
    api_mode: profile.api_mode || 'chat_completions',
    reasoning_effort: profile.reasoning_effort || '',
  }
}

export function resolveProviderDraft({
  nextPreset,
  rememberedDraft,
}: {
  nextPreset: ProviderPreset
  rememberedDraft?: Partial<ProviderDraft>
}): ProviderDraft {
  const draft = rememberedDraft || {}
  return {
    base_url: draft.base_url || nextPreset.base_url,
    model: draft.model || nextPreset.model,
    api_mode: draft.api_mode || nextPreset.api_mode || 'chat_completions',
    reasoning_effort:
      draft.reasoning_effort !== undefined
        ? draft.reasoning_effort
        : nextPreset.reasoning_effort || '',
  }
}
