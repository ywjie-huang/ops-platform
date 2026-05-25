import request from './request'

export interface ScheduledTask {
  id: number
  name: string
  task_type: string
  cron_expr: string
  params: Record<string, any> | null
  enabled: boolean
  description: string
  last_run_at: string | null
  last_status: string
  created_at: string | null
}

export interface TaskExecutionLog {
  id: number
  task_id: number
  started_at: string | null
  finished_at: string | null
  status: string
  result: string
  error: string
}

export function getSchedulerTasks(params?: { page?: number; page_size?: number }) {
  return request.get('/scheduler/tasks', { params })
}

export function getTaskTypes() {
  return request.get('/scheduler/task-types')
}

export function createSchedulerTask(data: {
  name: string
  task_type: string
  cron_expr: string
  params?: Record<string, any> | null
  description?: string
}) {
  return request.post('/scheduler/tasks', data)
}

export function updateSchedulerTask(id: number, data: {
  name?: string
  task_type?: string
  cron_expr?: string
  params?: Record<string, any> | null
  description?: string
  enabled?: boolean
}) {
  return request.put(`/scheduler/tasks/${id}`, data)
}

export function deleteSchedulerTask(id: number) {
  return request.delete(`/scheduler/tasks/${id}`)
}

export function toggleSchedulerTask(id: number) {
  return request.post(`/scheduler/tasks/${id}/toggle`)
}

export function runSchedulerTaskNow(id: number) {
  return request.post(`/scheduler/tasks/${id}/run`)
}

export function getTaskExecutionLogs(taskId: number, params?: { page?: number; page_size?: number }) {
  return request.get(`/scheduler/tasks/${taskId}/logs`, { params })
}
