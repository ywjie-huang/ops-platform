<template>
  <div class="exec-pane">
    <div class="exec-status" role="status" aria-live="polite">
      <span class="exec-dot" :class="statusClass" aria-hidden="true"></span>
      <span class="exec-status-text">{{ statusText }}</span>
      <span v-if="title" class="exec-title mono">{{ title }}</span>
      <el-button
        v-if="!connecting"
        link
        size="small"
        aria-label="重新连接容器终端"
        @click="reconnect"
      >
        <el-icon><Refresh /></el-icon>重连
      </el-button>
    </div>
    <div ref="terminalRef" class="exec-terminal" :class="{ errored }" aria-label="容器终端"></div>
    <div v-if="errorMessage" class="exec-error" role="alert">{{ errorMessage }}</div>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, nextTick } from 'vue'
import { Terminal } from 'xterm'
import { FitAddon } from 'xterm-addon-fit'
import 'xterm/css/xterm.css'
import { Refresh } from '@element-plus/icons-vue'
import { getToken } from '@/utils/auth'
import { parseExecControlFrame } from './execConnection'

const props = defineProps<{
  wsUrl: string
  title?: string
}>()

const terminalRef = ref<HTMLElement | null>(null)
const connected = ref(false)
const connecting = ref(false)
const errored = ref(false)
const errorMessage = ref('')

let terminal: Terminal | null = null
let fitAddon: FitAddon | null = null
let ws: WebSocket | null = null
let socketGeneration = 0
let resizeObserver: ResizeObserver | null = null
let ready = false

const statusClass = ref('is-connecting')
const statusText = ref('连接中…')

function setStatus() {
  if (errored.value) {
    statusClass.value = 'is-error'
    statusText.value = '连接异常'
  } else if (connected.value) {
    statusClass.value = 'is-online'
    statusText.value = '已连接'
  } else if (connecting.value) {
    statusClass.value = 'is-connecting'
    statusText.value = '连接中…'
  } else {
    statusClass.value = 'is-offline'
    statusText.value = '已断开'
  }
}

function fitTerminal() {
  if (!fitAddon) return
  fitAddon.fit()
  if (ready && ws?.readyState === WebSocket.OPEN && terminal && terminal.cols > 0 && terminal.rows > 0) {
    ws.send(JSON.stringify({ cols: terminal.cols, rows: terminal.rows }))
  }
}

function failConnection(message: string) {
  ready = false
  connecting.value = false
  connected.value = false
  errored.value = true
  errorMessage.value = message
  setStatus()
}

function initTerminal() {
  terminal = new Terminal({
    cursorBlink: true,
    fontSize: 13,
    fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', Menlo, monospace",
    theme: {
      background: '#1a1b26',
      foreground: '#c0caf5',
      cursor: '#c0caf5',
      selectionBackground: '#33467c',
    },
    allowProposedApi: true,
  })
  fitAddon = new FitAddon()
  terminal.loadAddon(fitAddon)
  terminal.open(terminalRef.value!)
  fitTerminal()
  terminal.onData((data) => {
    if (ready && ws?.readyState === WebSocket.OPEN) ws.send(data)
  })
  resizeObserver = new ResizeObserver(() => fitTerminal())
  resizeObserver.observe(terminalRef.value!)
}

function connect() {
  const token = getToken()
  if (!token) {
    failConnection('未登录或登录已过期')
    return
  }
  teardownSocket()
  ready = false
  connecting.value = true
  connected.value = false
  errored.value = false
  errorMessage.value = ''
  setStatus()

  const generation = ++socketGeneration
  const socket = new WebSocket(props.wsUrl)
  ws = socket

  socket.onopen = () => {
    if (generation !== socketGeneration) return
    // 首帧鉴权
    socket.send(JSON.stringify({ token }))
    nextTick(fitTerminal)
  }

  socket.onmessage = (event) => {
    if (generation !== socketGeneration) return
    const data = event.data
    const ctrl = parseExecControlFrame(data)
    if (ctrl?.type === 'ready') {
      ready = true
      connecting.value = false
      connected.value = true
      setStatus()
      nextTick(fitTerminal)
      return
    }
    if (ctrl?.type === 'error') {
      failConnection(ctrl.message || '进入容器失败')
      return
    }
    terminal?.write(typeof data === 'string' ? data : '')
  }

  socket.onclose = (event) => {
    if (generation !== socketGeneration) return
    const wasReady = ready
    ready = false
    connecting.value = false
    connected.value = false
    if (!errored.value && !wasReady) {
      errored.value = true
      errorMessage.value = event.reason || '容器终端在就绪前断开'
    }
    setStatus()
  }

  socket.onerror = () => {
    if (generation !== socketGeneration) return
    if (!errored.value) {
      const message = ready
        ? '容器终端连接中断，请检查 Agent 状态'
        : '连接失败，请检查容器终端功能是否已开启（ENABLE_EXEC_TERMINAL）及权限'
      failConnection(message)
    }
  }
}

function teardownSocket() {
  ready = false
  if (ws) {
    try { ws.onopen = null; ws.onmessage = null; ws.onclose = null; ws.onerror = null } catch { /* noop */ }
    try { ws.close() } catch { /* noop */ }
    ws = null
  }
}

function reconnect() {
  if (terminal) terminal.clear()
  connect()
}

onMounted(async () => {
  await nextTick()
  initTerminal()
  connect()
})

onBeforeUnmount(() => {
  teardownSocket()
  resizeObserver?.disconnect()
  resizeObserver = null
  terminal?.dispose()
  terminal = null
})
</script>

<style scoped>
.exec-pane {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.exec-status {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-secondary);
}
.exec-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex: none;
}
.exec-dot.is-online { background: var(--success-color); }
.exec-dot.is-connecting { background: var(--warning-color); }
.exec-dot.is-offline { background: var(--text-muted); }
.exec-dot.is-error { background: var(--danger-color); }
.exec-status-text { font-weight: 600; }
.exec-title {
  margin-left: auto;
  color: var(--text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 60%;
}
.exec-terminal {
  height: 440px;
  background: #1a1b26;
  border-radius: 7px;
  padding: 6px 8px;
  border: 1px solid var(--border-color);
}
.exec-terminal.errored { opacity: 0.5; }
.exec-error {
  font-size: 12px;
  color: var(--danger-color);
  background: color-mix(in srgb, var(--danger-color) 10%, var(--surface-color));
  border: 1px solid color-mix(in srgb, var(--danger-color) 35%, var(--border-color));
  padding: 8px 10px;
  border-radius: 6px;
}
</style>
