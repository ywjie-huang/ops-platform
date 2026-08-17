import request from './request'

export interface RoleItem {
  id: number
  name: string
  code: string
  description: string
  is_system: boolean
  permissions: { id: number; name: string; code: string; module: string }[]
  user_count: number
  created_at: string | null
}

export interface RoleStats {
  total_roles: number
  system_roles: number
  custom_roles: number
  assigned_users: number
  total_users: number
  perm_total: number
  perm_modules: number
  no_perm_roles: number
}

export interface PermItem {
  id: number
  name: string
  code: string
  module: string
  description?: string
}

export interface PermGroup {
  parent: string
  children: { module: string; label: string; permissions: PermItem[] }[]
}

export function getRoles(params?: {
  keyword?: string
  type?: string
  no_perm?: boolean
  page?: number
  page_size?: number
}) {
  return request.get('/roles/', { params })
}
export function getRole(id: number) { return request.get(`/roles/${id}`) }
export function getRoleStats() { return request.get('/roles/stats') }
export function createRole(data: { name: string; code: string; description: string }) {
  return request.post('/roles/', data)
}
export function updateRole(id: number, data: { name: string; code: string; description: string }) {
  return request.put(`/roles/${id}`, data)
}
export function deleteRole(id: number) { return request.delete(`/roles/${id}`) }
export function assignPermissions(id: number, permission_ids: number[]) {
  return request.put(`/roles/${id}/permissions`, { permission_ids })
}
export function getPermissionTree() { return request.get('/roles/meta/permission-tree') }
