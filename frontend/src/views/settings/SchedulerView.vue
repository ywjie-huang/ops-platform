<template>
  <div>
    <div class="page-header">
      <h2 class="page-title">定时任务</h2>
      <el-button type="primary" @click="showDialog()">
        <el-icon><Plus /></el-icon>新建任务
      </el-button>
    </div>

    <!-- 任务列表 -->
    <div class="data-card">
      <el-table :data="items" v-loading="loading" stripe>
        <el-table-column prop="name" label="任务名称" min-width="140" />
        <el-table-column label="任务类型" width="120">
          <template #default="{ row }">
            <el-tag>{{ taskTypeLabels[row.task_type] || row.task_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="cron_expr" label="Cron 表达式" width="140" />
        <el-table-column label="启用" width="80" align="center">
          <template #default="{ row }">
            <el-switch v-model="row.enabled" @change="handleToggle(row)" />
          </template>
        </el-table-column>
        <el-table-column label="上次执行" width="180">
          <template #default="{ row }">
            <template v-if="row.last_run_at">
              <div>{{ formatTime(row.last_run_at) }}</div>
              <el-tag :type="statusType(row.last_status)" size="small">
                {{ statusLabels[row.last_status] || row.last_status }}
              </el-tag>
            </template>
            <span v-else class="text-muted">未执行</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="showDialog(row)">编辑</el-button>
            <el-button link type="primary" size="small" @click="handleRunNow(row)">立即执行</el-button>
            <el-button link type="primary" size="small" @click="showLogs(row)">日志</el-button>
            <el-popconfirm title="确认删除该任务？" @confirm="handleDelete(row)">
              <template #reference>
                <el-button link type="danger" size="small">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-wrap" v-if="total > pageSize">
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="fetchData"
        />
      </div>
    </div>

    <!-- 新建/编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑任务' : '新建任务'" width="520px" destroy-on-close>
      <el-form :model="form" :rules="rules" ref="formRef" label-width="110px">
        <el-form-item label="任务名称" prop="name">
          <el-input v-model="form.name" placeholder="如：每日凌晨巡检" />
        </el-form-item>
        <el-form-item label="任务类型" prop="task_type">
          <el-select v-model="form.task_type" style="width:100%">
            <el-option v-for="t in taskTypes" :key="t.key" :label="t.label" :value="t.key" />
          </el-select>
        </el-form-item>
        <el-form-item label="Cron 表达式" prop="cron_expr">
          <el-input v-model="form.cron_expr" placeholder="如：0 2 * * *（每天凌晨 2 点）" />
          <div class="form-tip">格式：分 时 日 月 星期（5 个字段，空格分隔）</div>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <!-- 执行日志抽屉 -->
    <el-drawer v-model="logsVisible" :title="`${logsTaskName} — 执行日志`" size="560px" destroy-on-close>
      <el-table :data="logs" v-loading="logsLoading" stripe size="small">
        <el-table-column label="开始时间" width="160">
          <template #default="{ row }">{{ formatTime(row.started_at) }}</template>
        </el-table-column>
        <el-table-column label="耗时" width="80">
          <template #default="{ row }">{{ calcDuration(row) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">
              {{ statusLabels[row.status] || row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="result" label="结果" show-overflow-tooltip />
        <el-table-column prop="error" label="错误" show-overflow-tooltip />
      </el-table>
      <div class="pagination-wrap" v-if="logsTotal > logsPageSize">
        <el-pagination
          v-model:current-page="logsPage"
          :page-size="logsPageSize"
          :total="logsTotal"
          layout="total, prev, pager, next"
          @current-change="fetchLogs"
        />
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, type FormInstance } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import {
  getSchedulerTasks, getTaskTypes, createSchedulerTask, updateSchedulerTask,
  deleteSchedulerTask, toggleSchedulerTask, runSchedulerTaskNow, getTaskExecutionLogs,
  type ScheduledTask, type TaskExecutionLog,
} from '@/api/scheduler'

const loading = ref(false)
const saving = ref(false)
const items = ref<ScheduledTask[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20

const taskTypes = ref<{ key: string; label: string }[]>([])
const taskTypeLabels: Record<string, string> = {}

const statusLabels: Record<string, string> = {
  success: '成功',
  failed: '失败',
  running: '执行中',
}

// 弹窗
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const formRef = ref<FormInstance>()
const form = reactive({
  name: '',
  task_type: 'patrol',
  cron_expr: '',
  description: '',
})
const rules = {
  name: [{ required: true, message: '请输入任务名称', trigger: 'blur' }],
  task_type: [{ required: true, message: '请选择任务类型', trigger: 'change' }],
  cron_expr: [{ required: true, message: '请输入 Cron 表达式', trigger: 'blur' }],
}

// 日志抽屉
const logsVisible = ref(false)
const logsLoading = ref(false)
const logsTaskName = ref('')
const logsTaskId = ref(0)
const logs = ref<TaskExecutionLog[]>([])
const logsTotal = ref(0)
const logsPage = ref(1)
const logsPageSize = 20

function formatTime(iso: string | null): string {
  if (!iso) return '-'
  return new Date(iso).toLocaleString('zh-CN')
}

function statusType(status: string): '' | 'success' | 'danger' | 'warning' {
  if (status === 'success') return 'success'
  if (status === 'failed') return 'danger'
  if (status === 'running') return 'warning'
  return ''
}

function calcDuration(row: TaskExecutionLog): string {
  if (!row.started_at || !row.finished_at) return '-'
  const ms = new Date(row.finished_at).getTime() - new Date(row.started_at).getTime()
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

async function fetchTaskTypes() {
  try {
    const res: any = await getTaskTypes()
    taskTypes.value = res.data?.items || []
    for (const t of taskTypes.value) {
      taskTypeLabels[t.key] = t.label
    }
  } catch { /* ignore */ }
}

async function fetchData() {
  loading.value = true
  try {
    const res: any = await getSchedulerTasks({ page: page.value, page_size: pageSize })
    items.value = res.data?.items || []
    total.value = res.data?.total || 0
  } finally { loading.value = false }
}

function showDialog(task?: ScheduledTask) {
  if (task) {
    editingId.value = task.id
    form.name = task.name
    form.task_type = task.task_type
    form.cron_expr = task.cron_expr
    form.description = task.description
  } else {
    editingId.value = null
    form.name = ''
    form.task_type = 'patrol'
    form.cron_expr = ''
    form.description = ''
  }
  dialogVisible.value = true
}

async function handleSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    if (editingId.value) {
      await updateSchedulerTask(editingId.value, {
        name: form.name,
        task_type: form.task_type,
        cron_expr: form.cron_expr,
        description: form.description,
      })
      ElMessage.success('更新成功')
    } else {
      await createSchedulerTask({
        name: form.name,
        task_type: form.task_type,
        cron_expr: form.cron_expr,
        description: form.description,
      })
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchData()
  } finally { saving.value = false }
}

async function handleToggle(row: ScheduledTask) {
  try {
    await toggleSchedulerTask(row.id)
    ElMessage.success(row.enabled ? '已启用' : '已禁用')
  } catch { row.enabled = !row.enabled }
}

async function handleRunNow(row: ScheduledTask) {
  try {
    await runSchedulerTaskNow(row.id)
    ElMessage.success('任务已触发')
    fetchData()
  } catch { /* handled by interceptor */ }
}

async function handleDelete(row: ScheduledTask) {
  await deleteSchedulerTask(row.id)
  ElMessage.success('删除成功')
  fetchData()
}

async function showLogs(row: ScheduledTask) {
  logsTaskId.value = row.id
  logsTaskName.value = row.name
  logsPage.value = 1
  logsVisible.value = true
  await fetchLogs()
}

async function fetchLogs() {
  logsLoading.value = true
  try {
    const res: any = await getTaskExecutionLogs(logsTaskId.value, { page: logsPage.value, page_size: logsPageSize })
    logs.value = res.data?.items || []
    logsTotal.value = res.data?.total || 0
  } finally { logsLoading.value = false }
}

onMounted(() => { fetchTaskTypes(); fetchData() })
</script>

<style scoped>
.form-tip { font-size: 12px; color: #909399; line-height: 1.4; margin-top: 4px; }
.text-muted { color: #909399; font-size: 13px; }
.pagination-wrap { display: flex; justify-content: flex-end; margin-top: 16px; }
</style>
