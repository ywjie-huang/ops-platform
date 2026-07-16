import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'

const { default: routes } = await import('./routes.ts')
const assetGroup = routes.find((route) => route.path === '/assets')
const listSource = readFileSync(new URL('../../views/assets/AssetListView.vue', import.meta.url), 'utf8')
const detailSource = readFileSync(new URL('../../views/assets/AssetDetailView.vue', import.meta.url), 'utf8')
const apiSource = readFileSync(new URL('../../api/assets.ts', import.meta.url), 'utf8')

test('asset routes expose canonical host collection and detail paths', () => {
  assert.equal(assetGroup.redirect, '/assets/hosts')
  assert.ok(assetGroup.children.some((route) => route.path === 'hosts' && route.name === 'AssetList'))
  assert.ok(assetGroup.children.some((route) => route.path === 'hosts/:publicId' && route.name === 'AssetDetail'))
})

test('legacy list and numeric detail routes remain resolvable', () => {
  assert.ok(assetGroup.children.some((route) => route.path === 'list' && route.redirect === '/assets/hosts'))
  assert.ok(assetGroup.children.some((route) => route.path === ':legacyId(\\d+)' && route.name === 'LegacyAssetDetail'))
})

test('asset screens use public IDs for canonical navigation and lookup', () => {
  assert.match(listSource, /\/assets\/hosts\/\$\{row\.public_id\}/)
  assert.match(detailSource, /route\.params\.publicId/)
  assert.match(detailSource, /getAssetByPublicId/)
  assert.match(apiSource, /\/assets\/public\/\$\{publicId\}/)
})
