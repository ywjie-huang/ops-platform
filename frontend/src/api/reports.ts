import request from './request'

export function getPresetReports() { return request.get('/reports/presets') }
export function getPresetDetail(id: string) { return request.get(`/reports/presets/${id}`) }
export function getDataSources() { return request.get('/reports/data-sources') }
export function getDimensions() { return request.get('/reports/dimensions') }
export function queryCustomReport(data: any) { return request.post('/reports/custom', data) }
