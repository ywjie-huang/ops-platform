<template>
  <div>
    <div class="page-header"><h2 class="page-title">Docker 监控</h2></div>

    <!-- 概览卡片 -->
    <el-row :gutter="16" style="margin-bottom:16px">
      <el-col :span="6" v-for="item in overviewCards" :key="item.label">
        <div class="stat-card">
          <div class="stat-label">{{ item.label }}</div>
          <div class="stat-value" :style="{ color: item.color }">{{ item.value }}</div>
        </div>
      </el-col>
    </el-row>

    <!-- Docker 主机列表 -->
    <div class="data-card">
      <div class="filter-bar">
        <el-input v-model="hostKeyword" placeholder="搜索主机…" clearable style="width:220px" @keyup.enter="fetchHosts" />
        <el-button type="primary" @click="handleCreate">注册主机</el-button>
      </div>

      <el-table :data="hosts" stripe v-loading="loading" @row-click="goDetail" style="cursor:pointer">
        <el-table-column prop="name" label="主机名称" min-width="140">
          <template #default="{row}"><strong>{{ row.name }}</strong></template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{row}">
            <el-tag :type="row.online ? 'success' : 'danger'" size="small">
              {{ row.online ? '在线' : '离线' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="endpoint" label="Agent 地址" width="200" />
        <el-table-column prop="host_ip" label="主机 IP" width="140" />
        <el-table-column prop="docker_version" label="Docker" width="100" />
        <el-table-column prop="host_os" label="系统" min-width="200" show-overflow-tooltip />
        <el-table-column prop="last_heartbeat" label="最后同步" width="170">
          <template #default="{row}">
            {{ row.last_heartbeat ? formatTime(row.last_heartbeat) : '从未' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{row}">
            <el-button link type="success" size="small" @click.stop="handleRefresh(row)">刷新</el-button>
            <el-button link type="primary" size="small" @click.stop="handleEdit(row)">编辑</el-button>
            <el-button link type="danger" size="small" @click.stop="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 注册/编辑主机弹窗 -->
    <el-dialog v-model="hostDialogVisible" :title="editingHostId ? '编辑主机' : '注册 Docker 主机'" width="600px" destroy-on-close>
      <!-- 新建时显示部署指南 -->
      <template v-if="!editingHostId">
        <el-steps :active="setupStep" finish-status="success" align-center style="margin-bottom:20px">
          <el-step title="部署 Agent" />
          <el-step title="注册主机" />
        </el-steps>

        <!-- 步骤 1：部署说明 -->
        <div v-if="setupStep === 0">
          <p style="margin:0 0 12px;color:var(--text-muted);font-size:14px">
            在目标 Docker 主机上执行以下命令启动 Agent：
          </p>
          <div class="setup-command-box">
            <pre class="setup-command">docker run -d \
  -p 9001:9001 \
  --name ops-agent \
  --restart=always \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  hub1.lczy.com/public/ops-agent:latest</pre>
            <el-button type="primary" size="small" style="margin-top:8px" @click="copyAgentCmd">复制命令</el-button>
          </div>
          <el-button type="primary" style="margin-top:16px" @click="setupStep = 1">下一步，填写信息</el-button>
        </div>

        <!-- 步骤 2：填写信息 -->
        <div v-if="setupStep === 1">
          <el-form ref="hostFormRef" :model="hostForm" :rules="hostRules" label-width="100px">
            <el-form-item label="主机名称" prop="name">
              <el-input v-model="hostForm.name" placeholder="例：docker-prod-01" />
            </el-form-item>
            <el-form-item label="Agent 地址" prop="endpoint">
              <el-input v-model="hostForm.endpoint" placeholder="例：192.168.1.200:9001" />
              <div class="el-form-item__tip" style="font-size:12px;color:var(--text-muted);margin-top:4px">
                填写目标主机 IP 和 Agent 端口（默认 9001）
              </div>
            </el-form-item>
            <el-form-item label="说明">
              <el-input v-model="hostForm.description" placeholder="备注信息" />
            </el-form-item>
          </el-form>
        </div>
      </template>

      <!-- 编辑时只显示表单 -->
      <el-form v-else ref="hostFormRef" :model="hostForm" :rules="hostRules" label-width="100px">
        <el-form-item label="主机名称" prop="name">
          <el-input v-model="hostForm.name" placeholder="例：docker-prod-01" />
        </el-form-item>
        <el-form-item label="Agent 地址" prop="endpoint">
          <el-input v-model="hostForm.endpoint" placeholder="例：192.168.1.200:9001" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="hostForm.description" placeholder="备注信息" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="hostDialogVisible = false">取消</el-button>
        <template v-if="!editingHostId">
          <el-button v-if="setupStep === 1" @click="setupStep = 0">上一步</el-button>
          <el-button v-if="setupStep === 1" type="primary" :loading="saving" @click="handleHostSubmit">注册</el-button>
        </template>
        <el-button v-else type="primary" :loading="saving" @click="handleHostSubmit">保存</el-button>
      </template>
    </el-dialog>


  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, type FormInstance } from 'element-plus'
import {
  getDockerOverview,
  getDockerHosts,
  createDockerHost,
  updateDockerHost,
  deleteDockerHost,
  refreshDockerHost,
} from '@/api/containers'

const router = useRouter()

// ─── 状态 ──────────────────────────────────────────────────

const loading = ref(false)
const saving = ref(false)
const hosts = ref<any[]>([])
const overview = ref<any>({})
const hostKeyword = ref('')

// 主机弹窗
const hostDialogVisible = ref(false)
const editingHostId = ref<number | null>(null)
const setupStep = ref(0)  // 0=部署说明, 1=填写信息
const hostFormRef = ref<FormInstance>()
const hostForm = reactive({ name: '', endpoint: '', description: '' })
const hostRules = {
  name: [{ required: true, message: '请输入主机名称', trigger: 'blur' }],
  endpoint: [{ required: true, message: '请输入 Agent 地址', trigger: 'blur' }],
}

function copyAgentCmd() {
  const cmd = `docker run -d \\\n  -p 9001:9001 \\\n  --name ops-agent \\\n  --restart=always \\\n  -v /var/run/docker.sock:/var/run/docker.sock:ro \\\n  hub1.lczy.com/public/ops-agent:latest`
  navigator.clipboard.writeText(cmd).then(() => ElMessage.success('已复制命令'))
}

let refreshTimer: ReturnType<typeof setInterval> | null = null

// ─── 计算属性 ──────────────────────────────────────────────

const overviewCards = computed(() => [
  { label: '主机总数', value: overview.value.host_total ?? '-', color: '' },
  { label: '在线主机', value: overview.value.host_online ?? '-', color: overview.value.host_online > 0 ? 'var(--el-color-success)' : 'var(--el-color-danger)' },
  { label: '容器总数', value: overview.value.container_total ?? '-', color: '' },
  { label: '运行中容器', value: overview.value.container_running ?? '-', color: overview.value.container_running > 0 ? 'var(--el-color-success)' : '' },
])

// ─── 工具函数 ──────────────────────────────────────────────

function formatTime(ts: string) {
  if (!ts) return '-'
  try { return new Date(ts).toLocaleString('zh-CN') } catch { return ts }
}

// ─── 数据获取 ──────────────────────────────────────────────

async function fetchOverview() {
  try {
    const res: any = await getDockerOverview()
    overview.value = res.data
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '加载失败') }
}

async function fetchHosts() {
  loading.value = true
  try {
    const res: any = await getDockerHosts({ keyword: hostKeyword.value })
    hosts.value = res.data
  } finally { loading.value = false }
}

// ─── 操作 ──────────────────────────────────────────────────

function handleCreate() {
  editingHostId.value = null
  setupStep.value = 0
  Object.assign(hostForm, { name: '', endpoint: '', description: '' })
  hostDialogVisible.value = true
}

function handleEdit(row: any) {
  editingHostId.value = row.id
  Object.assign(hostForm, { name: row.name, endpoint: row.endpoint, description: row.description || '' })
  hostDialogVisible.value = true
}

async function handleHostSubmit() {
  const valid = await hostFormRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    if (editingHostId.value) {
      await updateDockerHost(editingHostId.value, hostForm)
      ElMessage.success('更新成功')
    } else {
      const res: any = await createDockerHost(hostForm)
      ElMessage.success(res.msg || '注册成功')
    }
    hostDialogVisible.value = false
    fetchHosts()
    fetchOverview()
  } finally { saving.value = false }
}

async function handleDelete(row: any) {
  await ElMessageBox.confirm(`确定删除主机「${row.name}」？所有容器数据将被清除。`, '删除确认', { type: 'warning' })
  await deleteDockerHost(row.id)
  ElMessage.success('删除成功')
  fetchHosts()
  fetchOverview()
}

async function handleRefresh(row: any) {
  try {
    await refreshDockerHost(row.id)
    ElMessage.success('刷新成功')
    fetchHosts()
  } catch {
    ElMessage.error('Agent 连接失败')
  }
}

function goDetail(row: any) {
  router.push(`/assets/docker/${row.id}`)
}

// ─── 自动刷新 ──────────────────────────────────────────────

function startAutoRefresh() {
  refreshTimer = setInterval(() => {
    fetchOverview()
    fetchHosts()
  }, 15000)
}

onMounted(() => {
  fetchOverview()
  fetchHosts()
  startAutoRefresh()
})

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer)
})
</script>

<style scoped>
.stat-card { background: #fff; border: 1px solid var(--border-color); border-radius: 8px; padding: 16px; }
.stat-label { font-size: 13px; color: var(--text-muted); }
.stat-value { font-size: 24px; font-weight: 700; }
.setup-command-box {
  background: #1e293b;
  border-radius: 8px;
  padding: 16px;
}
.setup-command {
  color: #e2e8f0;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 13px;
  line-height: 1.6;
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
