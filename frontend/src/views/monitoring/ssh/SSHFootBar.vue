<template>
  <footer class="ssh-footbar" aria-label="SSH 会话状态">
    <span class="fb">{{ terminalSize || '-·-' }}</span>
    <span class="fb"><span class="pv">{{ currentPath || '/' }}</span></span>
    <span v-if="credentialLabel" class="fb">{{ credentialLabel }}</span>
    <span v-if="layoutLabel" class="fb">{{ layoutLabel }}</span>
    <span class="sp" />
    <span class="fb-keys">
      <span><kbd>Ctrl B</kbd>文件</span>
      <span><kbd>Ctrl \</kbd>分屏</span>
      <span><kbd>⌃⇧T</kbd>新会话</span>
    </span>
  </footer>
</template>

<script setup lang="ts">
defineProps<{
  terminalSize: string
  currentPath: string
  credentialLabel: string
  layoutLabel: string
}>()
</script>

<style scoped lang="scss">
.ssh-footbar {
  display: flex;
  align-items: center;
  height: 26px;
  padding: 0 14px;
  border-top: 1px solid var(--ssh-line);
  font-family: var(--ssh-mono);
  font-size: 10.5px;
  color: var(--ssh-t4);
  flex-shrink: 0;
  user-select: none;
  overflow: hidden;
}
.fb { padding: 0 10px; white-space: nowrap; }
.fb + .fb { border-left: 1px solid var(--ssh-line); }
.fb .pv { color: var(--ssh-t2); }
.sp { flex: 1; }
.fb-keys {
  display: flex;
  gap: 12px;
  font-family: Inter, -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif;
  white-space: nowrap;
  kbd {
    font-family: var(--ssh-mono);
    font-size: 9px;
    border: 1px solid var(--ssh-line);
    border-radius: 4px;
    padding: 1px 4px;
    margin-right: 4px;
  }
}
@media (max-width: 900px) {
  .fb-keys { display: none; }
}
</style>
