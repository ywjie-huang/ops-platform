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
