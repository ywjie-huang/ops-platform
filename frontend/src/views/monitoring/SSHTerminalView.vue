<template>
  <div class="ssh-page">
    <div class="ssh-header">
      <el-button text @click="$router.back()">
        <el-icon><ArrowLeft /></el-icon> 返回
      </el-button>
      <span class="ssh-title">🖥️ SSH 终端 — {{ hostName }} ({{ hostIp }})</span>
      <div class="ssh-actions">
        <el-tag :type="connected ? 'success' : 'danger'" size="small">
          {{ connected ? '已连接' : '未连接' }}
        </el-tag>
      </div>
    </div>

    <!-- 登录表单 -->
    <div v-if="showLoginForm" class="login-form">
      <el-card shadow="hover">
        <template #header><span>SSH 登录</span></template>
        <el-form :model="loginForm" label-width="80px">
          <el-form-item label="主机">
            <el-input :model-value="`${hostIp}:${loginForm.port}`" disabled />
          </el-form-item>

          <!-- 密钥选择 -->
          <el-form-item label="认证方式">
            <el-select v-model="loginForm.authMode" style="width:100%" @change="onAuthModeChange">
              <el-option label="使用资产自带凭据" value="asset" />
              <el-option v-for="key in sshKeys" :key="key.id" :label="`${key.auth_type === 'key' ? '🔑' : '🔒'} ${key.name} (${key.username})`" :value="`key-${key.id}`" />
            </el-select>
          </el-form-item>

          <el-form-item label="用户名">
            <el-input v-model="loginForm.username" placeholder="root" :disabled="loginForm.authMode !== 'asset'" />
          </el-form-item>
          <el-form-item v-if="loginForm.authMode === 'asset'" label="密码">
            <el-input v-model="loginForm.password" type="password" show-password placeholder="请输入 SSH 密码" @keyup.enter="connectSSH" />
          </el-form-item>
          <el-form-item v-else label="凭据">
            <span class="credential-hint">
              {{ selectedKeyHint }}
            </span>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="connectSSH" :loading="connecting">连接</el-button>
          </el-form-item>
        </el-form>
      </el-card>
    </div>

    <!-- 终端容器 -->
    <div ref="terminalRef" class="terminal-container" v-show="!showLoginForm" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onActivated, onDeactivated, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import { getAsset } from '@/api/assets'
import { getSSHKeys } from '@/api/sshKeys'
import { Terminal } from 'xterm'
import { FitAddon } from 'xterm-addon-fit'
import 'xterm/css/xterm.css'

const route = useRoute()

const terminalRef = ref<HTMLElement>()
const hostName = ref('')
const hostIp = ref('')
const connected = ref(false)
const connecting = ref(false)
const showLoginForm = ref(false)
const sshKeys = ref<any[]>([])

const loginForm = ref({
  username: 'root',
  password: '',
  port: 22,
  authMode: 'asset' as string,  // 'asset' | 'key-{id}'
})

const selectedKeyHint = computed(() => {
  if (loginForm.value.authMode === 'asset') return ''
  const keyId = Number(loginForm.value.authMode.replace('key-', ''))
  const key = sshKeys.value.find(k => k.id === keyId)
  if (!key) return '未知密钥'
  return key.auth_type === 'key'
    ? `使用私钥认证，用户名: ${key.username}，端口: ${key.port}`
    : `使用密码认证，用户名: ${key.username}，端口: ${key.port}`
})

let terminal: Terminal | null = null
let fitAddon: FitAddon | null = null
let ws: WebSocket | null = null
let resizeObserver: ResizeObserver | null = null

function onAuthModeChange(val: string) {
  if (val === 'asset') return
  const keyId = Number(val.replace('key-', ''))
  const key = sshKeys.value.find(k => k.id === keyId)
  if (key) {
    loginForm.value.username = key.username
    loginForm.value.port = key.port
  }
}

async function initTerminal() {
  terminal = new Terminal({
    cursorBlink: true,
    fontSize: 14,
    fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', Menlo, monospace",
    theme: {
      background: '#1e1e2e',
      foreground: '#cdd6f4',
      cursor: '#f5e0dc',
      selectionBackground: '#585b70',
      black: '#45475a',
      red: '#f38ba8',
      green: '#a6e3a1',
      yellow: '#f9e2af',
      blue: '#89b4fa',
      magenta: '#f5c2e7',
      cyan: '#94e2d5',
      white: '#bac2de',
      brightBlack: '#585b70',
      brightRed: '#f38ba8',
      brightGreen: '#a6e3a1',
      brightYellow: '#f9e2af',
      brightBlue: '#89b4fa',
      brightMagenta: '#f5c2e7',
      brightCyan: '#94e2d5',
      brightWhite: '#a6adc8',
    },
  })

  fitAddon = new FitAddon()
  terminal.loadAddon(fitAddon)

  await nextTick()
  if (!terminalRef.value) return

  terminal.open(terminalRef.value)
  fitAddon.fit()

  // 监听终端输入
  terminal.onData((data) => {
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(data)
    }
  })

  // 监听窗口大小变化
  resizeObserver = new ResizeObserver(() => {
    fitAddon?.fit()
    if (ws?.readyState === WebSocket.OPEN && terminal) {
      ws.send(JSON.stringify({ cols: terminal.cols, rows: terminal.rows }))
    }
  })
  resizeObserver.observe(terminalRef.value)
}

function connectSSH() {
  if (!terminal) return

  connecting.value = true
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
  const assetId = route.params.id
  ws = new WebSocket(`${protocol}//${location.host}/api/v1/ws/ssh/${assetId}`)

  ws.onopen = () => {
    // 终端显示后重新 fit（因为初始化时被隐藏，尺寸为 0）
    showLoginForm.value = false
    nextTick(() => fitAddon?.fit())

    // 构建认证信息
    const authData: any = {
      username: loginForm.value.username,
      port: loginForm.value.port,
    }

    if (loginForm.value.authMode === 'asset') {
      // 使用资产自带密码
      authData.password = loginForm.value.password
    } else {
      // 使用指定密钥
      const keyId = Number(loginForm.value.authMode.replace('key-', ''))
      authData.key_id = keyId
    }

    ws!.send(JSON.stringify(authData))
  }

  ws.onmessage = (event) => {
    if (terminal) {
      terminal.write(event.data)
    }
    // 首次收到数据即表示连接成功
    if (connecting.value) {
      connected.value = true
      connecting.value = false
    }
  }

  ws.onclose = () => {
    connected.value = false
    connecting.value = false
    if (terminal) {
      terminal.write('\r\n\x1b[33m连接已关闭\x1b[0m\r\n')
    }
  }

  ws.onerror = () => {
    connected.value = false
    connecting.value = false
    if (terminal) {
      terminal.write('\r\n\x1b[31m连接出错\x1b[0m\r\n')
    }
  }
}

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
}

// keep-alive 下用 onActivated/onDeactivated 管理生命周期
onActivated(async () => {
  const assetId = route.params.id

  // 并行获取资产信息和密钥列表
  try {
    const [assetRes, keysRes]: any[] = await Promise.all([
      getAsset(Number(assetId)),
      getSSHKeys({ page_size: 100 }),
    ])
    hostName.value = assetRes.data.name
    hostIp.value = assetRes.data.ip_address
    loginForm.value.username = assetRes.data.ssh_username || 'root'
    loginForm.value.port = assetRes.data.ssh_port || 22

    sshKeys.value = keysRes.data.items || []

    // 如果有默认密钥，自动选中
    const defaultKey = sshKeys.value.find(k => k.is_default)
    if (defaultKey) {
      loginForm.value.authMode = `key-${defaultKey.id}`
      loginForm.value.username = defaultKey.username
      loginForm.value.port = defaultKey.port
    } else {
      loginForm.value.authMode = 'asset'
    }
  } catch {
    hostName.value = '未知'
    hostIp.value = '未知'
  }
  loginForm.value.password = ''

  await initTerminal()

  // 显示登录表单，让用户确认或输入密码
  showLoginForm.value = true
})

// 离开页面时清理旧连接，避免切换主机时串连
onDeactivated(cleanup)
</script>

<style lang="scss" scoped>
.ssh-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 100px);
}

.ssh-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 0;
  flex-shrink: 0;
}

.ssh-title {
  font-size: 15px;
  font-weight: 600;
  flex: 1;
}

.ssh-actions {
  display: flex;
  gap: 8px;
}

.login-form {
  display: flex;
  justify-content: center;
  padding: 40px;

  .el-card {
    width: 440px;
  }
}

.credential-hint {
  font-size: 13px;
  color: var(--text-muted);
}

.terminal-container {
  flex: 1;
  background: #1e1e2e;
  border-radius: 8px;
  overflow: hidden;
  padding: 4px;

  :deep(.xterm) {
    height: 100%;
  }
}
</style>
