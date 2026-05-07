import request from './request'

export function getAlerts(params?: { keyword?: string; status?: string; level?: string }) {
  return request.get('/alerts/', { params })
}
export function getAlert(id: number) { return request.get(`/alerts/${id}`) }
export function createAlert(data: any) { return request.post('/alerts/', data) }
export function updateAlert(id: number, data: any) { return request.put(`/alerts/${id}`, data) }
export function deleteAlert(id: number) { return request.delete(`/alerts/${id}`) }
