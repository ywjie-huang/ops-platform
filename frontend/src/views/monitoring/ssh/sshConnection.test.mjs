import assert from 'node:assert/strict'
import { test } from 'node:test'

const {
  buildAuthPayload,
  getInitialLoginState,
} = await import('./sshConnection.ts')

test('prefers saved asset password over unrelated default key for initial login mode', () => {
  const asset = {
    ssh_username: 'ops',
    ssh_port: 2222,
    ssh_key_id: null,
    has_ssh_password: true,
  }
  const sshKeys = [
    { id: 9, username: 'deploy', port: 22, is_default: true, auth_type: 'key' },
  ]

  assert.deepEqual(getInitialLoginState(asset, sshKeys), {
    authMode: 'asset',
    username: 'ops',
    port: 2222,
  })
})

test('uses asset key when asset already binds a specific ssh key', () => {
  const asset = {
    ssh_username: 'ops',
    ssh_port: 22,
    ssh_key_id: 5,
    has_ssh_password: false,
  }
  const sshKeys = [
    { id: 5, username: 'deploy', port: 2200, is_default: false, auth_type: 'key' },
    { id: 9, username: 'other', port: 22, is_default: true, auth_type: 'key' },
  ]

  assert.deepEqual(getInitialLoginState(asset, sshKeys), {
    authMode: 'key-5',
    username: 'deploy',
    port: 2200,
  })
})

test('omits empty password when using asset credential so backend can fall back to stored password', () => {
  assert.deepEqual(buildAuthPayload({
    username: 'root',
    port: 22,
    authMode: 'asset',
    password: '',
  }), {
    username: 'root',
    port: 22,
  })
})

test('includes key id when login mode is ssh key', () => {
  assert.deepEqual(buildAuthPayload({
    username: 'deploy',
    port: 2200,
    authMode: 'key-3',
    password: '',
  }), {
    username: 'deploy',
    port: 2200,
    key_id: 3,
  })
})

test('includes key id for empty-password key auth payload', () => {
  assert.deepEqual(buildAuthPayload({
    username: 'ops',
    password: '',
    port: 22,
    authMode: 'key-8',
  }), {
    username: 'ops',
    port: 22,
    key_id: 8,
  })
})
