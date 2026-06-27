import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'

const assetListView = readFileSync(new URL('./AssetListView.vue', import.meta.url), 'utf8')
const assetDetailView = readFileSync(new URL('./AssetDetailView.vue', import.meta.url), 'utf8')

test('asset list keeps SSH as status/configuration, not a direct terminal row action', () => {
  assert.match(assetListView, /SSH 状态/)
  assert.doesNotMatch(assetListView, /monitoring\/hosts\/\$\{row\.id\}\/ssh/)
})

test('asset detail promotes monitoring and keeps terminal entry secondary', () => {
  const detailActions = assetDetailView.match(/<div class="detail-actions">[\s\S]*?<\/div>/)?.[0] || ''

  assert.doesNotMatch(detailActions, /SSH 连接/)
  assert.doesNotMatch(detailActions, /monitoring\/hosts\/\$\{assetId\}\/ssh/)
  assert.match(assetDetailView, /查看监控/)
  assert.match(assetDetailView, /打开 SSH 终端/)
})
