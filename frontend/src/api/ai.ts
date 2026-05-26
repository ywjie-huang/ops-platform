/**
 * AI 助手 API — SSE 流式对话 + 工具确认
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
  conversation_id?: string
}

export interface AiInfo {
  model: string
  configured: boolean
}

function authHeaders(): Record<string, string> {
  const token = getToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

/**
 * 获取 AI 模型信息。
 */
export async function getAiInfo(): Promise<AiInfo> {
  const resp = await fetch(`${BASE}/ai/info`, {
    headers: authHeaders(),
  })
  const data = await resp.json()
  return data.data
}

/**
 * 发送消息，返回 SSE 事件流。
 */
export async function* sendAiMessageStream(
  message: string,
  conversation_id?: string,
): AsyncGenerator<SSEEvent> {
  const resp = await fetch(`${BASE}/ai/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders(),
    },
    body: JSON.stringify({ message, conversation_id }),
  })

  if (!resp.ok) {
    throw new Error(`请求失败: ${resp.status}`)
  }

  yield* _readSSEStream(resp)
}

/**
 * 确认执行写操作，返回 SSE 事件流。
 */
export async function* confirmAiActionStream(
  pending_id: string,
  conversation_id: string,
): AsyncGenerator<SSEEvent> {
  const resp = await fetch(`${BASE}/ai/chat/confirm`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders(),
    },
    body: JSON.stringify({ pending_id, conversation_id }),
  })

  if (!resp.ok) {
    throw new Error(`请求失败: ${resp.status}`)
  }

  yield* _readSSEStream(resp)
}

/**
 * 拒绝写操作，返回 SSE 事件流。
 */
export async function* rejectAiActionStream(
  pending_id: string,
  conversation_id: string,
): AsyncGenerator<SSEEvent> {
  const resp = await fetch(`${BASE}/ai/chat/reject`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders(),
    },
    body: JSON.stringify({ pending_id, conversation_id }),
  })

  if (!resp.ok) {
    throw new Error(`请求失败: ${resp.status}`)
  }

  yield* _readSSEStream(resp)
}

/**
 * 通用 SSE 流读取器。
 */
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
        try {
          yield JSON.parse(line.slice(6)) as SSEEvent
        } catch { /* ignore malformed */ }
      }
    }
  }

  // 处理剩余 buffer
  if (buffer.startsWith('data: ')) {
    try {
      yield JSON.parse(buffer.slice(6)) as SSEEvent
    } catch { /* ignore */ }
  }
}
