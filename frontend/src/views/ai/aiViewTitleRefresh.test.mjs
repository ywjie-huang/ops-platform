import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'

const source = readFileSync(new URL('./AiView.vue', import.meta.url), 'utf8')

test('AI view schedules a delayed conversation title refresh after chat streams finish', () => {
  assert.match(source, /function scheduleConversationTitleRefresh\(\)/)
  assert.match(source, /window\.setTimeout\(\(\) => \{\s*loadConversations\(\)\s*\}, 1500\)/s)
  assert.match(source, /await loadConversations\(\)\s*scheduleConversationTitleRefresh\(\)/)
})

test('AI view also refreshes titles after confirm and reject continuations', () => {
  assert.match(
    source,
    /confirmAiActionStream[\s\S]*await loadConversations\(\)\s*scheduleConversationTitleRefresh\(\)/,
  )
  assert.match(
    source,
    /rejectAiActionStream[\s\S]*await loadConversations\(\)\s*scheduleConversationTitleRefresh\(\)/,
  )
})
