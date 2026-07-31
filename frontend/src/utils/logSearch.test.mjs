import assert from 'node:assert/strict'
import { test } from 'node:test'

const {
  filterLogLines,
  highlightLogLines,
  normalizeLogKeyword,
} = await import('./logSearch.ts')

test('filters log lines case-insensitively', () => {
  const keyword = normalizeLogKeyword(' ERROR ')
  assert.equal(keyword, 'error')
  assert.equal(
    filterLogLines('INFO started\nError connection refused\nWARN retrying', keyword),
    'Error connection refused',
  )
})

test('splits every matched keyword into safe display segments', () => {
  assert.deepEqual(highlightLogLines('error: Error\nready', 'error'), [
    [
      { text: 'error', highlighted: true },
      { text: ': ', highlighted: false },
      { text: 'Error', highlighted: true },
    ],
    [{ text: 'ready', highlighted: false }],
  ])
})

test('treats regular expression characters in keywords as literal text', () => {
  assert.equal(filterLogLines('a.b matched\naxb skipped', 'a.b'), 'a.b matched')
  assert.deepEqual(highlightLogLines('a.b matched', 'a.b'), [[
    { text: 'a.b', highlighted: true },
    { text: ' matched', highlighted: false },
  ]])
})
