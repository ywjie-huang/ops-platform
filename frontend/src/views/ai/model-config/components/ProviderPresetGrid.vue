<template>
  <div class="card provider-card" :class="{ 'is-open': isOpen }">
    <!-- 摘要行：收起态只留一行 -->
    <div class="pv-summary">
      <div class="pv-logo" :class="{ 'has-img': !!currentLogo }">
        <img v-if="currentLogo" :src="currentLogo" :alt="presetName" />
        <template v-else>{{ profile.icon }}</template>
      </div>
      <div class="pv-sum-text">
        <div class="pv-name">{{ presetName }}</div>
        <div class="pv-sub">{{ hostLabel }} · 默认模型 {{ profile.model || '—' }}</div>
      </div>
      <button class="btn btn-sm" type="button" @click="isOpen = !isOpen">
        {{ isOpen ? '收起 ▴' : '更换服务商 ▾' }}
      </button>
    </div>

    <!-- 展开网格：按 国际 / 国内 / 本地·通用 分组 -->
    <div class="pv-grid">
      <template v-for="g in groups" :key="g.id">
        <div class="pv-group-cap">{{ g.label }}</div>
        <div class="pv-tiles">
          <button
            v-for="p in g.items"
            :key="p.id"
            type="button"
            class="pv-tile"
            :class="{ selected: profile.provider === p.id }"
            :aria-pressed="profile.provider === p.id"
            @click="onSelect(p)"
          >
            <span class="pv-logo" :class="{ 'has-img': !!logoOf(p.id) }">
              <img v-if="logoOf(p.id)" :src="logoOf(p.id)" :alt="p.name" />
              <template v-else>{{ p.icon }}</template>
            </span>
            <span class="pv-t-text">
              <span class="pv-t-name">{{ p.name }}</span>
              <span class="pv-t-hint">{{ p.hint }}</span>
            </span>
          </button>
        </div>
      </template>
      <div class="pv-foot">
        <button class="btn btn-sm" type="button" @click="isOpen = false">收起 ▴</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { LLMProfile } from '@/api/settings'
import { providerLogoOf } from '../../providerLogos'
import type { ProviderPreset, ProviderGroup } from '../../providerPreset'

const props = defineProps<{
  profile: LLMProfile
  providers: ProviderPreset[]
}>()

const emit = defineEmits<{
  (e: 'select', provider: ProviderPreset): void
}>()

const logoOf = providerLogoOf

const GROUP_LABELS: Record<ProviderGroup, string> = {
  intl: '国际',
  cn: '国内',
  local: '本地 / 通用',
}

const groups = computed(() =>
  (['intl', 'cn', 'local'] as ProviderGroup[])
    .map((id) => ({ id, label: GROUP_LABELS[id], items: props.providers.filter((p) => p.group === id) }))
    .filter((g) => g.items.length > 0),
)

// 新建（地址和模型都为空）时默认展开；切换配置时重算
const isBlank = (p: LLMProfile) => !(p.base_url || '').trim() && !(p.model || '').trim()
const isOpen = ref(isBlank(props.profile))
watch(
  () => props.profile.id,
  () => { isOpen.value = isBlank(props.profile) },
)

const currentLogo = computed(() => providerLogoOf(props.profile.provider))
const presetName = computed(
  () => props.providers.find((p) => p.id === props.profile.provider)?.name || '自定义',
)
const hostLabel = computed(() => {
  const u = (props.profile.base_url || '').trim()
  if (!u) return '（手动填写）'
  try {
    return new URL(u).hostname
  } catch {
    return u
  }
})

function onSelect(p: ProviderPreset) {
  emit('select', p)
  isOpen.value = false // 选中即自动折叠
}
</script>

<style scoped>
.card {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--radius, 10px);
  padding: 16px 18px;
  position: relative;
  flex: none;
  box-shadow: 0 1px 2px rgba(17, 17, 17, 0.035);
}

/* ── 摘要行 ── */
.pv-summary { display: flex; align-items: center; gap: 12px; position: relative; }
.pv-logo {
  width: 38px; height: 38px; border-radius: 9px; display: grid; place-items: center;
  background: #f5f5f5; color: var(--text-secondary); font-weight: 800; font-size: 12px; flex: none;
}
.pv-logo:not(.has-img) { box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.28), inset 0 -8px 14px rgba(0, 0, 0, 0.1); }
.pv-logo.has-img { background: #fff; border: 1px solid var(--border-strong, #e2e2e6); box-shadow: 0 1px 2px rgba(17, 17, 17, 0.06); }
.pv-logo.has-img img { width: 62%; height: 62%; object-fit: contain; display: block; }
.pv-sum-text { flex: 1; min-width: 0; }
.pv-name { font-size: 13.5px; font-weight: 700; color: var(--text-primary); }
.pv-sub {
  font-size: 11.5px; color: var(--text-muted); margin-top: 2px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}

/* ── 展开网格 ── */
.pv-grid { margin-top: 14px; display: none; flex-direction: column; gap: 10px; }
.provider-card.is-open .pv-grid { display: flex; }
.pv-group-cap { font-size: 11px; font-weight: 700; color: var(--text-muted); letter-spacing: 0.06em; }
.pv-tiles { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 8px; }
.pv-tile {
  display: flex; flex-direction: column; align-items: center; gap: 8px;
  padding: 14px 10px 12px; border: 1px solid var(--border-color); border-radius: 10px;
  cursor: pointer; background: var(--surface-color); transition: all 0.13s;
  text-align: center; font-family: inherit;
}
.pv-tile:hover { border-color: #c9c9cf; background: var(--surface-2, #f6f6f8); transform: translateY(-1px); box-shadow: 0 3px 8px rgba(17, 17, 17, 0.06); }
.pv-tile:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 2px; }
.pv-tile.selected { border-color: var(--primary-color); background: var(--primary-bg); box-shadow: 0 0 0 1px var(--primary-color); }
.pv-tile .pv-logo { width: 46px; height: 46px; border-radius: 12px; font-size: 13px; }
.pv-tile.selected .pv-logo.has-img { border-color: var(--primary-color); box-shadow: 0 0 0 3px var(--primary-bg); }
.pv-t-text { display: flex; flex-direction: column; align-items: center; gap: 2px; }
.pv-t-name { font-size: 12.5px; font-weight: 600; color: var(--text-primary); }
.pv-t-hint { font-size: 10.5px; color: var(--text-muted); margin-top: 1px; }
.pv-foot { display: flex; justify-content: flex-end; }

/* ── 展开动画 ── */
@keyframes fadeUp { from { opacity: 0; transform: translateY(7px); } }
.provider-card.is-open .pv-grid { animation: fadeUp 0.22s ease; }

/* ── 按钮 ── */
.btn {
  display: inline-flex; align-items: center; gap: 6px; padding: 7px 14px; border-radius: 7px;
  font-size: 12.5px; font-weight: 600; cursor: pointer; border: 1px solid var(--border-strong, #e2e2e6);
  background: var(--surface-color); color: var(--text-primary); transition: all 0.15s; font-family: inherit;
}
.btn:hover { border-color: #c9c9cf; transform: translateY(-1px); box-shadow: 0 3px 8px rgba(17, 17, 17, 0.07); }
.btn:active { transform: none; box-shadow: none; }
.btn:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 2px; }
.btn-sm { padding: 5px 11px; font-size: 12px; }

@media (prefers-reduced-motion: reduce) {
  * { animation: none !important; transition: none !important; }
}
</style>
