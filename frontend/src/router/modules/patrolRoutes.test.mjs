import assert from 'node:assert/strict'
import { test } from 'node:test'

const { default: routes } = await import('./routes.ts')

function findRoute(path) {
  return routes.find((route) => route.path === path)
}

test('patrol routes expose command center as default and cockpit as hidden secondary view', () => {
  const patrolRoute = findRoute('/patrol')
  assert.ok(patrolRoute, 'expected /patrol route group to exist')

  const defaultRoute = patrolRoute.children.find((route) => route.path === '')
  assert.equal(defaultRoute.name, 'Patrol')
  assert.equal(defaultRoute.meta.title, '巡检指挥台')
  assert.equal(defaultRoute.meta.permission, 'patrol.view')

  const cockpitRoute = patrolRoute.children.find((route) => route.path === 'cockpit')
  assert.ok(cockpitRoute, 'expected /patrol/cockpit route to exist')
  assert.equal(cockpitRoute.name, 'PatrolCockpit')
  assert.equal(cockpitRoute.meta.title, '态势大屏')
  assert.equal(cockpitRoute.meta.hidden, true)
  assert.equal(cockpitRoute.meta.activeMenu, '/patrol')
  assert.equal(cockpitRoute.meta.permission, 'patrol.view')

  const settingsRoute = patrolRoute.children.find((route) => route.path === 'settings')
  assert.ok(settingsRoute, 'expected /patrol/settings compatibility route to exist')
  assert.equal(settingsRoute.name, 'PatrolSettings')
  assert.equal(settingsRoute.redirect, '/patrol')
  assert.equal(settingsRoute.meta.hidden, true)
  assert.equal(settingsRoute.meta.activeMenu, '/patrol')
  assert.equal(settingsRoute.meta.permission, 'patrol.view')
})
