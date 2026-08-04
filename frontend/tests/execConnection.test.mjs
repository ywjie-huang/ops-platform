import test from 'node:test'
import assert from 'node:assert/strict'

const { parseExecControlFrame } = await import(
  new URL('../src/components/execConnection.ts', import.meta.url).href
)

test('parses ready and error control frames', () => {
  assert.deepEqual(parseExecControlFrame('{"type":"ready"}'), { type: 'ready' })
  assert.deepEqual(
    parseExecControlFrame('{"type":"error","message":"Agent disconnected"}'),
    { type: 'error', message: 'Agent disconnected' },
  )
})

test('keeps terminal output and unrelated JSON out of the control channel', () => {
  assert.equal(parseExecControlFrame('/ # '), null)
  assert.equal(parseExecControlFrame('{"container":"ops-mysql"}'), null)
  assert.equal(parseExecControlFrame('{not-json'), null)
  assert.equal(parseExecControlFrame(new Uint8Array([1, 2, 3])), null)
})

test('normalizes an error frame without a string message', () => {
  assert.deepEqual(parseExecControlFrame('{"type":"error","message":42}'), {
    type: 'error',
    message: '',
  })
})
