<template>
  <div class="sidebar" :class="{ collapsed: appStore.sidebarCollapsed }">
    <div class="sidebar-logo">
      <el-icon :size="22"><Cpu /></el-icon>
      <span v-show="!appStore.sidebarCollapsed" class="logo-text">OPS 运维平台</span>
    </div>

    <el-scrollbar>
      <el-menu
        :default-active="activeMenu"
        :collapse="appStore.sidebarCollapsed"
        :collapse-transition="false"
        background-color="#1e293b"
        text-color="rgba(255,255,255,0.75)"
        active-text-color="#60a5fa"
        router
      >
        <template v-for="item in processedRoutes" :key="item.route.path">
          <!-- 单个菜单项（无子菜单或只有一个可见子菜单） -->
          <el-menu-item
            v-if="item.isSingle"
            :index="item.menuPath"
          >
            <el-icon v-if="item.menuIcon">
              <component :is="item.menuIcon" />
            </el-icon>
            <template #title>{{ item.menuTitle }}</template>
          </el-menu-item>

          <!-- 子菜单（多个可见子菜单） -->
          <el-sub-menu v-else :index="item.route.path">
            <template #title>
              <el-icon v-if="item.route.meta?.icon">
                <component :is="item.route.meta.icon" />
              </el-icon>
              <span>{{ item.route.meta?.title }}</span>
            </template>
            <el-menu-item
              v-for="child in item.children"
              :key="child.path"
              :index="`${item.route.path}/${child.path}`.replace('//', '/')"
            >
              <el-icon v-if="child.meta?.icon">
                <component :is="child.meta.icon" />
              </el-icon>
              <template #title>{{ child.meta?.title }}</template>
            </el-menu-item>
          </el-sub-menu>
        </template>
      </el-menu>
    </el-scrollbar>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAppStore } from '@/stores/modules/app'
import { useAuthStore } from '@/stores/modules/auth'
import { Cpu } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()
const authStore = useAuthStore()

const activeMenu = computed(() => route.path)

const menuRoutes = computed(() => {
  return router.options.routes.filter(r => {
    if (r.meta?.hidden) return false
    const hasAccess = (rt: any): boolean => {
      if (rt.meta?.permission) return authStore.hasPermission(rt.meta.permission)
      if (rt.children) return rt.children.some((c: any) => hasAccess(c))
      return true
    }
    return hasAccess(r)
  })
})

const processedRoutes = computed(() => {
  return menuRoutes.value.map((route: any) => {
    const children = (route.children || []).filter((c: any) => !c.meta?.hidden)
    const isSingle = children.length <= 1
    const menuPath = isSingle
      ? `${route.path}/${children[0]?.path || ''}`.replace('//', '/')
      : route.path
    const menuIcon = isSingle
      ? (children[0]?.meta?.icon || route.meta?.icon)
      : route.meta?.icon
    const menuTitle = isSingle
      ? (children[0]?.meta?.title || route.meta?.title)
      : route.meta?.title
    return { route, children, isSingle, menuPath, menuIcon, menuTitle }
  })
})
</script>

<style lang="scss" scoped>
.sidebar {
  position: fixed;
  left: 0;
  top: 0;
  bottom: 0;
  width: var(--sidebar-width);
  background: #1e293b;
  z-index: 100;
  display: flex;
  flex-direction: column;
  transition: width 0.3s;
  overflow: hidden;

  &.collapsed {
    width: var(--sidebar-collapsed-width);
  }
}

.sidebar-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 56px;
  padding: 0 16px;
  color: #fff;
  border-bottom: 1px solid rgba(255,255,255,0.08);
  flex-shrink: 0;
}

.logo-text {
  font-size: 15px;
  font-weight: 700;
  white-space: nowrap;
  letter-spacing: 0.02em;
}

:deep(.el-menu) {
  border-right: none;
}

:deep(.el-menu-item.is-active) {
  background: rgba(59, 130, 246, 0.2) !important;
}

:deep(.el-sub-menu .el-menu-item) {
  padding-left: 50px !important;
}
</style>
