<template>
  <div class="card profile-list-card">
    <div class="profile-list-header">
      <span class="profile-list-title">模型配置</span>
      <div class="profile-list-actions">
        <button class="btn btn-sm" :disabled="!hasActive" @click="$emit('clone')">复制</button>
        <button class="btn btn-sm btn-primary" @click="$emit('add')">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          新增
        </button>
      </div>
    </div>
    <div class="profile-items" v-loading="loading">
      <div
        v-for="p in profiles"
        :key="p.id"
        class="profile-item"
        :class="{ active: activeProfileId === p.id }"
        role="option"
        :aria-selected="activeProfileId === p.id"
        tabindex="0"
        @click="$emit('select', p)"
        @keydown.enter.space.prevent="$emit('select', p)"
      >
        <div class="profile-icon">{{ p.icon }}</div>
        <div class="profile-info">
          <div class="profile-name">
            {{ p.name }}
            <span v-if="isDirty && p.id === activeProfileId" class="tag tag-default" style="margin-left: 4px;">未保存</span>
          </div>
          <div class="profile-meta">{{ p.provider }} · {{ extractHost(p.base_url) }}</div>
        </div>
        <span
          class="profile-status"
          :class="p.is_active ? 'active' : 'inactive'"
          :title="p.is_active ? '当前使用中' : '未启用'"
        ></span>
      </div>
      <div v-if="!profiles.length && !loading" class="empty-state">
        <svg class="empty-state-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="12" y1="8" x2="12" y2="16"/><line x1="8" y1="12" x2="16" y2="12"/></svg>
        <span class="empty-state-text">暂无配置，点击"新增"开始</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { LLMProfile } from '@/api/settings'

defineProps<{
  profiles: LLMProfile[]
  activeProfileId: string | null
  loading?: boolean
  isDirty?: boolean
  hasActive?: boolean
}>()

defineEmits<{
  (e: 'select', profile: LLMProfile): void
  (e: 'add'): void
  (e: 'clone'): void
}>()

function extractHost(url: string): string {
  try {
    return new URL(url).hostname
  } catch {
    return url || '—'
  }
}
</script>

<style scoped>
.card {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: 20px;
}
.profile-list-card {
  padding: 0;
  overflow: hidden;
}
.profile-list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 16px 12px;
  border-bottom: 1px solid var(--border-color);
}
.profile-list-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.profile-list-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}
.profile-items {
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-height: 120px;
}
.profile-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.12s;
  border: 1px solid transparent;
}
.profile-item:hover { background: var(--bg-color); }
.profile-item:focus-visible {
  outline: 2px solid var(--primary-color);
  outline-offset: 2px;
}
.profile-item.active {
  background: var(--primary-bg);
  border-color: rgba(94, 106, 210, 0.2);
}
.profile-icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  background: #f5f5f5;
  font-size: 14px;
  font-weight: 700;
  color: var(--text-secondary);
}
.profile-item.active .profile-icon {
  background: rgba(94, 106, 210, 0.12);
  color: var(--primary-color);
}
.profile-info { flex: 1; min-width: 0; }
.profile-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.profile-meta {
  font-size: 11px;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.profile-status {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.profile-status.active { background: var(--success-color, #16a34a); }
.profile-status.inactive { background: #d9d9d9; }
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px 16px;
  text-align: center;
  gap: 8px;
}
.empty-state-icon {
  width: 40px;
  height: 40px;
  color: var(--text-muted);
  opacity: 0.5;
}
.empty-state-text {
  font-size: 13px;
  color: var(--text-muted);
}
.tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 0 8px;
  height: 22px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
}
.tag-default { background: #f5f5f5; color: var(--text-secondary); }
.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid var(--border-color);
  background: var(--surface-color);
  color: var(--text-primary);
  transition: all 0.15s;
}
.btn-sm { padding: 4px 12px; font-size: 12px; }
.btn-primary {
  background: var(--primary-color);
  color: white;
  border-color: var(--primary-color);
}
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
