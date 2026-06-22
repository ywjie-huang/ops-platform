import assert from 'node:assert/strict'
import { test } from 'node:test'

const {
  assetRiskScore,
  getAssetCompleteness,
  getAssetSshState,
  sortAssetsByRisk,
} = await import('./assetDisplay.ts')

test('calculates asset completeness from basic, spec, owner, and SSH fields', () => {
  const complete = {
    name: 'web-prod-01',
    ip_address: '172.16.100.21',
    asset_type: '云主机',
    status: '使用中',
    owner: '陈明',
    spec: '8C / 16G',
    os: 'Ubuntu 22.04',
    ssh_username: 'deploy',
    ssh_port: 22,
    ssh_key_id: 2,
    has_ssh_password: false,
  }
  const incomplete = {
    name: 'db-prod-02',
    ip_address: '172.16.100.32',
    asset_type: '云主机',
    status: '使用中',
    owner: '',
    spec: '',
    os: 'CentOS 7.9',
    ssh_username: '',
    ssh_port: 22,
    ssh_key_id: null,
    has_ssh_password: false,
  }

  assert.deepEqual(getAssetCompleteness(complete), { completed: 8, total: 8, percent: 100 })
  assert.deepEqual(getAssetCompleteness(incomplete), { completed: 5, total: 8, percent: 63 })
})

test('labels SSH state from key, password, partial, and missing configuration', () => {
  assert.equal(getAssetSshState({ ssh_key_id: 1, has_ssh_password: false, ssh_username: 'deploy', ssh_port: 22 }).state, 'key')
  assert.equal(getAssetSshState({ ssh_key_id: null, has_ssh_password: true, ssh_username: 'root', ssh_port: 22 }).state, 'password')
  assert.equal(getAssetSshState({ ssh_key_id: null, has_ssh_password: false, ssh_username: 'root', ssh_port: 22 }).state, 'partial')
  assert.equal(getAssetSshState({ ssh_key_id: null, has_ssh_password: false, ssh_username: '', ssh_port: 22 }).state, 'missing')
})

test('sorts assets by missing SSH, low completeness, shutdown status, then name', () => {
  const assets = [
    { id: 1, name: 'healthy', status: '使用中', owner: 'A', spec: '8C', os: 'Ubuntu', ssh_username: 'root', ssh_port: 22, ssh_key_id: 1, has_ssh_password: false },
    { id: 2, name: 'missing-ssh', status: '使用中', owner: 'A', spec: '8C', os: 'Ubuntu', ssh_username: '', ssh_port: 22, ssh_key_id: null, has_ssh_password: false },
    { id: 3, name: 'shutdown', status: '已关机', owner: 'A', spec: '8C', os: 'Ubuntu', ssh_username: 'root', ssh_port: 22, ssh_key_id: 1, has_ssh_password: false },
    { id: 4, name: 'incomplete', status: '使用中', owner: '', spec: '', os: 'Ubuntu', ssh_username: 'root', ssh_port: 22, ssh_key_id: 1, has_ssh_password: false },
  ]

  assert.ok(assetRiskScore(assets[1]) > assetRiskScore(assets[0]))
  assert.deepEqual(sortAssetsByRisk(assets).map((asset) => asset.name), [
    'missing-ssh',
    'incomplete',
    'shutdown',
    'healthy',
  ])
})
