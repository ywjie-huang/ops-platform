import request from './request'

export function getTickets(params?: { keyword?: string; status?: string; priority?: string }) {
  return request.get('/tickets/', { params })
}
export function getTicket(id: number) { return request.get(`/tickets/${id}`) }
export function createTicket(data: any) { return request.post('/tickets/', data) }
export function updateTicket(id: number, data: any) { return request.put(`/tickets/${id}`, data) }
export function deleteTicket(id: number) { return request.delete(`/tickets/${id}`) }
