<template>
  <div class="host-cell">
    <span v-if="loading" class="host-loading">加载中...</span>
    <div v-else-if="hosts.length > 0" class="host-tags">
      <el-tag
        v-for="host in visibleHosts"
        :key="host.id"
        size="small"
        type="primary"
        effect="plain"
        class="host-tag"
        :title="host.ip"
        tabindex="0"
        role="link"
        :aria-label="`跳转到主机 ${host.name}（${host.ip}）`"
        @click.stop="$emit('navigate', host.id)"
        @keydown.enter.stop="$emit('navigate', host.id)"
        @keydown.space.stop="$emit('navigate', host.id)"
      >
        {{ host.name }}
      </el-tag>
      <el-tag
        v-if="!expanded && hosts.length > 3"
        size="small"
        type="info"
        effect="plain"
        class="host-tag host-tag-more"
        tabindex="0"
        role="button"
        :aria-label="`展开更多主机，还有 ${hosts.length - 3} 台`"
        :aria-expanded="false"
        @click.stop="$emit('toggleExpand')"
        @keydown.enter.stop="$emit('toggleExpand')"
        @keydown.space.stop="$emit('toggleExpand')"
      >
        +{{ hosts.length - 3 }}
      </el-tag>
      <el-tag
        v-else-if="expanded && hosts.length > 3"
        size="small"
        type="info"
        effect="plain"
        class="host-tag host-tag-more"
        tabindex="0"
        role="button"
        aria-label="收起主机列表"
        :aria-expanded="true"
        @click.stop="$emit('toggleExpand')"
        @keydown.enter.stop="$emit('toggleExpand')"
        @keydown.space.stop="$emit('toggleExpand')"
      >
        收起
      </el-tag>
    </div>
    <span v-else class="host-empty">—</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Host {
  id: number
  name: string
  ip: string
}

const props = defineProps<{
  hosts: Host[]
  expanded: boolean
  loading: boolean
}>()

defineEmits<{
  navigate: [hostId: number]
  toggleExpand: []
}>()

const visibleHosts = computed(() =>
  props.expanded ? props.hosts : props.hosts.slice(0, 3)
)
</script>

<style scoped>
.host-cell {
  min-height: 24px;
  display: flex;
  align-items: center;
}

.host-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.host-tag {
  cursor: pointer;
  transition: opacity 0.2s;
}

.host-tag:focus-visible {
  outline: 2px solid var(--primary-color);
  outline-offset: 2px;
}

.host-tag:hover {
  opacity: 0.8;
}

.host-tag-more {
  cursor: pointer;
}

.host-empty {
  color: var(--text-secondary);
  font-size: 13px;
}

.host-loading {
  color: var(--text-muted);
  font-size: 12px;
}
</style>
