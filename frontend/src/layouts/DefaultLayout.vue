<template>
  <div class="app-wrapper" :class="{ 'sidebar-collapsed': appStore.sidebarCollapsed }">
    <Sidebar />
    <div class="main-container">
      <Header />
      <AppMain />
    </div>
    <CommandPalette />
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import Sidebar from './Sidebar.vue'
import Header from './Header.vue'
import AppMain from './AppMain.vue'
import CommandPalette from '@/components/CommandPalette.vue'
import { useAppStore } from '@/stores/modules/app'
import { useCommandPaletteStore } from '@/stores/modules/commandPalette'

const appStore = useAppStore()
const palette = useCommandPaletteStore()

function onGlobalKey(e: KeyboardEvent) {
  // ⌘K (mac) / Ctrl+K (win/linux) 切换命令面板
  if ((e.metaKey || e.ctrlKey) && (e.key === 'k' || e.key === 'K')) {
    e.preventDefault()
    palette.toggle()
  }
}

onMounted(() => window.addEventListener('keydown', onGlobalKey))
onUnmounted(() => window.removeEventListener('keydown', onGlobalKey))
</script>

<style lang="scss" scoped>
.app-wrapper {
  display: flex;
  height: 100vh;
  background: var(--bg-color);
}
.main-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  margin-left: var(--sidebar-width);
  height: 100vh;
  overflow: hidden;
  transition: margin-left 0.12s ease-out;
}
.sidebar-collapsed .main-container {
  margin-left: var(--sidebar-collapsed-width);
}
</style>
