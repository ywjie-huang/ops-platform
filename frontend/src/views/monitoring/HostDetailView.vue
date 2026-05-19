<template>
  <div>
    <div class="page-header">
      <div style="display:flex;align-items:center;gap:12px">
        <el-button text @click="$router.back()">← 返回</el-button>
        <h2 class="page-title">主机详情</h2>
      </div>
      <div style="display:flex;gap:8px;align-items:center">
        <el-tag v-if="host?.prometheus_ok" type="success" size="small">Prometheus 已连接</el-tag>
        <el-tag v-else type="danger" size="small">Prometheus 未连接</el-tag>
        <el-button type="primary" @click="$router.push(`/monitoring/hosts/${route.params.id}/ssh`)">
          <el-icon><Monitor /></el-icon> SSH 连接
        </el-button>
      </div>
    </div>

    <div v-if="host" class="detail-content">
      <!-- 指标概览 -->
      <div class="stat-grid">
        <div v-for="g in gauges" :key="g.label" class="stat-card">
          <el-progress type="circle" :percentage="g.value" :color="gaugeColor(g.value)" :width="100" :stroke-width="10" />
          <div class="stat-label">{{ g.label }}</div>
          <div class="stat-sub">{{ g.sub }}</div>
        </div>
      </div>

      <!-- 详细数据 -->
      <div class="detail-grid">
        <div class="detail-panel">
          <h3 class="panel-title">🖥️ 系统信息</h3>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="主机名">{{ host.hostname }}</el-descriptions-item>
            <el-descriptions-item label="IP">{{ host.ip }}</el-descriptions-item>
            <el-descriptions-item label="规格">{{ host.spec || '-' }}</el-descriptions-item>
            <el-descriptions-item label="系统">{{ host.os_info || '-' }}</el-descriptions-item>
            <el-descriptions-item label="负责人">{{ host.owner || '-' }}</el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="statusTagType(host.status)" size="small" round>{{ host.status }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="运行时间">{{ formatUptime(host.uptime_hours) }}</el-descriptions-item>
          </el-descriptions>
        </div>

        <div class="detail-panel">
          <h3 class="panel-title">📊 CPU</h3>
          <el-descriptions :column="1" border size="small">
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
        </div>

        <div class="detail-panel">
          <h3 class="panel-title">💾 内存</h3>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="使用率">
              <el-progress :percentage="host.memory?.usage || 0" :color="gaugeColor(host.memory?.usage || 0)" :stroke-width="12" />
            </el-descriptions-item>
            <el-descriptions-item label="总量">{{ host.memory?.total_gb || '-' }} GB</el-descriptions-item>
            <el-descriptions-item label="已用">{{ host.memory?.used_gb || '-' }} GB</el-descriptions-item>
            <el-descriptions-item label="可用">{{ host.memory?.available_gb || '-' }} GB</el-descriptions-item>
          </el-descriptions>
        </div>

        <div class="detail-panel">
          <h3 class="panel-title">💿 磁盘</h3>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="使用率">
              <el-progress :percentage="host.disk?.usage || 0" :color="gaugeColor(host.disk?.usage || 0)" :stroke-width="12" />
            </el-descriptions-item>
            <el-descriptions-item label="总量">{{ host.disk?.total_gb || '-' }} GB</el-descriptions-item>
            <el-descriptions-item label="读速率">{{ host.disk?.read_mb_s || 0 }} MB/s</el-descriptions-item>
            <el-descriptions-item label="写速率">{{ host.disk?.write_mb_s || 0 }} MB/s</el-descriptions-item>
          </el-descriptions>
        </div>

        <div class="detail-panel">
          <h3 class="panel-title">🌐 网络</h3>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="入站流量">{{ host.network?.in_mbps || 0 }} Mbps</el-descriptions-item>
            <el-descriptions-item label="出站流量">{{ host.network?.out_mbps || 0 }} Mbps</el-descriptions-item>
            <el-descriptions-item label="TCP 连接数">{{ host.tcp_connections ?? '-' }}</el-descriptions-item>
          </el-descriptions>
        </div>

        <div class="detail-panel">
          <h3 class="panel-title">⚙️ 进程</h3>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="运行中">{{ host.processes?.running ?? '-' }}</el-descriptions-item>
          </el-descriptions>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onActivated } from 'vue'
import { useRoute } from 'vue-router'
import { Monitor } from '@element-plus/icons-vue'
import { getHostDetail } from '@/api/monitoring'

const route = useRoute()
const host = ref<any>(null)

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
  host.value = null
  const res: any = await getHostDetail(Number(route.params.id))
  host.value = res.data
}

onActivated(fetchDetail)
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.stat-card {
  background: #fff;
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 20px;
  text-align: center;
  transition: box-shadow 0.2s;
}
.stat-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.06); }

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

.detail-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.detail-panel {
  background: #fff;
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 16px 20px;
}

.panel-title {
  font-size: 14px;
  font-weight: 700;
  margin-bottom: 12px;
}

@media (max-width: 1100px) {
  .stat-grid { grid-template-columns: repeat(2, 1fr); }
  .detail-grid { grid-template-columns: repeat(2, 1fr); }
}

@media (max-width: 600px) {
  .stat-grid { grid-template-columns: 1fr; }
  .detail-grid { grid-template-columns: 1fr; }
}
</style>
