<template>
  <div class="dashboard">
    <!-- 欢迎栏 -->
    <div class="welcome-bar">
      <div>
        <h2>👋 早上好，{{ authStore.fullName || '管理员' }}</h2>
        <p>这是你的运维管理平台概览</p>
      </div>
      <div class="welcome-time">{{ currentTime }}</div>
    </div>

    <!-- 核心指标卡片 -->
    <div class="stat-grid">
      <div v-for="(card, i) in statCards" :key="card.label" class="stat-card" :style="{ background: card.bg }">
        <div class="stat-card-left">
          <div class="stat-card-label">{{ card.label }}</div>
          <div class="stat-card-value">{{ card.value }}</div>
          <div class="stat-card-desc">{{ card.desc }}</div>
        </div>
        <div class="stat-card-icon" :style="{ color: card.iconColor }">
          <el-icon :size="40"><component :is="card.icon" /></el-icon>
        </div>
      </div>
    </div>

    <!-- 快捷统计条 -->
    <div class="quick-bar">
      <div v-for="item in summary.quick_stats" :key="item.label" class="quick-item">
        <span class="quick-dot" :class="'dot-' + item.tone"></span>
        <span class="quick-label">{{ item.label }}</span>
        <span class="quick-value">{{ item.value }}</span>
      </div>
    </div>

    <!-- 主内容区 -->
    <div class="dashboard-grid">
      <!-- 左侧：最近资产 + 最近工单 -->
      <div class="dashboard-main">
        <!-- 最近资产变更 -->
        <div class="panel">
          <div class="panel-header">
            <h3>🖥️ 最近资产变更</h3>
            <el-button text size="small" @click="$router.push('/assets/list')">查看全部 →</el-button>
          </div>
          <div class="compact-list">
            <div v-for="item in summary.recent_asset_changes" :key="item.title" class="compact-item">
              <div class="compact-dot" :class="'dot-' + item.tone"></div>
              <div class="compact-body">
                <div class="compact-title">{{ item.title }}</div>
                <div class="compact-meta">{{ item.meta }}</div>
              </div>
              <el-tag :type="tagType(item.tone)" size="small" round>{{ item.tag }}</el-tag>
            </div>
            <div v-if="!summary.recent_asset_changes?.length" class="empty-hint">暂无数据</div>
          </div>
        </div>

        <!-- 最近工单 -->
        <div class="panel">
          <div class="panel-header">
            <h3>📋 最近工单</h3>
            <el-button text size="small" @click="$router.push('/tickets')">查看全部 →</el-button>
          </div>
          <div class="compact-list">
            <div v-for="item in summary.recent_tickets" :key="item.title" class="compact-item">
              <div class="compact-dot" :class="'dot-' + item.tone"></div>
              <div class="compact-body">
                <div class="compact-title">{{ item.title }}</div>
                <div class="compact-meta">{{ item.meta }}</div>
              </div>
              <el-tag :type="tagType(item.tone)" size="small" round>{{ item.tag }}</el-tag>
            </div>
            <div v-if="!summary.recent_tickets?.length" class="empty-hint">暂无工单</div>
          </div>
        </div>
      </div>

      <!-- 右侧：告警 + 角色 + 类型 -->
      <div class="dashboard-side">
        <!-- 最近告警 -->
        <div class="panel">
          <div class="panel-header">
            <h3>🔔 最近告警</h3>
            <el-button text size="small" @click="$router.push('/monitoring/events')">查看全部 →</el-button>
          </div>
          <div class="compact-list">
            <div v-for="item in summary.recent_alerts" :key="item.title" class="compact-item">
              <div class="compact-dot" :class="'dot-' + item.tone"></div>
              <div class="compact-body">
                <div class="compact-title">{{ item.title }}</div>
                <div class="compact-meta">{{ item.meta }}</div>
              </div>
              <el-tag :type="tagType(item.tone)" size="small" round>{{ item.tag }}</el-tag>
            </div>
            <div v-if="!summary.recent_alerts?.length" class="empty-hint">暂无告警</div>
          </div>
        </div>

        <!-- 角色分布 -->
        <div class="panel">
          <div class="panel-header"><h3>👥 角色分布</h3></div>
          <div class="bar-list">
            <div v-for="item in summary.role_distribution" :key="item.label" class="bar-item">
              <div class="bar-label">{{ item.label }}</div>
              <div class="bar-track">
                <div class="bar-fill" :style="{ width: rolePct(item.value) + '%', background: item.tone === 'primary' ? '#3b82f6' : '#94a3b8' }"></div>
              </div>
              <div class="bar-value">{{ item.value }}</div>
            </div>
          </div>
        </div>

        <!-- 资产类型分布 -->
        <div class="panel">
          <div class="panel-header"><h3>📦 资产类型</h3></div>
          <div class="bar-list">
            <div v-for="item in summary.type_breakdown" :key="item.label" class="bar-item">
              <div class="bar-label">{{ item.label }}</div>
              <div class="bar-track">
                <div class="bar-fill" :style="{ width: typePct(item.value) + '%', background: item.color }"></div>
              </div>
              <div class="bar-value">{{ item.value }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { getDashboardStats, getDashboardSummary } from '@/api/dashboard'
import { useAuthStore } from '@/stores/modules/auth'
import { Box, Monitor, Warning, Tickets } from '@element-plus/icons-vue'

const authStore = useAuthStore()
const stats = ref<any>({})
const summary = ref<any>({})

const currentTime = computed(() => {
  const now = new Date()
  return now.toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' })
})

const statCards = computed(() => [
  { label: '资产总数', value: stats.value.asset_total ?? '-', desc: '全部托管资产', icon: Box, color: '#3b82f6', iconColor: 'rgba(59,130,246,0.15)', bg: 'linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%)' },
  { label: '在线主机', value: stats.value.online_hosts ?? '-', desc: '当前在线运行', icon: Monitor, color: '#22c55e', iconColor: 'rgba(34,197,94,0.15)', bg: 'linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%)' },
  { label: '待处理告警', value: stats.value.open_alerts ?? '-', desc: '需要关注处理', icon: Warning, color: '#ef4444', iconColor: 'rgba(239,68,68,0.15)', bg: 'linear-gradient(135deg, #fef2f2 0%, #fecaca 100%)' },
  { label: '待处理工单', value: stats.value.pending_tickets ?? '-', desc: '等待处理跟进', icon: Tickets, color: '#f59e0b', iconColor: 'rgba(245,158,11,0.15)', bg: 'linear-gradient(135deg, #fffbeb 0%, #fde68a 100%)' },
])

function tagType(tone: string) {
  const map: Record<string, string> = { green: 'success', red: 'danger', orange: 'warning', blue: 'primary' }
  return map[tone] || 'info'
}

const maxRole = computed(() => Math.max(...(summary.value.role_distribution || []).map((r: any) => r.value), 1))
const maxType = computed(() => summary.value.max_type_value || 1)

function rolePct(val: number) { return Math.round((val / maxRole.value) * 100) }
function typePct(val: number) { return Math.round((val / maxType.value) * 100) }

onMounted(async () => {
  try {
    const [s, d]: any = await Promise.all([getDashboardStats(), getDashboardSummary()])
    stats.value = s.data
    summary.value = d.data
  } catch {}
})
</script>

<style lang="scss" scoped>
.dashboard { max-width: 1400px; }

// ── 欢迎栏 ──
.welcome-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  h2 { font-size: 20px; font-weight: 700; margin-bottom: 4px; }
  p { font-size: 14px; color: var(--text-muted); }
  .welcome-time { font-size: 13px; color: var(--text-muted); }
}

// ── 指标卡片 ──
.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}

.stat-card {
  border-radius: 14px;
  padding: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border: 1px solid rgba(0,0,0,0.04);
  transition: transform 0.2s, box-shadow 0.2s;
  &:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,0.08); }
}

.stat-card-label { font-size: 13px; color: var(--text-secondary); margin-bottom: 6px; }
.stat-card-value { font-size: 32px; font-weight: 800; letter-spacing: -0.02em; line-height: 1; margin-bottom: 4px; }
.stat-card-desc { font-size: 12px; color: var(--text-muted); }
.stat-card-icon { opacity: 0.8; }

// ── 快捷统计条 ──
.quick-bar {
  display: flex;
  gap: 24px;
  padding: 14px 20px;
  background: #fff;
  border: 1px solid var(--border-color);
  border-radius: 10px;
  margin-bottom: 16px;
}

.quick-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.quick-dot, .compact-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.dot-green { background: #22c55e; }
.dot-blue { background: #3b82f6; }
.dot-orange { background: #f59e0b; }
.dot-red { background: #ef4444; }

.quick-label { color: var(--text-muted); }
.quick-value { font-weight: 700; color: var(--text-primary); }

// ── 主内容区 ──
.dashboard-grid {
  display: grid;
  grid-template-columns: 1fr 380px;
  gap: 16px;
}

.dashboard-main { display: flex; flex-direction: column; gap: 16px; }
.dashboard-side { display: flex; flex-direction: column; gap: 16px; }

// ── 面板 ──
.panel {
  background: #fff;
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 16px 20px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
  h3 { font-size: 14px; font-weight: 700; }
}

// ── 紧凑列表 ──
.compact-list { display: flex; flex-direction: column; gap: 2px; }

.compact-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 8px;
  transition: background 0.12s;
  &:hover { background: #f8fafc; }
}

.compact-body { flex: 1; min-width: 0; }
.compact-title { font-size: 13px; font-weight: 600; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.compact-meta { font-size: 12px; color: var(--text-muted); margin-top: 2px; }

.empty-hint { text-align: center; padding: 20px; color: var(--text-muted); font-size: 13px; }

// ── 横向条形图 ──
.bar-list { display: flex; flex-direction: column; gap: 10px; }

.bar-item {
  display: flex;
  align-items: center;
  gap: 10px;
}

.bar-label { width: 60px; font-size: 12px; color: var(--text-secondary); text-align: right; flex-shrink: 0; }

.bar-track {
  flex: 1;
  height: 8px;
  background: #f1f5f9;
  border-radius: 4px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.6s ease;
}

.bar-value { width: 30px; font-size: 12px; font-weight: 700; color: var(--text-primary); text-align: right; }

// ── 响应式 ──
@media (max-width: 1100px) {
  .stat-grid { grid-template-columns: repeat(2, 1fr); }
  .dashboard-grid { grid-template-columns: 1fr; }
}

@media (max-width: 600px) {
  .stat-grid { grid-template-columns: 1fr; }
  .quick-bar { flex-wrap: wrap; gap: 12px; }
}
</style>
