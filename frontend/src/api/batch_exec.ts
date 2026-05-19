import request from './request'

// 执行历史
export function getExecHistory(params?: { keyword?: string; status?: string; page?: number; page_size?: number }) {
  return request.get('/batch-exec/history', { params })
}
export function deleteExecHistory(id: number) {
  return request.delete(`/batch-exec/history/${id}`)
}
