import request from './request'

export interface HostListItem {
  id: number
  name: string
  ip_address: string
  owner: string
  status: string
  cpu: number
  cpu_cores?: number
  memory: number
  memory_total_bytes?: number
  memory_available_bytes?: number
  disk: number
  disk_total_bytes?: number
  disk_available_bytes?: number
  network_in: number
  network_out: number
  load: number
  prometheus_ok: boolean
}

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
  disk?: { usage: number; total_gb: number; used_gb?: number; available_gb?: number; read_mb_s: number; write_mb_s: number }
  network?: { in_mbps: number; out_mbps: number }
  load?: { '1m': number; '5m': number; '15m': number }
  processes?: { running: number }
}

export interface HostTrendPoint {
  timestamp: number
  value: number
}

export interface HostTrendSeries {
  key: string
  label: string
  unit: string
  points: HostTrendPoint[]
}

export interface HostTrendData {
  range_minutes: number
  step_seconds: number
  series: HostTrendSeries[]
}

export function getHosts() { return request.get('/monitoring/hosts') }
export function getHostDetail(id: number) { return request.get(`/monitoring/hosts/${id}`) }
export function getPrometheusHealth() { return request.get('/monitoring/prometheus/health') }
export function getHostTrends(id: number, params = { minutes: 60, step_seconds: 60 }) {
  return request.get(`/monitoring/hosts/${id}/trends`, { params })
}
