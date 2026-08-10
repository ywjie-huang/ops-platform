<template>
  <div class="ssh-page">
    <SSHTopBar
      :host-name="activeHost?.name || ''"
      :host-ip="activeHost?.ip || ''"
      :login-username="activePaneMeta.loginUsername"
      :login-port="activePaneMeta.loginPort"
      :status="activePaneMeta.status"
      :connection-time="activePaneMeta.connectionTime"
      @back="$router.back()"
      @toggle-fullscreen="toggleFullscreen"
      @open-search="openCommands"
      @open-settings="openInfo"
      @disconnect="activePaneGrid?.disconnectActivePane()"
      @reconnect="activePaneGrid?.reconnectActivePane()"
    />

    <div class="workbench">
      <SSHSessionRail
        :tabs="workbench.tabs"
        :active-tab-id="workbench.activeTabId"
        :meta="paneMeta"
        @activate-tab="handleActivateTab"
        @add-tab="toggleHostPicker"
        @close-tab="handleCloseTab"
        @rename-tab="handleRenameTab"
        @reconnect-tab="handleReconnectTab"
        @open-commands="openCommands"
        @open-info="openInfo"
      />

      <main class="stage">
        <SSHPaneGrid
          v-for="tab in workbench.tabs"
          v-show="tab.id === workbench.activeTabId"
          :key="tab.id"
          :ref="(instance) => setPaneGridRef(tab.id, instance)"
          :class="{ 'is-hidden': tab.id !== workbench.activeTabId }"
          :tab="tab"
          :visible="tab.id === workbench.activeTabId"
          :active-pane-id="tab.id === workbench.activeTabId ? workbench.activePaneId : ''"
          :asset-id="tab.host.assetId"
          :host-ip="tab.host.ip"
          :host-name="tab.host.name"
          :ssh-keys="sshKeys"
          :dock-open="workbench.rightPanelOpen"
          :initial-login-state="loginStateOf(tab)"
          @activate-pane="handleActivatePane(tab.id, $event)"
          @close-pane="handleClosePane(tab.id, $event)"
          @pane-split="handleSplit('vertical')"
          @pane-toggle-dock="toggleFilePanel"
          @pane-status-change="handlePaneStatusChange"
          @pane-meta-change="handlePaneMetaChange"
          @pane-key-change="handlePaneKeyChange"
        />
      </main>

      <SSHDockPanel
        ref="dockPanelRef"
        v-model:open="workbench.rightPanelOpen"
        :active-tab="workbench.rightPanelTab"
        :connected="activePaneMeta.connected"
        :asset-id="activeAssetId"
        :current-key-id="activePaneMeta.currentKeyId"
        :ssh-keys="sshKeys"
        :active-pane="activePane"
        :active-pane-meta="activePaneMeta"
        @change-tab="handleDockTabChange"
        @refit-terminal="handleRefitTerminal"
        @edit-file="openEditDialog"
        @path-change="handlePathChange"
      />
    </div>

    <SSHFootBar
      :terminal-size="activePaneMeta.terminalSize"
      :current-path="activePaneMeta.currentPath"
      :credential-label="credentialLabel"
      :layout-label="layoutLabel"
    />

    <FileEditDialog
      v-model:visible="editDialogVisible"
      :file-path="editFilePath"
      :asset-id="activeAssetId"
      :current-key-id="activePaneMeta.currentKeyId"
      @saved="dockPanelRef?.navigateTo(dockPanelRef?.currentPath || '/')"
    />

    <SSHHostPicker
      v-if="hostPickerOpen"
      :assets="pickerAssets"
      :current-asset-id="routeAssetId"
      @select="handlePickHost"
      @close="hostPickerOpen = false"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onActivated, onDeactivated, onMounted, onUnmounted, reactive, ref, type ComponentPublicInstance } from 'vue'
import { useRoute } from 'vue-router'
import { getAsset, getAssets } from '@/api/assets'
import { getSSHKeys } from '@/api/sshKeys'
import FileEditDialog from './ssh/FileEditDialog.vue'
import SSHDockPanel from './ssh/SSHDockPanel.vue'
import SSHFootBar from './ssh/SSHFootBar.vue'
import SSHHostPicker from './ssh/SSHHostPicker.vue'
import SSHPaneGrid from './ssh/SSHPaneGrid.vue'
import type { SSHPaneMeta } from './ssh/SSHPane.vue'
import SSHSessionRail from './ssh/SSHSessionRail.vue'
import SSHTopBar from './ssh/SSHTopBar.vue'
import { getInitialLoginState, type LoginFormState } from './ssh/sshConnection'
import type { SSHConnectionStatus, SSHHostRef, SSHPaneLayout, SSHRightPanelTab } from './ssh/types'
import {
  addTab,
  closePane,
  createInitialWorkbenchState,
  removeTab,
  renameTab,
  setActivePane,
  setTabHost,
  splitActiveTab,
  updatePaneMeta,
} from './ssh/useSSHWorkbench'

const route = useRoute()

const dockPanelRef = ref<InstanceType<typeof SSHDockPanel>>()
type SSHPaneGridPublic = InstanceType<typeof SSHPaneGrid>

const routeAssetId = Number(route.params.id)
const sshKeys = ref<any[]>([])
const pickerAssets = ref<any[]>([])
const hostPickerOpen = ref(false)
const editDialogVisible = ref(false)
const editFilePath = ref('')
const paneMeta = reactive<Record<string, SSHPaneMeta>>({})
const workbench = reactive(createInitialWorkbenchState({
  assetId: routeAssetId,
  name: '',
  ip: '',
  username: 'root',
  port: 22,
  authMode: 'asset',
}))
const paneGridRefs = reactive(new Map<string, SSHPaneGridPublic>())

const activeTab = computed(() => workbench.tabs.find((tab) => tab.id === workbench.activeTabId))
const activePane = computed(() => activeTab.value?.panes.find((item) => item.id === workbench.activePaneId))
const activeHost = computed(() => activeTab.value?.host)
const activeAssetId = computed(() => activeHost.value?.assetId || routeAssetId)
const activePaneGrid = computed(() => paneGridRefs.get(workbench.activeTabId))
const canSplit = computed(() => activeTab.value?.layout === 'single')

function loginStateOf(tab: { host: SSHHostRef }): LoginFormState {
  return {
    username: tab.host.username,
    port: tab.host.port,
    authMode: tab.host.authMode,
  }
}
const activePaneMeta = computed<SSHPaneMeta>(() => {
  const pane = activeTab.value?.panes.find((item) => item.id === workbench.activePaneId)
  return paneMeta[workbench.activePaneId] ?? {
    connected: false,
    connecting: false,
    status: pane?.status ?? 'idle',
    fontSize: pane?.fontSize ?? 13,
    currentKeyId: undefined,
    authMode: pane?.authMode ?? 'asset',
    connectionSeconds: pane?.connectionSeconds ?? 0,
    currentPath: pane?.currentPath ?? '/',
    lastError: pane?.lastError ?? null,
    loginUsername: activeHost.value?.username ?? 'root',
    loginPort: activeHost.value?.port ?? 22,
    terminalSize: '',
    connectionTime: '',
  }
})
const layoutLabel = computed(() => {
  if (activeTab.value?.layout === 'vertical') return '左右分屏'
  if (activeTab.value?.layout === 'horizontal') return '上下分屏'
  return ''
})
const credentialLabel = computed(() => {
  if (!activePaneMeta.value.connected) return ''
  const keyId = activePaneMeta.value.currentKeyId
  if (!keyId) return '资产凭据'
  const key = sshKeys.value.find((item) => item.id === keyId)
  return key ? key.name : `密钥 #${keyId}`
})

function toggleFullscreen() {
  const page = document.querySelector('.ssh-page')
  if (!page) return

  if (document.fullscreenElement) {
    document.exitFullscreen()
  } else {
    page.requestFullscreen()
  }
}

function toggleHostPicker() {
  hostPickerOpen.value = !hostPickerOpen.value
}

function handlePickHost(asset: any) {
  const login = getInitialLoginState(asset, sshKeys.value)
  const host: SSHHostRef = {
    assetId: asset.id,
    name: asset.name || asset.ip_address || `主机 #${asset.id}`,
    ip: asset.ip_address || '',
    username: login.username,
    port: login.port,
    authMode: login.authMode,
  }
  addTab(workbench, host.name, host)
  hostPickerOpen.value = false
}

function setPaneGridRef(
  tabId: string,
  instance: Element | ComponentPublicInstance | SSHPaneGridPublic | null,
) {
  if (!instance) {
    paneGridRefs.delete(tabId)
    return
  }

  const grid = instance as SSHPaneGridPublic
  if (typeof grid.getActivePaneMeta === 'function') {
    paneGridRefs.set(tabId, grid)
  }
}

function handleActivateTab(tabId: string) {
  const targetTab = workbench.tabs.find((tab) => tab.id === tabId)
  if (!targetTab) return

  workbench.activeTabId = targetTab.id
  workbench.activePaneId = targetTab.panes[0].id
  nextTick(() => {
    const path = paneMeta[workbench.activePaneId]?.currentPath
    if (path) syncDockToTerminal(path)
  })
}

function handleCloseTab(tabId: string) {
  const targetTab = workbench.tabs.find((tab) => tab.id === tabId)
  targetTab?.panes.forEach((pane) => {
    delete paneMeta[pane.id]
  })
  paneGridRefs.delete(tabId)
  removeTab(workbench, tabId)
}

function handleRenameTab(tabId: string, title: string) {
  renameTab(workbench, tabId, title)
}

function handleReconnectTab(tabId: string) {
  handleActivateTab(tabId)
  nextTick(() => activePaneGrid.value?.reconnectActivePane())
}

function handleSplit(layout: Exclude<SSHPaneLayout, 'single'>) {
  if (!canSplit.value) return

  splitActiveTab(workbench, layout)
  nextTick(() => activePaneGrid.value?.refitActivePane())
}

function handleActivatePane(tabId: string, paneId: string) {
  if (workbench.activeTabId !== tabId) {
    workbench.activeTabId = tabId
  }

  setActivePane(workbench, paneId)
}

function handleClosePane(tabId: string, paneId: string) {
  const tab = workbench.tabs.find((item) => item.id === tabId)
  if (!tab) return

  if (tab.panes.length > 1) {
    if (workbench.activeTabId !== tabId) return
    closePane(workbench, paneId)
    delete paneMeta[paneId]
    nextTick(() => activePaneGrid.value?.refitActivePane())
    return
  }

  // 单窗格: 红点关闭整个会话; 最后一个会话则断开连接
  if (workbench.tabs.length > 1) {
    handleCloseTab(tabId)
  } else if (workbench.activeTabId === tabId) {
    activePaneGrid.value?.disconnectActivePane()
  }
}

function handlePaneStatusChange(paneId: string, status: SSHConnectionStatus) {
  const tab = workbench.tabs.find((item) => item.panes.some((pane) => pane.id === paneId))
  const pane = tab?.panes.find((item) => item.id === paneId)
  if (pane) {
    pane.status = status
  }
  if (tab) {
    tab.status = tab.panes.some((item) => item.status === 'connected')
      ? 'connected'
      : tab.panes.some((item) => item.status === 'connecting')
        ? 'connecting'
        : status
  }
}

function handlePaneMetaChange(paneId: string, meta: SSHPaneMeta) {
  const paneExists = workbench.tabs.some((tab) => tab.panes.some((pane) => pane.id === paneId))
  if (!paneExists) return

  const prevPath = paneMeta[paneId]?.currentPath
  paneMeta[paneId] = meta
  updatePaneMeta(workbench, paneId, {
    authMode: meta.authMode,
    connectionSeconds: meta.connectionSeconds,
    currentPath: meta.currentPath,
    lastError: meta.lastError,
  })

  // 终端里 cd 触发的路径变化: 同步右侧文件面板
  if (meta.currentPath && meta.currentPath !== prevPath && paneId === workbench.activePaneId) {
    syncDockToTerminal(meta.currentPath)
  }
}

function syncDockToTerminal(path: string) {
  if (!workbench.rightPanelOpen || workbench.rightPanelTab !== 'files') return
  if (!path || dockPanelRef.value?.currentPath === path) return
  dockPanelRef.value?.navigateTo(path)
}

function handlePaneKeyChange(paneId: string, keyId: number | undefined) {
  const existing = paneMeta[paneId]
  if (existing) {
    existing.currentKeyId = keyId
  }
}

function handlePathChange(path: string) {
  updatePaneMeta(workbench, workbench.activePaneId, { currentPath: path })
}

function handleRefitTerminal() {
  nextTick(() => activePaneGrid.value?.refitActivePane())
}

function navigateDock(preferTerminalPath: boolean) {
  nextTick(() => {
    const dockPath = dockPanelRef.value?.currentPath || '/'
    const terminalPath = activePaneMeta.value.currentPath
    dockPanelRef.value?.navigateTo(preferTerminalPath && terminalPath ? terminalPath : dockPath)
  })
}

function toggleFilePanel() {
  workbench.rightPanelOpen = !workbench.rightPanelOpen
  if (workbench.rightPanelOpen && activePaneMeta.value.connected) {
    navigateDock(true)
  }

  handleRefitTerminal()
}

function openDockTab(tab: SSHRightPanelTab) {
  workbench.rightPanelOpen = true
  workbench.rightPanelTab = tab
  if (tab === 'files' && activePaneMeta.value.connected) {
    navigateDock(true)
  }

  handleRefitTerminal()
}

function openCommands() {
  openDockTab('actions')
}

function openInfo() {
  openDockTab('info')
}

function handleDockTabChange(tab: SSHRightPanelTab) {
  workbench.rightPanelTab = tab
  if (tab === 'files' && workbench.rightPanelOpen && activePaneMeta.value.connected) {
    navigateDock(true)
  }
}

function openEditDialog(path: string) {
  editFilePath.value = path
  editDialogVisible.value = true
}

function cleanup() {
  paneGridRefs.forEach((grid) => grid.disconnectAllPanes())
  Object.keys(paneMeta).forEach((key) => {
    delete paneMeta[key]
  })
}

function onKeydown(event: KeyboardEvent) {
  if (!(event.ctrlKey || event.metaKey)) return

  const key = event.key.toLowerCase()
  if (key === 'b') {
    event.preventDefault()
    toggleFilePanel()
    return
  }

  if (key === 'k') {
    event.preventDefault()
    openCommands()
    return
  }

  if (event.key === '\\') {
    event.preventDefault()
    handleSplit('vertical')
    return
  }

  if (event.shiftKey && key === 't') {
    event.preventDefault()
    toggleHostPicker()
  }
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown)
})

onActivated(async () => {
  try {
    const [assetRes, keysRes, pickerRes]: any[] = await Promise.all([
      getAsset(routeAssetId),
      getSSHKeys({ page_size: 100 }),
      getAssets({ ssh: 'ready', page_size: 200 }),
    ])

    sshKeys.value = keysRes.data.items || []
    pickerAssets.value = pickerRes.data.items || []

    const login = getInitialLoginState(assetRes.data, sshKeys.value)
    const primaryTab = workbench.tabs.find((tab) => tab.host.assetId === routeAssetId)
    if (primaryTab) {
      setTabHost(workbench, primaryTab.id, {
        assetId: routeAssetId,
        name: assetRes.data.name || '未知主机',
        ip: assetRes.data.ip_address || '',
        username: login.username,
        port: login.port,
        authMode: login.authMode,
      })
      if (primaryTab.title === 'Session 1' || primaryTab.title === '会话 1') {
        renameTab(workbench, primaryTab.id, assetRes.data.name || primaryTab.title)
      }
    }
  } catch {
    const primaryTab = workbench.tabs.find((tab) => tab.host.assetId === routeAssetId)
    if (primaryTab) {
      setTabHost(workbench, primaryTab.id, {
        assetId: routeAssetId,
        name: '未知主机',
        ip: '未知地址',
        username: 'root',
        port: 22,
        authMode: 'asset',
      })
    }
  }
})

onDeactivated(cleanup)
</script>

<style lang="scss" scoped>
.ssh-page {
  /* 设计令牌 (v2 · 深空 + 靛蓝) */
  --ssh-bg: #06070b;
  --ssh-bg-soft: #0a0c12;
  --ssh-glass: rgba(255, 255, 255, 0.03);
  --ssh-card: #0c0e15;
  --ssh-term-bg: #08090e;
  --ssh-line: rgba(255, 255, 255, 0.07);
  --ssh-line-2: rgba(255, 255, 255, 0.12);
  --ssh-t1: #eef1f8;
  --ssh-t2: #9aa3b5;
  --ssh-t3: #5c6577;
  --ssh-t4: #3a4152;
  --ssh-accent: #8b9dff;
  --ssh-accent-2: #a78bfa;
  --ssh-accent-bg: rgba(139, 157, 255, 0.13);
  --ssh-accent-glow: rgba(120, 140, 255, 0.22);
  --ssh-ok: #34d399;
  --ssh-ok-bg: rgba(52, 211, 153, 0.14);
  --ssh-warn: #fbbf24;
  --ssh-err: #f87171;
  --ssh-err-bg: rgba(248, 113, 113, 0.12);
  --ssh-mono: 'JetBrains Mono', 'Cascadia Code', ui-monospace, Menlo, Consolas, monospace;

  /* 旧 token 别名: 供 SFTP 面板 / 文件编辑弹窗沿用 */
  --ssh-panel: transparent;
  --ssh-border: var(--ssh-line);
  --ssh-border-strong: var(--ssh-line-2);
  --ssh-text: var(--ssh-t1);
  --ssh-muted: var(--ssh-t3);
  --ssh-faint: var(--ssh-t4);
  --ssh-hover: rgba(255, 255, 255, 0.05);
  --ssh-term: var(--ssh-term-bg);
  --ssh-accent-dim: var(--ssh-accent-bg);
  --ssh-danger: var(--ssh-err);
  --ssh-danger-dim: var(--ssh-err-bg);
  --ssh-ok-dim: var(--ssh-ok-bg);
  --ssh-warn-dim: rgba(251, 191, 36, 0.13);
  --ssh-font-mono: var(--ssh-mono);
  --ssh-font-ui: Inter, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', system-ui, sans-serif;

  display: flex;
  flex-direction: column;
  position: relative;
  height: calc(100vh - 56px);
  margin: -20px;
  overflow: hidden;
  color: var(--ssh-t1);
  background:
    radial-gradient(1200px 500px at 70% -10%, rgba(120, 130, 255, 0.1), transparent 60%),
    radial-gradient(900px 400px at 10% 110%, rgba(52, 211, 153, 0.05), transparent 60%),
    var(--ssh-bg);
  font-family: var(--ssh-font-ui);
  font-size: 13px;
}

.workbench {
  display: flex;
  flex: 1;
  min-height: 0;
}

.stage {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding: 14px;
}

:deep(.el-loading-mask) {
  background: rgba(6, 7, 11, 0.72);
}

:deep(.el-loading-spinner .circular circle) {
  stroke: var(--ssh-accent);
}

@media (max-width: 900px) {
  .ssh-page {
    height: calc(100vh - 48px);
  }

  .stage {
    padding: 10px;
  }
}
</style>
