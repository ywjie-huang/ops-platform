<template>
  <div class="patrol-command">
    <div class="page-header command-header">
      <div>
        <h2 class="page-title">巡检指挥台</h2>
        <p class="page-subtitle">异常对象优先 · 按主机 / K8s / 资产分泳道 · 右侧直接进入处置路径</p>
      </div>
      <div class="header-actions">
        <el-button @click="goCockpit">
          <el-icon><DataAnalysis /></el-icon> 态势大屏
        </el-button>
        <el-button @click="$router.push('/patrol/settings')">
          <el-icon><Setting /></el-icon> 阈值配置
        </el-button>
        <el-button type="primary" :loading="running" @click="handleRun">
          <el-icon><VideoPlay /></el-icon> 立即巡检
        </el-button>
      </div>
    </div>

    <div class="command-grid">
      <aside class="command-panel run-panel">
        <div class="panel-head">
          <div class="panel-title">
            <svg class="panel-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 8v5l3 3"/><circle cx="12" cy="12" r="10"/></svg>
            <span>巡检批次</span>
          </div>
          <el-select v-model="statusFilter" clearable placeholder="全部" size="small" class="status-filter" @change="fetchReports">
            <el-option label="全部" value="" />
            <el-option label="正常" value="normal" />
            <el-option label="警告" value="warning" />
            <el-option label="严重" value="critical" />
          </el-select>
        </div>

        <div v-loading="loading" class="run-list">
          <button
            v-for="report in reports"
            :key="report.id"
            class="run-item"
            :class="{ active: selectedReport?.id === report.id }"
            type="button"
            @click="selectReport(report)"
          >
            <span class="run-top">
              <span class="run-title">
                <strong>{{ report.title }}</strong>
                <span>{{ report.operator || '系统任务' }} · {{ relativeTime(report.created_at) }}</span>
              </span>
              <span class="status-pill" :class="statusTone(report.status)">{{ getPatrolPriority(report) }}</span>
            </span>
            <span class="run-bars" :aria-label="`${report.normal_count} 正常，${report.warning_count} 警告，${report.critical_count} 严重`">
              <i class="bar-normal" :style="{ flexGrow: Math.max(report.normal_count || 0, 1) }"></i>
              <i class="bar-warning" :style="{ flexGrow: Math.max(report.warning_count || 0, 1) }"></i>
              <i class="bar-critical" :style="{ flexGrow: Math.max(report.critical_count || 0, 1) }"></i>
            </span>
            <span class="run-foot">
              <span>{{ report.total_checks }} 项检查</span>
              <span>{{ (report.warning_count || 0) + (report.critical_count || 0) }} 个异常项</span>
            </span>
          </button>

          <div v-if="!loading && !reports.length" class="empty-state">
            <svg class="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="M16 13H8"/><path d="M16 17H8"/></svg>
            <p class="empty-text">暂无巡检报告</p>
            <p class="empty-hint">点击「立即巡检」生成第一份报告。</p>
          </div>
        </div>

        <div class="lane-pagination report-pagination">
          <button
            type="button"
            class="page-btn"
            :disabled="reportPager.page <= 1 || loading"
            aria-label="巡检批次上一页"
            @click="setReportPage(reportPager.page - 1)"
          >
            <svg class="panel-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4"><path d="m15 18-6-6 6-6"/></svg>
          </button>
          <span> {{ reportPager.page }} / {{ reportPager.totalPages }} </span>
          <button
            type="button"
            class="page-btn"
            :disabled="reportPager.page >= reportPager.totalPages || loading"
            aria-label="巡检批次下一页"
            @click="setReportPage(reportPager.page + 1)"
          >
            <svg class="panel-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4"><path d="m9 18 6-6-6-6"/></svg>
          </button>
        </div>
      </aside>

      <section class="command-main">
        <div class="summary-grid">
          <article class="summary-card summary-hero">
            <div>
              <h3>{{ selectedReport ? '本次巡检结论' : '等待选择巡检批次' }}</h3>
              <p>{{ selectedReport?.summary || '从左侧选择一份巡检报告，查看异常对象和处置建议。' }}</p>
              <div v-if="selectedReport" class="summary-meta">
                <span>{{ selectedReport.operator || '系统任务' }}</span>
                <span>{{ relativeTime(selectedReport.created_at) }}</span>
                <span>{{ overview.total }} 项检查</span>
              </div>
            </div>
            <div class="summary-side">
              <div class="score-ring" :class="statusTone(overview.status)" :title="'健康分 ' + overview.healthScore">
                <strong>{{ overview.healthScore }}</strong>
              </div>
              <span class="status-pill large" :class="statusTone(overview.status)">{{ overview.priorityLabel }}</span>
            </div>
          </article>
          <article class="summary-card metric danger">
            <span>严重项</span>
            <strong>{{ overview.critical }}</strong>
            <small>{{ overview.priority }}</small>
          </article>
          <article class="summary-card metric warning">
            <span>警告项</span>
            <strong>{{ overview.warning }}</strong>
            <small>{{ overview.abnormal }} 个异常项</small>
          </article>
          <article class="summary-card metric success">
            <span>健康分</span>
            <strong>{{ overview.healthScore }}</strong>
            <small>{{ overview.normal }} / {{ overview.total }} 正常</small>
          </article>
          <article class="summary-card metric info">
            <span>覆盖对象</span>
            <strong>{{ riskObjects.length }}</strong>
            <small>主机 / K8s / 资产</small>
          </article>
        </div>

        <div class="object-board">
          <section v-for="lane in riskLanes" :key="lane.key" class="object-lane">
            <div class="lane-head">
              <strong>{{ lane.label }}</strong>
              <span>{{ lane.objects.length }} 个对象</span>
            </div>
            <div class="object-list">
              <button
                v-for="object in lane.page.items"
                :key="object.key"
                class="object-card"
                :class="{ selected: selectedObject?.key === object.key }"
                type="button"
                @click="selectedObjectKey = object.key"
              >
                <span class="object-top">
                  <span class="object-name">
                    <strong>{{ object.targetName }}</strong>
                    <span>{{ object.targetIp || object.impact }}</span>
                  </span>
                  <span class="status-pill" :class="object.tone">{{ object.priority }}</span>
                </span>
                <span class="object-headline">{{ object.headline }}</span>
                <span class="object-counts">
                  <span
                    v-for="badge in buildObjectCounts(object)"
                    :key="`${object.key}-${badge.tone}`"
                    class="count"
                    :class="badge.tone"
                  >
                    {{ badge.value }} {{ badge.label }}
                  </span>
                </span>
              </button>

              <div v-if="!lane.objects.length" class="lane-empty">
                暂无{{ lane.label }}巡检对象
              </div>
            </div>
            <div class="lane-pagination">
              <button
                type="button"
                class="page-btn"
                :disabled="lane.page.page <= 1"
                :aria-label="`${lane.label}上一页`"
                @click="setLanePage(lane.key, lane.page.page - 1)"
              >
                <svg class="panel-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4"><path d="m15 18-6-6 6-6"/></svg>
              </button>
              <span>{{ lane.page.page }} / {{ lane.page.totalPages }}</span>
              <button
                type="button"
                class="page-btn"
                :disabled="lane.page.page >= lane.page.totalPages"
                :aria-label="`${lane.label}下一页`"
                @click="setLanePage(lane.key, lane.page.page + 1)"
              >
                <svg class="panel-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4"><path d="m9 18 6-6-6-6"/></svg>
              </button>
            </div>
          </section>
        </div>
      </section>

      <aside class="command-panel detail-panel">
        <div class="panel-head">
          <div class="panel-title">
            <svg class="panel-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v20"/><path d="M2 12h20"/><circle cx="12" cy="12" r="4"/></svg>
            <span>处置面板</span>
          </div>
          <el-button v-if="selectedReport" link type="primary" @click="handleExport(selectedReport)">导出 Excel</el-button>
        </div>

        <div v-if="selectedObject" class="detail-scroll">
          <section class="target-card">
            <div class="target-main">
              <div>
                <h3>{{ selectedObject.targetName }}</h3>
                <p>{{ selectedObject.categoryLabel }} · {{ selectedObject.targetIp || selectedObject.impact }}</p>
              </div>
              <span class="status-pill large" :class="selectedObject.tone">{{ selectedObject.priority }}</span>
            </div>
            <div class="meta-grid">
              <div><span>巡检结论</span><strong>{{ selectedObject.critical }} 严重 / {{ selectedObject.warning }} 警告</strong></div>
              <div><span>检查项</span><strong>{{ selectedObject.total }}</strong></div>
              <div><span>影响范围</span><strong>{{ selectedObject.impact }}</strong></div>
              <div><span>报告时间</span><strong>{{ relativeTime(selectedReport?.created_at) }}</strong></div>
            </div>
          </section>

          <section>
            <h4 class="section-title">关键发现</h4>
            <div class="finding-list">
              <article v-for="item in selectedObject.items" :key="item.id || `${item.check_name}-${item.value}`" class="finding">
                <div class="finding-top">
                  <strong>{{ item.check_name }}</strong>
                  <span class="status-pill" :class="statusTone(item.status)">{{ statusLabel(item.status) }}</span>
                </div>
                <p>{{ item.detail || '暂无详情' }}</p>
                <dl>
                  <div><dt>当前值</dt><dd>{{ item.value || '-' }}</dd></div>
                  <div><dt>阈值</dt><dd>{{ item.threshold || '-' }}</dd></div>
                </dl>
              </article>
            </div>
          </section>

          <section class="playbook" v-if="selectedObject">
            <h4 class="section-title">建议处置剧本</h4>
            <ol class="playbook-steps">
              <li>打开对象详情，确认影响范围与最近变更</li>
              <li>通过 Web 终端处理磁盘、负载或进程异常</li>
              <li>观察 30 分钟关键指标是否回落</li>
              <li>无法短期恢复时创建工单并转交对应负责人</li>
            </ol>
          </section>

          <section>
            <h4 class="section-title">建议动作</h4>
            <div class="action-list">
              <button class="action-row" type="button" @click="goHostDetail">
                <span class="action-icon">
                  <svg class="panel-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-3 3"/></svg>
                </span>
                <span><strong>查看对象详情</strong><small>打开主机、集群或资产详情页</small></span>
              </button>
              <button class="action-row" type="button" @click="goTerminal">
                <span class="action-icon">
                  <svg class="panel-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 17l6-6-6-6"/><path d="M12 19h8"/></svg>
                </span>
                <span><strong>打开 Web 终端</strong><small>处理磁盘、负载或进程异常</small></span>
              </button>
              <button class="action-row" type="button" @click="goTickets">
                <span class="action-icon">
                  <svg class="panel-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a4 4 0 0 1-4 4H7l-4 4V7a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4z"/></svg>
                </span>
                <span><strong>创建/查看工单</strong><small>带上巡检项、阈值与当前值</small></span>
              </button>
            </div>
          </section>

          <div class="detail-actions">
            <el-button @click="selectedObjectKey = ''">清除选择</el-button>
            <el-button v-if="selectedReport" type="danger" plain @click="handleDelete(selectedReport)">删除报告</el-button>
          </div>
        </div>

        <div v-else class="empty-state detail-empty">
          <svg class="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><path d="M12 8v4"/><path d="M12 16h.01"/></svg>
          <p class="empty-text">请选择异常对象</p>
          <p class="empty-hint">从中间的主机、K8s 或资产对象进入处置面板。</p>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onActivated, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { DataAnalysis, Setting, VideoPlay } from '@element-plus/icons-vue'
import { deletePatrolReport, exportPatrolReport, getPatrolReportDetail, getPatrolReports, runPatrol } from '@/api/patrol'
import { formatRelativeTime } from '@/utils/time'
import {
  buildCockpitRouteLocation,
  buildObjectCounts,
  buildPager,
  buildPatrolOverview,
  buildRiskObjects,
  getPatrolPriority,
  groupRiskObjectsByCategory,
  paginateRiskObjects,
  pickPrimaryRiskObject,
  statusLabel,
  statusTone,
  type PatrolItemLike,
  type PatrolReportLike,
} from '@/utils/patrolCommand'

const router = useRouter()
const running = ref(false)
const loading = ref(false)
const reports = ref<PatrolReportLike[]>([])
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const statusFilter = ref('')
const selectedReport = ref<PatrolReportLike | null>(null)
const detailItems = ref<PatrolItemLike[]>([])
const selectedObjectKey = ref('')
const lanePages = ref<Record<string, number>>({ host: 1, k8s: 1, asset: 1 })

const overview = computed(() => buildPatrolOverview(selectedReport.value))
const riskObjects = computed(() => buildRiskObjects(detailItems.value))
const reportPager = computed(() => buildPager(total.value, page.value, pageSize.value))
const riskLanes = computed(() => groupRiskObjectsByCategory(riskObjects.value).map((lane) => ({
  ...lane,
  page: paginateRiskObjects(lane.objects, lanePages.value[lane.key] || 1),
})))
const selectedObject = computed(() => riskObjects.value.find((item) => item.key === selectedObjectKey.value) || pickPrimaryRiskObject(riskObjects.value))

watch(riskObjects, (objects) => {
  if (!objects.length) {
    selectedObjectKey.value = ''
    return
  }
  if (!objects.some((item) => item.key === selectedObjectKey.value)) {
    selectedObjectKey.value = pickPrimaryRiskObject(objects)?.key || objects[0].key
  }
})

watch(riskLanes, (lanes) => {
  const nextPages = { ...lanePages.value }
  let changed = false

  for (const lane of lanes) {
    if (nextPages[lane.key] !== lane.page.page) {
      nextPages[lane.key] = lane.page.page
      changed = true
    }
  }

  if (changed) lanePages.value = nextPages
})

async function fetchReports() {
  loading.value = true
  try {
    const res: any = await getPatrolReports({ status: statusFilter.value, page: page.value, page_size: pageSize.value })
    reports.value = res.data.items
    total.value = res.data.total
    if (!selectedReport.value && reports.value.length) {
      await selectReport(reports.value[0])
    } else if (selectedReport.value) {
      const current = reports.value.find((item) => item.id === selectedReport.value?.id)
      if (current) selectedReport.value = current
    }
  } finally {
    loading.value = false
  }
}

async function selectReport(report: PatrolReportLike) {
  selectedReport.value = report
  selectedObjectKey.value = ''
  lanePages.value = { host: 1, k8s: 1, asset: 1 }
  try {
    const res: any = await getPatrolReportDetail(report.id as number)
    selectedReport.value = res.data.report
    detailItems.value = res.data.items
    await nextTick()
  } catch (e: any) {
    detailItems.value = []
    ElMessage.error(e?.response?.data?.detail || '加载巡检详情失败')
  }
}

async function handleRun() {
  running.value = true
  try {
    const res: any = await runPatrol()
    ElMessage.success(`巡检完成：${res.data.summary}`)
    selectedReport.value = null
    await fetchReports()
  } finally {
    running.value = false
  }
}

async function handleExport(row: PatrolReportLike | null) {
  if (!row?.id) return
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

async function handleDelete(row: PatrolReportLike | null) {
  if (!row?.id) return
  await ElMessageBox.confirm(`确定删除巡检报告「${row.title}」？此操作不可恢复。`, '删除确认', {
    type: 'warning',
    confirmButtonText: '确认删除',
    cancelButtonText: '取消',
  })
  await deletePatrolReport(row.id)
  ElMessage.success('删除成功')
  selectedReport.value = null
  detailItems.value = []
  await fetchReports()
}

function goHostDetail() {
  const object = selectedObject.value
  if (!object) return
  if (object.category === 'host') router.push('/monitoring/hosts')
  else if (object.category === 'k8s') router.push('/assets/containers')
  else router.push('/assets/list')
}

function goTerminal() {
  router.push('/monitoring/hosts')
}

function goTickets() {
  router.push('/tickets')
}

function goCockpit() {
  router.push(buildCockpitRouteLocation(selectedReport.value))
}

function setLanePage(key: string, value: number) {
  lanePages.value = { ...lanePages.value, [key]: value }
}

async function setReportPage(value: number) {
  const nextPage = buildPager(total.value, value, pageSize.value).page
  if (nextPage === page.value) return
  page.value = nextPage
  await fetchReports()
}

function relativeTime(value?: string) {
  return value ? formatRelativeTime(value) : '-'
}

onActivated(fetchReports)
</script>

<style scoped>
.patrol-command {
  min-width: 0;
}

.command-header {
  align-items: flex-start;
}

.page-subtitle {
  margin: 4px 0 0;
  color: var(--text-muted);
  font-size: 13px;
}

.header-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
}

.command-grid {
  display: grid;
  grid-template-columns: 286px minmax(0, 1fr) 380px;
  gap: 14px;
  min-height: calc(100vh - 116px);
}

.command-panel,
.summary-card,
.object-lane {
  min-width: 0;
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  background: var(--surface-color);
}

.command-panel {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  overflow: hidden;
}

.panel-head {
  min-height: 48px;
  padding: 12px 14px;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.panel-title {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 700;
}

.panel-title span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.panel-icon {
  width: 16px;
  height: 16px;
  flex: 0 0 auto;
}

.status-filter {
  width: 104px;
}

.run-list {
  min-height: 0;
  overflow-y: auto;
  padding: 10px;
  display: grid;
  align-content: start;
  gap: 8px;
}

.run-item,
.object-card,
.playbook {
  border: 1px solid var(--border-color);
  border-radius: 8px;
  background: linear-gradient(180deg, color-mix(in srgb, var(--primary-color) 5%, #fff), #fff);
  padding: 12px;
}
.playbook-steps {
  margin: 0;
  padding-left: 18px;
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.7;
}

.action-row {
  width: 100%;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  background: #fff;
  color: var(--text-primary);
  text-align: left;
  transition: border-color 0.16s ease-out, background 0.16s ease-out, transform 0.16s ease-out;
}

.run-item {
  padding: 10px;
  display: grid;
  gap: 8px;
}

.run-item:hover,
.object-card:hover {
  border-color: color-mix(in srgb, var(--primary-color) 36%, var(--border-color));
}

.run-item.active {
  border-color: color-mix(in srgb, var(--primary-color) 48%, var(--border-color));
  background: color-mix(in srgb, var(--primary-color) 7%, #fff);
}

.run-top,
.run-foot,
.object-top,
.finding-top,
.target-main {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}

.run-title,
.object-name {
  min-width: 0;
  display: grid;
  gap: 2px;
}

.run-title strong,
.object-name strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
}

.run-title span,
.run-foot,
.object-name span,
.object-headline,
.empty-hint {
  color: var(--text-muted);
  font-size: 12px;
}

.run-bars {
  height: 7px;
  display: flex;
  gap: 3px;
}

.run-bars i {
  border-radius: 999px;
}

.bar-normal { background: var(--success-color); }
.bar-warning { background: var(--warning-color); }
.bar-critical { background: var(--danger-color); }

.status-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 22px;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
}

.status-pill.large {
  min-height: 26px;
  padding: 3px 10px;
}

.status-pill.success,
.count.success {
  color: color-mix(in srgb, var(--success-color) 76%, #111);
  background: color-mix(in srgb, var(--success-color) 10%, #fff);
  border: 1px solid color-mix(in srgb, var(--success-color) 24%, var(--border-color));
}

.status-pill.warning,
.count.warning {
  color: #875600;
  background: color-mix(in srgb, var(--warning-color) 13%, #fff);
  border: 1px solid color-mix(in srgb, var(--warning-color) 28%, var(--border-color));
}

.status-pill.danger,
.count.danger {
  color: color-mix(in srgb, var(--danger-color) 84%, #111);
  background: color-mix(in srgb, var(--danger-color) 10%, #fff);
  border: 1px solid color-mix(in srgb, var(--danger-color) 28%, var(--border-color));
}

.status-pill.info {
  color: var(--text-secondary);
  background: var(--bg-color);
  border: 1px solid var(--border-color);
}

.command-main {
  min-width: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 14px;
}

.summary-grid {
  display: grid;
  grid-template-columns: minmax(260px, 1.5fr) repeat(4, minmax(110px, 0.4fr));
  gap: 10px;
}

.summary-card {
  padding: 14px;
}

.summary-hero {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  background:
    radial-gradient(circle at 0% 0%, rgba(229, 72, 77, 0.08), transparent 36%),
    linear-gradient(180deg, #fff, #fbfcfe);
}
.summary-side {
  display: grid;
  gap: 8px;
  justify-items: end;
  text-align: right;
}
.score-ring {
  width: 68px;
  height: 68px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  position: relative;
  background: conic-gradient(var(--danger-color) 0 28%, var(--warning-color) 28% 48%, var(--success-color) 48% 100%);
}
.score-ring::before {
  content: "";
  position: absolute;
  inset: 7px;
  border-radius: 50%;
  background: #fff;
  border: 1px solid var(--border-color);
}
.score-ring strong {
  position: relative;
  font-size: 18px;
  font-weight: 800;
  letter-spacing: -0.03em;
}
.summary-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}
.summary-meta span {
  display: inline-flex;
  align-items: center;
  min-height: 22px;
  padding: 0 8px;
  border-radius: 999px;
  border: 1px solid var(--border-color);
  background: var(--bg-color);
  color: var(--text-muted);
  font-size: 11px;
  font-weight: 700;
}
.metric.info strong { color: var(--primary-color); }

.summary-hero h3 {
  margin: 0 0 6px;
  font-size: 15px;
}

.summary-hero p {
  margin: 0;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.5;
}

.metric {
  display: grid;
  gap: 8px;
  align-content: space-between;
}

.metric span,
.metric small {
  color: var(--text-muted);
  font-size: 12px;
}

.metric strong {
  font-size: 28px;
  line-height: 1;
  font-variant-numeric: tabular-nums;
}

.metric.danger strong { color: var(--danger-color); }
.metric.warning strong { color: var(--warning-color); }
.metric.success strong { color: var(--success-color); }

.object-board {
  min-height: 0;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.object-lane {
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  overflow: hidden;
}

.lane-head {
  padding: 11px 12px;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  background: var(--bg-color);
}

.lane-head strong {
  font-size: 13px;
}

.lane-head span,
.lane-empty {
  color: var(--text-muted);
  font-size: 12px;
}

.object-list {
  min-height: 0;
  overflow-y: auto;
  padding: 9px;
  display: grid;
  align-content: start;
  gap: 8px;
}

.object-card {
  padding: 10px;
  display: grid;
  gap: 8px;
}

.object-card.selected {
  border-color: color-mix(in srgb, var(--danger-color) 42%, var(--border-color));
  background: linear-gradient(180deg, color-mix(in srgb, var(--danger-color) 6%, #fff), #fff);
  box-shadow: 0 8px 18px color-mix(in srgb, var(--danger-color) 10%, transparent);
}

.object-counts {
  display: flex;
  align-items: center;
  gap: 5px;
  flex-wrap: wrap;
}

.count {
  display: inline-flex;
  align-items: center;
  min-height: 21px;
  padding: 1px 7px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
}

.lane-empty {
  padding: 24px 8px;
  text-align: center;
}

.lane-pagination {
  min-height: 42px;
  padding: 8px 10px;
  border-top: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: var(--text-muted);
  font-size: 12px;
  background: var(--surface-color);
}

.report-pagination {
  flex: 0 0 auto;
}

.page-btn {
  width: 26px;
  height: 26px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  background: #fff;
  transition: border-color 0.16s ease-out, color 0.16s ease-out, background 0.16s ease-out;
}

.page-btn:hover:not(:disabled) {
  color: var(--primary-color);
  border-color: color-mix(in srgb, var(--primary-color) 36%, var(--border-color));
  background: var(--primary-bg);
}

.page-btn:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.detail-panel {
  min-height: 0;
}

.detail-scroll {
  min-height: 0;
  overflow-y: auto;
  padding: 12px;
  display: grid;
  align-content: start;
  gap: 14px;
}

.target-card,
.finding,
.action-row {
  border: 1px solid var(--border-color);
  border-radius: 8px;
  background: #fff;
}

.target-card {
  padding: 12px;
  display: grid;
  gap: 12px;
}

.target-main h3 {
  margin: 0;
  font-size: 17px;
}

.target-main p {
  margin: 4px 0 0;
  color: var(--text-muted);
  font-size: 12px;
}

.meta-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.meta-grid div {
  border: 1px solid var(--border-color);
  border-radius: 7px;
  padding: 8px;
  display: grid;
  gap: 4px;
  background: var(--bg-color);
}

.meta-grid span {
  color: var(--text-muted);
  font-size: 12px;
}

.meta-grid strong {
  font-size: 13px;
}

.section-title {
  margin: 0 0 8px;
  font-size: 13px;
  font-weight: 700;
}

.finding-list,
.action-list {
  display: grid;
  gap: 8px;
}

.finding {
  padding: 9px;
  display: grid;
  gap: 7px;
}

.finding p {
  margin: 0;
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.55;
}

.finding dl {
  margin: 0;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.finding dl div {
  min-width: 0;
}

.finding dt {
  color: var(--text-muted);
  font-size: 12px;
}

.finding dd {
  margin: 2px 0 0;
  color: var(--text-primary);
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.action-row {
  display: grid;
  grid-template-columns: 30px minmax(0, 1fr);
  gap: 9px;
  align-items: center;
  padding: 9px;
}

.action-icon {
  width: 30px;
  height: 30px;
  border-radius: 7px;
  display: grid;
  place-items: center;
  color: var(--primary-color);
  background: var(--primary-bg);
}

.action-row strong,
.action-row small {
  display: block;
}

.action-row small {
  margin-top: 2px;
  color: var(--text-muted);
}

.detail-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
}

.empty-state {
  display: grid;
  justify-items: center;
  align-content: center;
  gap: 8px;
  padding: 32px 14px;
  text-align: center;
}

.detail-empty {
  min-height: 360px;
}

.empty-icon {
  width: 46px;
  height: 46px;
  color: var(--text-muted);
  opacity: 0.45;
}

.empty-text {
  margin: 0;
  color: var(--text-secondary);
  font-weight: 700;
}

.empty-hint {
  margin: 0;
}

@media (max-width: 1280px) {
  .command-grid {
    grid-template-columns: 270px minmax(0, 1fr);
  }

  .detail-panel {
    grid-column: 1 / -1;
    min-height: 540px;
  }
}

@media (max-width: 980px) {
  .command-grid,
  .object-board {
    grid-template-columns: 1fr;
  }

  .run-panel {
    min-height: 420px;
  }

  .object-lane {
    min-height: 240px;
  }

  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .summary-hero {
    grid-column: 1 / -1;
  }
}

@media (max-width: 768px) {
  .command-header,
  .summary-hero,
  .target-main {
    flex-direction: column;
  }

  .header-actions {
    justify-content: flex-start;
  }

  .summary-grid,
  .meta-grid,
  .finding dl {
    grid-template-columns: 1fr;
  }
}
</style>
