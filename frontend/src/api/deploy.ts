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

export function getDeployApp(name: string) {
  return request.get(`/deploy/apps/${name}`)
}

export function createDeployApp(data: any) {
  return request.post('/deploy/apps', data)
}

export function updateDeployApp(name: string, data: any) {
  return request.put(`/deploy/apps/${name}`, data)
}

export function deleteDeployApp(name: string) {
  return request.delete(`/deploy/apps/${name}`)
}

// ── 构建产物（环境级别） ──
export function uploadArtifact(appName: string, envId: number, file: File) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post(`/deploy/apps/${appName}/envs/${envId}/artifact`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function deleteArtifact(appName: string, envId: number) {
  return request.delete(`/deploy/apps/${appName}/envs/${envId}/artifact`)
}

// ── 环境列表 ──
export function getDeployEnvs() {
  return request.get('/deploy/envs')
}

// ── 应用环境配置 ──
export function getAppEnvs(appName: string) {
  return request.get(`/deploy/apps/${appName}/envs`)
}

export function updateAppEnv(appName: string, envId: number, data: any) {
  return request.put(`/deploy/apps/${appName}/envs/${envId}`, data)
}

export function deleteAppEnv(appName: string, envId: number) {
  return request.delete(`/deploy/apps/${appName}/envs/${envId}`)
}

// ── 部署执行 ──
export function executeDeploy(data: { app_name: string; env_id: number; version?: string }) {
  return request.post('/deploy/execute', data)
}

export function cancelDeploy(recordId: number) {
  return request.post(`/deploy/records/${recordId}/cancel`)
}

export function getDeployRecords(params?: {
  app_name?: string
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

export function rollbackDeploy(recordId: number) {
  return request.post(`/deploy/records/${recordId}/rollback`)
}

// ── 审批 ──
export function getDeployApprovals(params?: { status?: string }) {
  return request.get('/deploy/approvals', { params })
}

export function approveDeploy(approvalId: number) {
  return request.post(`/deploy/approvals/${approvalId}/approve`)
}

export function rejectDeploy(approvalId: number, comment?: string) {
  return request.post(`/deploy/approvals/${approvalId}/reject`, { comment })
}

// ── 配置管理 ──
export function getAppConfigs(appName: string, envId?: number) {
  return request.get(`/deploy/apps/${appName}/configs`, { params: envId ? { env_id: envId } : {} })
}

export function createAppConfig(appName: string, data: any) {
  return request.post(`/deploy/apps/${appName}/configs`, data)
}

export function updateAppConfig(configId: number, data: any) {
  return request.put(`/deploy/configs/${configId}`, data)
}

export function deleteAppConfig(configId: number) {
  return request.delete(`/deploy/configs/${configId}`)
}
