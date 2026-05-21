import request from './request'

export function getAssets(params?: { keyword?: string; asset_type?: string; status?: string; page?: number; page_size?: number }) {
  return request.get('/assets/', { params })
}

export function getAsset(id: number) {
  return request.get(`/assets/${id}`)
}

export function createAsset(data: any) {
  return request.post('/assets/', data)
}

export function updateAsset(id: number, data: any) {
  return request.put(`/assets/${id}`, data)
}

export function deleteAsset(id: number) {
  return request.delete(`/assets/${id}`)
}

export function getAssetStats() {
  return request.get('/assets/stats')
}
