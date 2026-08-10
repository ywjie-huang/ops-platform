<template>
  <aside class="session-rail" aria-label="会话列表">
    <div class="sess-head">
      <span>会话 · {{ tabs.length }}</span>
      <button type="button" title="沿用上次认证，直接新建并连接 (Ctrl+Shift+T)" aria-label="新建会话" @click="$emit('add-tab')">+</button>
    </div>

    <div class="sess-list">
      <div
        v-for="tab in tabs"
        :key="tab.id"
        class="sess-card"
        :class="{ active: tab.id === activeTabId, off: isOff(tab) }"
        @click="$emit('activate-tab', tab.id)"
      >
        <div class="sess-row1">
          <span class="sess-dot" :class="dotClass(tab)" />
          <template v-if="editingId === tab.id">
            <input
              ref="renameInput"
              v-model="draft"
              class="rename-input"
              maxlength="40"
              @click.stop
              @blur="commitRename(tab.id)"
              @keydown.enter.prevent="commitRename(tab.id)"
              @keydown.esc.prevent="editingId = null"
            />
          </template>
          <span v-else class="sess-name" :title="tab.title" @dblclick.stop="startRename(tab)">{{ tab.title }}</span>
          <button
            v-if="tabs.length > 1"
            type="button"
            class="sess-x"
            aria-label="关闭会话"
            @click.stop="$emit('close-tab', tab.id)"
          >×</button>
        </div>
        <div class="sess-sub">
          <template v-if="subtitle(tab).relink">
            已断开 · <span class="relink" @click.stop="handleRelink(tab.id)">点击重连</span>
          </template>
          <template v-else>{{ subtitle(tab).text }}</template>
        </div>
        <span v-if="tab.layout !== 'single'" class="sess-badge">{{ tab.panes.length }} 分屏</span>
      </div>
    </div>

    <button type="button" class="sess-new" @click="$emit('add-tab')">
      + 新建会话 <span class="kbd">⌃⇧T</span>
    </button>

    <div class="sess-foot">
      <button type="button" @click="$emit('open-commands')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2l2.9 6.3 6.6.7-5 4.5 1.4 6.5L12 16.7 6.1 20l1.4-6.5-5-4.5 6.6-.7z"/></svg>
        命令收藏
      </button>
      <button type="button" @click="$emit('open-info')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 3"/></svg>
        历史会话
      </button>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { nextTick, ref } from 'vue'
import type { SSHPaneMeta } from './SSHPane.vue'
import type { SSHTabState } from './types'

const props = defineProps<{
  tabs: SSHTabState[]
  activeTabId: string
  meta: Record<string, SSHPaneMeta>
}>()

const emit = defineEmits<{
  'activate-tab': [tabId: string]
  'add-tab': []
  'close-tab': [tabId: string]
  'rename-tab': [tabId: string, title: string]
  'reconnect-tab': [tabId: string]
  'open-commands': []
  'open-info': []
}>()

const editingId = ref<string | null>(null)
const draft = ref('')
const renameInput = ref<HTMLInputElement[] | null>(null)

function tabMeta(tab: SSHTabState): SSHPaneMeta | undefined {
  for (const pane of tab.panes) {
    const meta = props.meta[pane.id]
    if (meta) return meta
  }
  return undefined
}

function dotClass(tab: SSHTabState) {
  if (tab.status === 'connected') return 'ok'
  if (tab.status === 'connecting') return 'warn'
  if (tab.status === 'error') return 'err'
  return 'off'
}

function isOff(tab: SSHTabState) {
  return tab.status === 'disconnected' || tab.status === 'idle'
}

function subtitle(tab: SSHTabState): { text: string; relink?: boolean } {
  const meta = tabMeta(tab)
  if (tab.status === 'connecting') return { text: '连接中…' }
  if (tab.status === 'connected') {
    const path = meta?.currentPath || tab.panes[0]?.currentPath || '~'
    const time = meta?.connectionTime
    return { text: time ? `${path} · ${time}` : path }
  }
  if (tab.status === 'error') {
    return { text: meta?.lastError || tab.panes[0]?.lastError || '连接失败' }
  }
  if (tab.status === 'disconnected') return { text: '', relink: true }
  return { text: '未连接' }
}

function handleRelink(tabId: string) {
  emit('reconnect-tab', tabId)
}

function startRename(tab: SSHTabState) {
  editingId.value = tab.id
  draft.value = tab.title
  nextTick(() => renameInput.value?.[0]?.focus())
}

function commitRename(tabId: string) {
  if (editingId.value !== tabId) return
  emit('rename-tab', tabId, draft.value)
  editingId.value = null
}
</script>

<style scoped lang="scss">
.session-rail {
  width: 224px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--ssh-line);
  padding: 12px 10px;
  gap: 4px;
  min-height: 0;
  user-select: none;
}
.sess-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 6px 10px;
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--ssh-t4);
  button {
    width: 22px;
    height: 22px;
    border-radius: 6px;
    border: none;
    background: transparent;
    color: var(--ssh-t3);
    cursor: pointer;
    font-size: 14px;
    line-height: 1;
    &:hover { background: var(--ssh-glass); color: var(--ssh-t1); }
  }
}
.sess-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 4px;
  &::-webkit-scrollbar { width: 6px; }
  &::-webkit-scrollbar-thumb { background: var(--ssh-line-2); border-radius: 3px; }
}
.sess-card {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 10px 12px;
  border-radius: 11px;
  cursor: pointer;
  color: var(--ssh-t3);
  flex-shrink: 0;
  &:hover { background: var(--ssh-glass); color: var(--ssh-t2); }
  &.active {
    background: var(--ssh-accent-bg);
    color: var(--ssh-t1);
    box-shadow: inset 0 0 0 1px var(--ssh-accent-glow);
    &::before {
      content: '';
      position: absolute;
      left: -10px;
      top: 12px;
      bottom: 12px;
      width: 2.5px;
      border-radius: 3px;
      background: linear-gradient(180deg, var(--ssh-accent), var(--ssh-accent-2));
      box-shadow: 0 0 8px var(--ssh-accent-glow);
    }
  }
  &.off .sess-name { color: var(--ssh-t3); }
}
.sess-row1 { display: flex; align-items: center; gap: 8px; }
.sess-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--ssh-t4);
  flex-shrink: 0;
  &.ok { background: var(--ssh-ok); box-shadow: 0 0 6px rgba(52, 211, 153, 0.6); }
  &.warn { background: var(--ssh-warn); }
  &.err { background: var(--ssh-err); }
  &.off { background: var(--ssh-t4); }
}
.sess-name {
  font-size: 12.5px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 0;
}
.rename-input {
  flex: 1;
  min-width: 0;
  border: none;
  background: transparent;
  color: var(--ssh-t1);
  font-size: 12.5px;
  font-weight: 600;
  outline: none;
  border-bottom: 1px solid var(--ssh-accent);
}
.sess-x {
  margin-left: auto;
  width: 17px;
  height: 17px;
  border-radius: 5px;
  display: none;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  color: var(--ssh-t4);
  font-size: 12px;
  cursor: pointer;
  flex-shrink: 0;
  &:hover { background: var(--ssh-line-2); color: var(--ssh-t1); }
}
.sess-card:hover .sess-x { display: inline-flex; }
.sess-sub {
  font-family: var(--ssh-mono);
  font-size: 10.5px;
  color: var(--ssh-t4);
  padding-left: 15px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.sess-card.active .sess-sub { color: var(--ssh-t3); }
.relink {
  color: var(--ssh-accent);
  cursor: pointer;
  &:hover { text-decoration: underline; }
}
.sess-badge {
  display: inline-block;
  margin-left: 15px;
  margin-top: 3px;
  font-family: var(--ssh-mono);
  font-size: 9.5px;
  color: var(--ssh-t3);
  border: 1px solid var(--ssh-line);
  border-radius: 4px;
  padding: 1px 5px;
  width: fit-content;
}
.sess-new {
  margin-top: 6px;
  height: 34px;
  border-radius: 10px;
  border: 1px dashed var(--ssh-line-2);
  background: transparent;
  color: var(--ssh-t3);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  font-family: inherit;
  flex-shrink: 0;
  .kbd { opacity: 0.5; font-family: var(--ssh-mono); font-size: 10px; }
  &:hover { color: var(--ssh-accent); border-color: var(--ssh-accent); background: var(--ssh-accent-bg); }
}
.sess-foot {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding-top: 10px;
  border-top: 1px solid var(--ssh-line);
  flex-shrink: 0;
  button {
    display: flex;
    align-items: center;
    gap: 9px;
    height: 32px;
    padding: 0 10px;
    border-radius: 9px;
    border: none;
    background: transparent;
    color: var(--ssh-t3);
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    font-family: inherit;
    svg { width: 14px; height: 14px; }
    &:hover { background: var(--ssh-glass); color: var(--ssh-t1); }
  }
}
@media (max-width: 900px) {
  .session-rail { width: 64px; padding: 12px 6px; }
  .sess-head span, .sess-sub, .sess-badge, .sess-new, .sess-foot, .sess-name, .rename-input { display: none; }
  .sess-card { padding: 10px; align-items: center; }
  .sess-row1 { justify-content: center; }
}
</style>
