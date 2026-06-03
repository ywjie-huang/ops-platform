import request from './request'

export interface HostDetail {
  id: number
  hostname: string
  ip: string
  spec?: string
  os_info?: string
  owner?: string
  status: string
  uptime_hours: number
  prometheus_ok: boolean
  tcp_connections?: number
  cpu?: { usage: number; cores: number }
  memory?: { usage: number; total_gb: number; used_gb: number; available_gb: number }
  disk?: { usage: number; total_gb: number; read_mb_s: number; write_mb_s: number }
  network?: { in_mbps: number; out_mbps: number }
  load?: { '1m': number; '5m': number; '15m': number }
  processes?: { running: number }
}

export function getHosts() { return request.get('/monitoring/hosts') }
export function getHostDetail(id: number) { return request.get(`/monitoring/hosts/${id}`) }
