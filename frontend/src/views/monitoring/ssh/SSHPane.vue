<template>
  <section
    class="ssh-pane"
    :class="{ 'is-active': active, 'is-connected': connected }"
    tabindex="0"
    @mousedown="$emit('activate', pane.id)"
    @focus="$emit('activate', pane.id)"
  >
    <div class="pane-header">
      <div class="pane-title">
        <span class="status-dot" :class="`is-${status}`" />
        <span>{{ pane.title }}</span>
      </div>
      <div class="pane-meta">
        <span v-if="connected">{{ loginUsername }}@{{ hostIp }}:{{ loginPort }}</span>
        <span v-if="terminalSize">{{ terminalSize }}</span>
        <button
          v-if="canClose"
          type="button"
          class="pane-close"
          aria-label="关闭窗格"
          @click.stop="$emit('close', pane.id)"
        >
          ×
        </button>
      </div>
    </div>

    <div ref="terminalRef" class="terminal-container" />

    <SSHLoginForm
      ref="loginFormRef"
      v-model:visible="showLoginForm"
      :host-ip="hostIp"
      :ssh-keys="sshKeys"
      :connecting="connecting"
      :connected="connected"
      @connect="connectSSH"
    />
  </section>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Terminal } from 'xterm'
import { FitAddon } from 'xterm-addon-fit'
import 'xterm/css/xterm.css'
import SSHLoginForm from './SSHLoginForm.vue'
import { buildAuthPayload, type LoginFormState } from './sshConnection'
import type { SSHConnectionStatus, SSHPaneState } from './types'

type ConnectFormData = {
  username: string
  password: string
  port: number
  authMode: string
}

export type SSHPaneMeta = {
  connected: boolean
  connecting: boolean
  status: SSHConnectionStatus
  fontSize: number
  currentKeyId?: number
  authMode: string | null
  connectionSeconds: number
  currentPath: string
  lastError: string | null
  loginUsername: string
  loginPort: number
  terminalSize: string
  connectionTime: string
}

const props = defineProps<{
  pane: SSHPaneState
  assetId: number
  hostIp: string
  sshKeys: any[]
  active: boolean
  visible: boolean
  canClose: boolean
  initialLoginState: LoginFormState | null
}>()

const emit = defineEmits<{
  activate: [paneId: string]
  close: [paneId: string]
  'status-change': [paneId: string, status: SSHConnectionStatus]
  'meta-change': [paneId: string, meta: SSHPaneMeta]
  'key-change': [paneId: string, keyId: number | undefined]
}>()

const terminalRef = ref<HTMLElement>()
const loginFormRef = ref<InstanceType<typeof SSHLoginForm>>()
const showLoginForm = ref(true)
const connected = ref(false)
const connecting = ref(false)
const status = ref<SSHConnectionStatus>('idle')
const fontSize = ref(props.pane.fontSize)
const terminalSize = ref('')
const loginUsername = ref('root')
const loginPort = ref(22)
const currentKeyId = ref<number | undefined>()
const connectionStartTime = ref(0)
const connectionTime = ref('')

let terminal: Terminal | null = null
let fitAddon: FitAddon | null = null
let ws: WebSocket | null = null
let resizeObserver: ResizeObserver | null = null
let timeInterval: ReturnType<typeof setInterval> | null = null
let socketGeneration = 0

function applyInitialLoginState(state: LoginFormState | null) {
  if (!state) {
    return
  }

  loginUsername.value = state.username
  loginPort.value = state.port

  if (loginFormRef.value) {
    loginFormRef.value.setDefaults(state.username, state.port)
    loginFormRef.value.setAuthMode(state.authMode)
    loginFormRef.value.clearPassword()
  }
}

watch(() => props.initialLoginState, applyInitialLoginState, { immediate: true })

watch(
  () => props.active,
  (isActive) => {
    if (isActive) {
      nextTick(() => {
        terminal?.focus()
        fitTerminal()
      })
    }
  },
)

watch(
  () => props.visible,
  (isVisible) => {
    if (isVisible) {
      nextTick(fitTerminal)
    }
  },
)

function emitStatus(nextStatus: SSHConnectionStatus) {
  status.value = nextStatus
  props.pane.status = nextStatus
  emit('status-change', props.pane.id, nextStatus)
  emitMeta()
}

function emitMeta() {
  emit('meta-change', props.pane.id, {
    connected: connected.value,
    connecting: connecting.value,
    status: status.value,
    fontSize: fontSize.value,
    currentKeyId: currentKeyId.value,
    authMode: props.pane.authMode,
    connectionSeconds: props.pane.connectionSeconds,
    currentPath: props.pane.currentPath,
    lastError: props.pane.lastError,
    loginUsername: loginUsername.value,
    loginPort: loginPort.value,
    terminalSize: terminalSize.value,
    connectionTime: connectionTime.value,
  })
}

function updateTerminalSize() {
  terminalSize.value = terminal ? `${terminal.cols}x${terminal.rows}` : ''
  emitMeta()
}

function startTimeCounter() {
  connectionStartTime.value = Date.now()
  if (timeInterval) {
    clearInterval(timeInterval)
  }

  timeInterval = setInterval(() => {
    const elapsed = Math.floor((Date.now() - connectionStartTime.value) / 1000)
    props.pane.connectionSeconds = elapsed
    const minutes = Math.floor(elapsed / 60)
    const seconds = elapsed % 60
    connectionTime.value = minutes > 0 ? `${minutes}m ${seconds}s` : `${seconds}s`
    emitMeta()
  }, 1000)
}

function stopTimeCounter() {
  if (timeInterval) {
    clearInterval(timeInterval)
    timeInterval = null
  }

  connectionTime.value = ''
  props.pane.connectionSeconds = 0
  emitMeta()
}

function fitTerminal() {
  if (!fitAddon || !props.visible) {
    return
  }

  fitAddon.fit()
  updateTerminalSize()
  if (ws?.readyState === WebSocket.OPEN && terminal && terminal.cols > 0 && terminal.rows > 0) {
    ws.send(JSON.stringify({ cols: terminal.cols, rows: terminal.rows }))
  }
}

async function initTerminal() {
  terminal = new Terminal({
    cursorBlink: true,
    fontSize: fontSize.value,
    fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', Menlo, monospace",
    theme: {
      background: '#1a1b26',
      foreground: '#c0caf5',
      cursor: '#c0caf5',
      cursorAccent: '#1a1b26',
      selectionBackground: '#33467c',
      selectionForeground: '#c0caf5',
      black: '#15161e',
      red: '#f7768e',
      green: '#9ece6a',
      yellow: '#e0af68',
      blue: '#7aa2f7',
      magenta: '#bb9af7',
      cyan: '#7dcfff',
      white: '#a9b1d6',
      brightBlack: '#414868',
      brightRed: '#f7768e',
      brightGreen: '#9ece6a',
      brightYellow: '#e0af68',
      brightBlue: '#7aa2f7',
      brightMagenta: '#bb9af7',
      brightCyan: '#7dcfff',
      brightWhite: '#c0caf5',
    },
    allowProposedApi: true,
  })

  fitAddon = new FitAddon()
  terminal.loadAddon(fitAddon)

  await nextTick()
  if (!terminalRef.value) {
    return
  }

  terminal.open(terminalRef.value)
  fitTerminal()

  terminal.onData((data) => {
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(data)
    }
  })

  terminal.onSelectionChange(() => {
    const text = terminal?.getSelection()
    if (text) {
      navigator.clipboard?.writeText(text).catch(() => {})
    }
  })

  resizeObserver = new ResizeObserver(() => {
    fitTerminal()
  })
  resizeObserver.observe(terminalRef.value)
  emitMeta()
}

function connectSSH(formData: ConnectFormData) {
  if (!terminal) {
    return
  }

  disconnect(false)
  connecting.value = true
  emitStatus('connecting')
  loginPort.value = formData.port
  loginUsername.value = formData.username
  props.pane.authMode = formData.authMode
  props.pane.lastError = null

  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
  const socket = new WebSocket(`${protocol}//${location.host}/api/v1/ws/ssh/${props.assetId}`)
  const generation = ++socketGeneration
  ws = socket

  socket.onopen = () => {
    if (generation !== socketGeneration || ws !== socket) {
      return
    }

    showLoginForm.value = false
    nextTick(fitTerminal)
    const authData = buildAuthPayload(formData)
    currentKeyId.value = typeof authData.key_id === 'number' ? authData.key_id : undefined
    emit('key-change', props.pane.id, currentKeyId.value)
    socket.send(JSON.stringify(authData))
    emitMeta()
  }

  socket.onmessage = (event) => {
    if (generation !== socketGeneration || ws !== socket) {
      return
    }

    terminal?.write(event.data)
    if (connecting.value) {
      connected.value = true
      connecting.value = false
      emitStatus('connected')
      startTimeCounter()
    }
  }

  socket.onclose = () => {
    if (generation !== socketGeneration || ws !== socket) {
      return
    }

    connected.value = false
    connecting.value = false
    stopTimeCounter()
    props.pane.lastError = status.value === 'connecting' ? '连接已关闭' : null
    emitStatus(status.value === 'connecting' ? 'error' : 'disconnected')
    terminal?.write('\r\n\x1b[33m连接已关闭\x1b[0m\r\n')
  }

  socket.onerror = () => {
    if (generation !== socketGeneration || ws !== socket) {
      return
    }

    connected.value = false
    connecting.value = false
    stopTimeCounter()
    props.pane.lastError = '连接出错'
    emitStatus('error')
    terminal?.write('\r\n\x1b[31m连接出错\x1b[0m\r\n')
  }
}

function copySelection() {
  const text = terminal?.getSelection()
  if (text) {
    navigator.clipboard?.writeText(text)
    ElMessage.success('已复制')
  }
}

async function pasteClipboard() {
  try {
    const text = await navigator.clipboard?.readText()
    if (text && ws?.readyState === WebSocket.OPEN) {
      ws.send(text)
    }
  } catch {
    ElMessage.warning('请使用 Ctrl+V 粘贴')
  }
}

function clearTerminal() {
  terminal?.clear()
}

function changeFontSize(delta: number) {
  const nextSize = fontSize.value + delta
  if (nextSize < 10 || nextSize > 24) {
    return
  }

  fontSize.value = nextSize
  props.pane.fontSize = nextSize
  if (terminal) {
    terminal.options.fontSize = nextSize
    nextTick(fitTerminal)
  }
  emitMeta()
}

function disconnect(showClosedMessage = true) {
  if (ws) {
    const socket = ws
    ws = null
    socketGeneration += 1
    socket.close()
  }

  connected.value = false
  connecting.value = false
  stopTimeCounter()
  emitStatus('disconnected')
  if (showClosedMessage) {
    terminal?.write('\r\n\x1b[33m连接已断开\x1b[0m\r\n')
  }
}

function reconnect() {
  showLoginForm.value = true
}

function getMeta(): SSHPaneMeta {
  return {
    connected: connected.value,
    connecting: connecting.value,
    status: status.value,
    fontSize: fontSize.value,
    currentKeyId: currentKeyId.value,
    authMode: props.pane.authMode,
    connectionSeconds: props.pane.connectionSeconds,
    currentPath: props.pane.currentPath,
    lastError: props.pane.lastError,
    loginUsername: loginUsername.value,
    loginPort: loginPort.value,
    terminalSize: terminalSize.value,
    connectionTime: connectionTime.value,
  }
}

function cleanup() {
  if (ws) {
    const socket = ws
    ws = null
    socketGeneration += 1
    socket.close()
  }
  terminal?.dispose()
  terminal = null
  fitAddon = null
  resizeObserver?.disconnect()
  resizeObserver = null
  connected.value = false
  connecting.value = false
  currentKeyId.value = undefined
  emit('key-change', props.pane.id, undefined)
  emitStatus('disconnected')
  stopTimeCounter()
}

onMounted(async () => {
  await initTerminal()
  await nextTick()
  applyInitialLoginState(props.initialLoginState)
})
onBeforeUnmount(cleanup)

defineExpose({
  copySelection,
  pasteClipboard,
  clearTerminal,
  changeFontSize,
  disconnect,
  reconnect,
  refit: fitTerminal,
  getMeta,
})
</script>

<style scoped lang="scss">
.ssh-pane {
  position: relative;
  display: flex;
  min-width: 0;
  min-height: 0;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid #27304d;
  border-radius: 7px;
  background: #111624;
  outline: none;
  transition: border-color 0.16s ease-out, box-shadow 0.16s ease-out, transform 0.16s ease-out;

  &.is-active {
    border-color: #6ea8fe;
    box-shadow:
      inset 0 0 0 1px rgb(110 168 254 / 26%),
      0 0 0 1px rgb(110 168 254 / 8%);
  }

  &:focus-visible {
    border-color: #6ea8fe;
  }
}

.pane-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  min-height: 34px;
  padding: 0 9px 0 10px;
  color: #c3ccee;
  background: linear-gradient(180deg, #1b2235, #171d2d);
  border-bottom: 1px solid #27304d;
  font-size: 12px;
}

.pane-title,
.pane-meta {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-width: 0;

  span:last-child {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.pane-meta {
  flex-shrink: 0;
  color: #7f8aaa;
  font-variant-numeric: tabular-nums;
}

.status-dot {
  width: 8px;
  height: 8px;
  flex: 0 0 auto;
  border-radius: 999px;
  background: #565f89;

  &.is-connected {
    background: #4ade80;
    box-shadow: 0 0 0 3px rgb(74 222 128 / 12%);
  }

  &.is-connecting {
    background: #f6c177;
    box-shadow: 0 0 0 3px rgb(246 193 119 / 12%);
  }

  &.is-error {
    background: #ff7b93;
    box-shadow: 0 0 0 3px rgb(255 123 147 / 12%);
  }

  &.is-disconnected {
    background: #6ea8fe;
  }
}

.pane-close {
  width: 22px;
  height: 22px;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: #7f8bb3;
  cursor: pointer;

  &:hover,
  &:focus-visible {
    background: #2a314b;
    color: #f4f7ff;
    outline: none;
  }
}

.terminal-container {
  flex: 1;
  min-height: 0;
  padding: 10px;
  overflow: hidden;
  background:
    linear-gradient(180deg, rgb(255 255 255 / 2%), transparent 26px),
    #0f1420;

  :deep(.xterm) {
    height: 100%;
  }

  :deep(.xterm-viewport) {
    background: transparent !important;
  }
}

@media (max-width: 768px) {
  .pane-header {
    min-height: 32px;
  }

  .pane-meta span:first-child {
    display: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .ssh-pane {
    transition: none;
  }
}
</style>
