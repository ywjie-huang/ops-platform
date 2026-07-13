import test from 'node:test'
import assert from 'node:assert/strict'
const providerPresetModule = await import(
  new URL('../src/views/ai/providerPreset.ts', import.meta.url).href
)
const { resolveProviderDraft, snapshotProviderDraft } = providerPresetModule

test('restores remembered custom base url when switching back to a provider', () => {
  const openaiDraft = snapshotProviderDraft({
    base_url: 'https://api.aijws.com/v1',
    model: 'gpt-5.5',
    api_mode: 'responses',
    reasoning_effort: 'high',
  })

  const resolved = resolveProviderDraft({
    nextPreset: {
      id: 'openai',
      name: 'OpenAI',
      icon: 'AI',
      base_url: 'https://api.openai.com/v1',
      model: 'gpt-4o',
      api_mode: 'responses',
      reasoning_effort: 'medium',
    },
    rememberedDraft: openaiDraft,
  })

  assert.equal(resolved.base_url, 'https://api.aijws.com/v1')
  assert.equal(resolved.model, 'gpt-5.5')
  assert.equal(resolved.api_mode, 'responses')
  assert.equal(resolved.reasoning_effort, 'high')
})

test('falls back to provider preset when no remembered draft exists', () => {
  const resolved = resolveProviderDraft({
    nextPreset: {
      id: 'deepseek',
      name: 'DeepSeek',
      icon: 'DS',
      base_url: 'https://api.deepseek.com/v1',
      model: 'deepseek-chat',
      api_mode: 'chat_completions',
      reasoning_effort: '',
    },
    rememberedDraft: undefined,
  })

  assert.equal(resolved.base_url, 'https://api.deepseek.com/v1')
  assert.equal(resolved.model, 'deepseek-chat')
  assert.equal(resolved.api_mode, 'chat_completions')
  assert.equal(resolved.reasoning_effort, '')
})
