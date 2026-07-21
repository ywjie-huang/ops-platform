<template>
  <aside class="ssh-left-rail" aria-label="快捷轨">
    <button
      type="button"
      class="rail-btn active"
      title="当前主机"
      aria-label="当前主机"
    >
      <el-icon><Monitor /></el-icon>
    </button>
    <button
      type="button"
      class="rail-btn"
      title="最近会话"
      aria-label="最近会话"
      @click="$emit('select', 'sessions')"
    >
      <el-icon><List /></el-icon>
    </button>
    <button
      type="button"
      class="rail-btn"
      title="收藏命令"
      aria-label="收藏命令"
      @click="$emit('select', 'snippets')"
    >
      <el-icon><Collection /></el-icon>
    </button>
    <button
      type="button"
      class="rail-btn"
      title="收藏目录"
      aria-label="收藏目录"
      @click="$emit('select', 'paths')"
    >
      <el-icon><FolderOpened /></el-icon>
    </button>
    <div class="rail-spacer" />
    <div class="rail-tip">ssh</div>
  </aside>
</template>

<script setup lang="ts">
import { Collection, FolderOpened, List, Monitor } from '@element-plus/icons-vue'

defineEmits<{
  select: [key: 'sessions' | 'snippets' | 'paths']
}>()
</script>

<style scoped lang="scss">
.ssh-left-rail {
  display: flex;
  flex: 0 0 48px;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  min-height: 0;
  padding: 8px 0;
  background: var(--ssh-panel);
  border-right: 1px solid var(--ssh-border);
}

.rail-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  padding: 0;
  color: var(--ssh-muted);
  background: transparent;
  border: 0;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.12s ease, color 0.12s ease;

  .el-icon {
    font-size: 16px;
  }

  &:hover {
    color: var(--ssh-text);
    background: var(--ssh-hover);
  }

  &.active {
    color: var(--ssh-accent);
    background: var(--ssh-accent-dim);
  }

  &:focus-visible {
    outline: 1px solid var(--ssh-accent);
    outline-offset: 1px;
  }
}

.rail-spacer {
  flex: 1;
}

.rail-tip {
  margin-bottom: 8px;
  color: var(--ssh-faint);
  font-size: 10px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  writing-mode: vertical-rl;
  transform: rotate(180deg);
}
</style>
