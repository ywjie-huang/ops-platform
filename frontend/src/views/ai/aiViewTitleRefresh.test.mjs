import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'

const source = readFileSync(new URL('./AiView.vue', import.meta.url), 'utf8')

test('AI view waits for pending generated titles before refreshing the list', () => {
  assert.match(source, /let titlePendingConvId: number \| null = null/)
  assert.match(source, /event\.title_pending && event\.conversation_id/)
  assert.match(
    source,
    /if \(titlePendingConvId\) \{\s*await waitForConversationTitle\(titlePendingConvId\)\s*\} else \{\s*await loadConversations\(\)\s*\}/s,
  )
  assert.match(source, /async function waitForConversationTitle/)
  assert.match(source, /conversation\.title !== DEFAULT_CONVERSATION_TITLE/)
})

test('AI view still refreshes once after confirm or reject continuations', () => {
  assert.match(source, /confirmAiActionStream[\s\S]*await loadConversations\(\)/)
  assert.match(source, /rejectAiActionStream[\s\S]*await loadConversations\(\)/)
  assert.doesNotMatch(source, /scheduleConversationTitleRefresh\(\)/)
})
