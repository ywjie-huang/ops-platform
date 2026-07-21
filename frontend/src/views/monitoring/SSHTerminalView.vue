<template>
  <div class="ssh-page" :class="{ 'right-panel-open': workbench.rightPanelOpen }">
    <SSHTerminalToolbar
      :host-name="hostName"
      :host-ip="hostIp"
      :connected="activePaneMeta.connected"
      :font-size="activePaneMeta.fontSize"
      :show-file-panel="workbench.rightPanelOpen"
      :can-split="canSplit"
      @change-font-size="activePaneGrid?.changeActivePaneFontSize($event)"
      @toggle-fullscreen="toggleFullscreen"
      @split-vertical="handleSplit('vertical')"
      @split-horizontal="handleSplit('horizontal')"
      @toggle-file-panel="toggleFilePanel"
      @disconnect="activePaneGrid?.disconnectActivePane()"
      @reconnect="activePaneGrid?.reconnectActivePane()"
    >
      <template #tabs>
        <SSHTabBar
          :tabs="workbench.tabs"
          :active-tab-id="workbench.activeTabId"
          @add-tab="handleAddTab"
          @activate-tab="handleActivateTab"
          @close-tab="handleCloseTab"
          @rename-tab="handleRenameTab"
        />
      </template>
    </SSHTerminalToolbar>

    <div class="ssh-body">
      <SSHLeftRail @select="handleRailSelect" />

      <div class="terminal-area">
        <SSHPaneGrid
          v-for="tab in workbench.tabs"
          v-show="tab.id === workbench.activeTabId"
          :key="tab.id"
          :ref="(instance) => setPaneGridRef(tab.id, instance)"
          :class="{ 'is-hidden': tab.id !== workbench.activeTabId }"
          :tab="tab"
          :visible="tab.id === workbench.activeTabId"
          :active-pane-id="tab.id === workbench.activeTabId ? workbench.activePaneId : ''"
          :asset-id="assetId"
          :host-ip="hostIp"
          :ssh-keys="sshKeys"
          :initial-login-state="initialLoginState"
          @activate-pane="handleActivatePane(tab.id, $event)"
          @close-pane="handleClosePane(tab.id, $event)"
          @pane-status-change="handlePaneStatusChange"
          @pane-meta-change="handlePaneMetaChange"
          @pane-key-change="handlePaneKeyChange"
        />

        <SSHStatusBar
          :host-ip="hostIp"
          :pane="activePaneForStatus"
          :layout-label="layoutText"
          :terminal-size="activePaneMeta.terminalSize"
          :connection-time="activePaneMeta.connectionTime"
          :login-username="activePaneMeta.loginUsername"
          :login-port="activePaneMeta.loginPort"
        />
      </div>

      <SSHRightPanel
        ref="rightPanelRef"
        v-model:open="workbench.rightPanelOpen"
        :active-tab="workbench.rightPanelTab"
        :connected="activePaneMeta.connected"
        :asset-id="assetId"
        :current-key-id="activePaneMeta.currentKeyId"
        :active-pane="activePane"
        :active-pane-meta="activePaneMeta"
        @change-tab="handleRightPanelTabChange"
        @refit-terminal="handleRefitTerminal"
        @edit-file="openEditDialog"
        @path-change="handlePathChange"
      />
    </div>

    <FileEditDialog
      v-model:visible="editDialogVisible"
      :file-path="editFilePath"
      :asset-id="assetId"
      :current-key-id="activePaneMeta.currentKeyId"
      @saved="rightPanelRef?.navigateTo(rightPanelRef?.currentPath || '/')"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onActivated, onDeactivated, onMounted, onUnmounted, reactive, ref, type ComponentPublicInstance } from 'vue'
import { useRoute } from 'vue-router'
import { getAsset } from '@/api/assets'
import { getSSHKeys } from '@/api/sshKeys'
import FileEditDialog from './ssh/FileEditDialog.vue'
import SSHLeftRail from './ssh/SSHLeftRail.vue'
import SSHPaneGrid from './ssh/SSHPaneGrid.vue'
import type { SSHPaneMeta } from './ssh/SSHPane.vue'
import SSHTabBar from './ssh/SSHTabBar.vue'
import SSHRightPanel from './ssh/SSHRightPanel.vue'
import SSHStatusBar from './ssh/SSHStatusBar.vue'
import SSHTerminalToolbar from './ssh/SSHTerminalToolbar.vue'
import { getInitialLoginState, type LoginFormState } from './ssh/sshConnection'
import type { SSHConnectionStatus, SSHPaneLayout, SSHRightPanelTab } from './ssh/types'
import {
  addTab,
  closePane,
  createInitialWorkbenchState,
  removeTab,
  renameTab,
  setActivePane,
  splitActiveTab,
  updatePaneMeta,
} from './ssh/useSSHWorkbench'

const route = useRoute()

const rightPanelRef = ref<InstanceType<typeof SSHRightPanel>>()
type SSHPaneGridPublic = InstanceType<typeof SSHPaneGrid>

const hostName = ref('')
const hostIp = ref('')
const sshKeys = ref<any[]>([])
const editDialogVisible = ref(false)
const editFilePath = ref('')
const initialLoginState = ref<LoginFormState | null>(null)
const paneMeta = reactive<Record<string, SSHPaneMeta>>({})
const workbench = reactive(createInitialWorkbenchState())
const paneGridRefs = reactive(new Map<string, SSHPaneGridPublic>())

const assetId = computed(() => Number(route.params.id))
const activeTab = computed(() => workbench.tabs.find((tab) => tab.id === workbench.activeTabId))
const activePane = computed(() => activeTab.value?.panes.find((item) => item.id === workbench.activePaneId))
const activePaneForStatus = computed(() => activePane.value ?? workbench.tabs[0].panes[0])
const activePaneGrid = computed(() => paneGridRefs.get(workbench.activeTabId))
const canSplit = computed(() => activeTab.value?.layout === 'single')
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
    loginUsername: initialLoginState.value?.username ?? 'root',
    loginPort: initialLoginState.value?.port ?? 22,
    terminalSize: '',
    connectionTime: '',
  }
})
const layoutText = computed(() => {
  if (activeTab.value?.layout === 'vertical') return 'vertical'
  if (activeTab.value?.layout === 'horizontal') return 'horizontal'
  return 'single'
})

function toggleFullscreen() {
  const page = document.querySelector('.ssh-page')
  if (!page) {
    return
  }

  if (document.fullscreenElement) {
    document.exitFullscreen()
  } else {
    page.requestFullscreen()
  }
}

function handleAddTab() {
  addTab(workbench, `Session ${workbench.tabs.length + 1}`)
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
  if (!targetTab) {
    return
  }

  workbench.activeTabId = targetTab.id
  workbench.activePaneId = targetTab.panes[0].id
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

function handleSplit(layout: Exclude<SSHPaneLayout, 'single'>) {
  if (!canSplit.value) {
    return
  }

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
  if (workbench.activeTabId !== tabId) {
    return
  }

  closePane(workbench, paneId)
  delete paneMeta[paneId]
  nextTick(() => activePaneGrid.value?.refitActivePane())
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
  if (!paneExists) {
    return
  }

  paneMeta[paneId] = meta
  updatePaneMeta(workbench, paneId, {
    authMode: meta.authMode,
    connectionSeconds: meta.connectionSeconds,
    currentPath: meta.currentPath,
    lastError: meta.lastError,
  })
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

function toggleFilePanel() {
  workbench.rightPanelOpen = !workbench.rightPanelOpen
  if (workbench.rightPanelOpen && activePaneMeta.value.connected) {
    nextTick(() => rightPanelRef.value?.navigateTo(rightPanelRef.value?.currentPath || '/'))
  }

  handleRefitTerminal()
}

function handleRightPanelTabChange(tab: SSHRightPanelTab) {
  workbench.rightPanelTab = tab
  if (tab === 'files' && workbench.rightPanelOpen && activePaneMeta.value.connected) {
    nextTick(() => rightPanelRef.value?.navigateTo(rightPanelRef.value?.currentPath || '/'))
  }
}

function openEditDialog(path: string) {
  editFilePath.value = path
  editDialogVisible.value = true
}

function handleRailSelect(key: 'sessions' | 'snippets' | 'paths') {
  if (key === 'paths') {
    workbench.rightPanelOpen = true
    workbench.rightPanelTab = 'files'
    handleRefitTerminal()
    return
  }

  if (key === 'snippets') {
    workbench.rightPanelOpen = true
    workbench.rightPanelTab = 'actions'
    handleRefitTerminal()
  }
}

function cleanup() {
  paneGridRefs.forEach((grid) => grid.disconnectAllPanes())
  Object.keys(paneMeta).forEach((key) => {
    delete paneMeta[key]
  })
}

function onKeydown(event: KeyboardEvent) {
  if (!(event.ctrlKey || event.metaKey)) {
    return
  }

  const key = event.key.toLowerCase()
  if (key === 'b') {
    event.preventDefault()
    toggleFilePanel()
    return
  }

  if (event.key === '\\') {
    event.preventDefault()
    handleSplit('vertical')
    return
  }

  if (event.shiftKey && key === 't') {
    event.preventDefault()
    handleAddTab()
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
    const [assetRes, keysRes]: any[] = await Promise.all([
      getAsset(assetId.value),
      getSSHKeys({ page_size: 100 }),
    ])

    hostName.value = assetRes.data.name
    hostIp.value = assetRes.data.ip_address
    sshKeys.value = keysRes.data.items || []
    initialLoginState.value = getInitialLoginState(assetRes.data, sshKeys.value)
  } catch {
    hostName.value = '未知主机'
    hostIp.value = '未知地址'
    initialLoginState.value = {
      authMode: 'asset',
      username: 'root',
      port: 22,
    }
  }
})

onDeactivated(cleanup)
</script>

<style lang="scss" scoped>
.ssh-page {
  --ssh-bg: #0b0f14;
  --ssh-panel: #0f141b;
  --ssh-surface: #141a22;
  --ssh-hover: #1a222d;
  --ssh-border: #1c2430;
  --ssh-border-strong: #2a3544;
  --ssh-text: #d8dee9;
  --ssh-muted: #6b7785;
  --ssh-faint: #3d4754;
  --ssh-accent: #5b9fd4;
  --ssh-accent-dim: rgba(91, 159, 212, 0.12);
  --ssh-ok: #3dd68c;
  --ssh-ok-dim: rgba(61, 214, 140, 0.12);
  --ssh-warn: #e0b44e;
  --ssh-warn-dim: rgba(224, 180, 78, 0.12);
  --ssh-danger: #e86c7a;
  --ssh-danger-dim: rgba(232, 108, 122, 0.12);
  --ssh-term: #0a0e12;
  --ssh-font-ui: Inter, "Segoe UI", "PingFang SC", "Microsoft YaHei", system-ui, sans-serif;
  --ssh-font-mono: "JetBrains Mono", "Cascadia Code", "SF Mono", "Fira Code", ui-monospace, monospace;

  display: flex;
  flex-direction: column;
  height: calc(100vh - 56px);
  margin: -20px;
  overflow: hidden;
  color: var(--ssh-text);
  background: var(--ssh-bg);
  font-family: var(--ssh-font-ui);
}

.ssh-body {
  display: grid;
  flex: 1;
  grid-template-columns: 48px minmax(0, 1fr);
  min-height: 0;
  background: var(--ssh-bg);
}

.ssh-page.right-panel-open .ssh-body {
  grid-template-columns: 48px minmax(0, 1fr) 320px;
}

.terminal-area {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  position: relative;
  background: var(--ssh-term);
}

:deep(.el-loading-mask) {
  background: rgba(8, 11, 15, 0.72);
}

:deep(.el-loading-spinner .circular circle) {
  stroke: var(--ssh-accent);
}

@media (max-width: 900px) {
  .ssh-page {
    height: calc(100vh - 48px);
  }

  .ssh-body,
  .ssh-page.right-panel-open .ssh-body {
    grid-template-columns: 48px minmax(0, 1fr);
  }
}
</style>
