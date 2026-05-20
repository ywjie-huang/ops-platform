<template>
  <div class="ssh-page" :class="{ 'file-panel-open': showFilePanel }">
    <SSHTerminalToolbar
      :host-name="hostName"
      :host-ip="hostIp"
      :connected="connected"
      :font-size="fontSize"
      :show-file-panel="showFilePanel"
      @copy="handleCopy"
      @paste="handlePaste"
      @clear="handleClear"
      @change-font-size="changeFontSize"
      @toggle-fullscreen="toggleFullscreen"
      @toggle-file-panel="toggleFilePanel"
      @disconnect="handleDisconnect"
      @reconnect="showLoginForm = true"
    />

    <div class="ssh-body">
      <div class="terminal-area">
        <SSHLoginForm
          ref="loginFormRef"
          v-model:visible="showLoginForm"
          :host-ip="hostIp"
          :ssh-keys="sshKeys"
          :connecting="connecting"
          :connected="connected"
          @connect="onLoginConnect"
        />

        <div ref="terminalRef" class="terminal-container" />

        <div v-if="connected" class="terminal-statusbar">
          <span>{{ hostIp }}:{{ loginPort }}</span>
          <span>{{ loginUsername }}</span>
          <span>{{ terminalSize }}</span>
          <span>已连接 {{ connectionTime }}</span>
        </div>
      </div>

      <SFTPFilePanel
        v-model:visible="showFilePanel"
        :connected="connected"
        :asset-id="Number(route.params.id)"
        :current-key-id="currentKeyId"
        @refit-terminal="nextTick(() => fitAddon?.fit())"
        @edit-file="openEditDialog"
      />
    </div>

    <FileEditDialog
      v-model:visible="editDialogVisible"
      :file-path="editFilePath"
      :asset-id="Number(route.params.id)"
      :current-key-id="currentKeyId"
      @saved="sftpPanelRef?.navigateTo(sftpPanelRef?.currentPath || '/')"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onActivated, onDeactivated, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getAsset } from '@/api/assets'
import { getSSHKeys } from '@/api/sshKeys'
import { Terminal } from 'xterm'
import { FitAddon } from 'xterm-addon-fit'
import 'xterm/css/xterm.css'
import SSHTerminalToolbar from './ssh/SSHTerminalToolbar.vue'
import SSHLoginForm from './ssh/SSHLoginForm.vue'
import SFTPFilePanel from './ssh/SFTPFilePanel.vue'
import FileEditDialog from './ssh/FileEditDialog.vue'

const route = useRoute()

// ── 子组件 ref ──
const loginFormRef = ref<InstanceType<typeof SSHLoginForm>>()
const sftpPanelRef = ref<InstanceType<typeof SFTPFilePanel>>()

// ── 终端状态 ──
const terminalRef = ref<HTMLElement>()
const hostName = ref('')
const hostIp = ref('')
const connected = ref(false)
const connecting = ref(false)
const showLoginForm = ref(false)
const sshKeys = ref<any[]>([])
const fontSize = ref(14)
const connectionStartTime = ref<number>(0)
const connectionTime = ref('')
const loginPort = ref(22)
const loginUsername = ref('root')

// ── 文件编辑 ──
const editDialogVisible = ref(false)
const editFilePath = ref('')

// ── 文件面板 ──
const showFilePanel = ref(false)

let terminal: Terminal | null = null
let fitAddon: FitAddon | null = null
let ws: WebSocket | null = null
let resizeObserver: ResizeObserver | null = null
let currentKeyId: number | undefined = undefined

const terminalSize = computed(() => {
  if (!terminal) return ''
  return `${terminal.cols}×${terminal.rows}`
})

// ── 连接时间计时 ──
let timeInterval: ReturnType<typeof setInterval> | null = null
function startTimeCounter() {
  connectionStartTime.value = Date.now()
  timeInterval = setInterval(() => {
    const elapsed = Math.floor((Date.now() - connectionStartTime.value) / 1000)
    const m = Math.floor(elapsed / 60)
    const s = elapsed % 60
    connectionTime.value = m > 0 ? `${m}m ${s}s` : `${s}s`
  }, 1000)
}
function stopTimeCounter() {
  if (timeInterval) { clearInterval(timeInterval); timeInterval = null }
  connectionTime.value = ''
}

// ── 终端初始化 ──
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
  if (!terminalRef.value) return
  terminal.open(terminalRef.value)
  fitAddon.fit()

  terminal.onData((data) => {
    if (ws?.readyState === WebSocket.OPEN) ws.send(data)
  })

  terminal.onSelectionChange(() => {
    const text = terminal?.getSelection()
    if (text) navigator.clipboard?.writeText(text).catch(() => {})
  })

  resizeObserver = new ResizeObserver(() => {
    fitAddon?.fit()
    if (ws?.readyState === WebSocket.OPEN && terminal) {
      ws.send(JSON.stringify({ cols: terminal.cols, rows: terminal.rows }))
    }
  })
  resizeObserver.observe(terminalRef.value)
}

// ── 连接 SSH ──
function onLoginConnect(formData: { username: string; password: string; port: number; authMode: string }) {
  loginPort.value = formData.port
  loginUsername.value = formData.username
  connectSSH(formData)
}

function connectSSH(formData: { username: string; password: string; port: number; authMode: string }) {
  if (!terminal) return
  connecting.value = true
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
  const assetId = route.params.id
  ws = new WebSocket(`${protocol}//${location.host}/api/v1/ws/ssh/${assetId}`)

  ws.onopen = () => {
    showLoginForm.value = false
    nextTick(() => fitAddon?.fit())

    const authData: any = {
      username: formData.username,
      port: formData.port,
    }

    if (formData.authMode === 'asset') {
      authData.password = formData.password
    } else {
      const keyId = Number(formData.authMode.replace('key-', ''))
      authData.key_id = keyId
      currentKeyId = keyId
    }

    ws!.send(JSON.stringify(authData))
  }

  ws.onmessage = (event) => {
    if (terminal) terminal.write(event.data)
    if (connecting.value) {
      connected.value = true
      connecting.value = false
      startTimeCounter()
    }
  }

  ws.onclose = () => {
    connected.value = false
    connecting.value = false
    stopTimeCounter()
    if (terminal) terminal.write('\r\n\x1b[33m连接已关闭\x1b[0m\r\n')
  }

  ws.onerror = () => {
    connected.value = false
    connecting.value = false
    stopTimeCounter()
    if (terminal) terminal.write('\r\n\x1b[31m连接出错\x1b[0m\r\n')
  }
}

// ── 工具栏操作 ──
function handleCopy() {
  const text = terminal?.getSelection()
  if (text) {
    navigator.clipboard?.writeText(text)
    ElMessage.success('已复制')
  }
}

async function handlePaste() {
  try {
    const text = await navigator.clipboard?.readText()
    if (text && ws?.readyState === WebSocket.OPEN) ws.send(text)
  } catch {
    ElMessage.warning('请使用 Ctrl+V 粘贴')
  }
}

function handleClear() {
  terminal?.clear()
}

function changeFontSize(delta: number) {
  const newSize = fontSize.value + delta
  if (newSize < 10 || newSize > 24) return
  fontSize.value = newSize
  if (terminal) {
    terminal.options.fontSize = newSize
    nextTick(() => fitAddon?.fit())
  }
}

function toggleFullscreen() {
  const el = document.querySelector('.ssh-page')
  if (!el) return
  if (document.fullscreenElement) {
    document.exitFullscreen()
  } else {
    el.requestFullscreen()
  }
}

function handleDisconnect() {
  ws?.close()
  ws = null
  connected.value = false
  stopTimeCounter()
}

function toggleFilePanel() {
  showFilePanel.value = !showFilePanel.value
  if (showFilePanel.value && connected.value) {
    sftpPanelRef.value?.navigateTo(sftpPanelRef.value?.currentPath || '/')
  }
  nextTick(() => fitAddon?.fit())
}

function openEditDialog(path: string) {
  editFilePath.value = path
  editDialogVisible.value = true
}

// ── 清理 ──
function cleanup() {
  ws?.close()
  ws = null
  terminal?.dispose()
  terminal = null
  fitAddon = null
  resizeObserver?.disconnect()
  resizeObserver = null
  connected.value = false
  connecting.value = false
  showFilePanel.value = false
  stopTimeCounter()
  currentKeyId = undefined
}

onActivated(async () => {
  const assetId = route.params.id
  try {
    const [assetRes, keysRes]: any[] = await Promise.all([
      getAsset(Number(assetId)),
      getSSHKeys({ page_size: 100 }),
    ])
    hostName.value = assetRes.data.name
    hostIp.value = assetRes.data.ip_address
    const username = assetRes.data.ssh_username || 'root'
    const port = assetRes.data.ssh_port || 22
    loginUsername.value = username
    loginPort.value = port

    sshKeys.value = keysRes.data.items || []
    const defaultKey = sshKeys.value.find(k => k.is_default)

    await nextTick()
    if (loginFormRef.value) {
      loginFormRef.value.setDefaults(username, port)
      if (defaultKey) {
        loginFormRef.value.setAuthMode(`key-${defaultKey.id}`)
        loginFormRef.value.setDefaults(defaultKey.username, defaultKey.port)
      } else {
        loginFormRef.value.setAuthMode('asset')
      }
      loginFormRef.value.clearPassword()
    }
  } catch {
    hostName.value = '未知'
    hostIp.value = '未知'
  }
  await initTerminal()
  showLoginForm.value = true
})

onDeactivated(cleanup)
</script>

<style lang="scss" scoped>
.ssh-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 56px);
  margin: -20px;
  background: #1a1b26;
  border-radius: 0;
  overflow: hidden;
}

.ssh-body {
  flex: 1;
  display: flex;
  min-height: 0;
}

.terminal-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  position: relative;
}

.terminal-container {
  flex: 1;
  padding: 8px;
  overflow: hidden;
  :deep(.xterm) { height: 100%; }
}

.terminal-statusbar {
  display: flex;
  gap: 16px;
  padding: 4px 12px;
  font-size: 11px;
  color: #565f89;
  background: #1f2335;
  border-top: 1px solid #33467c;
}

:deep(.el-loading-mask) { background: rgba(26,27,38,0.7); }
:deep(.el-loading-spinner .circular circle) { stroke: #7aa2f7; }
</style>
