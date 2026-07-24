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
const apiSource = readFileSync(new URL('../../api/containers.ts', import.meta.url), 'utf8')

test('container routes use readable resource names as canonical paths', () => {
  assert.ok(assetGroup.children.some((route) => route.path === 'docker/host/:name' && route.name === 'DockerDetail'))
  assert.ok(assetGroup.children.some((route) => route.path === 'containers/cluster/:name' && route.name === 'ContainerDetail'))
  assert.match(dockerListSource, /name: 'DockerDetail', params: \{ name: row\.name \}/)
  assert.match(clusterListSource, /name: 'ContainerDetail', params: \{ name: row\.name \}/)
})

test('vue router resolves only readable detail URLs', () => {
  const router = createRouter({ history: createMemoryHistory(), routes })

  assert.equal(router.resolve('/assets/docker/host/docker-prod-01').name, 'DockerDetail')
  assert.equal(router.resolve('/assets/containers/cluster/prod-k8s').name, 'ContainerDetail')
  assert.equal(router.resolve('/assets/docker/12').name, undefined)
  assert.equal(router.resolve('/assets/containers/4').name, undefined)
})

test('detail data and operations use names without numeric or transitional endpoints', () => {
  assert.doesNotMatch(apiSource, /hosts\/by-name|clusters\/by-name/)
  assert.doesNotMatch(apiSource, /hosts\/\$\{(?:host)?[Ii]d\}|clusters\/\$\{(?:cluster)?[Ii]d\}/)
  assert.doesNotMatch(dockerDetailSource, /hostId|route\.params\.id/)
  assert.doesNotMatch(clusterDetailSource, /clusterId|route\.params\.id/)
})

test('cached detail views ignore name params owned by the other resource route', () => {
  assert.match(dockerDetailSource, /route\.name === 'DockerDetail' \? String\(route\.params\.name/)
  assert.match(clusterDetailSource, /route\.name === 'ContainerDetail' \? String\(route\.params\.name/)
})
