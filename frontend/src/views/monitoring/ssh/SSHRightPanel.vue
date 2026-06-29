<template>
  <aside v-if="open" class="ssh-right-panel" aria-label="SSH 协作面板">
    <header class="right-panel-header">
      <div>
        <p class="panel-kicker">协作面板</p>
        <h3>{{ activePaneMeta.connected ? '当前会话' : '等待连接' }}</h3>
      </div>
      <el-button text size="small" aria-label="关闭协作面板" @click="closePanel">
        <el-icon><Close /></el-icon>
      </el-button>
    </header>

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
        <el-icon>
          <component :is="tab.icon" />
        </el-icon>
        <span>{{ tab.label }}</span>
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
        <p>从文件管理中打开文本文件后，当前版本仍使用编辑弹窗处理内容。这里预留给后续只读预览区。</p>
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
        <h4>会话动作</h4>
        <p>批量命令、片段和审批动作尚未接入。当前面板只展示活动会话信息，避免误触真实操作。</p>
        <dl>
          <div>
            <dt>连接状态</dt>
            <dd>{{ connected ? '已连接' : '未连接' }}</dd>
          </div>
          <div>
            <dt>认证 Key</dt>
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
        </dl>
      </div>
    </section>
  </aside>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import {
  Close,
  Document,
  Files,
  InfoFilled,
  Operation,
} from '@element-plus/icons-vue'
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

const tabs: Array<{ value: SSHRightPanelTab; label: string; icon: any }> = [
  { value: 'files', label: 'Files', icon: Files },
  { value: 'preview', label: 'Preview', icon: Document },
  { value: 'actions', label: 'Actions', icon: Operation },
  { value: 'info', label: 'Info', icon: InfoFilled },
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
  flex: 0 0 clamp(280px, 30vw, 340px);
  flex-direction: column;
  min-width: 280px;
  max-width: 360px;
  min-height: 0;
  overflow: hidden;
  background: #151b2b;
  border: 1px solid #27304d;
  border-radius: 8px;
  box-shadow: 0 8px 24px rgb(0 0 0 / 18%);
}

.right-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px 9px;
  background: #1a2133;
  border-bottom: 1px solid #27304d;

  h3 {
    margin: 0;
    color: #e8edff;
    font-size: 14px;
    font-weight: 700;
  }

  .el-button {
    color: #a9b1d6;
  }
}

.panel-kicker {
  margin: 0 0 2px;
  color: #7f8aaa;
  font-size: 11px;
}

.right-panel-tabs {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 4px;
  padding: 6px;
  background: #121725;
  border-bottom: 1px solid #27304d;
}

.right-panel-tab {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  min-width: 0;
  height: 32px;
  padding: 0 6px;
  color: #aeb8d8;
  background: transparent;
  border: 0;
  border-radius: 6px;
  cursor: pointer;
  font: inherit;
  font-size: 12px;
  transition:
    background 0.15s ease-out,
    color 0.15s ease-out,
    border-color 0.15s ease-out;

  span {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  &:hover {
    color: #f4f7ff;
    background: #20283c;
  }

  &:focus-visible {
    outline: 2px solid #7aa2f7;
    outline-offset: -2px;
  }

  &.active {
    color: #f4f7ff;
    background: #263552;
  }
}

.right-panel-content {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.placeholder-panel {
  padding: 16px;
  color: #aeb8d8;

  h4 {
    margin: 0 0 8px;
    color: #e8edff;
    font-size: 14px;
  }

  p {
    max-width: 60ch;
    margin: 0 0 16px;
    color: #aeb8d8;
    font-size: 13px;
    line-height: 1.6;
  }

  dl {
    display: grid;
    gap: 10px;
    margin: 0;
  }

  div {
    display: grid;
    grid-template-columns: 72px minmax(0, 1fr);
    gap: 10px;
    align-items: baseline;
  }

  dt {
    color: #7f8aaa;
    font-size: 12px;
  }

  dd {
    min-width: 0;
    margin: 0;
    overflow: hidden;
    color: #e8edff;
    font-size: 13px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

@media (max-width: 960px) {
  .ssh-right-panel {
    flex: 0 0 230px;
    min-width: 0;
    max-width: none;
  }

  .right-panel-header {
    padding: 8px 10px;

    h3 {
      font-size: 13px;
    }
  }

  .right-panel-tabs {
    grid-template-columns: repeat(4, 34px);
    justify-content: start;
  }

  .right-panel-tab span {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip: rect(0 0 0 0);
    white-space: nowrap;
  }
}

@media (max-width: 900px) {
  .ssh-right-panel {
    flex: 0 0 210px;
    width: 100%;
  }

  .right-panel-content {
    overflow: auto;
  }
}

@media (prefers-reduced-motion: reduce) {
  .right-panel-tab {
    transition: none;
  }
}
</style>
