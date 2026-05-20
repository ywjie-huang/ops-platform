<template>
  <div>
    <div class="page-header">
      <h2 class="page-title">巡检中心</h2>
      <el-button type="primary" :loading="running" @click="handleRun">
        <el-icon><VideoPlay /></el-icon> 立即巡检
      </el-button>
    </div>

    <!-- 最近一次巡检概览 -->
    <div v-if="latestReport" class="data-card" style="margin-bottom:16px">
      <div style="display:flex;align-items:center;gap:16px;margin-bottom:12px">
        <h3 style="margin:0">{{ latestReport.title }}</h3>
        <el-tag :type="statusType(latestReport.status)" size="small">{{ statusLabel(latestReport.status) }}</el-tag>
        <span style="color:var(--text-muted);font-size:13px">{{ latestReport.created_at }}</span>
        <span style="color:var(--text-muted);font-size:13px">操作人：{{ latestReport.operator || '-' }}</span>
      </div>
      <el-row :gutter="16">
        <el-col :span="6">
          <div class="mini-stat success">
            <div class="mini-stat-value">{{ latestReport.normal_count }}</div>
            <div class="mini-stat-label">正常</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="mini-stat warning">
            <div class="mini-stat-value">{{ latestReport.warning_count }}</div>
            <div class="mini-stat-label">警告</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="mini-stat danger">
            <div class="mini-stat-value">{{ latestReport.critical_count }}</div>
            <div class="mini-stat-label">严重</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="mini-stat info">
            <div class="mini-stat-value">{{ latestReport.total_checks }}</div>
            <div class="mini-stat-label">总检查项</div>
          </div>
        </el-col>
      </el-row>
    </div>

    <!-- 报告列表 -->
    <div class="data-card">
      <div class="filter-bar">
        <el-select v-model="statusFilter" placeholder="状态筛选" clearable style="width:120px" @change="fetchReports">
          <el-option label="全部" value="" />
          <el-option label="正常" value="normal" />
          <el-option label="警告" value="warning" />
          <el-option label="严重" value="critical" />
        </el-select>
      </div>

      <el-table :data="reports" stripe v-loading="loading" @row-click="handleRowClick" style="cursor:pointer">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="title" label="报告标题" min-width="200" />
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{row}">
            <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="检查结果" width="200">
          <template #default="{row}">
            <span style="color:var(--el-color-success)">{{ row.normal_count }} 正常</span> ·
            <span style="color:var(--el-color-warning)">{{ row.warning_count }} 警告</span> ·
            <span style="color:var(--el-color-danger)">{{ row.critical_count }} 严重</span>
          </template>
        </el-table-column>
        <el-table-column prop="operator" label="操作人" width="100" />
        <el-table-column prop="created_at" label="巡检时间" width="170" />
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{row}">
            <el-button link type="primary" size="small" @click.stop="handleExport(row)">导出 Excel</el-button>
            <el-button link type="danger" size="small" @click.stop="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50]"
          :total="total"
          layout="total, sizes, prev, pager, next"
          @current-change="fetchReports"
          @size-change="fetchReports"
        />
      </div>
    </div>

    <!-- 报告详情弹窗 -->
    <el-dialog v-model="detailVisible" title="巡检报告详情" width="900px" destroy-on-close>
      <div v-if="detailReport" style="margin-bottom:16px">
        <el-row :gutter="16">
          <el-col :span="6">
            <div class="mini-stat success">
              <div class="mini-stat-value">{{ detailReport.normal_count }}</div>
              <div class="mini-stat-label">正常</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="mini-stat warning">
              <div class="mini-stat-value">{{ detailReport.warning_count }}</div>
              <div class="mini-stat-label">警告</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="mini-stat danger">
              <div class="mini-stat-value">{{ detailReport.critical_count }}</div>
              <div class="mini-stat-label">严重</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="mini-stat info">
              <div class="mini-stat-value">{{ detailReport.total_checks }}</div>
              <div class="mini-stat-label">总检查项</div>
            </div>
          </el-col>
        </el-row>
      </div>

      <!-- 按分类分组展示 -->
      <div v-for="group in groupedItems" :key="group.category" style="margin-bottom:16px">
        <h4 style="margin:0 0 8px">{{ group.label }}</h4>

        <!-- 主机巡检：卡片折叠布局 -->
        <template v-if="group.category === 'host'">
          <div v-for="host in group.hosts" :key="host.name" class="host-card">
            <div class="host-card-header" @click="toggleHost(host.name)">
              <div class="host-card-left">
                <el-icon class="expand-icon" :class="{ expanded: expandedHosts.has(host.name) }"><ArrowRight /></el-icon>
                <span class="host-name">{{ host.name }}</span>
                <span class="host-ip">{{ host.ip }}</span>
              </div>
              <div class="host-card-right">
                <el-tag v-if="host.critical > 0" type="danger" size="small" effect="dark">{{ host.critical }} 严重</el-tag>
                <el-tag v-if="host.warning > 0" type="warning" size="small">{{ host.warning }} 警告</el-tag>
                <el-tag v-if="host.normal > 0 && host.critical === 0 && host.warning === 0" type="success" size="small">全部正常</el-tag>
                <span v-if="host.normal > 0 && (host.critical > 0 || host.warning > 0)" class="host-normal-count">{{ host.normal }} 正常</span>
              </div>
            </div>
            <div class="host-card-body" :class="{ expanded: expandedHosts.has(host.name) }">
              <el-table :data="host.items" stripe size="small">
                <el-table-column prop="check_name" label="检查项" width="130" />
                <el-table-column prop="status" label="状态" width="80">
                  <template #default="{row}">
                    <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="value" label="当前值" min-width="140" />
                <el-table-column prop="threshold" label="阈值" min-width="200" show-overflow-tooltip />
                <el-table-column prop="detail" label="详情" min-width="200" show-overflow-tooltip />
              </el-table>
            </div>
          </div>
        </template>

        <!-- K8s / 资产：保留表格 -->
        <el-table v-else :data="group.items" stripe size="small">
          <el-table-column prop="target_name" label="目标" min-width="140" />
          <el-table-column prop="target_ip" label="IP" width="120" />
          <el-table-column prop="check_name" label="检查项" width="130" />
          <el-table-column prop="status" label="状态" width="80">
            <template #default="{row}">
              <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="value" label="当前值" min-width="160" show-overflow-tooltip />
          <el-table-column prop="threshold" label="阈值" min-width="180" show-overflow-tooltip />
          <el-table-column prop="detail" label="详情" min-width="200" show-overflow-tooltip />
        </el-table>
      </div>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
        <el-button type="primary" @click="handleExport(detailReport)">导出 Excel</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { VideoPlay, ArrowRight } from '@element-plus/icons-vue'
import { runPatrol, getPatrolReports, getPatrolReportDetail, deletePatrolReport, exportPatrolReport } from '@/api/patrol'

const running = ref(false)
const loading = ref(false)
const reports = ref<any[]>([])
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const statusFilter = ref('')

const detailVisible = ref(false)
const detailReport = ref<any>(null)
const detailItems = ref<any[]>([])
const expandedHosts = ref<Set<string>>(new Set())

function toggleHost(name: string) {
  const s = new Set(expandedHosts.value)
  if (s.has(name)) s.delete(name)
  else s.add(name)
  expandedHosts.value = s
}

const latestReport = computed(() => reports.value[0] || null)

const CATEGORY_LABELS: Record<string, string> = {
  host: '🖥️ 主机巡检（Prometheus）',
  k8s: '☸️ K8s 集群巡检',
  asset: '📦 资产状态巡检',
}

const groupedItems = computed(() => {
  const groups: Record<string, any[]> = {}
  for (const item of detailItems.value) {
    const cat = item.category || 'other'
    if (!groups[cat]) groups[cat] = []
    groups[cat].push(item)
  }
  return Object.entries(groups).map(([cat, items]) => {
    const base = { category: cat, label: CATEGORY_LABELS[cat] || cat, items }
    // 主机巡检：按主机名分组
    if (cat === 'host') {
      const hostMap: Record<string, { name: string; ip: string; items: any[]; normal: number; warning: number; critical: number }> = {}
      for (const item of items) {
        const key = item.target_name || 'unknown'
        if (!hostMap[key]) {
          hostMap[key] = { name: key, ip: item.target_ip || '', items: [], normal: 0, warning: 0, critical: 0 }
        }
        hostMap[key].items.push(item)
        if (item.status === 'critical') hostMap[key].critical++
        else if (item.status === 'warning') hostMap[key].warning++
        else hostMap[key].normal++
      }
      // 有异常的主机默认展开
      const hosts = Object.values(hostMap).sort((a, b) => {
        if (a.critical !== b.critical) return b.critical - a.critical
        if (a.warning !== b.warning) return b.warning - a.warning
        return a.name.localeCompare(b.name)
      })
      // 自动展开有异常的主机
      for (const h of hosts) {
        if ((h.critical > 0 || h.warning > 0) && !expandedHosts.value.has(h.name)) {
          expandedHosts.value.add(h.name)
        }
      }
      return { ...base, hosts }
    }
    return base
  })
})

function statusType(s: string) {
  return s === 'normal' ? 'success' : s === 'warning' ? 'warning' : s === 'critical' ? 'danger' : 'info'
}

function statusLabel(s: string) {
  return s === 'normal' ? '正常' : s === 'warning' ? '警告' : s === 'critical' ? '严重' : s
}

async function fetchReports() {
  loading.value = true
  try {
    const res: any = await getPatrolReports({ status: statusFilter.value, page: page.value, page_size: pageSize.value })
    reports.value = res.data.items
    total.value = res.data.total
  } finally { loading.value = false }
}

async function handleRun() {
  running.value = true
  try {
    const res: any = await runPatrol()
    ElMessage.success(`巡检完成：${res.data.summary}`)
    fetchReports()
  } finally { running.value = false }
}

async function handleRowClick(row: any) {
  try {
    const res: any = await getPatrolReportDetail(row.id)
    detailReport.value = res.data.report
    detailItems.value = res.data.items
    detailVisible.value = true
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '加载失败') }
}

async function handleExport(row: any) {
  try {
    const res: any = await exportPatrolReport(row.id)
    const blob = new Blob([res.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${row.title || '巡检报告'}.xlsx`
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch {
    ElMessage.error('导出失败')
  }
}

async function handleDelete(row: any) {
  await ElMessageBox.confirm(`确定删除巡检报告「${row.title}」？`, '删除确认', { type: 'warning' })
  await deletePatrolReport(row.id)
  ElMessage.success('删除成功')
  fetchReports()
}

onMounted(fetchReports)
</script>

<style scoped>
.mini-stat { text-align: center; padding: 12px; border-radius: 8px; border: 1px solid var(--border-color); }
.mini-stat-value { font-size: 28px; font-weight: 700; }
.mini-stat-label { font-size: 13px; color: var(--text-muted); margin-top: 4px; }
.mini-stat.success .mini-stat-value { color: var(--el-color-success); }
.mini-stat.warning .mini-stat-value { color: var(--el-color-warning); }
.mini-stat.danger .mini-stat-value { color: var(--el-color-danger); }
.mini-stat.info .mini-stat-value { color: var(--el-color-info); }
.pagination-wrap { display: flex; justify-content: flex-end; margin-top: 16px; }

/* 主机卡片折叠 */
.host-card { border: 1px solid var(--border-color); border-radius: 8px; margin-bottom: 8px; overflow: hidden; }
.host-card-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 16px; cursor: pointer; background: var(--el-fill-color-lighter);
  transition: background 0.2s;
}
.host-card-header:hover { background: var(--el-fill-color-light); }
.host-card-left { display: flex; align-items: center; gap: 10px; }
.expand-icon { font-size: 12px; transition: transform 0.2s; }
.expand-icon.expanded { transform: rotate(90deg); }
.host-name { font-weight: 600; font-size: 14px; }
.host-ip { color: var(--text-muted); font-size: 13px; }
.host-card-right { display: flex; align-items: center; gap: 8px; }
.host-normal-count { color: var(--text-muted); font-size: 13px; }
.host-card-body {
  max-height: 0;
  overflow: hidden;
  transition: max-height 0.25s ease, padding 0.25s ease;
  padding: 0 16px;
}
.host-card-body.expanded {
  max-height: 600px;
  padding: 0 16px 12px;
}
</style>
