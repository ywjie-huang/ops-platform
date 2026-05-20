import request from './request'

export function getPresets() {
  return request.get('/batch-exec/presets/')
}

export function createPreset(data: { name: string; command: string; description?: string; sort_order?: number }) {
  return request.post('/batch-exec/presets/', data)
}

export function updatePreset(id: number, data: { name?: string; command?: string; description?: string; sort_order?: number }) {
  return request.put(`/batch-exec/presets/${id}`, data)
}

export function deletePreset(id: number) {
  return request.delete(`/batch-exec/presets/${id}`)
}
