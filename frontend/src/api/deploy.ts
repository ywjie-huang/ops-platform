import request from './request'

// ── 应用管理 ──
export function getDeployApps(params?: {
  keyword?: string
  app_type?: string
  deploy_strategy?: string
  status?: string
  page?: number
  page_size?: number
}) {
  return request.get('/deploy/apps', { params })
}

export function getDeployApp(id: number) {
  return request.get(`/deploy/apps/${id}`)
}

export function createDeployApp(data: any) {
  return request.post('/deploy/apps', data)
}

export function updateDeployApp(id: number, data: any) {
  return request.put(`/deploy/apps/${id}`, data)
}

export function deleteDeployApp(id: number) {
  return request.delete(`/deploy/apps/${id}`)
}

// ── 环境列表 ──
export function getDeployEnvs() {
  return request.get('/deploy/envs')
}

// ── 应用环境配置 ──
export function getAppEnvs(appId: number) {
  return request.get(`/deploy/apps/${appId}/envs`)
}

export function updateAppEnv(appId: number, envId: number, data: any) {
  return request.put(`/deploy/apps/${appId}/envs/${envId}`, data)
}

export function deleteAppEnv(appId: number, envId: number) {
  return request.delete(`/deploy/apps/${appId}/envs/${envId}`)
}

// ── 部署执行 ──
export function executeDeploy(data: { app_id: number; env_id: number; version?: string }) {
  return request.post('/deploy/execute', data)
}

export function cancelDeploy(recordId: number) {
  return request.post(`/deploy/records/${recordId}/cancel`)
}

export function getDeployRecords(params?: {
  app_id?: number
  env_id?: number
  status?: string
  page?: number
  page_size?: number
}) {
  return request.get('/deploy/records', { params })
}

export function getDeployRecord(id: number) {
  return request.get(`/deploy/records/${id}`)
}
