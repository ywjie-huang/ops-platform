/**
 * 日志实时跟随（快照 + SSE）的可复用逻辑。
 *
 * 抽取自 K8s Pod 日志抽屉与 Docker 容器日志抽屉的重复实现。
 * 调用方通过 destructure + 重命名接入，模板无需改动。
 */
import { computed, nextTick, ref, type Ref } from 'vue'
import { ElMessage } from 'element-plus'
import { filterLogLines, highlightLogLines, normalizeLogKeyword } from '@/utils/logSearch'

export interface UseLiveLogsOptions {
  /** 快照拉取：按行数（{ tail_lines }）或时间段（{ since }）。返回 axios 响应体。 */
  fetchSnapshot: (params: { tail_lines?: number; since?: number }) => Promise<any>
  /** 构建 SSE 实时流 URL（token 已含在 query）。 */
  buildStreamUrl: (sinceUnix: number) => string
  /** 抽屉可见性 ref：fetch 末尾据此决定是否自动开启实时跟随。 */
  drawerVisibleRef: Ref<boolean>
  /** 下载文件名（不含扩展名）。 */
  getDownloadName?: () => string
  loadingErrorMessage?: string
}

export function useLiveLogs(opts: UseLiveLogsOptions) {
  const logs = ref('')
  const loading = ref(false)
  const logKeyword = ref('')
  const logMode = ref<'lines' | 'time'>('lines')
  const logTailLines = ref(300)
  const logTimeWindow = ref(900) // 近 15 分钟
  const liveActive = ref(false)
  const logScrollRef = ref<HTMLElement | null>(null)
  // 实时跟随保留的最大行数，避免 DOM 无限增长
  const LIVE_LOG_MAX_LINES = 5000
  let logEs: EventSource | null = null
  let liveSince = 0

  // 实际返回的日志行数：用于在工具栏展示
  const totalLineCount = computed(() => {
    const text = logs.value.trim()
    return text ? text.split('\n').length : 0
  })
  const normalizedKeyword = computed(() => normalizeLogKeyword(logKeyword.value))
  const displayedLogs = computed(() => filterLogLines(logs.value, normalizedKeyword.value))
  const highlightedLines = computed(() => highlightLogLines(displayedLogs.value, normalizedKeyword.value))
  const displayedLineCount = computed(() => {
    const text = displayedLogs.value.trim()
    return text ? text.split('\n').length : 0
  })
  const displayText = computed(() => {
    if (displayedLogs.value) return displayedLogs.value
    return logs.value && normalizedKeyword.value ? '未找到匹配日志' : '暂无日志'
  })
  const countLabel = computed(() => {
    if (loading.value || !logs.value) return ''
    if (normalizedKeyword.value) return `匹配 ${displayedLineCount.value} / ${totalLineCount.value} 行`
    return `共 ${totalLineCount.value} 行`
  })

  async function fetch() {
    if (!opts.drawerVisibleRef) return
    // 重新加载快照前停掉旧的实时连接（随后会重新开启）
    stopLive()
    loading.value = true
    try {
      let res: any
      if (logMode.value === 'time') {
        const since = logTimeWindow.value === 0 ? 0 : Math.floor(Date.now() / 1000) - logTimeWindow.value
        res = await opts.fetchSnapshot({ since })
      } else {
        res = await opts.fetchSnapshot({ tail_lines: logTailLines.value })
      }
      logs.value = res.data?.logs || ''
      await nextTick(() => scrollToBottom(true))
    } catch (e: any) {
      ElMessage.error(e?.response?.data?.detail || opts.loadingErrorMessage || '加载日志失败')
    } finally {
      loading.value = false
    }
    // 以快照为起点开启近实时跟随（追加新行，不清空已有内容）
    if (opts.drawerVisibleRef.value) startLive()
  }

  // ─── 实时跟随（SSE） ───────────────────────────────────────
  function startLive() {
    stopLive()
    // 以「现在」为游标；快照内容保留在前，新行追加其后
    liveSince = Math.floor(Date.now() / 1000)
    const url = opts.buildStreamUrl(liveSince)
    logEs = new EventSource(url)
    liveActive.value = true
    logEs.onmessage = (ev) => {
      let data: any
      try {
        data = JSON.parse(ev.data)
      } catch {
        return
      }
      if (data.type === 'append') {
        const add = data.lines || ''
        if (!add) return
        logs.value = logs.value ? `${logs.value}\n${add}` : add
        trimTail()
        nextTick(() => scrollToBottom(false))
      } else if (data.type === 'error') {
        ElMessage.warning(data.message || '实时拉取出错')
      }
      // ready / heartbeat / done 不需要前端处理
    }
    logEs.onerror = () => {
      // 401（未登录/无权限）→ readyState=CLOSED 且不自动重连；暂态网络错误由浏览器自动重连
      if (logEs && logEs.readyState === EventSource.CLOSED) {
        liveActive.value = false
        ElMessage.error('实时连接已断开，请检查登录状态或权限')
        stopLive()
      }
    }
  }

  function stopLive() {
    liveActive.value = false
    if (logEs) {
      logEs.close()
      logEs = null
    }
  }

  function scrollToBottom(force = false) {
    const el = logScrollRef.value
    if (!el) return
    const nearBottom = force || el.scrollHeight - el.scrollTop - el.clientHeight < 60
    if (nearBottom) el.scrollTop = el.scrollHeight
  }

  function scrollToTop() {
    const el = logScrollRef.value
    if (el) el.scrollTop = 0
  }

  function trimTail() {
    const lines = logs.value.split('\n')
    if (lines.length > LIVE_LOG_MAX_LINES) {
      logs.value = lines.slice(lines.length - LIVE_LOG_MAX_LINES).join('\n')
    }
  }

  function copy() {
    if (!displayedLogs.value) return
    navigator.clipboard.writeText(displayedLogs.value).then(
      () => ElMessage.success('已复制到剪贴板'),
      () => ElMessage.error('复制失败'),
    )
  }

  function download() {
    if (!displayedLogs.value) return
    const name = opts.getDownloadName ? opts.getDownloadName() : 'logs'
    const blob = new Blob([displayedLogs.value], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `${name}.log`
    anchor.click()
    URL.revokeObjectURL(url)
  }

  return {
    logs, loading, logKeyword, logMode, logTailLines, logTimeWindow, liveActive, logScrollRef,
    totalLineCount, normalizedKeyword, displayedLogs, highlightedLines, displayedLineCount, displayText, countLabel,
    fetch, startLive, stopLive, scrollToBottom, scrollToTop, copy, download,
  }
}
