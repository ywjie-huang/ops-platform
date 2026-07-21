<template>
  <header class="ssh-toolbar">
    <div class="toolbar-left">
      <button type="button" class="icon-btn" aria-label="返回" title="返回" @click="$router.back()">
        <el-icon><ArrowLeft /></el-icon>
      </button>
      <div class="host-block">
        <span :class="['status-dot', connected ? 'is-ok' : 'is-idle']" />
        <strong class="host-name">{{ hostName || '未知主机' }}</strong>
        <span class="host-ip">{{ hostIp }}</span>
      </div>
      <span class="sep" />
    </div>

    <div class="toolbar-center">
      <slot name="tabs" />
    </div>

    <div class="toolbar-right">
      <button
        type="button"
        class="icon-btn"
        title="左右分屏"
        aria-label="左右分屏"
        :disabled="!canSplit"
        @click="$emit('split-vertical')"
      >
        <el-icon><DCaret /></el-icon>
      </button>
      <button
        type="button"
        class="icon-btn rotate"
        title="上下分屏"
        aria-label="上下分屏"
        :disabled="!canSplit"
        @click="$emit('split-horizontal')"
      >
        <el-icon><DCaret /></el-icon>
      </button>
      <span class="sep" />
      <button type="button" class="icon-btn font-btn" title="缩小字体" aria-label="缩小字体" @click="$emit('change-font-size', -1)">
        A-
      </button>
      <button type="button" class="icon-btn font-btn large" title="放大字体" aria-label="放大字体" @click="$emit('change-font-size', 1)">
        A+
      </button>
      <span class="sep" />
      <button
        type="button"
        class="icon-btn"
        :class="{ active: showFilePanel }"
        title="文件面板"
        aria-label="文件面板"
        @click="$emit('toggle-file-panel')"
      >
        <el-icon><FolderOpened /></el-icon>
      </button>
      <button type="button" class="icon-btn" title="全屏" aria-label="全屏" @click="$emit('toggle-fullscreen')">
        <el-icon><FullScreen /></el-icon>
      </button>
      <span class="sep" />
      <button
        v-if="connected"
        type="button"
        class="icon-btn danger"
        title="断开连接"
        aria-label="断开连接"
        @click="$emit('disconnect')"
      >
        <el-icon><SwitchButton /></el-icon>
      </button>
      <button
        v-else
        type="button"
        class="icon-btn ok"
        title="重新连接"
        aria-label="重新连接"
        @click="$emit('reconnect')"
      >
        <el-icon><RefreshRight /></el-icon>
      </button>
    </div>
  </header>
</template>

<script setup lang="ts">
import {
  ArrowLeft,
  DCaret,
  FolderOpened,
  FullScreen,
  RefreshRight,
  SwitchButton,
} from '@element-plus/icons-vue'

defineProps<{
  hostName: string
  hostIp: string
  connected: boolean
  fontSize: number
  showFilePanel: boolean
  canSplit: boolean
}>()

defineEmits<{
  'change-font-size': [delta: number]
  'toggle-fullscreen': []
  'split-vertical': []
  'split-horizontal': []
  'toggle-file-panel': []
  disconnect: []
  reconnect: []
}>()
</script>

<style lang="scss" scoped>
.ssh-toolbar {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 8px;
  height: 36px;
  padding: 0 8px 0 6px;
  background: var(--ssh-panel);
  border-bottom: 1px solid var(--ssh-border);
  user-select: none;
}

.toolbar-left,
.toolbar-right,
.toolbar-center {
  display: flex;
  align-items: center;
  min-width: 0;
}

.toolbar-left {
  gap: 6px;
}

.toolbar-right {
  gap: 2px;
  justify-content: flex-end;
}

.toolbar-center {
  overflow: hidden;
}

.icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  padding: 0;
  color: var(--ssh-muted);
  background: transparent;
  border: 0;
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.12s ease, color 0.12s ease;

  &:hover:not(:disabled) {
    color: var(--ssh-text);
    background: var(--ssh-hover);
  }

  &:disabled {
    opacity: 0.35;
    cursor: not-allowed;
  }

  &.active {
    color: var(--ssh-accent);
    background: var(--ssh-accent-dim);
  }

  &.danger:hover:not(:disabled) {
    color: var(--ssh-danger);
    background: var(--ssh-danger-dim);
  }

  &.ok {
    color: var(--ssh-ok);
  }

  &.rotate .el-icon {
    transform: rotate(90deg);
  }

  &:focus-visible {
    outline: 1px solid var(--ssh-accent);
    outline-offset: 1px;
  }
}

.font-btn {
  font-size: 11px;
  font-weight: 700;

  &.large {
    font-size: 13px;
  }
}

.sep {
  width: 1px;
  height: 16px;
  margin: 0 4px;
  background: var(--ssh-border);
}

.host-block {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.status-dot {
  width: 7px;
  height: 7px;
  flex: 0 0 auto;
  border-radius: 50%;
  background: var(--ssh-faint);

  &.is-ok {
    background: var(--ssh-ok);
    box-shadow: 0 0 0 3px var(--ssh-ok-dim);
  }
}

.host-name {
  overflow: hidden;
  max-width: 140px;
  color: var(--ssh-text);
  font-size: 12.5px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.host-ip {
  color: var(--ssh-muted);
  font-family: var(--ssh-font-mono);
  font-size: 11px;
  white-space: nowrap;
}

@media (max-width: 900px) {
  .host-ip {
    display: none;
  }

  .host-name {
    max-width: 96px;
  }
}
</style>
