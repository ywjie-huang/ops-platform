export type DockerHostLike = {
  id: number
  name: string
  online?: boolean
  status?: string
  endpoint?: string
  host_ip?: string
  last_heartbeat?: string | null
  metrics?: Record<string, unknown>
  container_total?: number
  container_running?: number
  container_exited?: number
  container_abnormal?: number
}

export type DockerContainerLike = {
  name: string
  image: string
  status: string
  restart_count?: number
  updated_at?: string
}

export type SyncState = 'never' | 'fresh' | 'stale' | 'offline'

const STALE_THRESHOLD_SECONDS = 60

export function secondsSince(timestamp?: string | null, now = new Date()): number | null {
  if (!timestamp) return null
  const parsed = new Date(timestamp)
  if (Number.isNaN(parsed.getTime())) return null
  return Math.max(0, Math.floor((now.getTime() - parsed.getTime()) / 1000))
}

export function getHostSyncState(host: DockerHostLike, now = new Date()): SyncState {
  if (!host.last_heartbeat) return 'never'
  if (host.online === false || host.status === 'stopped') return 'offline'
  const age = secondsSince(host.last_heartbeat, now)
  if (age == null) return 'never'
  return age > STALE_THRESHOLD_SECONDS ? 'stale' : 'fresh'
}

export function hostRiskScore(host: DockerHostLike, now = new Date()): number {
  const syncState = getHostSyncState(host, now)
  const abnormal = host.container_abnormal ?? 0
  if (syncState === 'offline' || syncState === 'never') return 400 + abnormal
  if (syncState === 'stale') return 300 + abnormal
  if (abnormal > 0) return 200 + abnormal
  return 0
}

export function sortHostsByRisk<T extends DockerHostLike>(hosts: T[], now = new Date()): T[] {
  return [...hosts].sort((a, b) => {
    const riskDiff = hostRiskScore(b, now) - hostRiskScore(a, now)
    if (riskDiff !== 0) return riskDiff
    return a.name.localeCompare(b.name, 'zh-CN')
  })
}

export function isAbnormalContainer(container: DockerContainerLike): boolean {
  return ['exited', 'dead', 'restarting', 'removing'].includes(container.status)
}

export function summarizeContainers(containers: DockerContainerLike[]) {
  const running = containers.filter((item) => item.status === 'running').length
  const exited = containers.filter((item) => item.status === 'exited').length
  const abnormal = containers.filter(isAbnormalContainer).length
  return {
    total: containers.length,
    running,
    exited,
    abnormal,
    restartRisk: containers.filter((item) => (item.restart_count ?? 0) > 3).length,
  }
}

export function sortContainersByRisk<T extends DockerContainerLike>(containers: T[]): T[] {
  return [...containers].sort((a, b) => {
    const abnormalDiff = Number(isAbnormalContainer(b)) - Number(isAbnormalContainer(a))
    if (abnormalDiff !== 0) return abnormalDiff
    const restartDiff = (b.restart_count ?? 0) - (a.restart_count ?? 0)
    if (restartDiff !== 0) return restartDiff
    return a.name.localeCompare(b.name, 'zh-CN')
  })
}
