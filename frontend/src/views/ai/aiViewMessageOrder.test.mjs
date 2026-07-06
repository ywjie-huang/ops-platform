import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'

const source = readFileSync(new URL('./AiView.vue', import.meta.url), 'utf8')

test('AI view keeps tool results in persisted message order', () => {
  assert.match(source, /buildDisplayMessagesFromHistory/)
  assert.doesNotMatch(source, /\.filter\(m => m\.role !== 'tool'\)/)
})

test('AI view uses stream event reducer so post-tool text is appended after tools', () => {
  assert.match(source, /applyAiStreamEvent/)
  assert.doesNotMatch(source, /const textMsg: DisplayMessage = \{ type: 'text'/)
})
