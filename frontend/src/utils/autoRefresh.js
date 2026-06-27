export function createAutoRefreshController(refresh, intervalMs) {
  let timer = null

  function stop() {
    if (timer) {
      clearInterval(timer)
      timer = null
    }
  }

  function start() {
    stop()
    timer = setInterval(() => {
      refresh()
    }, intervalMs)
  }

  function isRunning() {
    return timer !== null
  }

  return {
    start,
    stop,
    isRunning,
  }
}
