<template>
  <section
    class="ssh-pane"
    :class="{ 'is-active': active, 'is-dim': !active, 'is-connected': connected }"
    tabindex="0"
    @mousedown="$emit('activate', pane.id)"
    @focus="$emit('activate', pane.id)"
  >
    <header class="term-bar">
      <div class="tlights">
        <i
          class="tl-close"
          :title="canClose ? '关闭窗格' : '断开 / 关闭会话'"
          @click.stop="$emit('close', pane.id)"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.2"><path d="M18 6L6 18M6 6l12 12"/></svg>
        </i>
        <i /><i />
      </div>
      <div class="prompt-crumb" :title="`${loginUsername}@${hostName || hostIp}:${pane.currentPath || '~'}`">
        <span class="u">{{ loginUsername }}</span><span class="at">@</span><span class="h">{{ hostName || hostIp }}</span><span class="at">:</span><span class="p">{{ pane.currentPath || '~' }}</span>
      </div>
      <div class="sp" />
      <template v-if="active">
        <button type="button" class="tb-act" title="复制选中内容（聚焦窗格）" @click.stop="copySelection">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15V5a2 2 0 012-2h10"/></svg>
          复制
        </button>
        <button type="button" class="tb-act" title="清屏（聚焦窗格）" @click.stop="clearTerminal">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>
          清屏
        </button>
        <button
          v-if="canSplit"
          type="button"
          class="tb-act"
          title="左右分屏 (Ctrl+\)"
          @click.stop="$emit('split')"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M12 4v16"/></svg>
          分屏
        </button>
        <button
          type="button"
          class="tb-act"
          :class="{ on: dockOpen }"
          title="开关文件面板 (Ctrl+B)"
          @click.stop="$emit('toggle-dock')"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z"/></svg>
          文件
        </button>
        <div class="font-ctrl" @mouseleave="showFontMenu = false">
          <button
            type="button"
            class="tb-act"
            :class="{ on: showFontMenu }"
            title="调整字号"
            @click.stop="showFontMenu = !showFontMenu"
          >Aa</button>
          <div v-if="showFontMenu" class="font-menu" @mousedown.stop>
            <button type="button" @click.stop="changeFontSize(-1)">A-</button>
            <span class="font-size">{{ fontSize }}px</span>
            <button type="button" @click.stop="changeFontSize(1)">A+</button>
          </div>
        </div>
      </template>
    </header>

    <div ref="terminalRef" class="terminal-container" />

    <SSHLoginForm
      ref="loginFormRef"
      v-model:visible="showLoginForm"
      :host-ip="hostIp"
      :host-name="hostName"
      :ssh-keys="sshKeys"
      :connecting="connecting"
      :connected="connected"
      :last-error="pane.lastError"
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
import { buildWebSocketAuthPayload, type LoginFormState } from './sshConnection'
import type { SSHConnectionStatus, SSHPaneState } from './types'
import { getToken } from '@/utils/auth'

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
  hostName: string
  sshKeys: any[]
  active: boolean
  visible: boolean
  canClose: boolean
  canSplit: boolean
  dockOpen: boolean
  initialLoginState: LoginFormState | null
}>()

const emit = defineEmits<{
  activate: [paneId: string]
  close: [paneId: string]
  split: []
  'toggle-dock': []
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
const showFontMenu = ref(false)

let terminal: Terminal | null = null
let fitAddon: FitAddon | null = null
let ws: WebSocket | null = null
let resizeObserver: ResizeObserver | null = null
let timeInterval: ReturnType<typeof setInterval> | null = null
let socketGeneration = 0

// 注入 shell 集成钩子: 每条命令结束后通过 OSC 7 上报当前目录
// bash -> PROMPT_COMMAND, zsh -> add-zsh-hook; 前缀空格避免进入常见 HISTCONTROL 历史
const OSC7_SETUP_CMD =
  " __osc7(){ printf '\\033]7;file://%s%s\\033\\\\' \"${HOSTNAME:-ssh}\" \"$PWD\"; };" +
  " case \"$0\" in *zsh*) autoload -Uz add-zsh-hook 2>/dev/null && add-zsh-hook precmd __osc7 ;;" +
  " *) export PROMPT_COMMAND=\"${PROMPT_COMMAND:+$PROMPT_COMMAND;}__osc7\" ;; esac; __osc7\r"

function applyRemotePath(raw: string) {
  // OSC 7: file://host/path
  const match = raw.match(/^file:\/\/[^/]*(\/.*)$/)
  const path = match?.[1]
  if (!path) return

  let decoded = path
  try {
    decoded = decodeURIComponent(path)
  } catch {
    // 保留原始路径
  }

  if (props.pane.currentPath !== decoded) {
    props.pane.currentPath = decoded
    emitMeta()
  }
}

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
      background: '#08090e',
      foreground: '#c7d0e0',
      cursor: '#8b9dff',
      cursorAccent: '#08090e',
      selectionBackground: 'rgba(139, 157, 255, 0.28)',
      selectionForeground: '#eef1f8',
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
      brightWhite: '#eef1f8',
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

  // 监听 shell 上报的当前目录 (OSC 7 / iTerm2 CurrentDir)
  terminal.parser.registerOscHandler(7, (data) => {
    applyRemotePath(data)
    return true
  })
  terminal.parser.registerOscHandler(1337, (data) => {
    const match = data.match(/CurrentDir=(.*)$/)
    if (match?.[1]) {
      applyRemotePath(`file://ssh${match[1]}`)
    }
    return true
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

  const token = getToken()
  if (!token) {
    connecting.value = false
    props.pane.lastError = 'Authentication required. Please sign in again.'
    emitStatus('error')
    ElMessage.error(props.pane.lastError)
    terminal.write(`\r\n\x1b[31m${props.pane.lastError}\x1b[0m\r\n`)
    return
  }

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
    const authData = buildWebSocketAuthPayload(formData, token)
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
    if (connecting.value && typeof event.data === 'string' && event.data.includes('\x1b[32m')) {
      connected.value = true
      connecting.value = false
      emitStatus('connected')
      startTimeCounter()
      scheduleShellIntegration(socket, generation)
    }
  }

  socket.onclose = (event) => {
    if (generation !== socketGeneration || ws !== socket) {
      return
    }

    const hadConnected = connected.value
    connected.value = false
    connecting.value = false
    stopTimeCounter()
    const wasConnecting = !hadConnected
    const closeReason = event.reason || (wasConnecting ? 'Connection rejected by server.' : 'Connection closed.')
    props.pane.lastError = status.value === 'connecting' ? '连接已关闭' : null
    emitStatus(wasConnecting ? 'error' : 'disconnected')
    if (wasConnecting) {
      props.pane.lastError = closeReason
      showLoginForm.value = true
      ElMessage.error(closeReason)
    }
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

function scheduleShellIntegration(socket: WebSocket, generation: number) {
  // 等待后端打开 channel 并出现首个 shell 提示符后再注入
  window.setTimeout(() => {
    if (generation !== socketGeneration || ws !== socket) return
    if (socket.readyState !== WebSocket.OPEN) return
    socket.send(OSC7_SETUP_CMD)
  }, 800)
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
  border: 0;
  border-radius: 14px;
  background: var(--ssh-term-bg, #08090e);
  box-shadow: inset 0 0 0 1px var(--ssh-line, rgba(255, 255, 255, 0.07)), 0 10px 34px rgba(0, 0, 0, 0.4);
  outline: none;

  &.is-active {
    box-shadow:
      inset 0 0 0 1px var(--ssh-accent-glow, rgba(120, 140, 255, 0.22)),
      0 0 30px rgba(120, 140, 255, 0.07),
      0 10px 34px rgba(0, 0, 0, 0.4);
  }

  &.is-dim .term-bar {
    opacity: 0.45;
  }

  &.is-dim .term-bar:hover {
    opacity: 0.85;
  }

  &:focus-visible {
    outline: none;
  }
}

.term-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 40px;
  padding: 0 14px;
  border-bottom: 1px solid var(--ssh-line, rgba(255, 255, 255, 0.07));
  flex-shrink: 0;
  user-select: none;
  transition: opacity 0.15s ease;
}

.tlights {
  display: flex;
  gap: 6px;
  flex-shrink: 0;

  i {
    width: 11px;
    height: 11px;
    border-radius: 50%;
    display: inline-flex;
    align-items: center;
    justify-content: center;

    &:nth-child(1) { background: rgba(248, 113, 113, 0.85); }
    &:nth-child(2) { background: rgba(251, 191, 36, 0.85); }
    &:nth-child(3) { background: rgba(52, 211, 153, 0.85); }
  }

  .tl-close {
    cursor: pointer;

    svg {
      width: 7px;
      height: 7px;
      color: rgba(0, 0, 0, 0.65);
      opacity: 0;
      transition: opacity 0.12s;
    }

    &:hover {
      box-shadow: 0 0 0 3px rgba(248, 113, 113, 0.25);

      svg {
        opacity: 1;
      }
    }
  }
}

.term-bar:hover .tl-close svg {
  opacity: 1;
}

.prompt-crumb {
  font-family: var(--ssh-mono, ui-monospace, monospace);
  font-size: 11.5px;
  color: var(--ssh-t3, #5c6577);
  display: flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
  overflow: hidden;
  min-width: 0;

  .u { color: var(--ssh-ok, #34d399); }
  .h { color: var(--ssh-accent, #8b9dff); }
  .p {
    color: var(--ssh-accent-2, #a78bfa);
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .at { color: var(--ssh-t4, #3a4152); }
}

.sp {
  flex: 1;
}

.tb-act {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 26px;
  padding: 0 9px;
  border-radius: 7px;
  border: none;
  background: transparent;
  color: var(--ssh-t4, #3a4152);
  font-size: 11px;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  white-space: nowrap;

  svg {
    width: 12px;
    height: 12px;
  }

  &:hover {
    background: var(--ssh-glass, rgba(255, 255, 255, 0.03));
    color: var(--ssh-t1, #eef1f8);
  }

  &.on {
    color: var(--ssh-accent, #8b9dff);
    background: var(--ssh-accent-bg, rgba(139, 157, 255, 0.13));
  }
}

.font-ctrl {
  position: relative;
}

.font-menu {
  position: absolute;
  top: 30px;
  right: 0;
  z-index: 20;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 5px;
  border-radius: 9px;
  background: var(--ssh-card, #0c0e15);
  box-shadow: inset 0 0 0 1px var(--ssh-line-2, rgba(255, 255, 255, 0.12)), 0 10px 30px rgba(0, 0, 0, 0.5);

  button {
    height: 24px;
    padding: 0 8px;
    border: none;
    border-radius: 6px;
    background: transparent;
    color: var(--ssh-t2, #9aa3b5);
    font-size: 11px;
    font-weight: 700;
    font-family: inherit;
    cursor: pointer;

    &:hover {
      background: var(--ssh-glass, rgba(255, 255, 255, 0.03));
      color: var(--ssh-t1, #eef1f8);
    }
  }

  .font-size {
    min-width: 34px;
    text-align: center;
    font-family: var(--ssh-mono, ui-monospace, monospace);
    font-size: 10.5px;
    color: var(--ssh-t3, #5c6577);
  }
}

.terminal-container {
  flex: 1;
  min-height: 0;
  padding: 0;
  overflow: hidden;
  background: transparent;

  /* 内边距必须加在 .xterm 上: FitAddon 只会扣除 .xterm 自身的 padding,
     加在容器上会导致屏幕画布溢出盖住 viewport 滚动条 */
  :deep(.xterm) {
    height: 100%;
    padding: 12px 16px;
  }

  :deep(.xterm-viewport) {
    background: transparent !important;
  }

  :deep(.xterm-screen) {
    border-radius: 0;
  }

  :deep(.xterm-viewport::-webkit-scrollbar) {
    width: 10px;
  }

  :deep(.xterm-viewport::-webkit-scrollbar-track) {
    background: transparent;
  }

  :deep(.xterm-viewport::-webkit-scrollbar-thumb) {
    background: rgba(255, 255, 255, 0.12);
    border: 2px solid transparent;
    border-radius: 6px;
    background-clip: padding-box;

    &:hover {
      background: rgba(255, 255, 255, 0.24);
      background-clip: padding-box;
    }
  }
}
</style>
