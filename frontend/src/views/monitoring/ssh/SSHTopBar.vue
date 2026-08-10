<template>
  <header class="ssh-topbar">
    <button type="button" class="t-icon" title="返回" aria-label="返回" @click="$emit('back')">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 12H5m6-7l-7 7 7 7"/></svg>
    </button>
    <div class="crumb"><b>主机监控</b><span>/</span><span>SSH 会话</span></div>

    <div class="host-chip">
      <div class="host-ava">{{ avatarLetter }}</div>
      <div class="host-meta">
        <div class="hc-name">{{ hostName || '未知主机' }}</div>
        <div class="hc-addr">{{ loginUsername }}@{{ hostIp }}:{{ loginPort }}</div>
      </div>
    </div>

    <span class="live" :class="liveClass">
      <span class="pulse" />{{ liveText }}
    </span>

    <div class="sp" />

    <button type="button" class="search-box" title="搜索命令 (Ctrl+K)" @click="$emit('open-search')">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg>
      <span class="search-placeholder">搜索命令或文件</span>
      <kbd>Ctrl K</kbd>
    </button>
    <button type="button" class="t-icon" title="会话信息" aria-label="会话信息" @click="$emit('open-settings')">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M12 16v-5M12 8h.01"/></svg>
    </button>
    <button type="button" class="t-icon" title="全屏" aria-label="全屏" @click="$emit('toggle-fullscreen')">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 3H5a2 2 0 00-2 2v3m18 0V5a2 2 0 00-2-2h-3m0 18h3a2 2 0 002-2v-3M3 16v3a2 2 0 002 2h3"/></svg>
    </button>
    <button
      v-if="status === 'connected'"
      type="button"
      class="btn-ghost danger"
      @click="$emit('disconnect')"
    >
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18.36 6.64a9 9 0 11-12.72 0M12 2v10"/></svg>
      断开
    </button>
    <button v-else type="button" class="btn-ghost reconnect" @click="$emit('reconnect')">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 4v6h-6M1 20v-6h6"/><path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/></svg>
      重连
    </button>
  </header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { SSHConnectionStatus } from './types'

const props = defineProps<{
  hostName: string
  hostIp: string
  loginUsername: string
  loginPort: number
  status: SSHConnectionStatus
  connectionTime: string
}>()

defineEmits<{
  back: []
  'toggle-fullscreen': []
  'open-search': []
  'open-settings': []
  disconnect: []
  reconnect: []
}>()

const avatarLetter = computed(() => (props.hostName || 'S').trim().charAt(0).toUpperCase())

const liveClass = computed(() => {
  if (props.status === 'connected') return ''
  if (props.status === 'connecting') return 'warn'
  return 'err'
})

const liveText = computed(() => {
  if (props.status === 'connected') {
    return props.connectionTime ? `已连接 ${props.connectionTime}` : '已连接'
  }
  if (props.status === 'connecting') return '连接中…'
  return '未连接'
})
</script>

<style scoped lang="scss">
.ssh-topbar {
  display: flex;
  align-items: center;
  gap: 12px;
  height: 48px;
  padding: 0 14px;
  border-bottom: 1px solid var(--ssh-line);
  background: rgba(255, 255, 255, 0.015);
  flex-shrink: 0;
  user-select: none;
}
.t-icon {
  width: 30px;
  height: 30px;
  border-radius: 9px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  color: var(--ssh-t3);
  cursor: pointer;
  svg { width: 16px; height: 16px; }
  &:hover { background: var(--ssh-glass); color: var(--ssh-t1); }
}
.crumb {
  font-size: 12px;
  color: var(--ssh-t3);
  display: flex;
  gap: 7px;
  align-items: center;
  white-space: nowrap;
  b { color: var(--ssh-t2); font-weight: 600; }
}
.host-chip {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 4px 12px 4px 5px;
  border-radius: 10px;
  background: var(--ssh-glass);
  box-shadow: inset 0 0 0 1px var(--ssh-line);
}
.host-ava {
  width: 26px;
  height: 26px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 800;
  color: #fff;
  background: linear-gradient(135deg, var(--ssh-accent), var(--ssh-accent-2));
  box-shadow: 0 2px 10px var(--ssh-accent-glow);
}
.host-meta { line-height: 1.25; }
.hc-name {
  font-size: 12.5px;
  font-weight: 700;
  letter-spacing: -0.01em;
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.hc-addr {
  font-family: var(--ssh-mono);
  font-size: 10.5px;
  color: var(--ssh-t3);
  white-space: nowrap;
}
.live {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font-size: 11.5px;
  font-weight: 600;
  color: var(--ssh-ok);
  padding: 4px 11px;
  border-radius: 999px;
  background: var(--ssh-ok-bg);
  box-shadow: inset 0 0 0 1px rgba(52, 211, 153, 0.22);
  white-space: nowrap;
  .pulse {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--ssh-ok);
    animation: pulse-ok 2s ease infinite;
  }
  &.warn {
    color: var(--ssh-warn);
    background: rgba(251, 191, 36, 0.13);
    box-shadow: inset 0 0 0 1px rgba(251, 191, 36, 0.25);
    .pulse { background: var(--ssh-warn); animation-name: pulse-warn; }
  }
  &.err {
    color: var(--ssh-err);
    background: var(--ssh-err-bg);
    box-shadow: inset 0 0 0 1px rgba(248, 113, 113, 0.25);
    .pulse { background: var(--ssh-err); animation: none; }
  }
}
@keyframes pulse-ok {
  0%, 100% { box-shadow: 0 0 0 0 rgba(52, 211, 153, 0.5); }
  50% { box-shadow: 0 0 0 5px rgba(52, 211, 153, 0); }
}
@keyframes pulse-warn {
  0%, 100% { box-shadow: 0 0 0 0 rgba(251, 191, 36, 0.5); }
  50% { box-shadow: 0 0 0 5px rgba(251, 191, 36, 0); }
}
.sp { flex: 1; }
.search-box {
  display: flex;
  align-items: center;
  gap: 7px;
  width: 190px;
  height: 30px;
  padding: 0 10px;
  border-radius: 9px;
  border: none;
  background: var(--ssh-glass);
  box-shadow: inset 0 0 0 1px var(--ssh-line);
  color: var(--ssh-t4);
  font-size: 12px;
  font-family: inherit;
  cursor: pointer;
  text-align: left;
  svg { width: 13px; height: 13px; flex-shrink: 0; }
  .search-placeholder { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  kbd {
    margin-left: auto;
    font-family: var(--ssh-mono);
    font-size: 9.5px;
    color: var(--ssh-t4);
    border: 1px solid var(--ssh-line);
    border-radius: 4px;
    padding: 0 4px;
    flex-shrink: 0;
  }
  &:hover { color: var(--ssh-t2); box-shadow: inset 0 0 0 1px var(--ssh-line-2); }
}
.btn-ghost {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 30px;
  padding: 0 12px;
  border-radius: 9px;
  border: none;
  background: transparent;
  color: var(--ssh-t3);
  font-size: 12px;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  white-space: nowrap;
  svg { width: 13px; height: 13px; }
  &:hover { background: var(--ssh-glass); color: var(--ssh-t1); }
  &.danger {
    color: var(--ssh-err);
    &:hover { background: var(--ssh-err-bg); }
  }
  &.reconnect {
    color: var(--ssh-ok);
    &:hover { background: var(--ssh-ok-bg); }
  }
}
@media (max-width: 900px) {
  .search-box, .crumb { display: none; }
}
</style>
