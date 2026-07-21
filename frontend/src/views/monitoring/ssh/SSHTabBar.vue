<template>
  <div class="ssh-tab-bar" aria-label="SSH 会话标签">
    <div
      v-for="tab in tabs"
      :key="tab.id"
      class="ssh-tab-shell"
      :class="{ 'is-active': tab.id === activeTabId }"
    >
      <template v-if="editingTabId === tab.id">
        <div class="ssh-tab ssh-tab-editing">
          <span class="tab-status" :class="statusClass(tab.status)" aria-hidden="true" />
          <input
            ref="renameInputRef"
            v-model="draftTitle"
            class="rename-input"
            type="text"
            maxlength="40"
            @click.stop
            @blur="commitRename(tab.id)"
            @keydown.enter.prevent="commitRename(tab.id)"
            @keydown.esc.prevent="cancelRename"
          />
        </div>
      </template>
      <button
        v-else
        type="button"
        class="ssh-tab"
        :aria-current="tab.id === activeTabId ? 'page' : undefined"
        @click="$emit('activate-tab', tab.id)"
        @dblclick="startRename(tab)"
      >
        <span class="tab-status" :class="statusClass(tab.status)" aria-hidden="true" />
        <span class="tab-title">{{ tab.title }}</span>
        <span v-if="tab.layout !== 'single'" class="tab-hint">
          {{ tab.layout === 'vertical' ? 'split' : 'stack' }}
        </span>
      </button>

      <button
        v-if="tabs.length > 1"
        type="button"
        class="tab-close"
        aria-label="关闭会话"
        @click.stop="$emit('close-tab', tab.id)"
      >
        ×
      </button>
    </div>

    <button type="button" class="add-tab" aria-label="新建会话" title="新建会话" @click="$emit('add-tab')">
      +
    </button>
  </div>
</template>

<script setup lang="ts">
import { nextTick, ref } from 'vue'
import type { SSHConnectionStatus, SSHTabState } from './types'

const emit = defineEmits<{
  'activate-tab': [tabId: string]
  'add-tab': []
  'close-tab': [tabId: string]
  'rename-tab': [tabId: string, title: string]
}>()

defineProps<{
  tabs: SSHTabState[]
  activeTabId: string
}>()

const editingTabId = ref<string | null>(null)
const draftTitle = ref('')
const renameInputRef = ref<HTMLInputElement | null>(null)

function statusClass(status: SSHConnectionStatus) {
  return `is-${status}`
}

function startRename(tab: SSHTabState) {
  editingTabId.value = tab.id
  draftTitle.value = tab.title
  nextTick(() => renameInputRef.value?.focus())
}

function commitRename(tabId: string) {
  if (editingTabId.value !== tabId) {
    return
  }

  emit('rename-tab', tabId, draftTitle.value)
  editingTabId.value = null
}

function cancelRename() {
  editingTabId.value = null
}
</script>

<style scoped lang="scss">
.ssh-tab-bar {
  display: flex;
  align-items: center;
  gap: 2px;
  min-width: 0;
  overflow: hidden;
}

.ssh-tab-shell {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 2px;
  min-width: 0;
  max-width: 160px;
  border: 1px solid transparent;
  border-radius: 4px;
  background: transparent;
}

.ssh-tab-shell.is-active {
  background: var(--ssh-surface);
  border-color: var(--ssh-border);
}

.ssh-tab {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  min-width: 0;
  flex: 1 1 auto;
  height: 26px;
  padding: 0 8px 0 10px;
  border: 0;
  border-radius: 4px;
  background: transparent;
  color: var(--ssh-muted);
  cursor: pointer;
  font: inherit;
  font-size: 12px;
  white-space: nowrap;
}

.ssh-tab:hover,
.ssh-tab:focus-visible {
  color: var(--ssh-text);
  outline: none;
}

.ssh-tab-shell.is-active .ssh-tab {
  color: var(--ssh-text);
}

.ssh-tab-editing {
  cursor: default;
}

.tab-status {
  width: 6px;
  height: 6px;
  flex: 0 0 auto;
  border-radius: 999px;
  background: var(--ssh-faint);

  &.is-connected {
    background: var(--ssh-ok);
  }

  &.is-connecting {
    background: var(--ssh-warn);
  }

  &.is-error,
  &.is-disconnected {
    background: var(--ssh-danger);
  }
}

.tab-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tab-hint {
  flex: 0 0 auto;
  color: var(--ssh-faint);
  font-size: 10px;
}

.rename-input {
  width: 100%;
  min-width: 72px;
  border: none;
  background: transparent;
  color: inherit;
  font-size: 12px;
  outline: none;
}

.tab-close,
.add-tab {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  padding: 0;
  border: none;
  border-radius: 3px;
  background: transparent;
  color: var(--ssh-muted);
  cursor: pointer;
}

.tab-close {
  flex: 0 0 auto;
  margin-right: 4px;
  opacity: 0;
}

.ssh-tab-shell:hover .tab-close,
.ssh-tab-shell.is-active .tab-close {
  opacity: 1;
}

.tab-close:hover,
.add-tab:hover,
.tab-close:focus-visible,
.add-tab:focus-visible {
  color: var(--ssh-text);
  background: var(--ssh-hover);
  outline: none;
}

.add-tab {
  width: 26px;
  height: 26px;
  border: 1px dashed var(--ssh-border-strong);
  color: var(--ssh-muted);
  font-size: 14px;
}

.add-tab:hover {
  border-color: var(--ssh-muted);
}
</style>
