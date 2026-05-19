<template>
  <div class="report-detail">
    <div class="page-header">
      <el-button text @click="$router.push('/reports')">
        <el-icon><ArrowLeft /></el-icon> 返回报表中心
      </el-button>
      <h2 class="page-title">{{ reportMeta?.name || '报表详情' }}</h2>
      <p class="page-subtitle">{{ reportMeta?.description }}</p>
    </div>

    <div v-loading="loading" class="report-content">
      <div v-if="error" class="error-state">
        <el-empty description="加载失败，请稍后重试" />
      </div>
      <div v-else-if="reportData">
        <!-- 汇总指标 -->
        <div v-if="summaryCards.length" class="summary-grid">
          <div v-for="card in summaryCards" :key="card.label" class="summary-card">
            <div class="summary-value">{{ card.value }}</div>
            <div class="summary-label">{{ card.label }}</div>
          </div>
        </div>

        <!-- 数据表格 -->
        <div v-for="(table, idx) in tables" :key="idx" class="data-panel">
          <h3 class="panel-title">{{ table.title }}</h3>
          <el-table :data="table.rows" stripe border style="width: 100%">
            <el-table-column
              v-for="(col, ci) in table.columns"
              :key="ci"
              :prop="String(ci)"
              :label="col"
            />
          </el-table>
        </div>

        <!-- 备注 -->
        <div v-if="reportData.note" class="report-note">
          <el-icon><InfoFilled /></el-icon> {{ reportData.note }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onActivated } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowLeft, InfoFilled } from '@element-plus/icons-vue'
import { getPresetDetail } from '@/api/reports'

const route = useRoute()
const loading = ref(true)
const error = ref(false)
const reportMeta = ref<any>(null)
const reportData = ref<any>(null)

const summaryCards = computed(() => {
  if (!reportData.value) return []
  const d = reportData.value
  const cards: { label: string; value: any }[] = []
  if (d.total !== undefined) cards.push({ label: '总数', value: d.total })
  if (d.resolved !== undefined) cards.push({ label: '已解决', value: d.resolved })
  if (d.resolution_rate !== undefined) cards.push({ label: '解决率', value: d.resolution_rate })
  if (d.metrics) {
    const m = d.metrics
    if (m.total !== undefined) cards.push({ label: '总数', value: m.total })
    if (m.open !== undefined) cards.push({ label: '待处理', value: m.open })
    if (m.in_progress !== undefined) cards.push({ label: '处理中', value: m.in_progress })
    if (m.resolved !== undefined) cards.push({ label: '已解决', value: m.resolved })
    if (m.closed !== undefined) cards.push({ label: '已关闭', value: m.closed })
    if (m.completion_rate !== undefined) cards.push({ label: '完成率', value: m.completion_rate })
  }
  return cards
})

const tables = computed(() => {
  if (!reportData.value) return []
  const d = reportData.value
  const result: { title: string; columns: string[]; rows: any[] }[] = []

  // 处理直接有 columns + rows 的情况
  if (d.columns && d.rows) {
    result.push({ title: d.title || '数据', columns: d.columns, rows: toTableRows(d.columns, d.rows) })
  }

  // 处理 by_xxx 子表
  for (const key of Object.keys(d)) {
    const val = d[key]
    if (val && val.columns && val.rows) {
      const titleMap: Record<string, string> = {
        by_type: '按类型', by_status: '按状态', by_level: '按级别',
        by_priority: '按优先级', by_action: '按操作类型', by_target: '按对象类型',
        current: '当前数据',
      }
      result.push({ title: titleMap[key] || key, columns: val.columns, rows: toTableRows(val.columns, val.rows) })
    }
  }

  return result
})

function toTableRows(columns: string[], rows: any[][]) {
  return rows.map(row => {
    const obj: Record<string, any> = {}
    columns.forEach((_, i) => { obj[String(i)] = row[i] })
    return obj
  })
}

async function fetchReport() {
  loading.value = true
  error.value = false
  reportMeta.value = null
  reportData.value = null
  try {
    const id = route.params.id as string
    const res: any = await getPresetDetail(id)
    if (res.data) {
      reportMeta.value = res.data.report
      reportData.value = res.data.data
    } else {
      error.value = true
    }
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
}

// keep-alive 下 onMounted 只触发一次，用 onActivated 每次进入都刷新
onActivated(fetchReport)
</script>

<style lang="scss" scoped>
.report-detail { max-width: 1200px; }

.page-header {
  margin-bottom: 24px;
  .el-button { padding: 0; margin-bottom: 8px; }
}

.page-subtitle {
  font-size: 14px;
  color: var(--text-muted);
  margin-top: 4px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.summary-card {
  background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
  border-radius: 12px;
  padding: 20px;
  text-align: center;
  border: 1px solid rgba(59, 130, 246, 0.1);
}

.summary-value {
  font-size: 28px;
  font-weight: 800;
  color: #1e40af;
  margin-bottom: 4px;
}

.summary-label {
  font-size: 13px;
  color: var(--text-secondary);
}

.data-panel {
  background: #fff;
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 20px;
  margin-bottom: 16px;
}

.panel-title {
  font-size: 15px;
  font-weight: 700;
  margin-bottom: 14px;
}

.report-note {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--text-muted);
  padding: 12px 16px;
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 8px;
  margin-top: 16px;
}
</style>
