<template>
  <div class="alert-trend">
    <div class="chart-header">
      <span class="chart-title">告警趋势</span>
      <span class="chart-subtitle">近 7 天</span>
    </div>
    <svg :width="width" :height="height" :viewBox="`0 0 ${width} ${height}`" class="chart-svg">
      <!-- 面积 -->
      <polygon :points="areaPoints" fill="#ef4444" fill-opacity="0.08" />
      <!-- 线条 -->
      <polyline :points="linePoints" fill="none" stroke="#ef4444" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
      <!-- 数据点 -->
      <circle
        v-for="(p, i) in dotPositions"
        :key="i"
        :cx="p.x"
        :cy="p.y"
        r="3"
        fill="#fff"
        stroke="#ef4444"
        stroke-width="1.5"
      />
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
  height: 100,
})

const padding = { top: 10, right: 10, bottom: 0, left: 10 }

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

const dotPositions = computed(() => points.value)
</script>

<style scoped>
.alert-trend {
  background: #fff;
  border-radius: 10px;
  padding: 16px;
  border: 1px solid var(--border-color, #e5e7eb);
}
.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.chart-title {
  font-size: 14px;
  font-weight: 700;
  color: #1e293b;
}
.chart-subtitle {
  font-size: 12px;
  color: #94a3b8;
}
.chart-svg {
  display: block;
}
.chart-labels {
  display: flex;
  justify-content: space-between;
  margin-top: 8px;
  font-size: 11px;
  color: #94a3b8;
}
</style>
