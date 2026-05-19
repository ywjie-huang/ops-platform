import request from './request'

export function getSSHKeys(params?: { keyword?: string; page?: number; page_size?: number }) {
  return request.get('/ssh-keys/', { params })
}

export function getSSHKey(id: number) {
  return request.get(`/ssh-keys/${id}`)
}

export function createSSHKey(data: any) {
  return request.post('/ssh-keys/', data)
}

export function updateSSHKey(id: number, data: any) {
  return request.put(`/ssh-keys/${id}`, data)
}

export function deleteSSHKey(id: number) {
  return request.delete(`/ssh-keys/${id}`)
}
