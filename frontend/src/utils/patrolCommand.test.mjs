import assert from 'node:assert/strict'
import { test } from 'node:test'

const {
  buildPatrolOverview,
  buildRiskObjects,
  getPatrolPriority,
  statusLabel,
  statusTone,
} = await import('./patrolCommand.ts')

const report = {
  status: 'critical',
  total_checks: 8,
  normal_count: 4,
  warning_count: 2,
  critical_count: 2,
}

const items = [
  { category: 'host', target_name: 'web-01', target_ip: '10.0.0.1', check_name: '磁盘使用率', status: 'critical', value: '92%', threshold: '严重 90%', detail: '/data 分区过高' },
  { category: 'host', target_name: 'web-01', target_ip: '10.0.0.1', check_name: 'CPU 使用率', status: 'warning', value: '86%', threshold: '警告 80%', detail: '持续 10 分钟' },
  { category: 'host', target_name: 'db-02', target_ip: '10.0.0.2', check_name: '系统负载', status: 'critical', value: '12.8', threshold: '严重 10', detail: '数据库负载过高' },
  { category: 'k8s', target_name: 'k8s-prod', target_ip: '', check_name: 'Pod 重启', status: 'warning', value: '6 次', threshold: '警告 3 次', detail: 'payment-worker 重启频繁' },
  { category: 'asset', target_name: 'cert-api', target_ip: '', check_name: '证书有效期', status: 'normal', value: '120 天', threshold: '警告 15 天', detail: '证书有效' },
]

test('summarizes patrol report counts and priority state', () => {
  assert.deepEqual(buildPatrolOverview(report), {
    total: 8,
    normal: 4,
    warning: 2,
    critical: 2,
    abnormal: 4,
    healthScore: 55,
    priority: 'P1',
    priorityLabel: '需处置',
    status: 'critical',
  })

  assert.equal(getPatrolPriority(report), 'P1')
  assert.equal(statusLabel('warning'), '警告')
  assert.equal(statusTone('critical'), 'danger')
})

test('groups patrol items into risk objects ordered by severity and category', () => {
  const objects = buildRiskObjects(items)

  assert.deepEqual(objects.map((item) => ({
    key: item.key,
    category: item.category,
    targetName: item.targetName,
    critical: item.critical,
    warning: item.warning,
    status: item.status,
    priority: item.priority,
    headline: item.headline,
  })), [
    {
      key: 'host::web-01',
      category: 'host',
      targetName: 'web-01',
      critical: 1,
      warning: 1,
      status: 'critical',
      priority: 'P1',
      headline: '磁盘使用率 92%',
    },
    {
      key: 'host::db-02',
      category: 'host',
      targetName: 'db-02',
      critical: 1,
      warning: 0,
      status: 'critical',
      priority: 'P1',
      headline: '系统负载 12.8',
    },
    {
      key: 'k8s::k8s-prod',
      category: 'k8s',
      targetName: 'k8s-prod',
      critical: 0,
      warning: 1,
      status: 'warning',
      priority: 'P2',
      headline: 'Pod 重启 6 次',
    },
    {
      key: 'asset::cert-api',
      category: 'asset',
      targetName: 'cert-api',
      critical: 0,
      warning: 0,
      status: 'normal',
      priority: '正常',
      headline: '证书有效期 120 天',
    },
  ])
})
