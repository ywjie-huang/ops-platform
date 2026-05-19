<template>
  <div>
    <div class="page-header">
      <h2 class="page-title">告警事件</h2>
    </div>

    <div class="data-card">
      <div class="toolbar">
        <el-input
          v-model="keyword"
          placeholder="搜索告警名称 / 实例"
          clearable
          size="small"
          style="width: 240px"
          @keyup.enter="fetchData"
        />
        <el-select v-model="filterSeverity" placeholder="严重程度" clearable size="small" style="width: 140px">
          <el-option label="critical" value="critical" />
          <el-option label="warn" value="warn" />
          <el-option label="warning" value="warning" />
          <el-option label="info" value="info" />
        </el-select>
        <el-select v-model="filterStatus" placeholder="状态" clearable size="small" style="width: 140px">
          <el-option label="firing" value="firing" />
          <el-option label="resolved" value="resolved" />
        </el-select>
        <el-button type="primary" size="small" @click="fetchData">查询</el-button>
      </div>

      <el-table :data="items" stripe v-loading="loading">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column label="来源信息" width="160" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.instance">{{ row.instance }}</span>
            <span v-else-if="row.job">{{ row.job }}</span>
            <span v-else class="no-data">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="alert_name" label="告警名称" min-width="150">
          <template #default="{ row }">
            <strong>{{ row.alert_name }}</strong>
          </template>
        </el-table-column>
        <el-table-column label="严重程度" width="100">
          <template #default="{ row }">
            <el-tag :type="severityType(row.severity)" size="small">{{ row.severity }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 'firing' ? 'danger' : 'success'" size="small" effect="dark">
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="alert_value" label="告警值" width="120" show-overflow-tooltip>
          <template #default="{ row }">
            <code v-if="row.alert_value">{{ row.alert_value }}</code>
            <span v-else class="no-data">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="summary" label="告警摘要" min-width="200" show-overflow-tooltip />
        <el-table-column label="连续触发次数" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="row.firing_count > 3 ? 'danger' : 'info'" size="small" effect="plain">
              {{ row.firing_count }} 次
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="触发时间" width="170">
          <template #default="{ row }">
            {{ formatTime(row.starts_at) }}
          </template>
        </el-table-column>
        <el-table-column label="恢复时间" width="170">
          <template #default="{ row }">
            {{ row.ends_at ? formatTime(row.ends_at) : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="原始数据" width="80">
          <template #default="{ row }">
            <el-popover trigger="click" width="400">
              <template #reference><el-button size="small" text type="primary">查看</el-button></template>
              <div><strong>Labels:</strong><pre style="font-size:12px;white-space:pre-wrap">{{ formatJson(row.raw_labels) }}</pre></div>
              <div><strong>Annotations:</strong><pre style="font-size:12px;white-space:pre-wrap">{{ formatJson(row.raw_annotations) }}</pre></div>
            </el-popover>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination" v-if="total > pageSize">
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="fetchData"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getAlertManagerEvents } from '@/api/alertmanager'

interface AlertEvent {
  id: number
  fingerprint: string
  alert_name: string
  severity: string
  status: string
  alert_value: string
  summary: string
  description: string
  instance: string
  job: string
  firing_count: number
  starts_at: string | null
  ends_at: string | null
  received_at: string | null
  raw_labels: string
  raw_annotations: string
}

const loading = ref(false)
const items = ref<AlertEvent[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const keyword = ref('')
const filterSeverity = ref('')
const filterStatus = ref('')

function severityType(severity: string) {
  if (severity === 'critical') return 'danger'
  if (severity === 'warning' || severity === 'warn') return 'warning'
  return 'info'
}

function formatTime(iso: string | null) {
  if (!iso || iso === '0001-01-01T00:00:00') return '-'
  const d = new Date(iso)
  if (isNaN(d.getTime()) || d.getFullYear() < 2000) return '-'
  return d.toLocaleString('zh-CN', { hour12: false })
}

function formatJson(str: string) {
  try { return JSON.stringify(JSON.parse(str), null, 2) } catch { return str || '-' }
}

async function fetchData() {
  loading.value = true
  try {
    const res: any = await getAlertManagerEvents({
      keyword: keyword.value,
      severity: filterSeverity.value,
      status: filterStatus.value,
      page: page.value,
      page_size: pageSize,
    })
    items.value = res?.data?.items ?? []
    total.value = res?.data?.total ?? 0
  } catch {
    items.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

onMounted(fetchData)
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.page-title {
  margin: 0;
  font-size: 18px;
}
.data-card {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}
.toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
  align-items: center;
}
.pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}
.no-data {
  color: #c0c4cc;
}
</style>
