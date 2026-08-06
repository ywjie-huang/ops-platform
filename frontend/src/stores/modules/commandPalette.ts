import { defineStore } from 'pinia'
import { ref } from 'vue'

/**
 * 命令面板全局状态：开关 + 最近访问（frecency）
 * 供 Header 入口按钮、全局 ⌘K 快捷键、CommandPalette 组件本体共用。
 */

export interface RecentItem {
  /** 唯一键，用于去重，如 `asset:pub_xxx` */
  key: string
  title: string
  subtitle?: string
  /** 图标种类，对应 CommandPalette 的 IconKind */
  icon: string
  /** 跳转路径 */
  to: string
  /** 访问时间戳（ms） */
  ts: number
}

export type RecentInput = Omit<RecentItem, 'ts'>

const STORAGE_KEY = 'cmd-palette-recents'
const MAX_RECENTS = 5

function loadRecents(): RecentItem[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const arr = JSON.parse(raw)
    return Array.isArray(arr) ? arr : []
  } catch {
    return []
  }
}

export const useCommandPaletteStore = defineStore('commandPalette', () => {
  const open = ref(false)
  const recents = ref<RecentItem[]>(loadRecents())

  function persist() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(recents.value))
    } catch {
      /* 忽略隐私模式 / 配额异常 */
    }
  }

  function toggle(v?: boolean) {
    open.value = typeof v === 'boolean' ? v : !open.value
  }
  function openPalette() {
    open.value = true
  }
  function close() {
    open.value = false
  }

  function pushRecent(input: RecentInput) {
    const entry: RecentItem = { ...input, ts: Date.now() }
    const filtered = recents.value.filter((r) => r.key !== entry.key)
    filtered.unshift(entry)
    recents.value = filtered.slice(0, MAX_RECENTS)
    persist()
  }

  function clearRecents() {
    recents.value = []
    try {
      localStorage.removeItem(STORAGE_KEY)
    } catch {
      /* noop */
    }
  }

  return { open, recents, toggle, openPalette, close, pushRecent, clearRecents }
})
