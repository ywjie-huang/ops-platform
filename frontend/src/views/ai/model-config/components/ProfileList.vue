<template>
  <div class="plist">
    <div class="plist-head">
      <span class="plist-title">配置列表 <span class="count">{{ profiles.length }}</span></span>
    </div>
    <div class="plist-search" v-if="profiles.length > 6">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
      <input v-model="keyword" placeholder="搜索名称 / 模型" />
    </div>
    <div class="plist-items" v-loading="loading">
      <div
        v-for="p in filtered"
        :key="p.id"
        class="pitem"
        :class="{ active: activeProfileId === p.id }"
        role="option"
        :aria-selected="activeProfileId === p.id"
        tabindex="0"
        @click="$emit('select', p)"
        @keydown.enter.space.prevent="$emit('select', p)"
      >
        <div class="pi-logo" :class="{ 'has-img': !!logoOf(p.provider) }">
          <img v-if="logoOf(p.provider)" :src="logoOf(p.provider)" :alt="p.provider" />
          <template v-else>{{ p.icon }}</template>
        </div>
        <div class="pi-info">
          <div class="pi-name">
            {{ p.name }}
            <span v-if="p.is_active" class="use-badge">★ 使用中</span>
          </div>
          <div class="pi-meta">{{ p.provider }} · {{ p.model || extractHost(p.base_url) }}</div>
        </div>
        <span v-if="dirtyIds.includes(p.id)" class="dirty-dot" title="有未保存修改"></span>
        <button class="more" title="复制 / 删除" @click.stop="toggleMenu(p.id)">⋯</button>
        <div v-if="menuForId === p.id" class="pitem-menu" @click.stop>
          <button class="pitem-menu-item" type="button" @click="onClone(p)">复制</button>
          <button
            class="pitem-menu-item danger"
            type="button"
            :disabled="profiles.length <= 1"
            @click="onRemove(p)"
          >删除</button>
        </div>
      </div>
      <div v-if="!filtered.length && !loading" class="list-empty">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="12" y1="8" x2="12" y2="16"/><line x1="8" y1="12" x2="16" y2="12"/></svg>
        <span v-if="profiles.length">没有匹配「{{ keyword }}」的配置</span>
        <span v-else>暂无配置<br />从右侧向导选择一个服务商开始</span>
      </div>
    </div>
    <div class="plist-foot">
      <button class="add-btn" type="button" @click="$emit('add')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        新增配置
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import type { LLMProfile } from '@/api/settings'
import { providerLogoOf } from '../../providerLogos'

const props = defineProps<{
  profiles: LLMProfile[]
  activeProfileId: string | null
  /** 有未保存修改的 profile id 列表（逐项脏点） */
  dirtyIds?: string[]
  loading?: boolean
}>()

const emit = defineEmits<{
  (e: 'select', profile: LLMProfile): void
  (e: 'add'): void
  (e: 'clone', profile: LLMProfile): void
  (e: 'remove', profile: LLMProfile): void
}>()

const logoOf = providerLogoOf
const dirtyIds = computed(() => props.dirtyIds || [])

// ── 搜索（>6 个时显示） ──
const keyword = ref('')
const filtered = computed(() => {
  const q = keyword.value.trim().toLowerCase()
  if (!q) return props.profiles
  return props.profiles.filter((p) =>
    [p.name, p.model, p.provider, p.base_url].some((s) => (s || '').toLowerCase().includes(q)),
  )
})

// ── ⋯ 快捷菜单 ──
const menuForId = ref<string | null>(null)
function toggleMenu(id: string) {
  menuForId.value = menuForId.value === id ? null : id
}
function closeMenu() {
  menuForId.value = null
}
function onClone(p: LLMProfile) {
  emit('clone', p)
  closeMenu()
}
function onRemove(p: LLMProfile) {
  emit('remove', p)
  closeMenu()
}
window.addEventListener('click', closeMenu)
onBeforeUnmount(() => window.removeEventListener('click', closeMenu))

function extractHost(url: string): string {
  try {
    return new URL(url).hostname
  } catch {
    return url || '—'
  }
}
</script>

<style scoped>
.plist {
  background: var(--surface-color); border: 1px solid var(--border-color); border-radius: var(--radius, 10px);
  display: flex; flex-direction: column; min-height: 0; overflow: hidden; position: relative;
  box-shadow: 0 1px 2px rgba(17, 17, 17, 0.035);
}
.plist-head { display: flex; align-items: center; justify-content: space-between; padding: 13px 14px 10px; position: relative; }
.plist-title {
  font-size: 12px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;
  letter-spacing: 0.05em; display: flex; align-items: center; gap: 7px;
}
.count {
  background: var(--surface-2, #f6f6f8); border: 1px solid var(--border-color);
  border-radius: 999px; padding: 0 7px; font-size: 11px; color: var(--text-muted);
}

/* ── 搜索 ── */
.plist-search { margin: 0 10px 9px; position: relative; }
.plist-search input {
  width: 100%; padding: 7px 10px 7px 30px; border: 1px solid var(--border-strong, #e2e2e6);
  border-radius: 7px; font-size: 12.5px; background: var(--surface-color); color: var(--text-primary); font-family: inherit;
}
.plist-search input:focus { outline: none; border-color: var(--primary-color); box-shadow: 0 0 0 2px rgba(94, 106, 210, 0.12); }
.plist-search svg { position: absolute; left: 9px; top: 50%; transform: translateY(-50%); width: 14px; height: 14px; color: var(--text-muted); }

/* ── 列表项 ── */
.plist-items { flex: 1; min-height: 0; overflow-y: auto; padding: 2px 8px 8px; display: flex; flex-direction: column; gap: 3px; }
.pitem {
  display: flex; gap: 10px; align-items: center; padding: 9px 10px; border-radius: 8px;
  border: 1px solid transparent; cursor: pointer; position: relative; transition: background 0.12s; outline: none;
}
.pitem:hover { background: var(--surface-2, #f6f6f8); }
.pitem:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 2px; }
.pitem.active { background: var(--primary-bg); border-color: rgba(94, 106, 210, 0.22); }
.pitem.active::before {
  content: ''; position: absolute; left: 0; top: 9px; bottom: 9px;
  width: 3px; border-radius: 2px; background: var(--primary-color);
}
.pi-logo {
  width: 34px; height: 34px; border-radius: 8px; display: grid; place-items: center;
  background: #f5f5f5; color: var(--text-secondary); font-size: 11px; font-weight: 800; flex: none;
}
.pi-logo:not(.has-img) { box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.28), inset 0 -8px 14px rgba(0, 0, 0, 0.1); }
.pi-logo.has-img { background: #fff; border: 1px solid var(--border-strong, #e2e2e6); box-shadow: 0 1px 2px rgba(17, 17, 17, 0.06); }
.pi-logo.has-img img { width: 64%; height: 64%; object-fit: contain; display: block; }
.pi-info { flex: 1; min-width: 0; }
.pi-name {
  font-size: 13px; font-weight: 600; color: var(--text-primary);
  display: flex; align-items: center; gap: 6px; white-space: nowrap; overflow: hidden;
}
.pi-meta {
  font-size: 11.5px; color: var(--text-muted); white-space: nowrap;
  overflow: hidden; text-overflow: ellipsis; margin-top: 2px;
}
.use-badge {
  flex: none; font-size: 10.5px; font-weight: 700; color: var(--primary-color);
  background: var(--surface-color); border: 1px solid rgba(94, 106, 210, 0.3); padding: 1px 6px; border-radius: 5px;
}
.dirty-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--warning-color); flex: none; }
.pitem:hover .dirty-dot { opacity: 0; }
.more {
  display: none; position: absolute; right: 8px; top: 50%; transform: translateY(-50%);
  border: 1px solid var(--border-strong, #e2e2e6); background: var(--surface-color); border-radius: 6px;
  width: 22px; height: 22px; color: var(--text-secondary); cursor: pointer; font-size: 14px; line-height: 1;
  place-items: center; padding-bottom: 3px;
}
.pitem:hover .more { display: grid; }
.pitem-menu {
  position: absolute; right: 8px; top: calc(100% - 2px); z-index: 30; min-width: 88px;
  background: var(--surface-color); border: 1px solid var(--border-strong, #e2e2e6); border-radius: 8px;
  box-shadow: 0 10px 26px -8px rgba(17, 17, 17, 0.22); padding: 4px; display: flex; flex-direction: column;
}
.pitem-menu-item {
  border: 0; background: transparent; text-align: left; padding: 6px 10px; border-radius: 5px;
  font-size: 12.5px; color: var(--text-primary); cursor: pointer; font-family: inherit;
}
.pitem-menu-item:hover { background: var(--surface-2, #f6f6f8); }
.pitem-menu-item.danger { color: #b42318; }
.pitem-menu-item.danger:hover { background: rgba(229, 72, 77, 0.1); }
.pitem-menu-item:disabled { opacity: 0.45; cursor: not-allowed; }

/* ── 底部新增按钮 ── */
.plist-foot { padding: 10px; border-top: 1px solid var(--border-color); flex: none; }
.add-btn {
  width: 100%; border: 1px dashed var(--border-strong, #e2e2e6); background: var(--surface-color);
  border-radius: 8px; padding: 8px; font-size: 12.5px; font-weight: 600; color: var(--text-secondary);
  cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 6px;
  transition: all 0.15s; font-family: inherit;
}
.add-btn:hover { border-color: var(--primary-color); color: var(--primary-color); background: var(--primary-bg); }
.add-btn:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 2px; }
.add-btn svg { width: 13px; height: 13px; }

/* ── 空态 ── */
.list-empty {
  flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 9px; color: var(--text-muted); font-size: 12.5px; padding: 24px; text-align: center; line-height: 1.6;
}
.list-empty svg { width: 34px; height: 34px; opacity: 0.45; }

.plist-items::-webkit-scrollbar { width: 8px; }
.plist-items::-webkit-scrollbar-thumb { background: #d8d8dd; border-radius: 5px; border: 2px solid transparent; background-clip: content-box; }

@media (prefers-reduced-motion: reduce) {
  * { animation: none !important; transition: none !important; }
}
</style>
