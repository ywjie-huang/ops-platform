<template>
  <aside v-if="open" class="dock" aria-label="SSH 协作面板">
    <div class="dock-tabs" role="tablist">
      <button
        v-for="tab in tabs"
        :key="tab.value"
        type="button"
        role="tab"
        class="dock-tab"
        :class="{ active: activeTab === tab.value }"
        :aria-selected="activeTab === tab.value"
        @click="$emit('change-tab', tab.value)"
      >
        <svg v-if="tab.value === 'files'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z"/></svg>
        <svg v-else-if="tab.value === 'actions'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M13 2L3 14h7l-1 8 10-12h-7z"/></svg>
        <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M12 16v-5M12 8h.01"/></svg>
        {{ tab.label }}
      </button>
      <button type="button" class="dock-close" title="关闭面板" aria-label="关闭面板" @click="closePanel">×</button>
    </div>

    <div class="dock-body" role="tabpanel">
      <SFTPFilePanel
        v-if="activeTab === 'files'"
        ref="sftpPanelRef"
        :connected="connected"
        :asset-id="assetId"
        :current-key-id="currentKeyId"
        @edit-file="$emit('edit-file', $event)"
        @path-change="$emit('path-change', $event)"
      />

      <div v-else-if="activeTab === 'actions'" class="empty-pane">
        <div class="empty-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M13 2L3 14h7l-1 8 10-12h-7z"/></svg>
        </div>
        <p class="empty-title">暂无收藏命令</p>
        <p class="empty-desc">常用命令可收藏在此处，一键发送到当前终端，后续版本开放。</p>
      </div>

      <div v-else class="info-pane">
        <div class="info-row"><span class="ik">活动窗格</span><span class="iv">{{ activePaneTitle }}</span></div>
        <div class="info-row"><span class="ik">登录用户</span><span class="iv">{{ activePaneMeta.loginUsername }}:{{ activePaneMeta.loginPort }}</span></div>
        <div class="info-row"><span class="ik">认证方式</span><span class="iv">{{ credentialLabel }}</span></div>
        <div class="info-row"><span class="ik">终端尺寸</span><span class="iv">{{ activePaneMeta.terminalSize || '-' }}</span></div>
        <div class="info-row"><span class="ik">连接时长</span><span class="iv">{{ activePaneMeta.connectionTime || '-' }}</span></div>
        <div class="info-row"><span class="ik">当前路径</span><span class="iv">{{ activePane?.currentPath || '/' }}</span></div>
        <div v-if="activePaneMeta.lastError" class="info-row err">
          <span class="ik">最近错误</span><span class="iv">{{ activePaneMeta.lastError }}</span>
        </div>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import SFTPFilePanel from './SFTPFilePanel.vue'
import type { SSHPaneMeta } from './SSHPane.vue'
import type { SSHPaneState, SSHRightPanelTab } from './types'

const props = defineProps<{
  open: boolean
  activeTab: SSHRightPanelTab
  connected: boolean
  assetId: number
  currentKeyId: number | undefined
  sshKeys: any[]
  activePane?: SSHPaneState
  activePaneMeta: SSHPaneMeta
}>()

const emit = defineEmits<{
  'update:open': [value: boolean]
  'change-tab': [tab: SSHRightPanelTab]
  'edit-file': [path: string]
  'path-change': [path: string]
  'refit-terminal': []
}>()

const sftpPanelRef = ref<InstanceType<typeof SFTPFilePanel>>()

const tabs: Array<{ value: SSHRightPanelTab; label: string }> = [
  { value: 'files', label: '文件' },
  { value: 'actions', label: '命令' },
  { value: 'info', label: '信息' },
]

const activePaneTitle = computed(() => props.activePane?.title || props.activePane?.id || '未选择')
const currentPath = computed(() => sftpPanelRef.value?.currentPath || '/')

const credentialLabel = computed(() => {
  if (!props.currentKeyId) return '资产凭据'
  const key = props.sshKeys.find((item) => item.id === props.currentKeyId)
  return key ? key.name : `密钥 #${props.currentKeyId}`
})

function closePanel() {
  emit('update:open', false)
  emit('refit-terminal')
}

function navigateTo(path: string) {
  return sftpPanelRef.value?.navigateTo(path)
}

defineExpose({ navigateTo, currentPath })
</script>

<style scoped lang="scss">
.dock {
  width: 330px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  margin: 14px 14px 14px 0;
  border-radius: 14px;
  background: var(--ssh-card);
  box-shadow: inset 0 0 0 1px var(--ssh-line), 0 10px 34px rgba(0, 0, 0, 0.35);
  overflow: hidden;
  min-height: 0;
}
.dock-tabs {
  display: flex;
  gap: 4px;
  padding: 10px 12px 0;
  flex-shrink: 0;
}
.dock-tab {
  flex: 1;
  height: 32px;
  border-radius: 9px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  border: none;
  background: transparent;
  color: var(--ssh-t3);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  font-family: inherit;
  svg { width: 13px; height: 13px; }
  &:hover { color: var(--ssh-t2); }
  &.active {
    color: var(--ssh-t1);
    background: var(--ssh-glass);
    box-shadow: inset 0 0 0 1px var(--ssh-line-2);
  }
}
.dock-close {
  width: 32px;
  height: 32px;
  border-radius: 9px;
  border: none;
  background: transparent;
  color: var(--ssh-t4);
  font-size: 14px;
  cursor: pointer;
  flex-shrink: 0;
  &:hover { background: var(--ssh-glass); color: var(--ssh-t1); }
}
.dock-body {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  margin-top: 10px;
}
.empty-pane {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 24px;
  text-align: center;
}
.empty-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--ssh-accent);
  background: var(--ssh-accent-bg);
  margin-bottom: 6px;
  svg { width: 20px; height: 20px; }
}
.empty-title { font-size: 13px; font-weight: 600; color: var(--ssh-t1); }
.empty-desc { font-size: 11.5px; color: var(--ssh-t3); line-height: 1.7; max-width: 220px; }
.info-pane {
  padding: 4px 14px;
  overflow-y: auto;
  &::-webkit-scrollbar { width: 6px; }
  &::-webkit-scrollbar-thumb { background: var(--ssh-line-2); border-radius: 3px; }
}
.info-row {
  display: flex;
  align-items: baseline;
  gap: 10px;
  padding: 9px 2px;
  border-bottom: 1px solid var(--ssh-line);
  &:last-child { border-bottom: none; }
  &.err .iv { color: var(--ssh-err); }
}
.ik {
  width: 64px;
  flex-shrink: 0;
  font-size: 11px;
  color: var(--ssh-t4);
}
.iv {
  flex: 1;
  min-width: 0;
  font-family: var(--ssh-mono);
  font-size: 12px;
  color: var(--ssh-t1);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* SFTP 面板融入 dock 的深色风格 */
.dock-body :deep(.file-panel) { background: transparent; }
.dock-body :deep(.file-path-bar),
.dock-body :deep(.file-shortcuts),
.dock-body :deep(.file-actions) { border-bottom-color: var(--ssh-line); }
.dock-body :deep(.file-path-bar .el-input__wrapper) {
  border-radius: 9px;
  background: var(--ssh-glass);
  border: none;
  box-shadow: inset 0 0 0 1px var(--ssh-line);
}
.dock-body :deep(.file-item) { border-radius: 8px; margin: 0 6px; border-left: none; }
.dock-body :deep(.file-actions .el-button) { border-radius: 8px; }

@media (max-width: 960px) {
  .dock { width: 280px; }
}
</style>
