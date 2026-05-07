import request from './request'

export function getRoles(params?: { keyword?: string; system_only?: boolean }) {
  return request.get('/roles/', { params })
}
export function getRole(id: number) { return request.get(`/roles/${id}`) }
export function createRole(data: any) { return request.post('/roles/', data) }
export function updateRole(id: number, data: any) { return request.put(`/roles/${id}`, data) }
export function deleteRole(id: number) { return request.delete(`/roles/${id}`) }
export function assignPermissions(id: number, permission_ids: number[]) {
  return request.put(`/roles/${id}/permissions`, { permission_ids })
}
export function getPermissionTree() { return request.get('/roles/meta/permission-tree') }
