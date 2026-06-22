import assert from 'node:assert/strict'
import { test } from 'node:test'

const {
  getHostSyncState,
  sortHostsByRisk,
  summarizeContainers,
  sortContainersByRisk,
} = await import('./dockerMonitor.ts')

test('marks stale Docker hosts when heartbeat is older than 60 seconds', () => {
  const now = new Date('2026-06-22T10:02:00+08:00')
  const host = {
    id: 1,
    name: 'docker-prod-01',
    online: true,
    last_heartbeat: '2026-06-22T10:00:30+08:00',
  }

  assert.equal(getHostSyncState(host, now), 'stale')
})

test('sorts hosts by offline, stale, abnormal, then healthy risk', () => {
  const now = new Date('2026-06-22T10:02:00+08:00')
  const hosts = [
    { id: 1, name: 'healthy', online: true, last_heartbeat: '2026-06-22T10:01:55+08:00', container_abnormal: 0 },
    { id: 2, name: 'abnormal', online: true, last_heartbeat: '2026-06-22T10:01:55+08:00', container_abnormal: 3 },
    { id: 3, name: 'offline', online: false, last_heartbeat: '2026-06-22T09:59:00+08:00', container_abnormal: 0 },
    { id: 4, name: 'stale', online: true, last_heartbeat: '2026-06-22T10:00:00+08:00', container_abnormal: 0 },
  ]

  assert.deepEqual(sortHostsByRisk(hosts, now).map((host) => host.name), [
    'offline',
    'stale',
    'abnormal',
    'healthy',
  ])
})

test('summarizes and sorts containers with abnormal statuses first', () => {
  const containers = [
    { name: 'nginx', image: 'nginx', status: 'running', restart_count: 0 },
    { name: 'api', image: 'app', status: 'restarting', restart_count: 12 },
    { name: 'worker', image: 'worker', status: 'exited', restart_count: 4 },
  ]

  assert.deepEqual(summarizeContainers(containers), {
    total: 3,
    running: 1,
    exited: 1,
    abnormal: 2,
    restartRisk: 2,
  })
  assert.deepEqual(sortContainersByRisk(containers).map((item) => item.name), ['api', 'worker', 'nginx'])
})
