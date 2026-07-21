<template>
  <footer class="ssh-status-bar" aria-label="SSH 会话状态">
    <span class="item" :class="statusClass">{{ statusLabel }}</span>
    <span class="item">{{ loginUsername }}@{{ loginPort }}</span>
    <span class="item">{{ authLabel }}</span>
    <span class="item">{{ terminalSize || '-' }}</span>
    <span class="item">{{ connectionLabel }}</span>
    <span class="item path">{{ pane.currentPath || '/' }}</span>
    <span class="item">{{ layoutLabel }}</span>
    <span v-if="pane.dirtyFilePath" class="item warn">未保存 {{ pane.dirtyFilePath }}</span>
    <span v-else-if="pane.lastError" class="item err">{{ pane.lastError }}</span>
    <span class="spacer" />
    <span class="hint">Ctrl+B 文件 · Ctrl+\ 分屏 · Ctrl+Shift+T 新会话</span>
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
  if (props.pane.status === 'connected') return '● connected'
  if (props.pane.status === 'connecting') return '● connecting'
  if (props.pane.status === 'error') return '● error'
  if (props.pane.status === 'disconnected') return '● disconnected'
  return '● idle'
})

const statusClass = computed(() => {
  if (props.pane.status === 'connected') return 'ok'
  if (props.pane.status === 'connecting') return 'warn'
  if (props.pane.status === 'error' || props.pane.status === 'disconnected') return 'err'
  return ''
})

const authLabel = computed(() => {
  const mode = props.pane.authMode || 'asset'
  if (mode === 'asset') return 'asset'
  if (String(mode).startsWith('key-')) return 'key'
  return String(mode)
})

const connectionLabel = computed(() => {
  if (props.connectionTime) return props.connectionTime
  return `${props.pane.connectionSeconds}s`
})
</script>

<style scoped lang="scss">
.ssh-status-bar {
  display: flex;
  align-items: center;
  height: 26px;
  padding: 0 10px;
  overflow: hidden;
  color: var(--ssh-muted);
  background: var(--ssh-panel);
  border-top: 1px solid var(--ssh-border);
  font-family: var(--ssh-font-mono);
  font-size: 11px;
  user-select: none;
}

.item {
  display: inline-flex;
  align-items: center;
  white-space: nowrap;
}

.item + .item::before {
  content: '·';
  margin: 0 8px;
  color: var(--ssh-faint);
}

.item.ok { color: var(--ssh-ok); }
.item.warn { color: var(--ssh-warn); }
.item.err { color: var(--ssh-danger); }
.item.path { color: var(--ssh-text); }

.spacer { flex: 1; }

.hint {
  color: var(--ssh-faint);
  font-family: var(--ssh-font-ui);
  font-size: 11px;
}

@media (max-width: 900px) {
  .hint { display: none; }
  .item.path { max-width: 120px; overflow: hidden; text-overflow: ellipsis; }
}
</style>
