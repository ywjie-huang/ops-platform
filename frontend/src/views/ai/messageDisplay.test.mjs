import assert from 'node:assert/strict'
import { test } from 'node:test'

const {
  applyAiStreamEvent,
  buildDisplayMessagesFromHistory,
  createAiStreamState,
} = await import('./messageDisplay.ts')

test('builds history display with tool results before the final assistant answer', () => {
  const messages = [
    {
      id: 1,
      role: 'user',
      content: 'Which server is abnormal today?',
      created_at: '2026-07-06T15:00:00+08:00',
    },
    {
      id: 2,
      role: 'assistant',
      content: 'I will check alerts and host metrics first.',
      tool_calls: [
        {
          id: 'call_1',
          type: 'function',
          function: { name: 'query_alerts', arguments: '{"limit":10}' },
        },
      ],
      created_at: '2026-07-06T15:00:01+08:00',
    },
    {
      id: 3,
      role: 'tool',
      content: 'No active alerts.',
      tool_call_id: 'call_1',
      tool_name: 'query_alerts',
      created_at: '2026-07-06T15:00:02+08:00',
    },
    {
      id: 4,
      role: 'assistant',
      content: 'No servers are currently abnormal.',
      created_at: '2026-07-06T15:00:03+08:00',
    },
  ]

  const display = buildDisplayMessagesFromHistory(messages, value => value)

  assert.deepEqual(display.map(item => item.type), ['user', 'text', 'tool_result', 'text'])
  assert.equal(display[2].tool, 'query_alerts')
  assert.deepEqual(display[2].args, { limit: 10 })
  assert.equal(display[3].content, 'No servers are currently abnormal.')
})

test('streams post-tool assistant text after the tool result instead of merging upward', () => {
  const display = []
  const state = createAiStreamState()
  let now = 1000

  const apply = event => applyAiStreamEvent(event, display, state, () => '15:00', () => now)

  apply({ type: 'text', content: 'I will check alerts first.' })
  apply({ type: 'tool_start', tool: 'query_alerts', args: { limit: 10 } })
  now = 1042
  apply({ type: 'tool_result', tool: 'query_alerts', result: 'No active alerts.', args: { limit: 10 } })
  apply({ type: 'text', content: 'No servers are currently abnormal.' })

  assert.deepEqual(display.map(item => item.type), ['text', 'tool_result', 'text'])
  assert.equal(display[0].content, 'I will check alerts first.')
  assert.equal(display[1].elapsed, 42)
  assert.equal(display[2].content, 'No servers are currently abnormal.')
})
