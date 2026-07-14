import test from 'node:test'
import assert from 'node:assert/strict'

const mod = await import(new URL('./modelConfigState.ts', import.meta.url).href)
const { serializeProfiles, normalizeLoadedProfiles, isLocalProvider } = mod

test('serializeProfiles ignores display-only differences in masked key text', () => {
  const a = [{
    id: '1', name: 'A', provider: 'deepseek', icon: 'DS',
    base_url: 'https://api.deepseek.com/v1', api_key: '', has_api_key: true,
    api_key_masked: 'sk-****1111', model: 'deepseek-chat', temperature: 0.7,
    max_tokens: 4096, top_p: 1, system_prompt: '', is_active: true,
  }]
  const b = [{
    ...a[0],
    api_key_masked: 'sk-****9999',
  }]
  assert.equal(serializeProfiles(a), serializeProfiles(b))
})

test('serializeProfiles detects draft key edits', () => {
  const base = [{
    id: '1', name: 'A', provider: 'deepseek', icon: 'DS',
    base_url: 'https://api.deepseek.com/v1', api_key: '', has_api_key: true,
    model: 'deepseek-chat', temperature: 0.7, max_tokens: 4096, top_p: 1,
    system_prompt: '', is_active: true,
  }]
  const edited = [{ ...base[0], api_key: 'sk-new' }]
  assert.notEqual(serializeProfiles(base), serializeProfiles(edited))
})

test('normalizeLoadedProfiles clears plaintext api_key', () => {
  const items = normalizeLoadedProfiles([{
    id: '1', name: 'A', provider: 'x', icon: 'X', base_url: 'http://x',
    api_key: 'should-not-keep', has_api_key: true, api_key_masked: 'sk-****',
    model: 'm', temperature: 0.5, max_tokens: 1, top_p: 1, system_prompt: '',
    is_active: false,
  }])
  assert.equal(items[0].api_key, '')
  assert.equal(items[0].has_api_key, true)
})

test('isLocalProvider detects ollama and loopback', () => {
  assert.equal(isLocalProvider({ provider: 'ollama', base_url: 'https://x' }), true)
  assert.equal(isLocalProvider({ provider: 'custom', base_url: 'http://localhost:11434/v1' }), true)
  assert.equal(isLocalProvider({ provider: 'deepseek', base_url: 'https://api.deepseek.com/v1' }), false)
})
