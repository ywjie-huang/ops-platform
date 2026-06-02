import request from './request'

export function getAlertManagerStatus() { return request.get('/alertmanager/status') }
export function getAlertManagerAlerts() { return request.get('/alertmanager/alerts') }
export function getAlertManagerRules() { return request.get('/alertmanager/rules') }
export function getAlertManagerRulesHosts() { return request.get('/alertmanager/rules/hosts') }
export function getAlertManagerEvents(params?: { keyword?: string; severity?: string; status?: string; page?: number; page_size?: number }) { return request.get('/alertmanager/events', { params }) }
