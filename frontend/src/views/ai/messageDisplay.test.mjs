import assert from 'node:assert/strict'
import { test } from 'node:test'

const {
  applyAiStreamEvent,
  buildDisplayMessagesFromHistory,
  createAiStreamState,
} = await import('./messageDisplay.ts')

test('builds history display with a merged trace before the final assistant answer', () => {
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

  assert.deepEqual(display.map(item => item.type), ['user', 'tool_trace', 'text'])
  assert.equal(display[1].steps[0].type, 'note')
  assert.equal(display[1].steps[0].content, 'I will check alerts and host metrics first.')
  assert.equal(display[1].steps[1].type, 'tool')
  assert.equal(display[1].steps[1].tool, 'query_alerts')
  assert.deepEqual(display[1].steps[1].args, { limit: 10 })
  assert.equal(display[2].content, 'No servers are currently abnormal.')
})

test('buffers pre-tool text into the merged trace and keeps final text after tools', () => {
  const display = []
  const state = createAiStreamState()
  let now = 1000

  const apply = event => applyAiStreamEvent(event, display, state, () => '15:00', () => now)

  apply({ type: 'text', content: 'I will check alerts first.' })
  apply({ type: 'tool_start', tool: 'query_alerts', args: { limit: 10 } })
  now = 1042
  apply({ type: 'tool_result', tool: 'query_alerts', result: 'No active alerts.', args: { limit: 10 } })
  apply({ type: 'text', content: 'No servers are currently abnormal.' })
  apply({ type: 'done' })

  assert.deepEqual(display.map(item => item.type), ['tool_trace', 'text'])
  assert.equal(display[0].steps[0].type, 'note')
  assert.equal(display[0].steps[0].content, 'I will check alerts first.')
  assert.equal(display[0].steps[1].type, 'tool')
  assert.equal(display[0].steps[1].elapsed, 42)
  assert.equal(display[1].content, 'No servers are currently abnormal.')
})

test('keeps text-only answers visible when no tool is used', () => {
  const display = []
  const state = createAiStreamState()
  const apply = event => applyAiStreamEvent(event, display, state, () => '15:00')

  apply({ type: 'text', content: 'I am GPT.' })
  apply({ type: 'done' })

  assert.deepEqual(display, [{ type: 'text', content: 'I am GPT.', time: '15:00' }])
})

test('turns text between tool calls into trace notes instead of final answers', () => {
  const display = []
  const state = createAiStreamState()
  const apply = event => applyAiStreamEvent(event, display, state, () => '15:00')

  apply({ type: 'tool_start', tool: 'query_alerts' })
  apply({ type: 'tool_result', tool: 'query_alerts', result: 'No active alerts.' })
  apply({ type: 'text', content: 'Alerts are empty; I will check metrics next.' })
  apply({ type: 'tool_start', tool: 'query_host_metrics' })

  assert.deepEqual(display.map(item => item.type), ['tool_trace'])
  assert.equal(display[0].steps[1].type, 'note')
  assert.equal(display[0].steps[1].content, 'Alerts are empty; I will check metrics next.')
  assert.equal(display[0].steps[2].tool, 'query_host_metrics')
})
