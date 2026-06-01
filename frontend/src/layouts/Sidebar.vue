<template>
  <div class="sidebar" :class="{ collapsed: appStore.sidebarCollapsed }">
    <div class="sidebar-logo">
      <div class="logo-dot"></div>
      <span v-show="!appStore.sidebarCollapsed">运维平台</span>
    </div>

    <el-scrollbar wrap-style="overflow-x: hidden">
      <el-menu
        :default-active="activeMenu"
        :collapse="appStore.sidebarCollapsed"
        :collapse-transition="false"
        background-color="transparent"
        text-color="#666"
        active-text-color="#5e6ad2"
        router
      >
        <template v-for="item in processedRoutes" :key="item.route.path">
          <el-menu-item
            v-if="item.isSingle"
            :index="item.menuPath"
          >
            <el-icon v-if="item.menuIcon"><component :is="item.menuIcon" /></el-icon>
            <template #title>{{ item.menuTitle }}</template>
          </el-menu-item>

          <el-sub-menu v-else :index="item.route.path">
            <template #title>
              <el-icon v-if="item.menuIcon"><component :is="item.menuIcon" /></el-icon>
              <span>{{ item.menuTitle }}</span>
            </template>
            <el-menu-item
              v-for="child in item.children"
              :key="child.path"
              :index="`${item.route.path}/${child.path}`.replace('//', '/')"
            >
              <el-icon v-if="child.icon"><component :is="child.icon" /></el-icon>
              <template #title>{{ child.title }}</template>
            </el-menu-item>
          </el-sub-menu>
        </template>
      </el-menu>
    </el-scrollbar>

    <!-- 折叠按钮 -->
    <div class="collapse-btn" @click="appStore.toggleSidebar">
      <el-icon :size="16"><Fold v-if="!appStore.sidebarCollapsed" /><Expand v-else /></el-icon>
      <span v-show="!appStore.sidebarCollapsed">收起菜单</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, type Component } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAppStore } from '@/stores/modules/app'
import { useAuthStore } from '@/stores/modules/auth'
import {
  Bell, BellFilled, Box, ChatDotRound, Connection, Cpu,
  DataAnalysis, DataLine, Document, Finished, Fold, Expand,
  Key, Monitor, Notebook, Odometer, PieChart, Platform,
  Promotion, Setting, Tools, User, Warning,
} from '@element-plus/icons-vue'

const iconMap: Record<string, Component> = {
  Bell, BellFilled, Box, ChatDotRound, Connection, Cpu,
  DataAnalysis, DataLine, Document, Finished, Key, Monitor,
  Notebook, Odometer, PieChart, Platform, Promotion, Setting,
  Tools, User, Warning,
}

function resolveIcon(name?: string): Component | undefined {
  return name ? iconMap[name] : undefined
}

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()
const authStore = useAuthStore()

const activeMenu = computed(() => (route.meta?.activeMenu as string) || route.path)

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
    const menuIcon = resolveIcon(isSingle
      ? (children[0]?.meta?.icon || route.meta?.icon)
      : route.meta?.icon)
    const menuTitle = isSingle
      ? (children[0]?.meta?.title || route.meta?.title)
      : route.meta?.title
    const resolvedChildren = children.map((c: any) => ({
      path: c.path,
      title: c.meta?.title,
      icon: resolveIcon(c.meta?.icon),
    }))
    return { route, children: resolvedChildren, isSingle, menuPath, menuIcon, menuTitle }
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
  background: var(--surface-color);
  border-right: 1px solid var(--border-color);
  z-index: 100;
  display: flex;
  flex-direction: column;
  overflow: hidden;

  &.collapsed {
    width: var(--sidebar-collapsed-width);

    :deep(.el-menu-item),
    :deep(.el-sub-menu__title) {
      padding: 0 !important;
      width: 36px;
      margin-left: auto;
      margin-right: auto;
    }
  }
}

.sidebar-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 56px;
  padding: 0 16px;
  flex-shrink: 0;
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
  border-bottom: 1px solid var(--border-color);
  white-space: nowrap;
  overflow: hidden;
}

.logo-dot {
  width: 8px;
  height: 8px;
  background: #5e6ad2;
  border-radius: 2px;
  flex-shrink: 0;
}

// ── Element Plus Menu 样式覆盖 ──
:deep(.el-menu) {
  border-right: none;
  padding: 8px;
}

:deep(.el-menu-item),
:deep(.el-sub-menu__title) {
  height: 36px !important;
  line-height: 36px !important;
  border-radius: 6px;
  margin-bottom: 2px;
  font-size: 13px;
  font-weight: 500;
  color: #666 !important;
  padding-left: 12px !important;
  display: flex !important;
  align-items: center !important;

  &:hover {
    background: #f5f5f5 !important;
    color: #111 !important;
  }

  .el-icon {
    font-size: 16px;
    margin-right: 8px;
    color: inherit;
  }
}

:deep(.el-menu-item.is-active) {
  background: rgba(94, 106, 210, 0.08) !important;
  color: #5e6ad2 !important;
}

:deep(.el-sub-menu .el-menu) {
  padding: 0;
  background: transparent;
}

:deep(.el-sub-menu .el-menu .el-menu-item) {
  padding-left: 40px !important;
  height: 34px !important;
  line-height: 34px !important;
}

// 折叠态
:deep(.el-menu--collapse) {
  padding: 8px 0;
  width: 100%;
  overflow: hidden;

  .el-menu-item,
  .el-sub-menu__title {
    padding: 0 !important;
    margin: 0 auto 2px;
    width: 36px;
    height: 36px !important;
    line-height: 36px !important;
    display: flex;
    align-items: center;
    justify-content: center;

    .el-icon {
      margin: 0;
      font-size: 16px;
    }

    // 隐藏箭头
    .el-sub-menu__icon-arrow {
      display: none;
    }
  }

  // 隐藏子菜单
  .el-sub-menu .el-menu {
    display: none;
  }
}

// ── 底部折叠按钮 ──
.collapse-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 44px;
  padding: 0 16px;
  border-top: 1px solid var(--border-color);
  font-size: 12px;
  color: var(--text-muted);
  cursor: pointer;
  flex-shrink: 0;
  transition: all 0.15s;
  white-space: nowrap;
  overflow: hidden;

  &:hover {
    color: var(--text-secondary);
    background: #f5f5f5;
  }
}
</style>
