import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'
import { createMemoryHistory, createRouter } from 'vue-router'

const { default: routes } = await import('./routes.ts')
const assetGroup = routes.find((route) => route.path === '/assets')
const dockerListSource = readFileSync(new URL('../../views/containers/DockerView.vue', import.meta.url), 'utf8')
const dockerDetailSource = readFileSync(new URL('../../views/containers/DockerDetailView.vue', import.meta.url), 'utf8')
const clusterListSource = readFileSync(new URL('../../views/containers/ContainerView.vue', import.meta.url), 'utf8')
const clusterDetailSource = readFileSync(new URL('../../views/containers/ContainerDetailView.vue', import.meta.url), 'utf8')

test('container routes use readable resource names as canonical paths', () => {
  assert.ok(assetGroup.children.some((route) => route.path === 'docker/host/:name' && route.name === 'DockerDetail'))
  assert.ok(assetGroup.children.some((route) => route.path === 'containers/cluster/:name' && route.name === 'ContainerDetail'))
  assert.match(dockerListSource, /name: 'DockerDetail', params: \{ name: row\.name \}/)
  assert.match(clusterListSource, /name: 'ContainerDetail', params: \{ name: row\.name \}/)
})

test('vue router resolves readable and legacy detail URLs to the intended routes', () => {
  const router = createRouter({ history: createMemoryHistory(), routes })

  assert.equal(router.resolve('/assets/docker/host/docker-prod-01').name, 'DockerDetail')
  assert.equal(router.resolve('/assets/containers/cluster/prod-k8s').name, 'ContainerDetail')
  assert.equal(router.resolve('/assets/docker/12').name, 'DockerDetailLegacy')
  assert.equal(router.resolve('/assets/containers/4').name, 'ContainerDetailLegacy')
})

test('legacy numeric paths remain compatible and canonicalize to name routes', () => {
  assert.ok(assetGroup.children.some((route) => route.path === 'docker/:id(\\d+)' && route.name === 'DockerDetailLegacy'))
  assert.ok(assetGroup.children.some((route) => route.path === 'containers/:id(\\d+)' && route.name === 'ContainerDetailLegacy'))
  assert.match(dockerDetailSource, /router\.replace\(\{ name: 'DockerDetail'/)
  assert.match(clusterDetailSource, /router\.replace\(\{ name: 'ContainerDetail'/)
})
