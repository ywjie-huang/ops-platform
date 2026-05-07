import request from './request'

export function getUsers(params?: { keyword?: string; role_id?: number }) {
  return request.get('/users/', { params })
}
export function getUser(id: number) { return request.get(`/users/${id}`) }
export function createUser(data: any) { return request.post('/users/', data) }
export function updateUser(id: number, data: any) { return request.put(`/users/${id}`, data) }
export function deleteUser(id: number) { return request.delete(`/users/${id}`) }
export function getUserRoles() { return request.get('/users/meta/roles') }
