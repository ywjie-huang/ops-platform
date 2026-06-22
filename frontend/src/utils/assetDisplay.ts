export type AssetLike = {
  id?: number
  name?: string
  asset_type?: string
  ip_address?: string
  status?: string
  owner?: string
  description?: string
  spec?: string
  os?: string
  ssh_port?: number | null
  ssh_username?: string | null
  has_ssh_password?: boolean
  ssh_key_id?: number | null
  created_at?: string
}

export type AssetSshState = 'key' | 'password' | 'partial' | 'missing'

function hasText(value?: string | null): boolean {
  return Boolean(value && value.trim())
}

export function getAssetCompleteness(asset: AssetLike) {
  const checks = [
    hasText(asset.name),
    hasText(asset.ip_address),
    hasText(asset.asset_type),
    hasText(asset.status),
    hasText(asset.owner),
    hasText(asset.spec),
    hasText(asset.os),
    getAssetSshState(asset).state !== 'missing',
  ]
  const completed = checks.filter(Boolean).length
  return {
    completed,
    total: checks.length,
    percent: Math.round((completed / checks.length) * 100),
  }
}

export function getAssetSshState(asset: AssetLike): { state: AssetSshState; label: string; tone: 'success' | 'warning' | 'danger' } {
  if (asset.ssh_key_id) return { state: 'key', label: '密钥认证', tone: 'success' }
  if (asset.has_ssh_password) return { state: 'password', label: '密码认证', tone: 'success' }
  if (hasText(asset.ssh_username)) return { state: 'partial', label: '仅用户名', tone: 'warning' }
  return { state: 'missing', label: '未配置', tone: 'danger' }
}

export function getCompletenessTone(percent: number): 'success' | 'warning' | 'danger' {
  if (percent >= 90) return 'success'
  if (percent >= 65) return 'warning'
  return 'danger'
}

export function isAttentionAsset(asset: AssetLike): boolean {
  return asset.status === '已关机' || getAssetCompleteness(asset).percent < 90 || getAssetSshState(asset).state !== 'key' && getAssetSshState(asset).state !== 'password'
}

export function assetRiskScore(asset: AssetLike): number {
  const completeness = getAssetCompleteness(asset).percent
  const sshState = getAssetSshState(asset).state
  let score = 0
  if (sshState === 'missing') score += 400
  if (sshState === 'partial') score += 260
  if (completeness < 65) score += 220
  else if (completeness < 90) score += 140
  if (asset.status === '已关机') score += 80
  if (asset.status === '已删除') score += 40
  return score
}

export function sortAssetsByRisk<T extends AssetLike>(assets: T[]): T[] {
  return [...assets].sort((a, b) => {
    const riskDiff = assetRiskScore(b) - assetRiskScore(a)
    if (riskDiff !== 0) return riskDiff
    return (a.name || '').localeCompare(b.name || '', 'zh-CN')
  })
}

export function formatAssetDate(dateStr?: string): string {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  if (Number.isNaN(date.getTime())) return '-'
  return date.toLocaleDateString('zh-CN')
}
