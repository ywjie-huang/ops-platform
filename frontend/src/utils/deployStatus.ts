/**
 * 部署状态统一映射 — 模式 B 状态机。
 * 各页面（总览/列表/详情/记录/审批）共用，避免多处复制漂移。
 */

export type DeployStatus =
  | 'pending' | 'triggering' | 'building' | 'deploying'
  | 'success' | 'failed' | 'cancelled'

const STATUS_META: Record<string, { label: string; type: 'info' | 'warning' | 'success' | 'danger' | 'primary' }> = {
  pending:    { label: '待审批',        type: 'info' },
  triggering: { label: 'Jenkins 执行中', type: 'primary' },
  building:   { label: '构建中',        type: 'warning' },  // 旧记录兼容
  deploying:  { label: '部署中',        type: 'warning' },  // 旧记录兼容
  success:    { label: '成功',          type: 'success' },
  failed:     { label: '失败',          type: 'danger' },
  cancelled:  { label: '已取消',        type: 'info' },
}

export function deployStatusLabel(v: string): string {
  return STATUS_META[v]?.label || v
}

export function deployStatusType(v: string): 'info' | 'warning' | 'success' | 'danger' | 'primary' {
  return STATUS_META[v]?.type || 'info'
}

/** 进行中状态（需要轮询/自动刷新） */
export const ACTIVE_STATUSES = ['pending', 'triggering', 'building', 'deploying']

export function isActiveStatus(v: string): boolean {
  return ACTIVE_STATUSES.includes(v)
}

/** 终态（可回滚） */
export function isFinalStatus(v: string): boolean {
  return ['success', 'failed', 'cancelled'].includes(v)
}

/** 矩阵/列表的关注度排序权重：进行中 > 失败 > 待审批 > 成功 > 其他 */
export function statusSeverity(v: string | null | undefined): number {
  if (!v) return 0
  if (v === 'triggering' || v === 'building' || v === 'deploying') return 4
  if (v === 'failed') return 3
  if (v === 'pending') return 2
  if (v === 'success') return 1
  return 0
}

export function triggerTypeLabel(v: string): string {
  return ({ manual: '手动', rollback: '回滚', webhook: 'Webhook' } as Record<string, string>)[v] || v
}

/** 部署耗时格式化：63.2 → "1m 3s" */
export function formatDeployDuration(sec: number | null | undefined): string {
  if (sec == null) return '—'
  if (sec < 60) return `${Math.round(sec)}s`
  const m = Math.floor(sec / 60)
  const s = Math.round(sec % 60)
  return `${m}m ${s}s`
}

/** 环境标识色：dev 蓝 / staging 琥珀 / prod 红，其余取中性色 */
export function envColor(envName: string | null | undefined): string {
  const n = (envName || '').toLowerCase()
  if (/prod|生产/.test(n)) return '#e5484d'
  if (/stag|预发|test|测试|uat/.test(n)) return '#f5a623'
  if (/dev|开发/.test(n)) return '#5e6ad2'
  return '#8b8b9e'
}
