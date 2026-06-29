<template>
  <footer class="ssh-status-bar" aria-label="SSH 会话状态">
    <span class="status-item is-host">{{ hostIp || '-' }}</span>
    <span class="status-item" :class="`is-${pane.status}`">{{ statusLabel }}</span>
    <span class="status-item">{{ authLabel }}</span>
    <span class="status-item">{{ terminalSize || '-' }}</span>
    <span class="status-item">{{ connectionLabel }}</span>
    <span class="status-item">{{ layoutLabel }}</span>
    <span class="status-item is-path">{{ pane.currentPath || '/' }}</span>
    <span v-if="pane.dirtyFilePath" class="is-warning">未保存 {{ pane.dirtyFilePath }}</span>
    <span v-else-if="pane.lastError" class="is-danger">{{ pane.lastError }}</span>
  </footer>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { SSHPaneState } from './types'

const props = defineProps<{
  hostIp: string
  pane: SSHPaneState
  layoutLabel: string
  terminalSize: string
  connectionTime: string
  loginUsername: string
  loginPort: number
}>()

const statusLabel = computed(() => {
  if (props.pane.status === 'connected') return `${props.loginUsername}:${props.loginPort}`
  if (props.pane.status === 'connecting') return '连接中'
  if (props.pane.status === 'error') return '连接出错'
  if (props.pane.status === 'disconnected') return '已断开'
  return '未连接'
})

const authLabel = computed(() => props.pane.authMode || 'asset')
const connectionLabel = computed(() => props.connectionTime ? `已连接 ${props.connectionTime}` : `${props.pane.connectionSeconds}s`)
</script>

<style scoped lang="scss">
.ssh-status-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  min-height: 32px;
  padding: 5px 8px;
  color: #7f8aaa;
  background: #121725;
  border-top: 1px solid #27304d;
  font-size: 11px;
}

.status-item,
.is-warning {
  display: inline-flex;
  align-items: center;
  min-height: 20px;
  padding: 0 7px;
  background: #171d2f;
  border: 1px solid #26314f;
  border-radius: 999px;
  font-variant-numeric: tabular-nums;
}

.status-item.is-host {
  color: #d7def7;
}

.status-item.is-connected {
  color: #91f2b5;
  border-color: rgb(74 222 128 / 28%);
  background: rgb(74 222 128 / 9%);
}

.status-item.is-connecting {
  color: #f6c177;
  border-color: rgb(246 193 119 / 28%);
  background: rgb(246 193 119 / 9%);
}

.status-item.is-error {
  color: #ff9bad;
  border-color: rgb(255 123 147 / 28%);
  background: rgb(255 123 147 / 9%);
}

.status-item.is-path {
  max-width: 240px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.is-warning {
  color: #f6c177;
  border-color: rgb(246 193 119 / 28%);
  background: rgb(246 193 119 / 9%);
}

.is-danger {
  display: inline-flex;
  align-items: center;
  min-height: 20px;
  padding: 0 7px;
  color: #ff9bad;
  background: rgb(255 123 147 / 9%);
  border: 1px solid rgb(255 123 147 / 28%);
  border-radius: 999px;
}

@media (max-width: 768px) {
  .status-item.is-path {
    max-width: 140px;
  }
}
</style>
