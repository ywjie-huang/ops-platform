export type ExecControlFrame =
  | { type: 'ready' }
  | { type: 'error'; message: string }

export function parseExecControlFrame(data: unknown): ExecControlFrame | null {
  if (typeof data !== 'string' || !data.startsWith('{')) {
    return null
  }

  try {
    const payload = JSON.parse(data) as Record<string, unknown>
    if (payload.type === 'ready') {
      return { type: 'ready' }
    }
    if (payload.type === 'error') {
      return {
        type: 'error',
        message: typeof payload.message === 'string' ? payload.message : '',
      }
    }
  } catch {
    return null
  }

  return null
}
