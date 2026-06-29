<template>
  <div class="ssh-tab-bar" aria-label="SSH 会话标签">
    <div
      v-for="tab in tabs"
      :key="tab.id"
      class="ssh-tab-shell"
      :class="{
        'is-active': tab.id === activeTabId,
      }"
    >
      <template v-if="editingTabId === tab.id">
        <div class="ssh-tab ssh-tab-editing">
          <span class="tab-status" :class="`is-${tab.status}`" aria-hidden="true" />
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
        <span class="tab-status" :class="`is-${tab.status}`" aria-hidden="true" />
        <span class="tab-copy">
          <span class="tab-title">{{ tab.title }}</span>
          <span v-if="tab.layout !== 'single'" class="tab-hint">
            {{ tab.layout === 'vertical' ? '左右分屏' : '上下分屏' }}
          </span>
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

    <button type="button" class="add-tab" aria-label="新建会话" @click="$emit('add-tab')">
      +
    </button>
  </div>
</template>

<script setup lang="ts">
import { nextTick, ref } from 'vue'
import type { SSHTabState } from './types'

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
  align-items: stretch;
  gap: 6px;
  min-height: 42px;
  padding: 7px 10px 0;
  background: #121725;
  border-bottom: 1px solid #27304d;
}

.ssh-tab-shell {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  min-width: 0;
  max-width: 240px;
  padding-right: 4px;
  border: 1px solid transparent;
  border-bottom: 0;
  border-radius: 7px 7px 0 0;
  background: #171d2f;
  transition: background-color 0.18s ease-out, border-color 0.18s ease-out;

  &::after {
    position: absolute;
    right: 10px;
    bottom: 0;
    left: 10px;
    height: 2px;
    content: '';
    background: transparent;
    border-radius: 999px 999px 0 0;
  }

  &.is-active {
    background: #1f263a;
    border-color: #344164;

    &::after {
      background: #6ea8fe;
    }
  }
}

.ssh-tab {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  flex: 1 1 auto;
  min-height: 34px;
  padding: 0 8px 0 10px;
  border: 0;
  border-radius: 7px 7px 0 0;
  background: transparent;
  color: #aeb8d8;
  cursor: pointer;
  transition: background-color 0.18s ease-out, border-color 0.18s ease-out, color 0.18s ease-out;
}

.ssh-tab:hover,
.ssh-tab:focus-visible {
  color: #eef3ff;
  outline: none;
}

.ssh-tab-shell.is-active .ssh-tab {
  color: #f4f7ff;
}

.ssh-tab-editing {
  cursor: default;
}

.tab-status {
  width: 8px;
  height: 8px;
  flex: 0 0 auto;
  border-radius: 999px;
  background: #565f89;

  &.is-connected {
    background: #4ade80;
    box-shadow: 0 0 0 3px rgb(74 222 128 / 12%);
  }

  &.is-connecting {
    background: #f6c177;
    box-shadow: 0 0 0 3px rgb(246 193 119 / 12%);
  }

  &.is-error {
    background: #ff7b93;
    box-shadow: 0 0 0 3px rgb(255 123 147 / 12%);
  }

  &.is-disconnected {
    background: #6ea8fe;
  }
}

.tab-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
}

.tab-copy {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.tab-hint {
  flex: 0 0 auto;
  font-size: 11px;
  color: #7f8aaa;
}

.rename-input {
  width: 100%;
  min-width: 88px;
  border: none;
  background: transparent;
  color: inherit;
  font-size: 13px;
  outline: none;
}

.tab-close,
.add-tab {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  padding: 0;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: #7f8aaa;
  cursor: pointer;
  transition: background-color 0.18s ease-out, color 0.18s ease-out;

  &:hover,
  &:focus-visible {
    background: #2a314b;
    color: #f4f7ff;
    outline: none;
  }
}

.tab-close {
  flex: 0 0 auto;
}

.add-tab {
  align-self: flex-start;
  margin-top: 4px;
  border: 1px solid #303a5c;
  background: #171d2f;
}

@media (max-width: 768px) {
  .ssh-tab-bar {
    overflow-x: auto;
    padding: 6px 8px;
  }

  .ssh-tab-shell {
    min-width: 132px;
  }
}
</style>
