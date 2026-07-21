<template>
  <aside v-if="open" class="ssh-right-panel" aria-label="SSH 协作面板">
    <nav class="right-panel-tabs" aria-label="协作面板标签" role="tablist">
      <button
        v-for="tab in tabs"
        :key="tab.value"
        type="button"
        role="tab"
        class="right-panel-tab"
        :class="{ active: activeTab === tab.value }"
        :aria-selected="activeTab === tab.value"
        :tabindex="activeTab === tab.value ? 0 : -1"
        @click="$emit('change-tab', tab.value)"
      >
        {{ tab.label }}
      </button>
      <button type="button" class="collab-close" aria-label="关闭协作面板" title="关闭" @click="closePanel">
        ×
      </button>
    </nav>

    <section class="right-panel-content" role="tabpanel">
      <SFTPFilePanel
        v-if="activeTab === 'files'"
        ref="sftpPanelRef"
        :connected="connected"
        :asset-id="assetId"
        :current-key-id="currentKeyId"
        @edit-file="$emit('edit-file', $event)"
        @path-change="$emit('path-change', $event)"
      />

      <div v-else-if="activeTab === 'preview'" class="placeholder-panel">
        <h4>文件预览</h4>
        <p>当前仍用编辑弹窗处理文本文件。这里预留给后续侧栏预览/编辑。</p>
        <dl>
          <div>
            <dt>当前目录</dt>
            <dd>{{ currentPath || '/' }}</dd>
          </div>
          <div>
            <dt>活动 Pane</dt>
            <dd>{{ activePaneTitle }}</dd>
          </div>
        </dl>
      </div>

      <div v-else-if="activeTab === 'actions'" class="placeholder-panel">
        <h4>快捷动作</h4>
        <p>收藏命令与审批动作尚未接入。当前只展示会话摘要。</p>
        <dl>
          <div>
            <dt>连接状态</dt>
            <dd>{{ connected ? '已连接' : '未连接' }}</dd>
          </div>
          <div>
            <dt>认证</dt>
            <dd>{{ currentKeyId ?? '资产凭据' }}</dd>
          </div>
        </dl>
      </div>

      <div v-else class="placeholder-panel">
        <h4>会话信息</h4>
        <dl>
          <div>
            <dt>活动 Pane</dt>
            <dd>{{ activePaneTitle }}</dd>
          </div>
          <div>
            <dt>登录用户</dt>
            <dd>{{ activePaneMeta.loginUsername }}:{{ activePaneMeta.loginPort }}</dd>
          </div>
          <div>
            <dt>终端尺寸</dt>
            <dd>{{ activePaneMeta.terminalSize || '-' }}</dd>
          </div>
          <div>
            <dt>连接时长</dt>
            <dd>{{ activePaneMeta.connectionTime || '-' }}</dd>
          </div>
          <div>
            <dt>当前路径</dt>
            <dd>{{ activePane?.currentPath || '/' }}</dd>
          </div>
        </dl>
      </div>
    </section>
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
  { value: 'files', label: 'Files' },
  { value: 'preview', label: 'Editor' },
  { value: 'actions', label: 'Actions' },
  { value: 'info', label: 'Session' },
]

const activePaneTitle = computed(() => props.activePane?.title || props.activePane?.id || '未选择')
const currentPath = computed(() => sftpPanelRef.value?.currentPath || '/')

function closePanel() {
  emit('update:open', false)
  emit('refit-terminal')
}

function navigateTo(path: string) {
  return sftpPanelRef.value?.navigateTo(path)
}

defineExpose({ navigateTo, currentPath })
</script>

<style lang="scss" scoped>
.ssh-right-panel {
  display: flex;
  flex: 0 0 320px;
  flex-direction: column;
  width: 320px;
  min-width: 280px;
  max-width: 360px;
  min-height: 0;
  overflow: hidden;
  background: var(--ssh-panel);
  border-left: 1px solid var(--ssh-border);
}

.right-panel-tabs {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr)) 28px;
  align-items: stretch;
  min-height: 34px;
  border-bottom: 1px solid var(--ssh-border);
}

.right-panel-tab,
.collab-close {
  border: 0;
  background: transparent;
  color: var(--ssh-muted);
  cursor: pointer;
  font: inherit;
}

.right-panel-tab {
  min-width: 0;
  border-bottom: 2px solid transparent;
  font-size: 12px;

  &:hover {
    color: var(--ssh-text);
    background: var(--ssh-hover);
  }

  &.active {
    color: var(--ssh-text);
    border-bottom-color: var(--ssh-accent);
    background: rgba(91, 159, 212, 0.05);
  }

  &:focus-visible {
    outline: 1px solid var(--ssh-accent);
    outline-offset: -1px;
  }
}

.collab-close {
  border-left: 1px solid var(--ssh-border);
  font-size: 14px;

  &:hover {
    color: var(--ssh-text);
    background: var(--ssh-hover);
  }
}

.right-panel-content {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.placeholder-panel {
  padding: 12px;
  color: var(--ssh-muted);
  font-size: 12.5px;

  h4 {
    margin: 0 0 8px;
    color: var(--ssh-text);
    font-size: 13px;
  }

  p {
    margin: 0 0 14px;
    line-height: 1.55;
  }

  dl {
    display: grid;
    gap: 0;
    margin: 0;
  }

  div {
    display: grid;
    grid-template-columns: 72px minmax(0, 1fr);
    gap: 8px;
    padding: 8px 0;
    border-bottom: 1px solid var(--ssh-border);
  }

  dt {
    color: var(--ssh-faint);
    font-size: 11px;
  }

  dd {
    min-width: 0;
    margin: 0;
    overflow: hidden;
    color: var(--ssh-text);
    font-family: var(--ssh-font-mono);
    font-size: 12px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

@media (max-width: 960px) {
  .ssh-right-panel {
    flex-basis: 260px;
    width: 260px;
    min-width: 0;
  }
}

@media (max-width: 900px) {
  .ssh-right-panel {
    flex: 0 0 220px;
    width: 100%;
    max-width: none;
    border-left: 0;
    border-top: 1px solid var(--ssh-border);
  }
}
</style>
