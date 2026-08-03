<template>
  <div class="trend-grid" :style="gridStyle">
    <article v-for="card in cards" :key="card.key" class="trend-card">
      <div class="trend-card-head">
        <strong>{{ card.label }}</strong>
        <span>{{ card.state }}</span>
      </div>
      <div v-if="loading" class="trend-placeholder" aria-hidden="true">
        <el-skeleton-item variant="image" class="trend-skeleton" />
      </div>
      <svg
        v-else-if="card.points.length"
        class="trend-chart"
        :viewBox="card.chart.viewBox"
        role="img"
        :aria-label="`${card.label} 趋势`"
      >
        <line
          v-for="(line, i) in card.chart.gridLines"
          :key="`g${i}`"
          :x1="line.x1"
          :x2="line.x2"
          :y1="line.y"
          :y2="line.y"
          class="trend-gridline"
        />
        <text
          v-for="(tick, i) in card.chart.yTicks"
          :key="`t${i}`"
          x="23"
          :y="tick.y"
          class="trend-tick-label"
        >{{ tick.label }}</text>
        <polygon :points="card.chart.areaPoints" class="trend-area" />
        <polyline :points="card.chart.linePoints" class="trend-line" />
        <text
          v-for="(label, i) in card.chart.xLabels"
          :key="`x${i}`"
          :x="label.x"
          :y="label.y"
          :text-anchor="label.anchor"
          class="trend-x-label"
        >{{ label.label }}</text>
      </svg>
      <div v-else class="trend-empty">{{ emptyHint }}</div>
    </article>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { buildTrendChartGeometry, type TrendChartGeometry } from '@/utils/hostDetail'
import type { HostTrendSeries } from '@/api/monitoring'

const props = withDefaults(defineProps<{
  series: HostTrendSeries[]
  loading?: boolean
  rangeMinutes?: number
  emptyHint?: string
  columns?: number
}>(), {
  loading: false,
  rangeMinutes: 60,
  emptyHint: '暂无指标数据',
  columns: 2,
})

const gridStyle = computed(() => ({
  gridTemplateColumns: `repeat(${props.columns}, minmax(0, 1fr))`,
}))

function rangeLabel() {
  const m = props.rangeMinutes
  if (m >= 60) return `-${Math.max(1, Math.round(m / 60))}h`
  return `-${m}m`
}

const cards = computed(() =>
  props.series.map((s) => {
    const points = s.points || []
    const chart: TrendChartGeometry = buildTrendChartGeometry(points, s.unit)
    // x 轴起止标签随窗口长度变化
    chart.xLabels = [
      { label: rangeLabel(), x: 28, y: 68, anchor: 'start' as const },
      { label: 'now', x: 258, y: 68, anchor: 'end' as const },
    ]
    const last = points.length ? points[points.length - 1].value : null
    const state = last === null
      ? '无数据'
      : `${Number.isInteger(last) ? last : Math.round(last * 10) / 10}${s.unit ? ' ' + s.unit : ''}`
    return { key: s.key, label: s.label, unit: s.unit, points, chart, state }
  }),
)
</script>

<style scoped>
.trend-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.trend-card {
  min-width: 0;
  padding: 10px;
  border: 1px solid var(--border-color);
  border-radius: 7px;
}

.trend-card-head {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-size: 12px;
}

.trend-card-head strong,
.trend-card-head span {
  overflow-wrap: anywhere;
}

.trend-card-head span {
  color: var(--text-muted);
}

.trend-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 72px;
  margin-top: 8px;
  border: 1px dashed var(--border-color);
  border-radius: 6px;
  color: var(--text-muted);
  background: color-mix(in srgb, var(--bg-color) 70%, var(--surface-color));
}

.trend-skeleton {
  width: 100%;
  height: 100%;
}

.trend-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 72px;
  margin-top: 8px;
  border: 1px dashed var(--border-color);
  border-radius: 6px;
  color: var(--text-muted);
  font-size: 11px;
  text-align: center;
  padding: 0 8px;
  background: color-mix(in srgb, var(--bg-color) 70%, var(--surface-color));
}

.trend-chart {
  display: block;
  width: 100%;
  height: 72px;
  margin-top: 8px;
  color: var(--primary-color);
}

.trend-gridline {
  stroke: var(--border-color);
  stroke-width: 1;
  vector-effect: non-scaling-stroke;
}

.trend-tick-label,
.trend-x-label {
  fill: var(--text-muted);
  font-size: 8px;
  dominant-baseline: middle;
}

.trend-tick-label {
  text-anchor: end;
}

.trend-x-label {
  dominant-baseline: auto;
}

.trend-line {
  fill: none;
  stroke: currentColor;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.trend-area {
  fill: currentColor;
  opacity: 0.1;
}
</style>
