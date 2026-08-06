<template>
  <Teleport to="body">
    <Transition name="cp-fade">
      <div v-if="palette.open" class="cp-backdrop" @click="onBackdrop">
        <div
          class="cp-panel"
          role="dialog"
          aria-modal="true"
          aria-label="命令面板"
          @click.stop
        >
          <!-- 输入区 -->
          <div class="cp-input-wrap">
            <svg class="cp-search-icon" viewBox="0 0 24 24" aria-hidden="true">
              <circle cx="11" cy="11" r="7" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
            <input
              ref="inputRef"
              v-model="query"
              type="text"
              class="cp-input"
              placeholder="搜索主机、容器、工单，或跳转页面…"
              autocomplete="off"
              spellcheck="false"
              aria-label="搜索"
              aria-controls="cp-list"
              aria-expanded="true"
              @keydown="onKeydown"
            />
            <span v-if="loading" class="cp-spinner" aria-hidden="true"></span>
            <kbd v-else class="cp-key-esc">esc</kbd>
          </div>

          <!-- 结果列表 -->
          <div id="cp-list" ref="listRef" class="cp-list" role="listbox">
            <template v-if="items.length">
              <div v-for="g in groups" :key="g.label" class="cp-group">
                <div class="cp-group-label">{{ g.label }}</div>
                <button
                  v-for="row in g.rows"
                  :key="row.item.id"
                  :data-idx="row.idx"
                  type="button"
                  role="option"
                  :aria-selected="row.idx === activeIndex"
                  class="cp-row"
                  :class="{ active: row.idx === activeIndex }"
                  @click="execute(row.item)"
                  @mousemove="hoverRow(row.idx)"
                >
                  <span class="cp-icon" v-html="iconSvg(row.item.icon)"></span>
                  <span class="cp-text">
                    <span class="cp-title">{{ row.item.title }}</span>
                    <span v-if="row.item.subtitle" class="cp-sub">{{ row.item.subtitle }}</span>
                  </span>
                  <svg
                    v-if="row.idx === activeIndex"
                    class="cp-enter"
                    viewBox="0 0 24 24"
                    aria-hidden="true"
                  >
                    <polyline points="9 18 15 12 9 6" />
                  </svg>
                </button>
              </div>
            </template>

            <!-- 空状态 -->
            <div v-else class="cp-empty">
              <template v-if="hasQuery">
                <p class="cp-empty-title">未找到「{{ query.trim() }}」相关结果</p>
                <button type="button" class="cp-fallback" @click="fallback">
                  在主机管理中查看「{{ query.trim() }}」
                </button>
              </template>
              <p v-else class="cp-empty-title">输入关键词搜索，或选择一个页面跳转</p>
            </div>
          </div>

          <!-- 底部快捷键提示 -->
          <div class="cp-footer">
            <span class="cp-hint"><kbd>↑</kbd><kbd>↓</kbd> 移动</span>
            <span class="cp-hint"><kbd>↵</kbd> 选择</span>
            <span class="cp-hint"><kbd>esc</kbd> 关闭</span>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/modules/auth'
import { useAppStore } from '@/stores/modules/app'
import { useCommandPaletteStore, type RecentInput } from '@/stores/modules/commandPalette'
import request from '@/api/request'
import routes from '@/router/modules/routes'

const router = useRouter()
const authStore = useAuthStore()
const appStore = useAppStore()
const palette = useCommandPaletteStore()

type IconKind =
  | 'recent'
  | 'nav'
  | 'action'
  | 'host'
  | 'ticket'
  | 'cluster'
  | 'docker'
  | 'container'

interface CmdItem {
  id: string
  group: string
  title: string
  subtitle?: string
  icon: IconKind
  /** 命中时记录到"最近访问"；不填则不记录 */
  recent?: RecentInput
  run: () => void
}

const query = ref('')
const inputRef = ref<HTMLInputElement>()
const listRef = ref<HTMLElement>()
const activeIndex = ref(0)
const loading = ref(false)

const hasQuery = computed(() => query.value.trim().length > 0)

/* ------------------------------------------------------------------ *
 * 第 1 层：页面跳转（从路由表派生，按权限过滤）
 * ------------------------------------------------------------------ */
interface NavDef {
  title: string
  path: string
  permission?: string
  parent?: string
}

const navCommands: NavDef[] = (() => {
  const out: NavDef[] = []
  for (const top of routes as RouteRecordRaw[]) {
    if (top.meta?.hidden) continue
    if (!top.children) continue
    const parentTitle = (top.meta?.title as string) || ''
    for (const child of top.children) {
      if (child.meta?.hidden) continue
      if (child.redirect) continue
      if (!child.meta?.title) continue
      const childPath = (child.path as string) || ''
      // 跳过动态参数路由（无法直接导航）
      if (childPath.includes(':')) continue
      const base = top.path === '/' ? '' : top.path
      const path = (base + '/' + childPath).replace(/\/+/g, '/')
      out.push({
        title: child.meta.title as string,
        path,
        permission: child.meta?.permission as string | undefined,
        parent: parentTitle,
      })
    }
  }
  return out
})()

function canAccess(permission?: string): boolean {
  if (!permission) return true
  return authStore.hasPermission(permission)
}

const navItems = computed<CmdItem[]>(() =>
  navCommands
    .filter((n) => canAccess(n.permission))
    .map((n) => ({
      id: 'nav:' + n.path,
      group: '跳转页面',
      title: n.title,
      subtitle: n.parent && n.parent !== n.title ? n.parent : undefined,
      icon: 'nav' as IconKind,
      recent: {
        key: 'nav:' + n.path,
        title: n.title,
        subtitle: n.parent,
        icon: 'nav',
        to: n.path,
      },
      run: () => {
        router.push(n.path)
        palette.close()
      },
    })),
)

/* ------------------------------------------------------------------ *
 * 第 2 层：快捷操作（页面之外的真正动作）
 * ------------------------------------------------------------------ */
const actionItems = computed<CmdItem[]>(() => {
  const list: CmdItem[] = []
  list.push({
    id: 'act:toggle-sidebar',
    group: '操作',
    title: '切换侧边栏',
    subtitle: '折叠 / 展开左侧导航',
    icon: 'action',
    run: () => {
      appStore.toggleSidebar()
      palette.close()
    },
  })
  if (authStore.hasPermission('deploy.create')) {
    list.push({
      id: 'act:new-app',
      group: '操作',
      title: '新建应用',
      subtitle: '应用发布 → 创建应用',
      icon: 'action',
      run: () => {
        router.push('/deploy/apps/create')
        palette.close()
      },
    })
  }
  list.push({
    id: 'act:logout',
    group: '操作',
    title: '退出登录',
    subtitle: '结束当前会话',
    icon: 'action',
    run: async () => {
      palette.close()
      await authStore.logout()
      router.push('/login')
    },
  })
  return list
})

/* ------------------------------------------------------------------ *
 * 静态项（跳转 + 操作）按关键词模糊匹配
 * ------------------------------------------------------------------ */
function matchScore(text: string, q: string): number {
  const t = (text || '').toLowerCase()
  if (!q) return 0
  if (t.startsWith(q)) return 3
  if (t.includes(q)) return 2
  return 0
}

const filteredStatic = computed<CmdItem[]>(() => {
  const q = query.value.trim().toLowerCase()
  if (!q) return []
  return [...navItems.value, ...actionItems.value]
    .map((it) => ({
      it,
      s: Math.max(matchScore(it.title, q), matchScore(it.subtitle || '', q)),
    }))
    .filter((x) => x.s > 0)
    .sort((a, b) => b.s - a.s)
    .slice(0, 8)
    .map((x) => x.it)
})

/* ------------------------------------------------------------------ *
 * 第 3 层：实体搜索（防抖 + AbortController，复用现有 keyword 接口）
 * ------------------------------------------------------------------ */
const entityItems = ref<CmdItem[]>([])
let searchTimer: ReturnType<typeof setTimeout> | null = null
let abortCtrl: AbortController | null = null

function asArray(res: unknown): any[] {
  const d = (res as any)?.data
  if (Array.isArray(d)) return d
  if (d && Array.isArray(d.items)) return d.items
  return []
}

async function runEntitySearch(q: string) {
  abortCtrl?.abort()
  const ctrl = new AbortController()
  abortCtrl = ctrl
  const { signal } = ctrl
  const safe = <T>(p: Promise<T>): Promise<T | null> =>
    p.then((r) => r as T).catch(() => null)

  const [assets, tickets, clusters, dockerHosts, dockerContainers] = await Promise.all([
    safe(request.get('/assets/', { params: { keyword: q, page_size: 5 }, signal })),
    safe(request.get('/tickets/', { params: { keyword: q, page_size: 5 }, signal })),
    safe(request.get('/containers/clusters', { params: { keyword: q }, signal })),
    safe(request.get('/containers/docker/hosts', { params: { keyword: q }, signal })),
    safe(request.get('/containers/docker/containers', { params: { keyword: q }, signal })),
  ])

  if (signal.aborted) return

  const items: CmdItem[] = []

  for (const a of asArray(assets).slice(0, 5)) {
    const id = a.public_id ?? a.id
    const to = `/assets/hosts/${a.public_id}`
    items.push({
      id: 'asset:' + id,
      group: '主机',
      title: a.name || a.hostname || a.ip_address || '未命名主机',
      subtitle: [a.ip_address, a.asset_type].filter(Boolean).join(' · '),
      icon: 'host',
      recent: { key: 'asset:' + id, title: a.name || a.ip_address, subtitle: a.ip_address, icon: 'host', to },
      run: () => {
        router.push(to)
        palette.close()
      },
    })
  }

  for (const t of asArray(tickets).slice(0, 5)) {
    const to = `/tickets/${t.id}`
    items.push({
      id: 'ticket:' + t.id,
      group: '工单',
      title: t.title || `#${t.id}`,
      subtitle: [t.priority, t.status].filter(Boolean).join(' · '),
      icon: 'ticket',
      recent: { key: 'ticket:' + t.id, title: t.title || `#${t.id}`, subtitle: t.status, icon: 'ticket', to },
      run: () => {
        router.push(to)
        palette.close()
      },
    })
  }

  for (const c of asArray(clusters).slice(0, 5)) {
    const to = `/assets/containers/cluster/${encodeURIComponent(c.name)}`
    items.push({
      id: 'cluster:' + c.name,
      group: 'K8s 集群',
      title: c.name,
      subtitle: [c.version, c.description].filter(Boolean).join(' · '),
      icon: 'cluster',
      recent: { key: 'cluster:' + c.name, title: c.name, subtitle: c.version, icon: 'cluster', to },
      run: () => {
        router.push(to)
        palette.close()
      },
    })
  }

  for (const h of asArray(dockerHosts).slice(0, 5)) {
    const to = `/assets/docker/host/${encodeURIComponent(h.name)}`
    items.push({
      id: 'dhost:' + h.name,
      group: 'Docker 主机',
      title: h.name,
      subtitle: h.endpoint,
      icon: 'docker',
      recent: { key: 'dhost:' + h.name, title: h.name, subtitle: h.endpoint, icon: 'docker', to },
      run: () => {
        router.push(to)
        palette.close()
      },
    })
  }

  for (const c of asArray(dockerContainers).slice(0, 5)) {
    const hostName = c.host_name || c.host
    const to = hostName
      ? `/assets/docker/host/${encodeURIComponent(hostName)}`
      : '/assets/docker'
    items.push({
      id: 'dc:' + (c.id || c.name),
      group: 'Docker 容器',
      title: c.name || (c.id || '').slice(0, 12) || '未命名容器',
      subtitle: [hostName, c.image].filter(Boolean).join(' · '),
      icon: 'container',
      recent: hostName
        ? { key: 'dc:' + (c.id || c.name), title: c.name || c.id, subtitle: hostName, icon: 'container', to }
        : undefined,
      run: () => {
        router.push(to)
        palette.close()
      },
    })
  }

  entityItems.value = items
  loading.value = false
}

watch(query, (val) => {
  const q = val.trim()
  entityItems.value = []
  if (!q) {
    if (searchTimer) clearTimeout(searchTimer)
    abortCtrl?.abort()
    loading.value = false
    return
  }
  abortCtrl?.abort() // 取消上一轮 in-flight 请求
  loading.value = true
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => runEntitySearch(q), 200)
})

/* ------------------------------------------------------------------ *
 * 空状态：最近访问 / 建议页面
 * ------------------------------------------------------------------ */
const recentItems = computed<CmdItem[]>(() => {
  if (hasQuery.value) return []
  return palette.recents.map((r) => ({
    id: 'recent:' + r.key,
    group: '最近访问',
    title: r.title,
    subtitle: r.subtitle,
    icon: (r.icon as IconKind) || 'nav',
    run: () => {
      router.push(r.to)
      palette.close()
    },
  }))
})

const SUGGEST_PATHS = [
  '/dashboard',
  '/assets/hosts',
  '/monitoring/hosts',
  '/monitoring/events',
  '/tickets',
  '/batch-exec',
  '/ai/chat',
]
const suggestedNav = computed<CmdItem[]>(() => {
  if (hasQuery.value) return []
  const byPath = new Map(navItems.value.map((n) => [n.id, n]))
  const out: CmdItem[] = []
  for (const p of SUGGEST_PATHS) {
    const it = byPath.get('nav:' + p)
    if (it) out.push({ ...it, group: '建议页面' })
  }
  return out
})

/* ------------------------------------------------------------------ *
 * 汇总 + 分组（键盘导航在扁平列表上进行）
 * ------------------------------------------------------------------ */
const items = computed<CmdItem[]>(() => {
  if (!hasQuery.value) {
    return recentItems.value.length ? recentItems.value : suggestedNav.value
  }
  return [...filteredStatic.value, ...entityItems.value]
})

const groups = computed(() => {
  const order: string[] = []
  const map = new Map<string, { item: CmdItem; idx: number }[]>()
  items.value.forEach((item, idx) => {
    if (!map.has(item.group)) {
      map.set(item.group, [])
      order.push(item.group)
    }
    map.get(item.group)!.push({ item, idx })
  })
  return order.map((label) => ({ label, rows: map.get(label)! }))
})

watch(items, () => {
  activeIndex.value = 0
})

/* ------------------------------------------------------------------ *
 * 交互
 * ------------------------------------------------------------------ */
function execute(item: CmdItem) {
  if (item.recent) palette.pushRecent(item.recent)
  item.run()
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'ArrowDown') {
    e.preventDefault()
    activeIndex.value = Math.min(activeIndex.value + 1, items.value.length - 1)
    scrollActive()
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    activeIndex.value = Math.max(activeIndex.value - 1, 0)
    scrollActive()
  } else if (e.key === 'Enter') {
    e.preventDefault()
    const it = items.value[activeIndex.value]
    if (it) execute(it)
  } else if (e.key === 'Escape') {
    e.preventDefault()
    palette.close()
  }
}

function hoverRow(idx: number) {
  activeIndex.value = idx
}

function scrollActive() {
  nextTick(() => {
    const el = listRef.value?.querySelector<HTMLElement>(`[data-idx="${activeIndex.value}"]`)
    el?.scrollIntoView({ block: 'nearest' })
  })
}

function onBackdrop(e: MouseEvent) {
  if (e.target === e.currentTarget) palette.close()
}

function fallback() {
  router.push('/assets/hosts')
  palette.close()
}

/* 打开时重置并聚焦；关闭时取消请求 */
watch(
  () => palette.open,
  (isOpen) => {
    if (isOpen) {
      query.value = ''
      entityItems.value = []
      activeIndex.value = 0
      loading.value = false
      nextTick(() => inputRef.value?.focus())
    } else {
      if (searchTimer) clearTimeout(searchTimer)
      abortCtrl?.abort()
      loading.value = false
    }
  },
)

/* ------------------------------------------------------------------ *
 * 图标（内联 SVG，stroke=currentColor）
 * ------------------------------------------------------------------ */
const ICONS: Record<IconKind, string> = {
  recent: '<path d="M3 3v5h5"/><path d="M3.05 13A9 9 0 1 0 6 5.3L3 8"/><line x1="12" y1="7" x2="12" y2="12"/><line x1="12" y1="12" x2="15" y2="15"/>',
  nav: '<path d="M9 18l6-6-6-6"/>',
  action: '<polyline points="13 17 18 12 13 7"/><polyline points="6 17 11 12 6 7"/>',
  host: '<rect x="3" y="4" width="18" height="6" rx="1"/><rect x="3" y="14" width="18" height="6" rx="1"/><line x1="7" y1="7" x2="7.01" y2="7"/><line x1="7" y1="17" x2="7.01" y2="17"/>',
  ticket: '<path d="M3 7a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v2a2 2 0 0 0 0 4v2a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-2a2 2 0 0 0 0-4z"/><line x1="13" y1="5" x2="13" y2="19"/>',
  cluster: '<polygon points="12 2 22 8.5 22 15.5 12 22 2 15.5 2 8.5 12 2"/><line x1="12" y1="22" x2="12" y2="15.5"/><polyline points="22 8.5 12 15.5 2 8.5"/>',
  docker: '<rect x="3" y="9" width="18" height="9" rx="1"/><line x1="7" y1="13.5" x2="7.01" y2="13.5"/><line x1="11" y1="13.5" x2="11.01" y2="13.5"/><line x1="15" y1="13.5" x2="15.01" y2="13.5"/><path d="M21 13c1.5 0 1.5 2 0 2"/>',
  container: '<path d="M3 7l9-4 9 4-9 4-9-4z"/><path d="M3 7v10l9 4 9-4V7"/>',
}

function iconSvg(kind: IconKind): string {
  const path = ICONS[kind] || ICONS.nav
  return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${path}</svg>`
}
</script>

<style lang="scss" scoped>
.cp-backdrop {
  position: fixed;
  inset: 0;
  background: color-mix(in srgb, #0b1020 35%, transparent);
  backdrop-filter: blur(2px);
  display: flex;
  justify-content: center;
  align-items: flex-start;
  padding-top: 12vh;
  z-index: 2000;
}

.cp-panel {
  width: 92vw;
  max-width: 580px;
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  box-shadow: 0 18px 48px -12px rgba(16, 24, 40, 0.32);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  max-height: 76vh;
}

.cp-input-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color);
}

.cp-search-icon {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
  fill: none;
  stroke: var(--text-muted);
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.cp-input {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  font-size: 15px;
  color: var(--text-primary);
  font-family: inherit;

  &::placeholder {
    color: var(--text-muted);
  }
}

.cp-key-esc {
  font-size: 11px;
  color: var(--text-muted);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  padding: 1px 6px;
  flex-shrink: 0;
}

.cp-spinner {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
  border: 2px solid var(--border-color);
  border-top-color: var(--primary-color, #5e6ad2);
  border-radius: 50%;
  animation: cp-spin 0.7s linear infinite;
}

@keyframes cp-spin {
  to {
    transform: rotate(360deg);
  }
}

.cp-list {
  overflow-y: auto;
  padding: 6px;
  flex: 1;
  min-height: 0;
}

.cp-group {
  margin-bottom: 2px;
}

.cp-group-label {
  font-size: 11px;
  color: var(--text-muted);
  padding: 8px 10px 4px;
  letter-spacing: 0.02em;
}

.cp-row {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 8px 10px;
  border: none;
  background: transparent;
  border-radius: 8px;
  cursor: pointer;
  text-align: left;
  font-family: inherit;
  color: var(--text-primary);
  transition: background-color 0.12s ease-out;

  &:focus-visible {
    outline: 2px solid var(--primary-color, #5e6ad2);
    outline-offset: -2px;
  }

  &.active {
    background: color-mix(in srgb, var(--primary-color, #5e6ad2) 10%, transparent);
  }
}

.cp-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);

  :deep(svg) {
    width: 18px;
    height: 18px;
  }
}

.cp-row.active .cp-icon {
  color: var(--primary-color, #5e6ad2);
}

.cp-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
  flex: 1;
}

.cp-title {
  font-size: 14px;
  line-height: 1.4;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.cp-sub {
  font-size: 12px;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.cp-enter {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  fill: none;
  stroke: var(--text-muted);
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.cp-empty {
  padding: 28px 16px;
  text-align: center;
  color: var(--text-muted);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.cp-empty-title {
  font-size: 13px;
  margin: 0;
}

.cp-fallback {
  border: 1px solid var(--border-color);
  background: transparent;
  color: var(--primary-color, #5e6ad2);
  border-radius: 6px;
  padding: 6px 12px;
  font-size: 13px;
  cursor: pointer;
  font-family: inherit;
  transition: background-color 0.12s ease-out;

  &:hover {
    background: color-mix(in srgb, var(--primary-color, #5e6ad2) 8%, transparent);
  }
}

.cp-footer {
  display: flex;
  gap: 16px;
  padding: 8px 16px;
  border-top: 1px solid var(--border-color);
  font-size: 11px;
  color: var(--text-muted);

  kbd {
    border: 1px solid var(--border-color);
    border-radius: 3px;
    padding: 0 4px;
    margin-right: 3px;
    font-family: inherit;
    color: var(--text-secondary);
  }
}

.cp-hint {
  white-space: nowrap;
}

/* 进出动画：位移用 transform，避免布局属性 */
.cp-fade-enter-active,
.cp-fade-leave-active {
  transition: opacity 0.15s ease-out;

  .cp-panel {
    transition: transform 0.15s ease-out, opacity 0.15s ease-out;
  }
}

.cp-fade-enter-from,
.cp-fade-leave-to {
  opacity: 0;

  .cp-panel {
    transform: translateY(-8px);
    opacity: 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .cp-spinner {
    animation-duration: 1.4s;
  }
  .cp-fade-enter-active,
  .cp-fade-leave-active,
  .cp-fade-enter-active .cp-panel,
  .cp-fade-leave-active .cp-panel {
    transition: none;
  }
}

@media (max-width: 768px) {
  .cp-backdrop {
    padding-top: 6vh;
  }
  .cp-panel {
    max-width: 94vw;
  }
  .cp-footer {
    display: none;
  }
}
</style>
