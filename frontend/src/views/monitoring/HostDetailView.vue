<template>
  <div class="host-detail">
    <header class="page-header">
      <div class="page-header-left">
        <el-button text class="back-btn" @click="$router.back()">
          <el-icon><ArrowLeft /></el-icon>
          <span>返回</span>
        </el-button>
        <h2 class="page-title">主机详情</h2>
      </div>
      <div class="page-header-right">
        <el-tag v-if="host?.prometheus_ok" type="success" size="small">Prometheus 已连接</el-tag>
        <el-tag v-else type="danger" size="small">Prometheus 未连接</el-tag>
        <el-button type="primary" @click="$router.push(`/monitoring/hosts/${route.params.id}/ssh`)">
          <el-icon><Monitor /></el-icon>
          <span>SSH 连接</span>
        </el-button>
      </div>
    </header>

    <!-- 错误状态 -->
    <div v-if="loadError" class="error-state">
      <el-icon :size="48" class="error-icon"><WarningFilled /></el-icon>
      <p class="error-text">{{ loadError }}</p>
      <el-button type="primary" @click="fetchDetail">重新加载</el-button>
    </div>

    <!-- 加载骨架屏 -->
    <div v-else-if="loading" class="detail-content">
      <div class="stat-grid">
        <div v-for="i in 4" :key="i" class="stat-card">
          <el-skeleton :loading="true" animated>
            <template #template>
              <div class="skeleton-gauge">
                <el-skeleton-item variant="circle" class="skeleton-circle" />
                <el-skeleton-item variant="text" class="skeleton-label" />
                <el-skeleton-item variant="text" class="skeleton-sub" />
              </div>
            </template>
          </el-skeleton>
        </div>
      </div>
      <div class="detail-grid">
        <div v-for="i in 5" :key="i" class="detail-panel">
          <el-skeleton :loading="true" animated>
            <template #template>
              <el-skeleton-item variant="text" class="skeleton-panel-title" />
              <div v-for="j in 3" :key="j" class="skeleton-row">
                <el-skeleton-item variant="text" class="skeleton-row-label" />
                <el-skeleton-item variant="text" class="skeleton-row-value" />
              </div>
            </template>
          </el-skeleton>
        </div>
      </div>
    </div>

    <!-- 正常内容 -->
    <div v-else-if="host" class="detail-content">
      <!-- 指标概览 -->
      <h3 class="section-heading">指标概览</h3>
      <div class="stat-grid" role="group" aria-label="主机指标概览">
        <div v-for="g in gauges" :key="g.label" class="stat-card">
          <el-progress
            type="circle"
            :percentage="g.value"
            :color="gaugeColor(g.value)"
            :width="100"
            :stroke-width="10"
            :aria-label="`${g.label} 使用率 ${g.value}%`"
          />
          <div class="stat-label">{{ g.label }}</div>
          <div class="stat-sub">{{ g.sub }}</div>
        </div>
      </div>

      <!-- 详细数据 -->
      <h3 class="section-heading">详细信息</h3>
      <div class="detail-grid">
        <section class="detail-panel">
          <h4 class="panel-title">
            <el-icon><InfoFilled /></el-icon>
            <span>系统信息</span>
          </h4>
          <el-descriptions :column="1" border size="small" aria-label="系统信息">
            <el-descriptions-item label="主机名">{{ host.hostname }}</el-descriptions-item>
            <el-descriptions-item label="IP">{{ host.ip }}</el-descriptions-item>
            <el-descriptions-item label="规格">{{ host.spec || '-' }}</el-descriptions-item>
            <el-descriptions-item label="系统">{{ host.os_info || '-' }}</el-descriptions-item>
            <el-descriptions-item label="负责人">{{ host.owner || '-' }}</el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="statusTagType(host.status)" size="small" round>{{ host.status }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="运行时间">{{ formatUptime(host.uptime_hours) }}</el-descriptions-item>
            <el-descriptions-item label="运行进程">{{ host.processes?.running ?? '-' }}</el-descriptions-item>
          </el-descriptions>
        </section>

        <section class="detail-panel">
          <h4 class="panel-title">
            <el-icon><Odometer /></el-icon>
            <span>CPU</span>
          </h4>
          <el-descriptions :column="1" border size="small" aria-label="CPU 详情">
            <el-descriptions-item label="使用率">
              <el-progress :percentage="host.cpu?.usage || 0" :color="gaugeColor(host.cpu?.usage || 0)" :stroke-width="12" />
            </el-descriptions-item>
            <el-descriptions-item label="核心数">{{ host.cpu?.cores || '-' }} 核</el-descriptions-item>
            <el-descriptions-item label="系统负载">
              <div>1m: {{ host.load?.['1m'] ?? '-' }}</div>
              <div>5m: {{ host.load?.['5m'] ?? '-' }}</div>
              <div>15m: {{ host.load?.['15m'] ?? '-' }}</div>
            </el-descriptions-item>
          </el-descriptions>
        </section>

        <section class="detail-panel">
          <h4 class="panel-title">
            <el-icon><Coin /></el-icon>
            <span>内存</span>
          </h4>
          <el-descriptions :column="1" border size="small" aria-label="内存详情">
            <el-descriptions-item label="使用率">
              <el-progress :percentage="host.memory?.usage || 0" :color="gaugeColor(host.memory?.usage || 0)" :stroke-width="12" />
            </el-descriptions-item>
            <el-descriptions-item label="总量">{{ host.memory?.total_gb || '-' }} GB</el-descriptions-item>
            <el-descriptions-item label="已用">{{ host.memory?.used_gb || '-' }} GB</el-descriptions-item>
            <el-descriptions-item label="可用">{{ host.memory?.available_gb || '-' }} GB</el-descriptions-item>
          </el-descriptions>
        </section>

        <section class="detail-panel">
          <h4 class="panel-title">
            <el-icon><Box /></el-icon>
            <span>磁盘</span>
          </h4>
          <el-descriptions :column="1" border size="small" aria-label="磁盘详情">
            <el-descriptions-item label="使用率">
              <el-progress :percentage="host.disk?.usage || 0" :color="gaugeColor(host.disk?.usage || 0)" :stroke-width="12" />
            </el-descriptions-item>
            <el-descriptions-item label="总量">{{ host.disk?.total_gb || '-' }} GB</el-descriptions-item>
            <el-descriptions-item label="读速率">{{ host.disk?.read_mb_s || 0 }} MB/s</el-descriptions-item>
            <el-descriptions-item label="写速率">{{ host.disk?.write_mb_s || 0 }} MB/s</el-descriptions-item>
          </el-descriptions>
        </section>

        <section class="detail-panel">
          <h4 class="panel-title">
            <el-icon><Connection /></el-icon>
            <span>网络</span>
          </h4>
          <el-descriptions :column="1" border size="small" aria-label="网络详情">
            <el-descriptions-item label="入站流量">{{ host.network?.in_mbps || 0 }} Mbps</el-descriptions-item>
            <el-descriptions-item label="出站流量">{{ host.network?.out_mbps || 0 }} Mbps</el-descriptions-item>
            <el-descriptions-item label="TCP 连接数">{{ host.tcp_connections ?? '-' }}</el-descriptions-item>
          </el-descriptions>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onActivated } from 'vue'
import { useRoute } from 'vue-router'
import {
  Monitor, ArrowLeft, WarningFilled, InfoFilled,
  Odometer, Coin, Box, Connection,
} from '@element-plus/icons-vue'
import { getHostDetail } from '@/api/monitoring'
import type { HostDetail } from '@/api/monitoring'

const route = useRoute()
const host = ref<HostDetail | null>(null)
const loading = ref(false)
const loadError = ref('')

const gauges = computed(() => {
  if (!host.value) return []
  return [
    { label: 'CPU', value: host.value.cpu?.usage || 0, sub: `${host.value.cpu?.cores || 0} 核` },
    { label: '内存', value: host.value.memory?.usage || 0, sub: `${host.value.memory?.used_gb || 0}/${host.value.memory?.total_gb || 0} GB` },
    { label: '磁盘', value: host.value.disk?.usage || 0, sub: `${host.value.disk?.total_gb || 0} GB` },
    { label: '负载', value: Math.min(Math.round((host.value.load?.['1m'] || 0) * 15), 100), sub: `1m: ${host.value.load?.['1m'] ?? '-'}` },
  ]
})

const gaugeColor = (v: number) => v > 90 ? '#ef4444' : v > 70 ? '#f59e0b' : '#22c55e'

function statusTagType(status: string) {
  return { '使用中': 'success', '已关机': 'warning', '已删除': 'info' }[status] || 'info'
}

function formatUptime(hours: number) {
  if (!hours) return '-'
  if (hours < 24) return `${hours} 小时`
  const days = Math.floor(hours / 24)
  const h = hours % 24
  return days > 0 ? `${days} 天 ${h} 小时` : `${h} 小时`
}

async function fetchDetail() {
  loading.value = true
  loadError.value = ''
  host.value = null
  try {
    const res: any = await getHostDetail(Number(route.params.id))
    host.value = res.data
  } catch (e: any) {
    loadError.value = e?.message || '加载主机详情失败，请检查网络或稍后重试'
  } finally {
    loading.value = false
  }
}

onActivated(fetchDetail)
</script>

<style scoped>
.host-detail {
  min-height: 100%;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 16px;
}

.page-header-left,
.page-header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.back-btn {
  gap: 4px;
}

/* 分组标题 */
.section-heading {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 12px;
}

.section-heading:not(:first-of-type) {
  margin-top: 24px;
}

/* 加载骨架屏 */
.skeleton-gauge {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.skeleton-circle {
  width: 100px;
  height: 100px;
}

.skeleton-label {
  width: 60px;
  margin-top: 10px;
}

.skeleton-sub {
  width: 80px;
  margin-top: 4px;
}

.skeleton-panel-title {
  width: 100px;
  height: 18px;
  margin-bottom: 12px;
}

.skeleton-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
}

.skeleton-row-label {
  width: 60px;
}

.skeleton-row-value {
  width: 120px;
}

/* 错误状态 */
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  text-align: center;
}

.error-icon {
  color: var(--danger-color);
  margin-bottom: 16px;
}

.error-text {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 20px;
  max-width: 400px;
}

/* 指标卡片网格 */
.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.stat-card {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 20px;
  text-align: center;
  transition: box-shadow 0.2s ease-out;
}

.stat-card:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
}

.stat-label {
  font-size: 14px;
  font-weight: 700;
  margin-top: 10px;
}

.stat-sub {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 2px;
}

/* 详情面板网格 */
.detail-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.detail-panel {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 16px 20px;
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 700;
  margin-bottom: 12px;
  color: var(--text-primary);
}

.panel-title .el-icon {
  font-size: 16px;
  color: var(--text-secondary);
}

/* 键盘焦点指示器 */
:focus-visible {
  outline: 2px solid var(--primary-color);
  outline-offset: 2px;
  border-radius: 4px;
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .stat-card {
    transition: none;
  }
}

/* 响应式 */
@media (max-width: 1100px) {
  .stat-grid { grid-template-columns: repeat(2, 1fr); }
  .detail-grid { grid-template-columns: repeat(2, 1fr); }
}

@media (max-width: 600px) {
  .stat-grid { grid-template-columns: 1fr; }
  .detail-grid { grid-template-columns: 1fr; }
}
</style>
