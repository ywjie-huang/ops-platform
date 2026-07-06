type MessageRole = 'user' | 'assistant' | 'tool'

export interface AiHistoryMessage {
  id?: number
  role: MessageRole
  content: string | null
  tool_calls?: Array<{
    id: string
    type: string
    function: { name: string; arguments: string }
  }> | null
  tool_call_id?: string | null
  tool_name?: string | null
  created_at: string
}

export interface AiStreamEvent {
  type: 'text' | 'tool_start' | 'tool_result' | 'tool_confirm' | 'error' | 'done'
  content?: string
  tool?: string
  args?: Record<string, unknown>
  result?: string
  pending_id?: string
  description?: string
  conversation_id?: number
}

export interface DisplayMessage {
  type: 'user' | 'text' | 'tool_start' | 'tool_result' | 'tool_confirm'
  content?: string
  tool?: string
  args?: Record<string, unknown>
  result?: string
  description?: string
  pending_id?: string
  time?: string
  elapsed?: number
}

interface ToolCallSnapshot {
  tool: string
  args?: Record<string, unknown>
}

export interface AiStreamState {
  currentTextMessage: DisplayMessage | null
  toolStartTime: Record<string, number>
}

export function createAiStreamState(): AiStreamState {
  return {
    currentTextMessage: null,
    toolStartTime: {},
  }
}

export function buildDisplayMessagesFromHistory(
  messages: AiHistoryMessage[],
  formatTime: (date: string) => string,
): DisplayMessage[] {
  const result: DisplayMessage[] = []
  const toolCallsById = new Map<string, ToolCallSnapshot>()

  for (const message of messages) {
    if (message.role === 'user') {
      result.push({ type: 'user', content: message.content || '', time: formatTime(message.created_at) })
      continue
    }

    if (message.role === 'assistant') {
      for (const toolCall of message.tool_calls || []) {
        toolCallsById.set(toolCall.id, {
          tool: toolCall.function.name,
          args: parseToolArguments(toolCall.function.arguments),
        })
      }

      if (message.content) {
        result.push({ type: 'text', content: message.content, time: formatTime(message.created_at) })
      }
      continue
    }

    if (message.role === 'tool') {
      const callId = message.tool_call_id || ''
      const snapshot = toolCallsById.get(callId)
      result.push({
        type: 'tool_result',
        tool: message.tool_name || snapshot?.tool,
        args: snapshot?.args,
        result: message.content || '',
        time: formatTime(message.created_at),
      })
    }
  }

  return result
}

export function applyAiStreamEvent(
  event: AiStreamEvent,
  messages: DisplayMessage[],
  state: AiStreamState,
  nowLabel: () => string,
  nowMs: () => number = Date.now,
): void {
  switch (event.type) {
    case 'text':
      ensureCurrentTextMessage(messages, state, nowLabel)
      state.currentTextMessage!.content = (state.currentTextMessage!.content || '') + (event.content || '')
      break
    case 'tool_start':
      state.currentTextMessage = null
      state.toolStartTime[event.tool || ''] = nowMs()
      messages.push({ type: 'tool_start', tool: event.tool, args: event.args })
      break
    case 'tool_result': {
      const startIdx = messages.findIndex(
        message => message.type === 'tool_start' && message.tool === event.tool,
      )
      if (startIdx !== -1) messages.splice(startIdx, 1)
      const elapsed = state.toolStartTime[event.tool || '']
        ? nowMs() - state.toolStartTime[event.tool || '']
        : undefined
      messages.push({
        type: 'tool_result',
        tool: event.tool,
        result: event.result,
        args: event.args,
        elapsed,
      })
      state.currentTextMessage = null
      break
    }
    case 'tool_confirm':
      messages.push({
        type: 'tool_confirm',
        tool: event.tool,
        description: event.description,
        pending_id: event.pending_id,
        args: event.args,
      })
      state.currentTextMessage = null
      break
    case 'error':
      ensureCurrentTextMessage(messages, state, nowLabel)
      state.currentTextMessage!.content = `${state.currentTextMessage!.content || ''}\n\n${event.content || ''}`
      break
    case 'done':
      break
  }
}

function ensureCurrentTextMessage(
  messages: DisplayMessage[],
  state: AiStreamState,
  nowLabel: () => string,
): void {
  if (!state.currentTextMessage) {
    state.currentTextMessage = { type: 'text', content: '', time: nowLabel() }
    messages.push(state.currentTextMessage)
  }
}

function parseToolArguments(value: string): Record<string, unknown> | undefined {
  try {
    const parsed = JSON.parse(value || '{}')
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : undefined
  } catch {
    return undefined
  }
}
