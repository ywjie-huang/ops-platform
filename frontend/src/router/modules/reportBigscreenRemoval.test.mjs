import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'

const { default: routes } = await import('./routes.ts')
const routeSource = readFileSync(new URL('./routes.ts', import.meta.url), 'utf8')

test('report navigation no longer exposes the removed bigscreen page', () => {
  const rootRoute = routes.find((route) => route.path === '/')
  assert.ok(rootRoute, 'expected root report navigation group to exist')

  assert.equal(
    rootRoute.children.some((route) => route.path === 'bigscreen' || route.name === 'BigScreen'),
    false,
  )
  assert.doesNotMatch(routeSource, /BigScreenView\.vue/)
})
