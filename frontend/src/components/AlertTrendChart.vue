<template>
  <div class="alert-trend">
    <svg :width="width" :height="height" :viewBox="`0 0 ${width} ${height}`" class="chart-svg">
      <defs>
        <linearGradient :id="gradId" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#e5484d" stop-opacity="0.1" />
          <stop offset="100%" stop-color="#e5484d" stop-opacity="0" />
        </linearGradient>
      </defs>
      <polygon :points="areaPoints" :fill="`url(#${gradId})`" />
      <polyline :points="linePoints" fill="none" stroke="#e5484d" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
    </svg>
    <div class="chart-labels">
      <span v-for="d in dates" :key="d">{{ d }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  dates: string[]
  counts: number[]
  width?: number
  height?: number
}>(), {
  width: 280,
  height: 60,
})

const gradId = `trendGrad_${Math.random().toString(36).slice(2, 8)}`
const padding = { top: 8, right: 8, bottom: 0, left: 8 }
const chartWidth = computed(() => props.width - padding.left - padding.right)
const chartHeight = computed(() => props.height - padding.top - padding.bottom)
const maxVal = computed(() => Math.max(...props.counts, 1))

const points = computed(() => {
  const { counts } = props
  if (!counts.length) return []
  const step = chartWidth.value / (counts.length - 1 || 1)
  return counts.map((v, i) => ({
    x: padding.left + i * step,
    y: padding.top + chartHeight.value - (v / maxVal.value) * chartHeight.value,
  }))
})

const linePoints = computed(() => points.value.map(p => `${p.x},${p.y}`).join(' '))
const areaPoints = computed(() => {
  const pts = points.value
  if (!pts.length) return ''
  const last = pts[pts.length - 1]
  const first = pts[0]
  return `${linePoints.value} ${last.x},${padding.top + chartHeight.value} ${first.x},${padding.top + chartHeight.value}`
})
</script>

<style scoped>
.alert-trend {
  padding: 0 16px 12px;
}
.chart-svg {
  display: block;
}
.chart-labels {
  display: flex;
  justify-content: space-between;
  margin-top: 8px;
  font-size: 10px;
  color: #bbb;
  font-family: 'SF Mono', 'Cascadia Code', monospace;
}
</style>
