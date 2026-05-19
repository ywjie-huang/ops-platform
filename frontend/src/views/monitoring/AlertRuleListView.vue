<template>
  <div>
    <div class="page-header">
      <h2 class="page-title">告警规则</h2>
      <div class="header-actions">
        <el-tag v-if="connected" type="success" size="small" effect="plain">Prometheus 已连接</el-tag>
        <el-tag v-else type="danger" size="small" effect="plain">Prometheus 未连接</el-tag>
      </div>
    </div>

    <div class="data-card">
      <div class="toolbar">
        <el-select v-model="filterSeverity" placeholder="严重程度" clearable size="small" style="width: 140px">
          <el-option label="critical" value="critical" />
          <el-option label="warn" value="warn" />
          <el-option label="warning" value="warning" />
          <el-option label="info" value="info" />
        </el-select>
        <el-select v-model="filterState" placeholder="状态" clearable size="small" style="width: 140px">
          <el-option label="firing" value="firing" />
          <el-option label="pending" value="pending" />
          <el-option label="inactive" value="inactive" />
        </el-select>
      </div>

      <el-table :data="filteredRules" stripe v-loading="loading">
        <el-table-column prop="name" label="规则名称" min-width="200">
          <template #default="{ row }">
            <strong>{{ row.name }}</strong>
          </template>
        </el-table-column>
        <el-table-column label="严重程度" width="100">
          <template #default="{ row }">
            <el-tag :type="severityType(row.labels?.severity)" size="small">
              {{ row.labels?.severity || '-' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="stateType(row.state)" size="small" effect="dark">
              {{ row.state }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="query" label="PromQL" min-width="280" show-overflow-tooltip>
          <template #default="{ row }">
            <code class="promql">{{ row.query }}</code>
          </template>
        </el-table-column>
        <el-table-column label="持续时间" width="100">
          <template #default="{ row }">
            {{ formatDuration(row.duration) }}
          </template>
        </el-table-column>
        <el-table-column prop="group_name" label="分组" width="120" />
        <el-table-column label="健康状态" width="90">
          <template #default="{ row }">
            <el-tag v-if="row.health === 'ok'" type="success" size="small">OK</el-tag>
            <el-tag v-else-if="row.health === 'err'" type="danger" size="small">ERR</el-tag>
            <el-tag v-else type="info" size="small">{{ row.health || '-' }}</el-tag>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { getAlertManagerRules, getAlertManagerStatus } from '@/api/alertmanager'

interface Rule {
  name: string
  query: string
  duration: number
  state: string
  labels: Record<string, string>
  annotations: Record<string, string>
  health: string
  last_error: string
  group_name: string
  file: string
}

const loading = ref(false)
const connected = ref(false)
const rules = ref<Rule[]>([])
const filterSeverity = ref('')
const filterState = ref('')

const filteredRules = computed(() => {
  return rules.value.filter(r => {
    if (filterSeverity.value && r.labels?.severity !== filterSeverity.value) return false
    if (filterState.value && r.state !== filterState.value) return false
    return true
  })
})

function severityType(severity?: string) {
  if (severity === 'critical') return 'danger'
  if (severity === 'warning' || severity === 'warn') return 'warning'
  return 'info'
}

function stateType(state: string) {
  if (state === 'firing') return 'danger'
  if (state === 'pending') return 'warning'
  return 'info'
}

function formatDuration(seconds: number) {
  if (!seconds) return '-'
  if (seconds < 60) return `${seconds}s`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`
  return `${Math.floor(seconds / 3600)}h${Math.floor((seconds % 3600) / 60)}m`
}

async function fetchData() {
  loading.value = true
  try {
    const [statusRes, rulesRes]: any[] = await Promise.all([
      getAlertManagerStatus(),
      getAlertManagerRules(),
    ])
    connected.value = statusRes?.data?.connected ?? false
    rules.value = rulesRes?.data ?? []
  } catch {
    connected.value = false
    rules.value = []
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
.header-actions {
  display: flex;
  gap: 8px;
  align-items: center;
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
}
.promql {
  font-size: 12px;
  color: #606266;
  word-break: break-all;
}
</style>
