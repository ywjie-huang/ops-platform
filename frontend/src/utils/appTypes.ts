export interface AppTypeOption {
  label: string
  value: string
  desc: string
}

export const APP_TYPES: AppTypeOption[] = [
  { label: 'Web 应用', value: 'web', desc: '有 HTTP 入口的 Web 服务' },
  { label: 'API 服务', value: 'api', desc: '对外提供接口的后端服务' },
  { label: '后台任务', value: 'worker', desc: '无入口的常驻任务 / 定时作业' },
  { label: '前端项目', value: 'frontend', desc: '静态资源构建与发布' },
  { label: '其他', value: 'other', desc: '不在以上分类内的应用' },
]

export function appTypeLabel(v: string): string {
  return APP_TYPES.find(t => t.value === v)?.label || v
}
