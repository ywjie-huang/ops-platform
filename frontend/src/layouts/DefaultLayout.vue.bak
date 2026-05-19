<template>
  <div class="app-wrapper" :class="{ 'sidebar-collapsed': appStore.sidebarCollapsed }">
    <Sidebar />
    <div class="main-container">
      <Header />
      <AppMain />
    </div>
  </div>
</template>

<script setup lang="ts">
import Sidebar from './Sidebar.vue'
import Header from './Header.vue'
import AppMain from './AppMain.vue'
import { useAppStore } from '@/stores/modules/app'

const appStore = useAppStore()
</script>

<style lang="scss" scoped>
.app-wrapper {
  display: flex;
  min-height: 100vh;
  background: var(--bg-color);
}
.main-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  margin-left: var(--sidebar-width);
  transition: margin-left 0.3s;
}
.sidebar-collapsed .main-container {
  margin-left: var(--sidebar-collapsed-width);
}
</style>
