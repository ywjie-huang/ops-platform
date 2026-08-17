import request from './request'

export interface UserItem {
  id: number
  username: string
  full_name: string
  roles: { id: number; name: string }[]
  created_at: string | null
  last_login_at: string | null
}

export interface UserStats {
  total_users: number
  new_users_7d: number
  today_logins: number
  today_login_failed: number
  active_7d: number
  no_role_count: number
}

export interface RoleItem {
  id: number
  name: string
  code: string
  description: string
}

export interface UserActivityLog {
  id: number
  action: string
  target_type: string
  target_name: string
  detail: string
  ip_address: string
  created_at: string | null
}

export interface UserActivity {
  login_count_30d: number
  login_failed_7d: number
  last_login_at: string | null
  recent_logs: UserActivityLog[]
}

export function getUsers(params?: {
  keyword?: string
  role_id?: number | ''
  activity?: string
  page?: number
  page_size?: number
}) {
  return request.get('/users/', { params })
}
export function getUser(id: number) { return request.get(`/users/${id}`) }
export function getUserStats() { return request.get('/users/stats') }
export function getUserActivity(id: number) { return request.get(`/users/${id}/activity`) }
export function createUser(data: { username: string; full_name: string; password: string; role_ids: number[] }) {
  return request.post('/users/', data)
}
export function updateUser(id: number, data: { username: string; full_name: string; role_ids: number[] }) {
  return request.put(`/users/${id}`, data)
}
export function resetUserPassword(id: number, password: string) {
  return request.put(`/users/${id}/password`, { password })
}
export function deleteUser(id: number) { return request.delete(`/users/${id}`) }
export function getUserRoles() { return request.get('/users/meta/roles') }
