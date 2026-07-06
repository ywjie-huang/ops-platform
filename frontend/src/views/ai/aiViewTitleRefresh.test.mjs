import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'

const source = readFileSync(new URL('./AiView.vue', import.meta.url), 'utf8')

test('AI view refreshes the conversation list once after chat streams finish', () => {
  assert.doesNotMatch(source, /function scheduleConversationTitleRefresh\(\)/)
  assert.doesNotMatch(source, /window\.setTimeout\(/)
  assert.doesNotMatch(source, /scheduleConversationTitleRefresh\(\)/)
  assert.match(source, /sendAiMessageStream[\s\S]*await loadConversations\(\)/)
})

test('AI view does not schedule duplicate refreshes after confirm or reject continuations', () => {
  assert.match(source, /confirmAiActionStream[\s\S]*await loadConversations\(\)/)
  assert.match(source, /rejectAiActionStream[\s\S]*await loadConversations\(\)/)
  assert.doesNotMatch(
    source,
    /confirmAiActionStream[\s\S]*scheduleConversationTitleRefresh\(\)/,
  )
  assert.doesNotMatch(
    source,
    /rejectAiActionStream[\s\S]*scheduleConversationTitleRefresh\(\)/,
  )
})
