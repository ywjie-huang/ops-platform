import assert from 'node:assert/strict'
import { test } from 'node:test'

const {
  buildAssetPayload,
  createAssetForm,
  createAssetFormFromAsset,
  isValidIpAddress,
} = await import('./assetForm.ts')

test('creates a stable default asset form for drawer resets', () => {
  assert.deepEqual(createAssetForm(), {
    name: '',
    asset_type: '云主机',
    ip_address: '',
    status: '使用中',
    owner: '',
    description: '',
    spec: '',
    os: '',
    ssh_port: 22,
    ssh_username: 'root',
    ssh_password: '',
    auth_method: 'password',
    ssh_key_id: null,
  })
})

test('creates an edit form from saved asset data and keeps passwords blank', () => {
  assert.deepEqual(createAssetFormFromAsset({
    name: 'k8s-master-2',
    asset_type: '云主机',
    ip_address: '172.16.24.32',
    status: '使用中',
    owner: 'admin',
    description: 'control plane',
    spec: '4C8G',
    os: 'Ubuntu 22.04',
    ssh_port: 2200,
    ssh_username: 'deploy',
    ssh_key_id: 9,
  }), {
    name: 'k8s-master-2',
    asset_type: '云主机',
    ip_address: '172.16.24.32',
    status: '使用中',
    owner: 'admin',
    description: 'control plane',
    spec: '4C8G',
    os: 'Ubuntu 22.04',
    ssh_port: 2200,
    ssh_username: 'deploy',
    ssh_password: '',
    auth_method: 'key',
    ssh_key_id: 9,
  })
})

test('validates IPv4 addresses without accepting malformed octets', () => {
  assert.equal(isValidIpAddress('172.16.24.32'), true)
  assert.equal(isValidIpAddress(' 10.0.0.1 '), true)
  assert.equal(isValidIpAddress('256.0.0.1'), false)
  assert.equal(isValidIpAddress('172.16.24'), false)
  assert.equal(isValidIpAddress('172.16.24.x'), false)
})

test('builds submit payloads for password and key authentication', () => {
  assert.deepEqual(buildAssetPayload({
    ...createAssetForm(),
    ssh_password: 'secret',
    ssh_key_id: 3,
  }), {
    name: '',
    asset_type: '云主机',
    ip_address: '',
    status: '使用中',
    owner: '',
    description: '',
    spec: '',
    os: '',
    ssh_port: 22,
    ssh_username: 'root',
    ssh_password: 'secret',
    ssh_key_id: null,
  })

  assert.deepEqual(buildAssetPayload({
    ...createAssetForm(),
    auth_method: 'key',
    ssh_password: 'secret',
    ssh_key_id: 3,
  }).ssh_password, '')
})
