<template>
  <div class="picker-backdrop" @click="$emit('close')">
    <div class="host-picker" @click.stop>
      <div class="picker-search">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg>
        <input
          ref="inputRef"
          v-model="keyword"
          type="text"
          placeholder="搜索主机名称或 IP，回车快速选择"
          spellcheck="false"
          @keydown.esc.stop="$emit('close')"
          @keydown.enter.prevent="selectFirst"
        />
        <kbd>ESC</kbd>
      </div>

      <div class="picker-list">
        <div
          v-for="asset in filtered"
          :key="asset.id"
          class="picker-item"
          @click="pick(asset)"
        >
          <div class="pi-ava">{{ letter(asset.name) }}</div>
          <div class="pi-meta">
            <span class="pi-name">
              {{ asset.name }}
              <span v-if="asset.id === currentAssetId" class="pi-tag">当前主机</span>
            </span>
            <span class="pi-sub">{{ asset.ip_address }}</span>
          </div>
          <span class="pi-auth">{{ authHint(asset) }}</span>
        </div>
        <div v-if="filtered.length === 0" class="picker-empty">
          {{ keyword ? '没有匹配的主机' : '没有可连接的主机' }}
        </div>
      </div>

      <div class="picker-foot">仅显示已配置 SSH 凭据（密钥或密码）的主机</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'

const props = defineProps<{
  assets: any[]
  currentAssetId: number
}>()

const emit = defineEmits<{
  select: [asset: any]
  close: []
}>()

const keyword = ref('')
const inputRef = ref<HTMLInputElement>()

const filtered = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  if (!kw) return props.assets
  return props.assets.filter((asset) =>
    String(asset.name || '').toLowerCase().includes(kw)
    || String(asset.ip_address || '').toLowerCase().includes(kw),
  )
})

function letter(name: string) {
  return (name || 'S').trim().charAt(0).toUpperCase()
}

function authHint(asset: any) {
  if (asset.ssh_key_id) return '密钥'
  if (asset.has_ssh_password) return '密码'
  return '凭据'
}

function pick(asset: any) {
  emit('select', asset)
}

function selectFirst() {
  const first = filtered.value[0]
  if (first) emit('select', first)
}

onMounted(() => {
  nextTick(() => inputRef.value?.focus())
})
</script>

<style scoped lang="scss">
.picker-backdrop {
  position: absolute;
  inset: 0;
  z-index: 60;
  background: rgba(6, 7, 11, 0.4);
  backdrop-filter: blur(2px);
}
.host-picker {
  position: absolute;
  top: 62px;
  left: 240px;
  width: 380px;
  max-width: calc(100vw - 280px);
  border-radius: 14px;
  background: var(--ssh-card);
  box-shadow:
    inset 0 0 0 1px var(--ssh-line-2),
    0 24px 60px rgba(0, 0, 0, 0.55),
    0 0 50px var(--ssh-accent-glow);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.picker-search {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 14px;
  border-bottom: 1px solid var(--ssh-line);
  svg { width: 14px; height: 14px; color: var(--ssh-t4); flex-shrink: 0; }
  input {
    flex: 1;
    min-width: 0;
    border: none;
    background: transparent;
    outline: none;
    color: var(--ssh-t1);
    font-size: 12.5px;
    font-family: inherit;
    &::placeholder { color: var(--ssh-t4); }
  }
  kbd {
    font-family: var(--ssh-mono);
    font-size: 9.5px;
    color: var(--ssh-t4);
    border: 1px solid var(--ssh-line);
    border-radius: 4px;
    padding: 1px 5px;
    flex-shrink: 0;
  }
}
.picker-list {
  max-height: 320px;
  overflow-y: auto;
  padding: 6px;
  &::-webkit-scrollbar { width: 8px; }
  &::-webkit-scrollbar-thumb { background: var(--ssh-line-2); border-radius: 4px; }
}
.picker-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 10px;
  border-radius: 10px;
  cursor: pointer;
  &:hover { background: var(--ssh-glass); }
}
.pi-ava {
  width: 30px;
  height: 30px;
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 12px;
  font-weight: 800;
  color: #fff;
  background: linear-gradient(135deg, var(--ssh-accent), var(--ssh-accent-2));
  box-shadow: 0 2px 8px var(--ssh-accent-glow);
}
.pi-meta {
  flex: 1;
  min-width: 0;
  line-height: 1.3;
}
.pi-name {
  display: block;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--ssh-t1);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pi-tag {
  margin-left: 6px;
  font-size: 9.5px;
  font-weight: 600;
  color: var(--ssh-accent);
  background: var(--ssh-accent-bg);
  border-radius: 4px;
  padding: 1px 5px;
  vertical-align: 1px;
}
.pi-sub {
  font-family: var(--ssh-mono);
  font-size: 10.5px;
  color: var(--ssh-t3);
}
.pi-auth {
  flex-shrink: 0;
  font-size: 10px;
  font-weight: 600;
  color: var(--ssh-t3);
  border: 1px solid var(--ssh-line);
  border-radius: 5px;
  padding: 2px 7px;
}
.picker-empty {
  padding: 28px 16px;
  text-align: center;
  font-size: 12px;
  color: var(--ssh-t4);
}
.picker-foot {
  padding: 9px 14px;
  border-top: 1px solid var(--ssh-line);
  font-size: 10.5px;
  color: var(--ssh-t4);
}
@media (max-width: 900px) {
  .host-picker { left: 76px; }
}
</style>
