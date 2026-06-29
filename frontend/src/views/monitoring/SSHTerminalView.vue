<template>
  <div class="ssh-page" :class="{ 'right-panel-open': workbench.rightPanelOpen }">
    <SSHTerminalToolbar
      :host-name="hostName"
      :host-ip="hostIp"
      :connected="activePaneMeta.connected"
      :font-size="activePaneMeta.fontSize"
      :show-file-panel="workbench.rightPanelOpen"
      :can-split="canSplit"
      @copy="activePaneGrid?.copyActivePane()"
      @paste="activePaneGrid?.pasteActivePane()"
      @clear="activePaneGrid?.clearActivePane()"
      @change-font-size="activePaneGrid?.changeActivePaneFontSize($event)"
      @toggle-fullscreen="toggleFullscreen"
      @split-vertical="handleSplit('vertical')"
      @split-horizontal="handleSplit('horizontal')"
      @toggle-file-panel="toggleFilePanel"
      @disconnect="activePaneGrid?.disconnectActivePane()"
      @reconnect="activePaneGrid?.reconnectActivePane()"
    />

    <div class="ssh-body">
      <div class="terminal-area">
        <SSHTabBar
          :tabs="workbench.tabs"
          :active-tab-id="workbench.activeTabId"
          @add-tab="handleAddTab"
          @activate-tab="handleActivateTab"
          @close-tab="handleCloseTab"
          @rename-tab="handleRenameTab"
        />

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
import { computed, nextTick, onActivated, onDeactivated, reactive, ref, type ComponentPublicInstance } from 'vue'
import { useRoute } from 'vue-router'
import { getAsset } from '@/api/assets'
import { getSSHKeys } from '@/api/sshKeys'
import FileEditDialog from './ssh/FileEditDialog.vue'
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
  if (activeTab.value?.layout === 'vertical') return '左右分屏'
  if (activeTab.value?.layout === 'horizontal') return '上下分屏'
  return '单终端'
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

function cleanup() {
  paneGridRefs.forEach((grid) => grid.disconnectAllPanes())
  Object.keys(paneMeta).forEach((key) => {
    delete paneMeta[key]
  })
}

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
  --ssh-bg: #0d111c;
  --ssh-shell: #121725;
  --ssh-surface: #171c2c;
  --ssh-surface-strong: #1d2436;
  --ssh-border: #303a5c;
  --ssh-border-soft: #232b45;
  --ssh-text: #d7def7;
  --ssh-muted: #7f8aaa;
  --ssh-accent: #6ea8fe;
  --ssh-success: #4ade80;
  --ssh-warning: #f6c177;
  --ssh-danger: #ff7b93;

  display: flex;
  flex-direction: column;
  height: calc(100vh - 56px);
  margin: -20px;
  padding: 10px;
  background:
    linear-gradient(180deg, rgb(19 25 41 / 96%), rgb(11 15 25 / 98%)),
    var(--ssh-bg);
  border-radius: 0;
  overflow: hidden;
}

.ssh-body {
  flex: 1;
  display: flex;
  gap: 10px;
  min-height: 0;
  padding-top: 10px;
}

.terminal-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  position: relative;
  overflow: hidden;
  background: var(--ssh-shell);
  border: 1px solid var(--ssh-border-soft);
  border-radius: 8px;
  box-shadow: 0 8px 24px rgb(0 0 0 / 18%);
}

:deep(.el-loading-mask) {
  background: rgb(26 27 38 / 70%);
}

:deep(.el-loading-spinner .circular circle) {
  stroke: #7aa2f7;
}

@media (max-width: 900px) {
  .ssh-page {
    height: calc(100vh - 48px);
    padding: 7px;
  }

  .ssh-body {
    flex-direction: column;
    gap: 7px;
    padding-top: 7px;
  }
}
</style>
