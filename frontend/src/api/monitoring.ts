import request from './request'

export function getHosts() { return request.get('/monitoring/hosts') }
export function getHostDetail(id: number) { return request.get(`/monitoring/hosts/${id}`) }
