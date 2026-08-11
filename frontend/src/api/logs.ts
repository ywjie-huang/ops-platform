/**
 * 日志检索 API — Elasticsearch 数据源
 */
import request from './request'

export interface LogSearchParams {
  keyword?: string
  namespace?: string
  pod?: string
  container?: string
  host?: string
  level?: string
  start?: string
  end?: string
  size?: number
  offset?: number
}

export interface LogItem {
  id: string
  index: string
  timestamp: string
  message: string
  namespace: string | null
  pod: string | null
  container: string | null
  host: string | null
  level: string | null
}

export interface LogSearchResult {
  total: number
  items: LogItem[]
}

export interface LogHistogramBucket {
  key: string
  count: number
}

export interface LogHistogram {
  interval: string
  buckets: LogHistogramBucket[]
}

export interface LogFilterOptions {
  namespaces: string[]
  hosts: string[]
  levels: string[]
}

export function searchLogs(params: LogSearchParams) {
  return request.get<unknown, { code: number; msg?: string; data: LogSearchResult }>(
    '/logs/search', { params, timeout: 20000 },
  )
}

export function getLogHistogram(params: LogSearchParams) {
  return request.get<unknown, { code: number; msg?: string; data: LogHistogram }>(
    '/logs/histogram', { params, timeout: 20000 },
  )
}

export function getLogFilterOptions(params?: { start?: string; end?: string }) {
  return request.get<unknown, { code: number; msg?: string; data: LogFilterOptions }>(
    '/logs/filter-options', { params, timeout: 20000 },
  )
}
