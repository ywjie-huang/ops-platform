/**
 * AI 助手 API — SSE 流式对话 + 对话管理
 */
import { getToken } from '@/utils/auth'

const BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1'

export interface SSEEvent {
  type: 'text' | 'tool_start' | 'tool_result' | 'tool_confirm' | 'error' | 'done'
  content?: string
  tool?: string
  args?: Record<string, unknown>
  result?: string
  pending_id?: string
  description?: string
  conversation_id?: number
}

export interface AiInfo {
  model: string
  configured: boolean
}

export interface Conversation {
  id: number
  title: string
  created_at: string
  updated_at: string
}

export interface ChatMessage {
  id: number
  role: 'user' | 'assistant' | 'tool'
  content: string | null
  tool_calls: Array<{
    id: string
    type: string
    function: { name: string; arguments: string }
  }> | null
  tool_call_id: string | null
  tool_name: string | null
  created_at: string
}

function authHeaders(): Record<string, string> {
  const token = getToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export async function getAiInfo(): Promise<AiInfo> {
  const resp = await fetch(`${BASE}/ai/info`, { headers: authHeaders() })
  const data = await resp.json()
  return data.data
}

export async function getConversations(): Promise<Conversation[]> {
  const resp = await fetch(`${BASE}/ai/conversations`, { headers: authHeaders() })
  const data = await resp.json()
  return data.data
}

export async function getMessages(conversationId: number): Promise<ChatMessage[]> {
  const resp = await fetch(`${BASE}/ai/conversations/${conversationId}/messages`, {
    headers: authHeaders(),
  })
  const data = await resp.json()
  return data.data
}

export async function deleteConversation(conversationId: number): Promise<void> {
  await fetch(`${BASE}/ai/conversations/${conversationId}`, {
    method: 'DELETE',
    headers: authHeaders(),
  })
}

export async function* sendAiMessageStream(
  message: string,
  conversation_id?: number,
): AsyncGenerator<SSEEvent> {
  const resp = await fetch(`${BASE}/ai/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ message, conversation_id }),
  })
  if (!resp.ok) throw new Error(`请求失败: ${resp.status}`)
  yield* _readSSEStream(resp)
}

export async function* confirmAiActionStream(
  pending_id: string,
  conversation_id: number,
): AsyncGenerator<SSEEvent> {
  const resp = await fetch(`${BASE}/ai/chat/confirm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ pending_id, conversation_id }),
  })
  if (!resp.ok) throw new Error(`请求失败: ${resp.status}`)
  yield* _readSSEStream(resp)
}

export async function* rejectAiActionStream(
  pending_id: string,
  conversation_id: number,
): AsyncGenerator<SSEEvent> {
  const resp = await fetch(`${BASE}/ai/chat/reject`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ pending_id, conversation_id }),
  })
  if (!resp.ok) throw new Error(`请求失败: ${resp.status}`)
  yield* _readSSEStream(resp)
}

async function* _readSSEStream(resp: Response): AsyncGenerator<SSEEvent> {
  const reader = resp.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try { yield JSON.parse(line.slice(6)) as SSEEvent } catch { /* ignore */ }
      }
    }
  }
  if (buffer.startsWith('data: ')) {
    try { yield JSON.parse(buffer.slice(6)) as SSEEvent } catch { /* ignore */ }
  }
}
