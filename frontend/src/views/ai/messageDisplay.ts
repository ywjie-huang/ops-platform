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
  title_pending?: boolean
}

export interface DisplayMessage {
  type: 'user' | 'text' | 'tool_trace' | 'tool_start' | 'tool_result' | 'tool_confirm'
  content?: string
  tool?: string
  args?: Record<string, unknown>
  result?: string
  description?: string
  pending_id?: string
  time?: string
  elapsed?: number
  steps?: ToolTraceStep[]
}

export interface ToolTraceStep {
  type: 'note' | 'tool'
  content?: string
  tool?: string
  args?: Record<string, unknown>
  result?: string
  elapsed?: number
  status?: 'running' | 'done'
}

interface ToolCallSnapshot {
  tool: string
  args?: Record<string, unknown>
}

export interface AiStreamState {
  pendingText: string
  traceMessage: DisplayMessage | null
  toolStartTime: Record<string, number>
}

export function createAiStreamState(): AiStreamState {
  return {
    pendingText: '',
    traceMessage: null,
    toolStartTime: {},
  }
}

export function buildDisplayMessagesFromHistory(
  messages: AiHistoryMessage[],
  formatTime: (date: string) => string,
): DisplayMessage[] {
  const result: DisplayMessage[] = []
  const toolCallsById = new Map<string, ToolCallSnapshot>()
  let activeTrace: DisplayMessage | null = null

  for (const message of messages) {
    if (message.role === 'user') {
      result.push({ type: 'user', content: message.content || '', time: formatTime(message.created_at) })
      activeTrace = null
      continue
    }

    if (message.role === 'assistant') {
      const toolCalls = message.tool_calls || []
      for (const toolCall of toolCalls) {
        toolCallsById.set(toolCall.id, {
          tool: toolCall.function.name,
          args: parseToolArguments(toolCall.function.arguments),
        })
      }

      if (toolCalls.length) {
        activeTrace = ensureHistoryTrace(result, activeTrace, formatTime(message.created_at))
        addTraceNote(activeTrace, message.content || '')
        continue
      }

      if (message.content) {
        result.push({ type: 'text', content: message.content, time: formatTime(message.created_at) })
      }
      activeTrace = null
      continue
    }

    if (message.role === 'tool') {
      const callId = message.tool_call_id || ''
      const snapshot = toolCallsById.get(callId)
      activeTrace = ensureHistoryTrace(result, activeTrace, formatTime(message.created_at))
      activeTrace.steps!.push({
        type: 'tool',
        tool: message.tool_name || snapshot?.tool,
        args: snapshot?.args,
        result: message.content || '',
        status: 'done',
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
      state.pendingText += event.content || ''
      break
    case 'tool_start':
      flushPendingTextToTrace(messages, state, nowLabel)
      state.toolStartTime[event.tool || ''] = nowMs()
      ensureStreamTrace(messages, state, nowLabel).steps!.push({
        type: 'tool',
        tool: event.tool,
        args: event.args,
        status: 'running',
      })
      break
    case 'tool_result': {
      const trace = ensureStreamTrace(messages, state, nowLabel)
      const elapsed = state.toolStartTime[event.tool || '']
        ? nowMs() - state.toolStartTime[event.tool || '']
        : undefined
      const runningStep = [...trace.steps!].reverse().find(
        step => step.type === 'tool' && step.tool === event.tool && step.status === 'running',
      )
      const nextStep = runningStep || {
        type: 'tool' as const,
        tool: event.tool,
        args: event.args,
      }
      nextStep.result = event.result
      nextStep.args = event.args || nextStep.args
      nextStep.elapsed = elapsed
      nextStep.status = 'done'
      if (!runningStep) trace.steps!.push(nextStep)
      break
    }
    case 'tool_confirm':
      flushPendingTextToTrace(messages, state, nowLabel)
      messages.push({
        type: 'tool_confirm',
        tool: event.tool,
        description: event.description,
        pending_id: event.pending_id,
        args: event.args,
      })
      break
    case 'error':
      flushPendingTextToText(messages, state, nowLabel, event.content || '')
      break
    case 'done':
      flushPendingTextToText(messages, state, nowLabel)
      break
  }
}

function ensureHistoryTrace(
  messages: DisplayMessage[],
  activeTrace: DisplayMessage | null,
  time: string,
): DisplayMessage {
  if (activeTrace) return activeTrace
  const trace: DisplayMessage = { type: 'tool_trace', steps: [], time }
  messages.push(trace)
  return trace
}

function ensureStreamTrace(
  messages: DisplayMessage[],
  state: AiStreamState,
  nowLabel: () => string,
): DisplayMessage {
  if (state.traceMessage) return state.traceMessage
  state.traceMessage = { type: 'tool_trace', steps: [], time: nowLabel() }
  messages.push(state.traceMessage)
  return state.traceMessage
}

function addTraceNote(trace: DisplayMessage, content: string): void {
  const text = content.trim()
  if (!text) return
  trace.steps!.push({ type: 'note', content: text })
}

function flushPendingTextToTrace(
  messages: DisplayMessage[],
  state: AiStreamState,
  nowLabel: () => string,
): void {
  const text = state.pendingText.trim()
  if (!text) return
  addTraceNote(ensureStreamTrace(messages, state, nowLabel), text)
  state.pendingText = ''
}

function flushPendingTextToText(
  messages: DisplayMessage[],
  state: AiStreamState,
  nowLabel: () => string,
  suffix = '',
): void {
  const parts = [state.pendingText.trim(), suffix.trim()].filter(Boolean)
  if (!parts.length) return
  messages.push({ type: 'text', content: parts.join('\n\n'), time: nowLabel() })
  state.pendingText = ''
}

export function traceStepLabel(step: ToolTraceStep): string {
  if (step.type === 'note') return '\u8ba1\u5212'
  if (step.status === 'running') return '\u6267\u884c\u4e2d'
  return '\u5b8c\u6210'
}

export function traceSummary(message: DisplayMessage): string {
  const steps = message.steps || []
  const toolCount = steps.filter(step => step.type === 'tool').length
  const running = steps.some(step => step.type === 'tool' && step.status === 'running')
  if (running) return `\u601d\u8003\u8fc7\u7a0b - \u6b63\u5728\u6267\u884c ${toolCount} \u9879\u67e5\u8be2`
  if (toolCount) return `\u601d\u8003\u8fc7\u7a0b - \u5df2\u5b8c\u6210 ${toolCount} \u9879\u67e5\u8be2`
  return '\u601d\u8003\u8fc7\u7a0b'
}

export function traceTotalElapsed(message: DisplayMessage): number | undefined {
  const total = (message.steps || []).reduce((sum, step) => sum + (step.elapsed || 0), 0)
  return total || undefined
}

export function traceHasResults(message: DisplayMessage): boolean {
  return (message.steps || []).some(step => step.type === 'tool' && !!step.result)
}

function parseToolArguments(value: string): Record<string, unknown> | undefined {
  try {
    const parsed = JSON.parse(value || '{}')
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : undefined
  } catch {
    return undefined
  }
}
