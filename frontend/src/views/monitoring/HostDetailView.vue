<template>
  <div class="host-detail">
    <header v-if="host" class="detail-header">
      <div class="identity-block">
        <el-button text class="back-btn" aria-label="返回主机列表" @click="router.back()">
          <el-icon><ArrowLeft /></el-icon>
          <span>返回</span>
        </el-button>

        <div class="identity-main">
          <div class="title-row">
            <h2 class="page-title">{{ host.hostname || '未命名主机' }}</h2>
            <span v-if="riskMeta" class="state-chip" :class="`tone-${riskMeta.tone}`">
              {{ riskMeta.label }}
            </span>
            <span v-if="collectionState" class="state-chip" :class="`tone-${collectionState.tone}`">
              {{ collectionState.label }}
            </span>
          </div>
          <div class="host-meta" aria-label="主机元信息">
            <span>{{ host.ip || '-' }}</span>
            <span>{{ host.owner || '未分配负责人' }}</span>
            <span>{{ host.status || '-' }}</span>
            <span>刷新 {{ lastRefreshTime || '-' }}</span>
          </div>
        </div>
      </div>

      <div class="header-actions">
        <el-button :loading="loading" @click="fetchDetail">
          <el-icon><Refresh /></el-icon>
          <span>刷新</span>
        </el-button>
        <el-button @click="copyIp">
          <el-icon><CopyDocument /></el-icon>
          <span>复制 IP</span>
        </el-button>
        <el-button type="primary" @click="goSsh">
          <el-icon><Monitor /></el-icon>
          <span>SSH</span>
        </el-button>
      </div>
    </header>

    <header v-else-if="loading" class="detail-header skeleton-header" aria-label="主机详情加载中">
      <div class="identity-block">
        <el-skeleton-item variant="button" class="skeleton-back" />
        <div class="identity-main">
          <el-skeleton-item variant="h3" class="skeleton-title" />
          <el-skeleton-item variant="text" class="skeleton-meta" />
        </div>
      </div>
      <div class="header-actions">
        <el-skeleton-item v-for="i in 3" :key="i" variant="button" class="skeleton-action" />
      </div>
    </header>

    <div v-if="loadError" class="error-state">
      <el-icon :size="48" class="error-icon"><WarningFilled /></el-icon>
      <p class="error-text">{{ loadError }}</p>
      <el-button type="primary" @click="fetchDetail">重新加载</el-button>
    </div>

    <div v-else-if="loading" class="detail-content" aria-label="正在加载主机详情">
      <div class="hero-grid">
        <section class="panel judgment-panel">
          <el-skeleton :rows="6" animated />
        </section>
        <aside class="panel action-panel">
          <el-skeleton :rows="5" animated />
        </aside>
      </div>
      <div class="diagnostic-grid">
        <section class="panel">
          <el-skeleton :rows="8" animated />
        </section>
        <aside class="panel">
          <el-skeleton :rows="8" animated />
        </aside>
      </div>
    </div>

    <div v-else-if="host" class="detail-content">
      <section v-if="collectionState && !host.prometheus_ok" class="collection-warning" role="status">
        <el-icon><WarningFilled /></el-icon>
        <div>
          <strong>{{ collectionState.label }}</strong>
          <p>{{ collectionState.description }}</p>
        </div>
      </section>

      <div class="hero-grid">
        <section class="panel judgment-panel" :class="currentJudgment ? `tone-${currentJudgment.tone}` : ''">
          <div class="panel-heading">
            <div>
              <span class="section-kicker">当前判断</span>
              <h3>{{ currentJudgment?.title }}</h3>
            </div>
            <span v-if="riskMeta" class="priority-pill" :class="`tone-${riskMeta.tone}`">
              {{ riskMeta.priority }}
            </span>
          </div>
          <p class="judgment-copy">{{ currentJudgment?.description }}</p>

          <div class="metric-grid" role="group" aria-label="主机关键指标">
            <article v-for="card in metricCards" :key="card.key" class="metric-card" :class="`tone-${card.tone}`">
              <div class="metric-card-head">
                <span>{{ card.label }}</span>
                <strong>{{ card.statusText }}</strong>
              </div>
              <div class="metric-value">
                <span>{{ card.value ?? '-' }}</span>
                <small>{{ card.unit }}</small>
              </div>
              <div
                class="metric-track"
                role="meter"
                :aria-label="`${card.label} ${card.statusText}`"
                aria-valuemin="0"
                aria-valuemax="100"
                :aria-valuenow="Math.round(card.barPercent)"
              >
                <span
                  v-for="segment in 10"
                  :key="segment"
                  class="metric-segment"
                  :class="{ active: segment <= metricSegmentCount(card.barPercent) }"
                />
              </div>
              <p>{{ card.detail }}</p>
            </article>
          </div>
        </section>

        <aside class="panel action-panel">
          <div class="panel-heading compact">
            <h3>建议动作</h3>
          </div>
          <div class="recommendation-list">
            <button
              v-for="(item, index) in recommendations"
              :key="item.key"
              type="button"
              class="recommendation-item"
              :class="`tone-${item.tone}`"
              @click="handleRecommendation(item.action)"
            >
              <span class="recommendation-index">{{ index + 1 }}</span>
              <span>
                <strong>{{ item.title }}</strong>
                <small>{{ item.description }}</small>
              </span>
            </button>
          </div>
        </aside>
      </div>

      <div class="diagnostic-grid">
        <section class="panel">
          <div class="panel-heading compact">
            <h3>指标趋势</h3>
            <span>{{ trendMetaText }}</span>
          </div>
          <div class="trend-grid">
            <article v-for="card in trendCards" :key="card.key" class="trend-card">
              <div class="trend-card-head">
                <strong>{{ card.label }}</strong>
                <span>{{ card.state }}{{ card.unit }}</span>
              </div>
              <div v-if="trendLoading" class="trend-placeholder" aria-hidden="true">
                <el-skeleton-item variant="image" class="trend-skeleton" />
              </div>
              <svg
                v-else-if="card.points.length"
                class="trend-chart"
                viewBox="0 0 160 56"
                role="img"
                :aria-label="`${card.label} 最近 1 小时趋势`"
              >
                <polygon :points="trendAreaPoints(card.points)" class="trend-area" />
                <polyline :points="trendLinePoints(card.points)" class="trend-line" />
              </svg>
              <div v-else class="trend-placeholder" aria-hidden="true">
                <el-icon><DataLine /></el-icon>
              </div>
            </article>
          </div>
        </section>

        <aside class="side-stack">
          <section class="panel">
            <div class="panel-heading compact">
              <h3>事件时间线</h3>
              <span>最近 24h</span>
            </div>
            <div class="empty-note">
              <el-icon><Connection /></el-icon>
              <span>事件聚合待接入，后续展示告警、部署、巡检和容器变化。</span>
            </div>
          </section>

          <section class="panel">
            <div class="panel-heading compact">
              <h3>关联跳转</h3>
            </div>
            <div class="relation-list">
              <span v-for="card in relationCards" :key="card.key" class="relation-item">
                <strong>{{ card.label }}</strong>
                <small>{{ card.value }}</small>
              </span>
            </div>
          </section>
        </aside>
      </div>

      <section class="steady-section">
        <div class="panel-heading compact">
          <h3>稳态详情</h3>
        </div>
        <div class="steady-grid">
          <article v-for="group in steadyDetailGroups" :key="group.key" class="panel detail-panel">
            <h4>{{ group.title }}</h4>
            <dl class="kv-list">
              <template v-for="row in group.rows" :key="row.label">
                <dt>{{ row.label }}</dt>
                <dd>{{ row.value }}</dd>
              </template>
            </dl>
          </article>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onActivated } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  ArrowLeft,
  Connection,
  CopyDocument,
  DataLine,
  Monitor,
  Refresh,
  WarningFilled,
} from '@element-plus/icons-vue'
import { getHostDetail, getHostTrends } from '@/api/monitoring'
import type { HostDetail, HostTrendData, HostTrendPoint } from '@/api/monitoring'
import {
  buildCollectionState,
  buildCurrentJudgment,
  buildHostMetricCards,
  buildHostRecommendations,
  buildRelationCards,
  buildSteadyDetailGroups,
  buildTrendCards,
  getHostRiskMeta,
} from '@/utils/hostDetail'

const route = useRoute()
const router = useRouter()
const host = ref<HostDetail | null>(null)
const loading = ref(false)
const trendLoading = ref(false)
const loadError = ref('')
const lastRefreshTime = ref('')
const trendData = ref<HostTrendData | null>(null)

const riskMeta = computed(() => host.value ? getHostRiskMeta(host.value) : null)
const collectionState = computed(() => host.value ? buildCollectionState(host.value) : null)
const currentJudgment = computed(() => host.value ? buildCurrentJudgment(host.value) : null)
const metricCards = computed(() => host.value ? buildHostMetricCards(host.value) : [])
const recommendations = computed(() => host.value ? buildHostRecommendations(host.value) : [])
const trendCards = computed(() => {
  if (!host.value) return []
  const trendMap = new Map((trendData.value?.series || []).map((series) => [series.key, series]))
  return buildTrendCards(host.value).map((card) => {
    const series = trendMap.get(card.key)
    const points = series?.points || []
    const lastPoint = points[points.length - 1]
    return {
      ...card,
      points,
      unit: series?.unit || card.unit,
      state: points.length ? `${lastPoint?.value ?? '-'} ` : card.state,
    }
  })
})
const relationCards = computed(() => host.value ? buildRelationCards(host.value) : [])
const steadyDetailGroups = computed(() => host.value ? buildSteadyDetailGroups(host.value) : [])
const trendMetaText = computed(() => {
  if (trendLoading.value) return '加载中'
  return trendData.value?.series?.some((series) => series.points.length) ? '最近 1 小时' : '暂无历史趋势'
})

function formatTime(date: Date) {
  return `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}:${date.getSeconds().toString().padStart(2, '0')}`
}

function metricSegmentCount(percent: number) {
  if (!percent) return 0
  return Math.min(10, Math.max(1, Math.ceil(percent / 10)))
}

function trendLinePoints(points: HostTrendPoint[]) {
  if (!points.length) return ''
  const width = 160
  const height = 56
  const padding = 4
  const values = points.map((point) => point.value)
  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = max - min || 1
  const step = (width - padding * 2) / (points.length - 1 || 1)
  return points.map((point, index) => {
    const x = padding + index * step
    const y = height - padding - ((point.value - min) / range) * (height - padding * 2)
    return `${x},${y}`
  }).join(' ')
}

function trendAreaPoints(points: HostTrendPoint[]) {
  const linePoints = trendLinePoints(points)
  if (!linePoints) return ''
  return `${linePoints} 156,56 4,56`
}

function goSsh() {
  router.push(`/monitoring/hosts/${route.params.id}/ssh`)
}

async function copyIp() {
  if (!host.value?.ip) return
  try {
    await navigator.clipboard.writeText(host.value.ip)
    ElMessage.success('IP 已复制')
  } catch {
    ElMessage.warning('复制失败，请手动复制 IP')
  }
}

async function copySummary() {
  if (!host.value) return
  const summary = [
    `主机：${host.value.hostname || '-'}`,
    `IP：${host.value.ip || '-'}`,
    `风险：${riskMeta.value?.label || '-'}`,
    `判断：${currentJudgment.value?.title || '-'}`,
    `负责人：${host.value.owner || '未分配负责人'}`,
  ].join('\n')

  try {
    await navigator.clipboard.writeText(summary)
    ElMessage.success('排障摘要已复制')
  } catch {
    ElMessage.warning('复制失败，请手动复制摘要')
  }
}

function handleRecommendation(action: string) {
  if (action === 'ssh') {
    goSsh()
    return
  }
  if (action === 'inspect') {
    ElMessage.info('关联检查项待接入，可先查看下方趋势和事件区域')
    return
  }
  if (action === 'copy') {
    copySummary()
  }
}

async function fetchDetail() {
  const isInitialLoad = !host.value
  loading.value = true
  loadError.value = ''
  if (isInitialLoad) {
    host.value = null
  }
  try {
    const res: any = await getHostDetail(Number(route.params.id))
    host.value = res.data
    lastRefreshTime.value = formatTime(new Date())
  } catch (e: any) {
    loadError.value = e?.message || '加载主机详情失败，请检查网络或稍后重试'
  } finally {
    loading.value = false
  }
}

async function fetchTrends() {
  trendLoading.value = true
  try {
    const res: any = await getHostTrends(Number(route.params.id), { minutes: 60, step_seconds: 60 })
    trendData.value = res.data
  } catch {
    trendData.value = null
  } finally {
    trendLoading.value = false
  }
}

onActivated(() => {
  fetchDetail()
  fetchTrends()
})
</script>

<style scoped>
.host-detail {
  min-height: 100%;
}

.detail-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.identity-block {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  min-width: 0;
}

.back-btn {
  flex-shrink: 0;
  gap: 4px;
}

.identity-main {
  min-width: 0;
}

.title-row,
.header-actions,
.metric-card-head,
.panel-heading {
  display: flex;
  align-items: center;
}

.title-row {
  flex-wrap: wrap;
  gap: 8px;
}

.page-title {
  margin: 0;
  color: var(--text-primary);
  font-size: 20px;
  font-weight: 700;
  overflow-wrap: anywhere;
}

.host-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 12px;
  margin-top: 5px;
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.5;
}

.header-actions {
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.header-actions :deep(.el-button) {
  min-width: 0;
}

.state-chip,
.priority-pill {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  max-width: 100%;
  padding: 0 9px;
  border: 1px solid var(--border-color);
  border-radius: 999px;
  background: var(--surface-color);
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 650;
  line-height: 1.2;
  overflow-wrap: anywhere;
}

.tone-success {
  --tone-color: var(--success-color);
  --tone-bg: color-mix(in srgb, var(--success-color) 8%, var(--surface-color));
  --tone-border: color-mix(in srgb, var(--success-color) 22%, var(--border-color));
  --tone-text: color-mix(in srgb, var(--success-color) 76%, black);
}

.tone-warning {
  --tone-color: var(--warning-color);
  --tone-bg: color-mix(in srgb, var(--warning-color) 10%, var(--surface-color));
  --tone-border: color-mix(in srgb, var(--warning-color) 24%, var(--border-color));
  --tone-text: color-mix(in srgb, var(--warning-color) 72%, black);
}

.tone-danger {
  --tone-color: var(--danger-color);
  --tone-bg: color-mix(in srgb, var(--danger-color) 8%, var(--surface-color));
  --tone-border: color-mix(in srgb, var(--danger-color) 22%, var(--border-color));
  --tone-text: color-mix(in srgb, var(--danger-color) 80%, black);
}

.tone-muted {
  --tone-color: var(--text-muted);
  --tone-bg: color-mix(in srgb, var(--text-muted) 8%, var(--surface-color));
  --tone-border: color-mix(in srgb, var(--text-muted) 18%, var(--border-color));
  --tone-text: var(--text-secondary);
}

.state-chip,
.priority-pill,
.metric-card,
.recommendation-item {
  border-color: var(--tone-border, var(--border-color));
  background: var(--tone-bg, var(--surface-color));
  color: var(--tone-text, var(--text-secondary));
}

.detail-content {
  display: grid;
  gap: 12px;
}

.hero-grid,
.diagnostic-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 12px;
}

.panel,
.collection-warning {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
}

.panel {
  padding: 14px;
}

.collection-warning {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  padding: 12px 14px;
  color: color-mix(in srgb, var(--danger-color) 82%, black);
  background: color-mix(in srgb, var(--danger-color) 7%, var(--surface-color));
  border-color: color-mix(in srgb, var(--danger-color) 20%, var(--border-color));
}

.collection-warning p {
  margin: 3px 0 0;
  color: var(--text-secondary);
  font-size: 12px;
}

.judgment-panel {
  border-color: var(--tone-border, var(--border-color));
}

.panel-heading {
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.panel-heading.compact {
  align-items: baseline;
}

.panel-heading h3 {
  margin: 0;
  color: var(--text-primary);
  font-size: 15px;
}

.panel-heading span {
  color: var(--text-muted);
  font-size: 12px;
}

.section-kicker {
  display: block;
  margin-bottom: 4px;
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 600;
}

.judgment-copy {
  margin: 0 0 12px;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.6;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.metric-card {
  min-width: 0;
  padding: 10px;
  border: 1px solid var(--tone-border, var(--border-color));
  border-radius: var(--border-radius);
}

.metric-card-head {
  justify-content: space-between;
  gap: 8px;
  color: var(--text-secondary);
  font-size: 12px;
}

.metric-card-head strong {
  color: var(--tone-text, var(--text-secondary));
  font-weight: 700;
}

.metric-value {
  display: flex;
  align-items: baseline;
  gap: 3px;
  margin-top: 6px;
  color: var(--text-primary);
}

.metric-value span {
  font-size: 24px;
  font-weight: 750;
  line-height: 1;
}

.metric-value small {
  color: var(--text-muted);
  font-size: 12px;
}

.metric-track {
  display: grid;
  grid-template-columns: repeat(10, minmax(0, 1fr));
  gap: 2px;
  height: 5px;
  margin-top: 8px;
}

.metric-segment {
  border-radius: 999px;
  background: color-mix(in srgb, var(--border-color) 72%, var(--bg-color));
}

.metric-segment.active {
  background: var(--tone-color, var(--primary-color));
}

.metric-card p {
  margin: 7px 0 0;
  color: var(--text-muted);
  font-size: 11px;
  overflow-wrap: anywhere;
}

.recommendation-list,
.side-stack {
  display: grid;
  gap: 8px;
}

.recommendation-item {
  appearance: none;
  display: grid;
  grid-template-columns: 22px 1fr;
  gap: 8px;
  width: 100%;
  min-width: 0;
  padding: 9px;
  font: inherit;
  border: 1px solid var(--tone-border, var(--border-color));
  border-radius: 7px;
  text-align: left;
  cursor: pointer;
  transition: border-color 180ms ease-out, background-color 180ms ease-out;
}

.recommendation-item:hover {
  border-color: var(--primary-color);
  background: color-mix(in srgb, var(--primary-color) 5%, var(--surface-color));
}

.recommendation-item:active {
  background: color-mix(in srgb, var(--primary-color) 8%, var(--surface-color));
}

.recommendation-index {
  font-weight: 750;
}

.recommendation-item strong,
.recommendation-item small {
  display: block;
  overflow-wrap: anywhere;
}

.recommendation-item strong {
  color: var(--text-primary);
  font-size: 12px;
}

.recommendation-item small {
  margin-top: 3px;
  color: var(--text-secondary);
  font-size: 11px;
  line-height: 1.4;
}

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
  height: 56px;
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

.trend-chart {
  display: block;
  width: 100%;
  height: 56px;
  margin-top: 8px;
  color: var(--primary-color);
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

.empty-note {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.5;
}

.empty-note span {
  min-width: 0;
  overflow-wrap: anywhere;
}

.relation-list {
  display: grid;
  gap: 7px;
}

.relation-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-secondary);
  font-size: 12px;
}

.relation-item strong {
  min-width: 0;
  color: var(--text-primary);
  overflow-wrap: anywhere;
}

.relation-item small {
  flex-shrink: 0;
  color: var(--text-muted);
}

.steady-section {
  display: grid;
  gap: 10px;
}

.steady-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.detail-panel h4 {
  margin: 0 0 10px;
  color: var(--text-primary);
  font-size: 13px;
}

.kv-list {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 8px 12px;
  margin: 0;
  font-size: 12px;
}

.kv-list dt {
  color: var(--text-muted);
}

.kv-list dd {
  min-width: 0;
  color: var(--text-primary);
  font-weight: 600;
  overflow-wrap: anywhere;
}

.skeleton-header {
  align-items: center;
}

.skeleton-back {
  width: 68px;
}

.skeleton-title {
  width: min(280px, 58vw);
}

.skeleton-meta {
  width: min(420px, 72vw);
  margin-top: 8px;
}

.skeleton-action {
  width: 82px;
}

.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  text-align: center;
}

.error-icon {
  margin-bottom: 16px;
  color: var(--danger-color);
}

.error-text {
  max-width: 400px;
  margin-bottom: 20px;
  color: var(--text-secondary);
  font-size: 14px;
}

:focus-visible {
  outline: 2px solid var(--primary-color);
  outline-offset: 2px;
  border-radius: 4px;
}

@media (prefers-reduced-motion: reduce) {
  .recommendation-item {
    transition: none;
  }
}

@media (max-width: 1180px) {
  .hero-grid,
  .diagnostic-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 860px) {
  .detail-header {
    flex-direction: column;
  }

  .header-actions {
    justify-content: flex-start;
    width: 100%;
  }

  .metric-grid,
  .trend-grid,
  .steady-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 560px) {
  .identity-block {
    width: 100%;
  }

  .metric-grid,
  .trend-grid,
  .steady-grid {
    grid-template-columns: 1fr;
  }

  .header-actions :deep(.el-button) {
    flex: 1 1 auto;
    min-height: 44px;
  }

  .recommendation-item {
    min-height: 44px;
    padding: 10px;
  }
}
</style>
