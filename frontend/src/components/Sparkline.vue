<template>
  <svg :width="width" :height="height" :viewBox="`0 0 ${width} ${height}`">
    <polyline
      :points="points"
      fill="none"
      :stroke="color"
      stroke-width="1.5"
      stroke-linecap="round"
      stroke-linejoin="round"
    />
    <polygon
      :points="areaPoints"
      :fill="color"
      fill-opacity="0.1"
    />
  </svg>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  data: number[]
  color?: string
  width?: number
  height?: number
}>(), {
  color: '#3b82f6',
  width: 80,
  height: 32,
})

const points = computed(() => {
  const { data, width, height } = props
  if (!data.length) return ''
  const max = Math.max(...data, 1)
  const min = Math.min(...data, 0)
  const range = max - min || 1
  const step = width / (data.length - 1 || 1)
  return data.map((v, i) => {
    const x = i * step
    const y = height - ((v - min) / range) * (height - 4) - 2
    return `${x},${y}`
  }).join(' ')
})

const areaPoints = computed(() => {
  const { data, width, height } = props
  if (!data.length) return ''
  const max = Math.max(...data, 1)
  const min = Math.min(...data, 0)
  const range = max - min || 1
  const step = width / (data.length - 1 || 1)
  const linePoints = data.map((v, i) => {
    const x = i * step
    const y = height - ((v - min) / range) * (height - 4) - 2
    return `${x},${y}`
  }).join(' ')
  return `${linePoints} ${width},${height} 0,${height}`
})
</script>
