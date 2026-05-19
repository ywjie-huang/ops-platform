<template>
  <div class="ssh-page" :class="{ 'file-panel-open': showFilePanel }">
    <!-- 顶部工具栏 -->
    <div class="ssh-toolbar">
      <div class="toolbar-left">
        <el-button text size="small" @click="$router.back()">
          <el-icon><ArrowLeft /></el-icon>
        </el-button>
        <el-divider direction="vertical" />
        <span class="host-info">
          <span :class="['status-dot', connected ? 'dot-green' : 'dot-grey']" />
          <strong>{{ hostName }}</strong>
          <span class="host-ip">{{ hostIp }}</span>
        </span>
      </div>

      <div class="toolbar-center">
        <!-- 终端操作 -->
        <el-tooltip content="复制选中内容" placement="bottom">
          <el-button text size="small" @click="handleCopy" :disabled="!connected">
            <el-icon><CopyDocument /></el-icon>
          </el-button>
        </el-tooltip>
        <el-tooltip content="粘贴" placement="bottom">
          <el-button text size="small" @click="handlePaste" :disabled="!connected">
            <el-icon><DocumentCopy /></el-icon>
          </el-button>
        </el-tooltip>
        <el-divider direction="vertical" />
        <el-tooltip content="清屏" placement="bottom">
          <el-button text size="small" @click="handleClear" :disabled="!connected">
            <el-icon><Delete /></el-icon>
          </el-button>
        </el-tooltip>
        <el-divider direction="vertical" />
        <!-- 字体大小 -->
        <el-tooltip content="缩小字体" placement="bottom">
          <el-button text size="small" @click="changeFontSize(-1)">
            <span style="font-size:12px;font-weight:700">A-</span>
          </el-button>
        </el-tooltip>
        <span class="font-size-label">{{ fontSize }}px</span>
        <el-tooltip content="放大字体" placement="bottom">
          <el-button text size="small" @click="changeFontSize(1)">
            <span style="font-size:16px;font-weight:700">A+</span>
          </el-button>
        </el-tooltip>
        <el-divider direction="vertical" />
        <el-tooltip content="全屏" placement="bottom">
          <el-button text size="small" @click="toggleFullscreen">
            <el-icon><FullScreen /></el-icon>
          </el-button>
        </el-tooltip>
      </div>

      <div class="toolbar-right">
        <el-tooltip content="文件管理器" placement="bottom">
          <el-button
            :type="showFilePanel ? 'primary' : 'default'"
            text size="small"
            @click="toggleFilePanel"
            :disabled="!connected"
          >
            <el-icon><FolderOpened /></el-icon>
          </el-button>
        </el-tooltip>
        <el-divider direction="vertical" />
        <el-tooltip v-if="connected" content="断开连接" placement="bottom">
          <el-button text size="small" type="danger" @click="handleDisconnect">
            <el-icon><SwitchButton /></el-icon>
          </el-button>
        </el-tooltip>
        <el-tooltip v-else content="重新连接" placement="bottom">
          <el-button text size="small" type="success" @click="showLoginForm = true">
            <el-icon><RefreshRight /></el-icon>
          </el-button>
        </el-tooltip>
      </div>
    </div>

    <div class="ssh-body">
      <!-- 主终端区域 -->
      <div class="terminal-area">
        <!-- 登录表单 -->
        <div v-if="showLoginForm" class="login-overlay">
          <el-card shadow="hover" class="login-card">
            <template #header>
              <div class="login-header">
                <span>🖥️ SSH 登录</span>
                <el-tag :type="connected ? 'success' : 'info'" size="small">
                  {{ connected ? '已连接' : '未连接' }}
                </el-tag>
              </div>
            </template>
            <el-form :model="loginForm" label-width="80px" @submit.prevent="connectSSH">
              <el-form-item label="主机">
                <el-input :model-value="`${hostIp}:${loginForm.port}`" disabled />
              </el-form-item>
              <el-form-item label="认证方式">
                <el-select v-model="loginForm.authMode" style="width:100%" @change="onAuthModeChange">
                  <el-option label="使用资产自带凭据" value="asset" />
                  <el-option v-for="key in sshKeys" :key="key.id"
                    :label="`${key.auth_type === 'key' ? '🔑' : '🔒'} ${key.name} (${key.username})`"
                    :value="`key-${key.id}`" />
                </el-select>
              </el-form-item>
              <el-form-item label="用户名">
                <el-input v-model="loginForm.username" placeholder="root" :disabled="loginForm.authMode !== 'asset'" />
              </el-form-item>
              <el-form-item v-if="loginForm.authMode === 'asset'" label="密码">
                <el-input v-model="loginForm.password" type="password" show-password placeholder="请输入 SSH 密码" @keyup.enter="connectSSH" />
              </el-form-item>
              <el-form-item v-else label="凭据">
                <span class="credential-hint">{{ selectedKeyHint }}</span>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" @click="connectSSH" :loading="connecting" style="width:100%">
                  {{ connecting ? '连接中…' : '连接' }}
                </el-button>
              </el-form-item>
            </el-form>
          </el-card>
        </div>

        <!-- 终端 -->
        <div ref="terminalRef" class="terminal-container" />

        <!-- 连接信息栏 -->
        <div v-if="connected" class="terminal-statusbar">
          <span>{{ hostIp }}:{{ loginForm.port }}</span>
          <span>{{ loginForm.username }}</span>
          <span>{{ terminalSize }}</span>
          <span>已连接 {{ connectionTime }}</span>
        </div>
      </div>

      <!-- 文件管理面板 -->
      <transition name="slide-right">
        <div v-if="showFilePanel" class="file-panel">
          <div class="file-panel-header">
            <h4>📁 文件管理</h4>
            <el-button text size="small" @click="showFilePanel = false">
              <el-icon><Close /></el-icon>
            </el-button>
          </div>

          <!-- 路径导航 -->
          <div class="file-path-bar">
            <el-input
              v-model="currentPath"
              size="small"
              @keyup.enter="navigateTo(currentPath)"
              :prefix-icon="Folder"
            />
            <el-button size="small" text @click="navigateTo(currentPath)">
              <el-icon><RefreshRight /></el-icon>
            </el-button>
          </div>

          <!-- 快捷路径 -->
          <div class="file-shortcuts">
            <el-button size="small" text @click="navigateTo('/')">/</el-button>
            <el-button size="small" text @click="navigateTo('/root')">~</el-button>
            <el-button size="small" text @click="navigateTo('/tmp')">/tmp</el-button>
            <el-button size="small" text @click="navigateTo('/etc')">/etc</el-button>
            <el-button size="small" text @click="navigateTo('/var/log')">/var/log</el-button>
          </div>

          <!-- 操作按钮 -->
          <div class="file-actions">
            <el-upload
              :show-file-list="false"
              :before-upload="handleUpload"
              accept="*"
            >
              <el-button size="small" type="primary" :loading="uploading">
                <el-icon><Upload /></el-icon> 上传
              </el-button>
            </el-upload>
            <el-button size="small" @click="handleMkdir">
              <el-icon><FolderAdd /></el-icon> 新建目录
            </el-button>
            <el-button size="small" @click="navigateTo(currentPath)">
              <el-icon><Refresh /></el-icon>
            </el-button>
          </div>

          <!-- 文件列表 -->
          <div class="file-list" v-loading="fileLoading">
            <!-- 上级目录 -->
            <div v-if="currentPath !== '/'" class="file-item" @click="navigateTo(parentPath)" @dblclick="navigateTo(parentPath)">
              <el-icon class="file-icon"><FolderOpened /></el-icon>
              <span class="file-name">..</span>
              <span class="file-meta">上级目录</span>
            </div>

            <div
              v-for="item in fileList"
              :key="item.path"
              class="file-item"
              :class="{ 'is-dir': item.is_dir, 'is-editing': editingPath === item.path }"
              @click="selectFile(item)"
              @dblclick="handleDoubleClick(item)"
            >
              <el-icon class="file-icon" :class="item.is_dir ? 'dir-icon' : 'file-icon-type'">
                <FolderOpened v-if="item.is_dir" />
                <Document v-else />
              </el-icon>

              <!-- 编辑模式 -->
              <template v-if="editingPath === item.path">
                <el-input
                  v-model="editingName"
                  size="small"
                  @keyup.enter="confirmRename(item)"
                  @keyup.escape="editingPath = ''"
                  @blur="confirmRename(item)"
                  ref="editInputRef"
                  class="rename-input"
                />
              </template>
              <template v-else>
                <span class="file-name" :title="item.name">{{ item.name }}</span>
              </template>

              <span class="file-meta">
                {{ item.is_dir ? '' : formatSize(item.size) }}
              </span>
              <span class="file-date">{{ item.modified?.slice(5, 16) }}</span>

              <!-- 操作菜单 -->
              <el-dropdown trigger="click" @command="(cmd: string) => handleFileAction(cmd, item)" class="file-menu">
                <el-icon class="file-menu-icon"><MoreFilled /></el-icon>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item v-if="!item.is_dir" command="download">
                      <el-icon><Download /></el-icon> 下载
                    </el-dropdown-item>
                    <el-dropdown-item v-if="!item.is_dir && isTextFile(item.name)" command="edit">
                      <el-icon><Edit /></el-icon> 编辑
                    </el-dropdown-item>
                    <el-dropdown-item command="rename">
                      <el-icon><EditPen /></el-icon> 重命名
                    </el-dropdown-item>
                    <el-dropdown-item command="delete" divided>
                      <el-icon><Delete /></el-icon>
                      <span style="color:var(--el-color-danger)">删除</span>
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>

            <div v-if="!fileLoading && fileList.length === 0 && currentPath !== '/'" class="empty-files">
              <el-empty description="空目录" :image-size="60" />
            </div>
          </div>
        </div>
      </transition>
    </div>

    <!-- 文件编辑弹窗 -->
    <el-dialog v-model="editDialogVisible" :title="`编辑: ${editFilePath}`" width="80%" top="5vh" destroy-on-close>
      <div v-loading="editLoading">
        <el-input
          v-model="editContent"
          type="textarea"
          :rows="28"
          :autosize="false"
          style="font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 13px;"
        />
      </div>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="editSaving" @click="saveFile">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onActivated, onDeactivated, nextTick, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ArrowLeft, CopyDocument, DocumentCopy, Delete, FullScreen, FolderOpened,
  SwitchButton, RefreshRight, Close, Upload, FolderAdd, Refresh, Folder,
  Document, MoreFilled, Download, Edit, EditPen,
} from '@element-plus/icons-vue'
import { getAsset } from '@/api/assets'
import { getSSHKeys } from '@/api/sshKeys'
import { sftpList, sftpRead, sftpWrite, sftpUpload, sftpDownload, sftpMkdir, sftpRemove, sftpRename } from '@/api/sftp'
import { Terminal } from 'xterm'
import { FitAddon } from 'xterm-addon-fit'
import 'xterm/css/xterm.css'

const route = useRoute()

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

const loginForm = ref({
  username: 'root',
  password: '',
  port: 22,
  authMode: 'asset',
})

const selectedKeyHint = computed(() => {
  if (loginForm.value.authMode === 'asset') return ''
  const keyId = Number(loginForm.value.authMode.replace('key-', ''))
  const key = sshKeys.value.find(k => k.id === keyId)
  if (!key) return '未知密钥'
  return key.auth_type === 'key'
    ? `私钥认证 · ${key.username} · 端口 ${key.port}`
    : `密码认证 · ${key.username} · 端口 ${key.port}`
})

const terminalSize = computed(() => {
  if (!terminal) return ''
  return `${terminal.cols}×${terminal.rows}`
})

// ── 文件管理状态 ──
const showFilePanel = ref(false)
const currentPath = ref('/')
const fileList = ref<any[]>([])
const fileLoading = ref(false)
const uploading = ref(false)
const selectedFile = ref<any>(null)
const editingPath = ref('')
const editingName = ref('')
const editInputRef = ref<any>(null)

// 文件编辑
const editDialogVisible = ref(false)
const editFilePath = ref('')
const editContent = ref('')
const editLoading = ref(false)
const editSaving = ref(false)

let terminal: Terminal | null = null
let fitAddon: FitAddon | null = null
let ws: WebSocket | null = null
let resizeObserver: ResizeObserver | null = null
let currentKeyId: number | undefined = undefined

const parentPath = computed(() => {
  const parts = currentPath.value.split('/').filter(Boolean)
  return parts.length > 1 ? '/' + parts.slice(0, -1).join('/') : '/'
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

// ── 认证方式切换 ──
function onAuthModeChange(val: string) {
  if (val === 'asset') return
  const keyId = Number(val.replace('key-', ''))
  const key = sshKeys.value.find(k => k.id === keyId)
  if (key) {
    loginForm.value.username = key.username
    loginForm.value.port = key.port
  }
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

  // 选中文字自动复制
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
function connectSSH() {
  if (!terminal) return
  connecting.value = true
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
  const assetId = route.params.id
  ws = new WebSocket(`${protocol}//${location.host}/api/v1/ws/ssh/${assetId}`)

  ws.onopen = () => {
    showLoginForm.value = false
    nextTick(() => fitAddon?.fit())

    const authData: any = {
      username: loginForm.value.username,
      port: loginForm.value.port,
    }

    if (loginForm.value.authMode === 'asset') {
      authData.password = loginForm.value.password
    } else {
      const keyId = Number(loginForm.value.authMode.replace('key-', ''))
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

// ── 文件管理 ──
function toggleFilePanel() {
  showFilePanel.value = !showFilePanel.value
  if (showFilePanel.value && connected.value) {
    navigateTo(currentPath.value)
  }
  // 重新 fit 终端
  nextTick(() => fitAddon?.fit())
}

async function navigateTo(path: string) {
  if (!connected.value) return
  const assetId = Number(route.params.id)
  fileLoading.value = true
  try {
    const res: any = await sftpList(assetId, path, currentKeyId)
    currentPath.value = res.data.path
    fileList.value = res.data.items
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '加载失败')
  } finally {
    fileLoading.value = false
  }
}

function selectFile(item: any) {
  selectedFile.value = item
}

function handleDoubleClick(item: any) {
  if (item.is_dir) {
    navigateTo(item.path)
  } else if (isTextFile(item.name)) {
    openEditor(item.path)
  }
}

function handleFileAction(cmd: string, item: any) {
  switch (cmd) {
    case 'download': downloadFile(item); break
    case 'edit': openEditor(item.path); break
    case 'rename': startRename(item); break
    case 'delete': deleteFile(item); break
  }
}

function isTextFile(name: string) {
  const ext = name.split('.').pop()?.toLowerCase() || ''
  return ['txt', 'log', 'conf', 'cfg', 'yml', 'yaml', 'json', 'xml', 'sh', 'bash', 'py', 'js', 'ts',
    'java', 'go', 'rs', 'c', 'cpp', 'h', 'hpp', 'md', 'sql', 'ini', 'toml', 'env', 'properties',
    'html', 'css', 'scss', 'less', 'vue', 'jsx', 'tsx', 'dockerfile', 'nginx', 'service'].includes(ext)
    || !name.includes('.')
}

function formatSize(bytes: number) {
  if (bytes === 0) return ''
  if (bytes < 1024) return `${bytes}B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}K`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)}M`
  return `${(bytes / 1024 / 1024 / 1024).toFixed(1)}G`
}

async function handleUpload(file: File) {
  if (!connected.value) return false
  const assetId = Number(route.params.id)
  uploading.value = true
  try {
    await sftpUpload(assetId, currentPath.value, file, currentKeyId)
    ElMessage.success(`上传成功: ${file.name}`)
    navigateTo(currentPath.value)
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '上传失败')
  } finally {
    uploading.value = false
  }
  return false // 阻止 el-upload 默认行为
}

async function downloadFile(item: any) {
  const assetId = Number(route.params.id)
  try {
    await sftpDownload(assetId, item.path, currentKeyId)
    ElMessage.success('下载开始')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '下载失败')
  }
}

async function openEditor(path: string) {
  const assetId = Number(route.params.id)
  editLoading.value = true
  editDialogVisible.value = true
  editFilePath.value = path
  editContent.value = ''
  try {
    const res: any = await sftpRead(assetId, path, currentKeyId)
    editContent.value = res.data.content
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '读取文件失败')
    editDialogVisible.value = false
  } finally {
    editLoading.value = false
  }
}

async function saveFile() {
  const assetId = Number(route.params.id)
  editSaving.value = true
  try {
    await sftpWrite(assetId, editFilePath.value, editContent.value, currentKeyId)
    ElMessage.success('保存成功')
    editDialogVisible.value = false
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '保存失败')
  } finally {
    editSaving.value = false
  }
}

async function handleMkdir() {
  try {
    const { value } = await ElMessageBox.prompt('请输入目录名称', '新建目录', {
      inputPattern: /^[^\s]+$/,
      inputErrorMessage: '目录名不能为空',
    })
    const assetId = Number(route.params.id)
    const newPath = `${currentPath.value.replace(/\/$/, '')}/${value}`
    await sftpMkdir(assetId, newPath, currentKeyId)
    ElMessage.success('创建成功')
    navigateTo(currentPath.value)
  } catch {
    // 取消
  }
}

async function deleteFile(item: any) {
  try {
    await ElMessageBox.confirm(
      `确认删除 ${item.is_dir ? '目录' : '文件'}「${item.name}」？${item.is_dir ? '目录必须为空才能删除。' : ''}`,
      '确认删除',
      { type: 'warning' }
    )
    const assetId = Number(route.params.id)
    await sftpRemove(assetId, item.path, item.is_dir, currentKeyId)
    ElMessage.success('删除成功')
    navigateTo(currentPath.value)
  } catch {
    // 取消
  }
}

function startRename(item: any) {
  editingPath.value = item.path
  editingName.value = item.name
  nextTick(() => editInputRef.value?.focus())
}

async function confirmRename(item: any) {
  if (!editingName.value || editingName.value === item.name) {
    editingPath.value = ''
    return
  }
  const dir = item.path.substring(0, item.path.lastIndexOf('/'))
  const newPath = `${dir}/${editingName.value}`
  try {
    const assetId = Number(route.params.id)
    await sftpRename(assetId, item.path, newPath, currentKeyId)
    editingPath.value = ''
    navigateTo(currentPath.value)
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '重命名失败')
  }
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
    loginForm.value.username = assetRes.data.ssh_username || 'root'
    loginForm.value.port = assetRes.data.ssh_port || 22

    sshKeys.value = keysRes.data.items || []
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
  showLoginForm.value = true
})

onDeactivated(cleanup)
</script>

<style lang="scss" scoped>
.ssh-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 80px);
  background: #1a1b26;
  border-radius: 8px;
  overflow: hidden;
}

// ── 工具栏 ──
.ssh-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 40px;
  padding: 0 12px;
  background: #24283b;
  border-bottom: 1px solid #33467c;
  flex-shrink: 0;
  user-select: none;

  .el-button { color: #a9b1d6; &:hover { color: #c0caf5; } }
  .el-divider { border-color: #33467c; }
}

.toolbar-left, .toolbar-center, .toolbar-right {
  display: flex;
  align-items: center;
  gap: 4px;
}

.host-info {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #c0caf5;
  .host-ip { color: #565f89; font-size: 12px; }
}

.status-dot {
  width: 8px; height: 8px; border-radius: 50%;
  &.dot-green { background: #9ece6a; box-shadow: 0 0 6px rgba(158,206,106,0.5); }
  &.dot-grey { background: #565f89; }
}

.font-size-label {
  font-size: 11px;
  color: #565f89;
  min-width: 30px;
  text-align: center;
}

// ── 主体 ──
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

// ── 状态栏 ──
.terminal-statusbar {
  display: flex;
  gap: 16px;
  padding: 4px 12px;
  font-size: 11px;
  color: #565f89;
  background: #1f2335;
  border-top: 1px solid #33467c;
}

// ── 登录覆盖层 ──
.login-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(26, 27, 38, 0.92);
  z-index: 10;
}

.login-card {
  width: 420px;
  background: #24283b;
  border: 1px solid #33467c;
  :deep(.el-card__header) { border-bottom: 1px solid #33467c; }
  :deep(.el-card__body) { padding: 20px 24px; }
}

.login-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: #c0caf5;
}

.credential-hint {
  font-size: 13px;
  color: #565f89;
}

// ── 文件管理面板 ──
.file-panel {
  width: 360px;
  background: #1f2335;
  border-left: 1px solid #33467c;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.file-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-bottom: 1px solid #33467c;
  h4 { margin: 0; font-size: 13px; color: #c0caf5; }
  .el-button { color: #a9b1d6; }
}

.file-path-bar {
  display: flex;
  gap: 4px;
  padding: 8px 12px;
  :deep(.el-input__wrapper) { background: #24283b; border-color: #33467c; box-shadow: none; }
  :deep(.el-input__inner) { color: #c0caf5; }
}

.file-shortcuts {
  display: flex;
  gap: 2px;
  padding: 0 12px 8px;
  flex-wrap: wrap;
  .el-button { color: #7aa2f7; font-size: 12px; }
}

.file-actions {
  display: flex;
  gap: 6px;
  padding: 8px 12px;
  border-bottom: 1px solid #33467c;
}

.file-list {
  flex: 1;
  overflow-y: auto;
  padding: 4px 0;

  &::-webkit-scrollbar { width: 6px; }
  &::-webkit-scrollbar-thumb { background: #33467c; border-radius: 3px; }
}

.file-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  cursor: pointer;
  transition: background 0.12s;
  font-size: 13px;
  color: #a9b1d6;

  &:hover { background: #24283b; }
  &.is-dir .file-name { color: #7aa2f7; }
}

.file-icon { font-size: 16px; flex-shrink: 0; }
.dir-icon { color: #7aa2f7; }
.file-icon-type { color: #565f89; }

.file-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-meta {
  font-size: 11px;
  color: #565f89;
  min-width: 50px;
  text-align: right;
}

.file-date {
  font-size: 11px;
  color: #414868;
  min-width: 70px;
}

.file-menu { margin-left: auto; }
.file-menu-icon {
  color: #565f89;
  cursor: pointer;
  &:hover { color: #c0caf5; }
}

.rename-input {
  flex: 1;
  :deep(.el-input__wrapper) { background: #24283b; border-color: #7aa2f7; box-shadow: none; }
  :deep(.el-input__inner) { color: #c0caf5; }
}

.empty-files {
  padding: 20px;
  :deep(.el-empty__description p) { color: #565f89; }
}

// ── 面板动画 ──
.slide-right-enter-active, .slide-right-leave-active {
  transition: width 0.25s ease;
}
.slide-right-enter-from, .slide-right-leave-to {
  width: 0 !important;
  overflow: hidden;
}

// ── Element Plus 暗色覆盖 ──
:deep(.el-loading-mask) { background: rgba(26,27,38,0.7); }
:deep(.el-loading-spinner .circular circle) { stroke: #7aa2f7; }
</style>
