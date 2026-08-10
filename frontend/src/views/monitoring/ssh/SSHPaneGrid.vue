<template>
  <div class="ssh-pane-grid" :class="`layout-${tab.layout}`">
    <SSHPane
      v-for="pane in tab.panes"
      :key="pane.id"
      :ref="(instance) => setPaneRef(pane.id, instance)"
      :pane="pane"
      :asset-id="assetId"
      :host-ip="hostIp"
      :host-name="hostName"
      :ssh-keys="sshKeys"
      :active="pane.id === activePaneId"
      :visible="visible"
      :can-close="tab.panes.length > 1"
      :can-split="tab.layout === 'single'"
      :dock-open="dockOpen"
      :initial-login-state="initialLoginState"
      @activate="$emit('activate-pane', $event)"
      @close="$emit('close-pane', $event)"
      @split="$emit('pane-split')"
      @toggle-dock="$emit('pane-toggle-dock')"
      @status-change="(paneId, status) => $emit('pane-status-change', paneId, status)"
      @meta-change="(paneId, meta) => $emit('pane-meta-change', paneId, meta)"
      @key-change="(paneId, keyId) => $emit('pane-key-change', paneId, keyId)"
    />
  </div>
</template>

<script setup lang="ts">
import { onBeforeUpdate, type ComponentPublicInstance } from 'vue'
import SSHPane, { type SSHPaneMeta } from './SSHPane.vue'
import type { LoginFormState } from './sshConnection'
import type { SSHConnectionStatus, SSHTabState } from './types'

const props = defineProps<{
  tab: SSHTabState
  activePaneId: string
  assetId: number
  hostIp: string
  hostName: string
  sshKeys: any[]
  initialLoginState: LoginFormState | null
  visible: boolean
  dockOpen: boolean
}>()

defineEmits<{
  'activate-pane': [paneId: string]
  'close-pane': [paneId: string]
  'pane-split': []
  'pane-toggle-dock': []
  'pane-status-change': [paneId: string, status: SSHConnectionStatus]
  'pane-meta-change': [paneId: string, meta: SSHPaneMeta]
  'pane-key-change': [paneId: string, keyId: number | undefined]
}>()

type SSHPanePublic = InstanceType<typeof SSHPane>

const paneRefs = new Map<string, SSHPanePublic>()

onBeforeUpdate(() => {
  paneRefs.clear()
})

function setPaneRef(
  paneId: string,
  instance: Element | ComponentPublicInstance | SSHPanePublic | null,
) {
  const pane = instance as SSHPanePublic | null
  if (pane && typeof pane.getMeta === 'function') {
    paneRefs.set(paneId, pane)
  }
}

function getActivePane() {
  return paneRefs.get(props.activePaneId)
}

function copyActivePane() {
  getActivePane()?.copySelection()
}

function pasteActivePane() {
  getActivePane()?.pasteClipboard()
}

function clearActivePane() {
  getActivePane()?.clearTerminal()
}

function changeActivePaneFontSize(delta: number) {
  getActivePane()?.changeFontSize(delta)
}

function disconnectActivePane() {
  getActivePane()?.disconnect()
}

function disconnectAllPanes() {
  paneRefs.forEach((pane) => pane.disconnect())
}

function reconnectActivePane() {
  getActivePane()?.reconnect()
}

function refitActivePane() {
  getActivePane()?.refit()
}

function getActivePaneMeta() {
  return getActivePane()?.getMeta()
}

defineExpose({
  copyActivePane,
  pasteActivePane,
  clearActivePane,
  changeActivePaneFontSize,
  disconnectActivePane,
  disconnectAllPanes,
  reconnectActivePane,
  refitActivePane,
  getActivePaneMeta,
})
</script>

<style scoped lang="scss">
.ssh-pane-grid {
  flex: 1;
  display: grid;
  min-width: 0;
  min-height: 0;
  gap: 12px;
  padding: 0;
  background: transparent;
}

.is-hidden {
  display: none;
}

.layout-single {
  grid-template-columns: minmax(0, 1fr);
  grid-template-rows: minmax(0, 1fr);
}

.layout-vertical {
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  grid-template-rows: minmax(0, 1fr);
}

.layout-horizontal {
  grid-template-columns: minmax(0, 1fr);
  grid-template-rows: minmax(0, 1fr) minmax(0, 1fr);
}

@media (max-width: 768px) {
  .layout-vertical {
    grid-template-columns: minmax(0, 1fr);
    grid-template-rows: minmax(0, 1fr) minmax(0, 1fr);
  }
}
</style>
