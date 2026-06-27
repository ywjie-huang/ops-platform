export interface AutoRefreshController {
  start: () => void
  stop: () => void
  isRunning: () => boolean
}

export function createAutoRefreshController(
  refresh: () => void | Promise<void>,
  intervalMs: number,
): AutoRefreshController
