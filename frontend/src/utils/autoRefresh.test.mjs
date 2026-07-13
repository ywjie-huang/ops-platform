import test from 'node:test'
import assert from 'node:assert/strict'
import { createAutoRefreshController } from './autoRefresh.js'

test('auto refresh controller replaces an existing timer when started twice', () => {
  const scheduled = []
  const cleared = []
  let nextId = 0

  const originalSetInterval = globalThis.setInterval
  const originalClearInterval = globalThis.clearInterval

  globalThis.setInterval = (callback, delay) => {
    const handle = { id: ++nextId, callback, delay }
    scheduled.push(handle)
    return handle
  }
  globalThis.clearInterval = (handle) => {
    cleared.push(handle)
  }

  try {
    const controller = createAutoRefreshController(() => {}, 15000)

    controller.start()
    controller.start()

    assert.equal(scheduled.length, 2)
    assert.equal(scheduled[0].delay, 15000)
    assert.deepEqual(cleared, [scheduled[0]])
    assert.equal(controller.isRunning(), true)
  } finally {
    globalThis.setInterval = originalSetInterval
    globalThis.clearInterval = originalClearInterval
  }
})

test('auto refresh controller stops the active timer', () => {
  const cleared = []

  const originalSetInterval = globalThis.setInterval
  const originalClearInterval = globalThis.clearInterval

  globalThis.setInterval = () => ({ id: 1 })
  globalThis.clearInterval = (handle) => {
    cleared.push(handle)
  }

  try {
    const controller = createAutoRefreshController(() => {}, 15000)

    controller.start()
    controller.stop()

    assert.deepEqual(cleared, [{ id: 1 }])
    assert.equal(controller.isRunning(), false)
  } finally {
    globalThis.setInterval = originalSetInterval
    globalThis.clearInterval = originalClearInterval
  }
})
