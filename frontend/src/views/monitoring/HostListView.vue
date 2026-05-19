<template>
  <div>
    <div class="page-header">
      <h2 class="page-title">主机监控</h2>
      <div class="header-actions">
        <el-tooltip :content="autoRefresh ? '关闭自动刷新' : '开启后每 60s 自动刷新数据'" placement="bottom">
          <el-button :type="autoRefresh ? 'primary' : 'default'" @click="toggleAutoRefresh">
            <el-icon><Refresh /></el-icon>
            {{ autoRefresh ? '自动刷新中' : '自动刷新' }}
          </el-button>
        </el-tooltip>
        <el-tooltip content="调整显示列" placement="bottom">
          <el-popover trigger="click" :width="200" placement="bottom-end">
            <template #reference>
              <el-button><el-icon><Setting /></el-icon></el-button>
            </template>
            <div class="column-setting">
              <div v-for="col in columns" :key="col.key" class="column-item">
                <el-checkbox v-model="col.visible" :label="col.label" />
              </div>
            </div>
          </el-popover>
        </el-tooltip>
      </div>
    </div>
    <div class="data-card">
      <el-table :data="items" stripe v-loading="loading">
        <el-table-column label="主机" min-width="120">
          <template #default="{row}">
            <div style="display:flex;align-items:center;gap:8px">
              <span :class="['status-dot', row.prometheus_ok ? 'dot-green' : 'dot-grey']" />
              <div>
                <strong>{{ row.name }}</strong>
                <br><span style="color:var(--text-muted);font-size:12px">{{ row.ip_address }}</span>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column v-if="colVisible('status')" label="状态" width="80">
          <template #default="{row}">
            <el-tag :type="statusTagType(row.status)" size="small" round>{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column v-if="colVisible('cpu')" label="CPU" width="130">
          <template #default="{row}">
            <span v-if="!row.prometheus_ok" class="no-data">-</span>
            <el-progress v-else :percentage="row.cpu" :color="cpuColor(row.cpu)" :stroke-width="10" />
          </template>
        </el-table-column>
        <el-table-column v-if="colVisible('memory')" label="内存" width="130">
          <template #default="{row}">
            <span v-if="!row.prometheus_ok" class="no-data">-</span>
            <el-progress v-else :percentage="row.memory" :color="cpuColor(row.memory)" :stroke-width="10" />
          </template>
        </el-table-column>
        <el-table-column v-if="colVisible('disk')" label="磁盘" width="130">
          <template #default="{row}">
            <span v-if="!row.prometheus_ok" class="no-data">-</span>
            <el-progress v-else :percentage="row.disk" :color="cpuColor(row.disk)" :stroke-width="10" />
          </template>
        </el-table-column>
        <el-table-column v-if="colVisible('network_in')" label="入站" width="100">
          <template #default="{row}">
            <span v-if="!row.prometheus_ok" class="no-data">-</span>
            <span v-else>{{ row.network_in }} Mbps</span>
          </template>
        </el-table-column>
        <el-table-column v-if="colVisible('network_out')" label="出站" width="100">
          <template #default="{row}">
            <span v-if="!row.prometheus_ok" class="no-data">-</span>
            <span v-else>{{ row.network_out }} Mbps</span>
          </template>
        </el-table-column>
        <el-table-column v-if="colVisible('load')" label="负载" width="80">
          <template #default="{row}">
            <span v-if="!row.prometheus_ok" class="no-data">-</span>
            <span v-else>{{ row.load }}</span>
          </template>
        </el-table-column>
        <el-table-column v-if="colVisible('owner')" prop="owner" label="负责人" width="80" />
        <el-table-column label="操作" width="70" fixed="right">
          <template #default="{row}">
            <el-button size="small" text type="primary" @click="$router.push(`/monitoring/hosts/${row.id}`)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onActivated, onDeactivated } from 'vue'
import { getHosts } from '@/api/monitoring'
import { Refresh, Setting } from '@element-plus/icons-vue'

const loading = ref(false)
const items = ref<any[]>([])
const autoRefresh = ref(false)
let refreshTimer: ReturnType<typeof setInterval> | null = null

const columns = reactive([
  { key: 'status', label: '状态', visible: true },
  { key: 'cpu', label: 'CPU', visible: true },
  { key: 'memory', label: '内存', visible: true },
  { key: 'disk', label: '磁盘', visible: true },
  { key: 'network_in', label: '入站', visible: true },
  { key: 'network_out', label: '出站', visible: true },
  { key: 'load', label: '负载', visible: true },
  { key: 'owner', label: '负责人', visible: true },
])

function colVisible(key: string) {
  return columns.find(c => c.key === key)?.visible ?? true
}

const cpuColor = (v: number) => v > 90 ? '#ef4444' : v > 70 ? '#f59e0b' : '#22c55e'

function statusTagType(status: string) {
  return { '使用中': 'success', '已关机': 'warning', '已删除': 'info' }[status] || 'info'
}

async function fetchData() {
  loading.value = true
  try {
    const res: any = await getHosts()
    items.value = res.data
  } finally {
    loading.value = false
  }
}

function toggleAutoRefresh() {
  autoRefresh.value = !autoRefresh.value
  if (autoRefresh.value) {
    refreshTimer = setInterval(fetchData, 60000)
  } else if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
}

function stopAutoRefresh() {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
}

onActivated(() => {
  fetchData()
  if (autoRefresh.value) {
    refreshTimer = setInterval(fetchData, 60000)
  }
})
onDeactivated(stopAutoRefresh)
</script>

<style scoped>
.header-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.column-setting {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.column-item {
  :deep(.el-checkbox__label) {
    font-size: 13px;
  }
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.dot-green { background: #22c55e; }
.dot-grey { background: #94a3b8; }

.no-data {
  color: var(--text-muted);
  font-size: 13px;
}
</style>
