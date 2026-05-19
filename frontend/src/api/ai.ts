import request from './request'

// 发送消息给 AI
export function sendAiMessage(data: { message: string; conversation_id?: string }) {
  return request.post('/ai/chat', data)
}

// 获取对话历史
export function getAiHistory(conversation_id: string) {
  return request.get(`/ai/history/${conversation_id}`)
}
