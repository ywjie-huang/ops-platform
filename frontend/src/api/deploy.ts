import request from './request'

// ─── 应用管理 ────────────────────────────────────────────────

export function getDeployApps(params?: { keyword?: string; deploy_method?: string; status?: string; page?: number; page_size?: number }) {
  return request.get('/deploy/apps', { params })
}
export function getDeployApp(id: number) { return request.get(`/deploy/apps/${id}`) }
export function createDeployApp(data: { name: string; display_name?: string; app_type?: string; deploy_method?: string; repo_url?: string; repo_branch?: string; build_script?: string; description?: string }) {
  return request.post('/deploy/apps', data)
}
export function updateDeployApp(id: number, data: any) { return request.put(`/deploy/apps/${id}`, data) }
export function deleteDeployApp(id: number) { return request.delete(`/deploy/apps/${id}`) }

// ─── 应用-环境配置 ───────────────────────────────────────────

export function getAppEnvConfigs(appId: number) { return request.get(`/deploy/apps/${appId}/envs`) }
export function saveAppEnvConfig(appId: number, data: any) { return request.post(`/deploy/apps/${appId}/envs`, data) }
export function deleteAppEnvConfig(appId: number, envId: number) { return request.delete(`/deploy/apps/${appId}/envs/${envId}`) }

// ─── 环境管理 ────────────────────────────────────────────────

export function getDeployEnvs() { return request.get('/deploy/envs') }
export function createDeployEnv(data: { name: string; display_name?: string; description?: string; sort_order?: number }) {
  return request.post('/deploy/envs', data)
}
export function updateDeployEnv(id: number, data: any) { return request.put(`/deploy/envs/${id}`, data) }
export function deleteDeployEnv(id: number) { return request.delete(`/deploy/envs/${id}`) }

// ─── 发布记录 ────────────────────────────────────────────────

export function getDeployRecords(params?: { application_id?: number; environment_id?: number; status?: string; keyword?: string; page?: number; page_size?: number }) {
  return request.get('/deploy/records', { params })
}
export function getDeployRecord(id: number) { return request.get(`/deploy/records/${id}`) }
export function createDeployment(data: { application_id: number; environment_id: number; version?: string; image?: string }) {
  return request.post('/deploy/records', data)
}
export function uploadAndDeploy(data: FormData) {
  return request.post('/deploy/records/upload', data, { headers: { 'Content-Type': 'multipart/form-data' }, timeout: 600000 })
}
export function retryDeployment(id: number) { return request.post(`/deploy/records/${id}/retry`) }
export function rollbackDeployment(id: number) { return request.post(`/deploy/records/${id}/rollback`) }
export function getDeployLogs(id: number, params?: { start?: number }) { return request.get(`/deploy/records/${id}/logs`, { params }) }

// ─── 看板与统计 ──────────────────────────────────────────────

export function getDeployStatus() { return request.get('/deploy/status') }
export function getDeployOverview() { return request.get('/deploy/overview') }
