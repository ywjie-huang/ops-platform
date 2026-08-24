<template>
  <div v-loading="pageLoading">
    <template v-if="app">
      <!-- 面包屑 -->
      <nav class="crumb" aria-label="面包屑">
        <router-link to="/deploy/apps">应用管理</router-link>
        <span class="sep">/</span>
        <span>{{ app.name }}</span>
      </nav>

      <!-- 页头 -->
      <div class="page-header detail-head">
        <div class="head-left">
          <h2 class="page-title">{{ app.name }}</h2>
          <span class="pill" :class="app.status === 'active' ? 'pill--success' : 'pill--info'">
            <i class="dot"></i>{{ app.status === 'active' ? '活跃' : '已归档' }}
          </span>
          <span class="type-tag">{{ typeLabel(app.app_type) }}</span>
        </div>
        <div class="head-actions">
          <el-button v-if="canUpdate" @click="goEdit">编辑</el-button>
          <el-button v-if="canUpdate" :type="app.status === 'active' ? 'danger' : 'success'" plain @click="toggleArchive">
            {{ app.status === 'active' ? '归档' : '恢复' }}
          </el-button>
          <el-button @click="$router.push('/deploy/apps')">返回列表</el-button>
        </div>
      </div>

      <!-- 信息条 -->
      <div class="info-strip" role="region" aria-label="应用信息">
        <div class="info-cell">
          <div class="info-k">JENKINS JOB</div>
          <div class="info-v mono">
            <span>{{ app.jenkins_job_name || '未配置' }}</span>
            <button v-if="app.jenkins_job_name" class="copy-btn" title="复制 Job 名" aria-label="复制 Jenkins Job 名" @click="copyText(app.jenkins_job_name)">
              <el-icon><CopyDocument /></el-icon>
            </button>
          </div>
        </div>
        <div class="info-cell">
          <div class="info-k">GIT 仓库</div>
          <div class="info-v mono info-v--sm">{{ app.git_url || '—' }}</div>
        </div>
        <div class="info-cell">
          <div class="info-k">默认分支</div>
          <div class="info-v mono">{{ app.git_branch || '—' }}</div>
        </div>
        <div class="info-cell">
          <div class="info-k">执行模式</div>
          <div class="info-v">Jenkins 治理触发<span class="type-tag">模式 B</span></div>
        </div>
      </div>

      <!-- 环境管道 -->
      <div class="pipe" role="region" aria-label="环境管道">
        <template v-for="(env, idx) in sortedEnvs" :key="env.id">
          <div v-if="idx > 0" class="pipe-arrow" aria-hidden="true">
            <el-icon><ArrowRight /></el-icon>
          </div>
          <div
            class="env-card"
            :class="{ 'env-card--running': isActive(env.latest_record), 'env-card--disabled': !env.enabled }"
            :style="{ borderTopColor: env.enabled ? envColor(env.env_name) : 'var(--border-color)' }"
          >
            <div class="env-head">
              <span class="env-dot" :style="{ background: envColor(env.env_name) }"></span>
              <span class="env-name">{{ env.env_display_name || env.env_name }}</span>
              <span class="env-key muted">{{ env.env_name }}</span>
              <span v-if="env.approval_required" class="approval-tag">需审批</span>
              <span class="sp"></span>
            </div>

            <div class="env-ver mono" :class="{ 'env-ver--none': !env.latest_record }">
              {{ env.latest_record?.version || '暂无部署' }}
            </div>

            <div>
              <span v-if="env.latest_record" class="pill" :class="`pill--${deployStatusType(env.latest_record.status)}`">
                <i class="dot" :class="{ 'dot--pulse': isActiveStatus(env.latest_record.status) }"></i>
                {{ deployStatusLabel(env.latest_record.status) }}
                <template v-if="env.latest_record.jenkins_build_number">· 构建 #{{ env.latest_record.jenkins_build_number }}</template>
              </span>
              <span v-else class="pill pill--info"><i class="dot"></i>{{ env.enabled ? '未部署' : '未启用' }}</span>
            </div>

            <div class="env-meta">
              <template v-if="env.latest_record">
                <span>{{ formatRelativeTime(env.latest_record.created_at || '') }} · {{ env.latest_record.trigger_user_name || '—' }}
                  <template v-if="env.latest_record.duration != null">· 耗时 {{ formatDeployDuration(env.latest_record.duration) }}</template>
                </span>
                <a
                  v-if="env.latest_record.jenkins_build_url"
                  class="meta-link mono"
                  :href="env.latest_record.jenkins_build_url"
                  target="_blank"
                  rel="noopener noreferrer"
                >构建 #{{ env.latest_record.jenkins_build_number }} ↗</a>
              </template>
              <span v-else class="muted">{{ env.enabled ? '该环境还没有部署记录' : '环境已停用，无法部署' }}</span>
            </div>

            <div class="env-foot">
              <template v-if="isActive(env.latest_record)">
                <el-button size="small" @click="goRecord(env.latest_record!.id)">查看进度</el-button>
                <el-button size="small" text type="danger" @click="handleCancel(env.latest_record!)">取消</el-button>
              </template>
              <el-button
                v-else
                size="small"
                type="primary"
                :disabled="!env.enabled || app.status !== 'active' || !canExecute"
                @click="openDeploy(env)"
              >
                <el-icon><Promotion /></el-icon>部署
              </el-button>
              <span class="sp"></span>
              <el-button size="small" text @click="goHistory(env)">历史</el-button>
            </div>
          </div>
        </template>
        <el-empty v-if="!sortedEnvs.length" description="尚未配置任何环境，请先在「编辑应用」中添加环境" :image-size="80" style="flex:1" />
      </div>
      <!-- Tabs -->
      <el-tabs v-model="activeTab" class="detail-tabs">
        <!-- 部署历史 -->
        <el-tab-pane label="部署历史" name="history">
          <div class="tab-toolbar">
            <el-select v-model="historyEnvId" placeholder="全部环境" clearable class="history-env-filter" aria-label="按环境筛选" @change="fetchHistory()">
              <el-option v-for="e in sortedEnvs" :key="e.env_id" :label="e.env_display_name || e.env_name" :value="e.env_id" />
            </el-select>
          </div>
          <div class="table-wrapper">
            <el-table :data="records" v-loading="historyLoading">
              <el-table-column label="ID" width="80">
                <template #default="{ row }"><span class="mono muted">#{{ row.id }}</span></template>
              </el-table-column>
              <el-table-column label="环境" width="110">
                <template #default="{ row }"><span class="type-tag">{{ row.env_name }}</span></template>
              </el-table-column>
              <el-table-column label="版本" min-width="150">
                <template #default="{ row }"><code class="mono version-code">{{ row.version }}</code></template>
              </el-table-column>
              <el-table-column label="状态" width="140">
                <template #default="{ row }">
                  <span class="pill" :class="`pill--${deployStatusType(row.status)}`">
                    <i class="dot" :class="{ 'dot--pulse': isActiveStatus(row.status) }"></i>{{ deployStatusLabel(row.status) }}
                  </span>
                </template>
              </el-table-column>
              <el-table-column label="触发方式" width="90">
                <template #default="{ row }">{{ triggerTypeLabel(row.trigger_type) }}</template>
              </el-table-column>
              <el-table-column label="触发人" width="100" prop="trigger_user_name" />
              <el-table-column label="耗时" width="90">
                <template #default="{ row }"><span class="muted">{{ formatDeployDuration(row.duration) }}</span></template>
              </el-table-column>
              <el-table-column label="时间" width="130">
                <template #default="{ row }">
                  <span class="muted" :title="formatFullDateTime(row.created_at)">{{ formatRelativeTime(row.created_at) }}</span>
                </template>
              </el-table-column>
              <el-table-column label="Jenkins" width="100">
                <template #default="{ row }">
                  <a v-if="row.jenkins_build_url" class="meta-link mono" :href="row.jenkins_build_url" target="_blank" rel="noopener noreferrer">#{{ row.jenkins_build_number }} ↗</a>
                  <span v-else class="muted">—</span>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="90" fixed="right">
                <template #default="{ row }">
                  <el-button text type="primary" size="small" @click="goRecord(row.id)">详情</el-button>
                </template>
              </el-table-column>
              <template #empty><el-empty description="暂无部署记录" :image-size="70" /></template>
            </el-table>
          </div>
          <el-pagination
            v-if="total > 0"
            class="pager"
            background
            :layout="paginationLayout"
            :total="total"
            :current-page="currentPage"
            :page-size="pageSize"
            :page-sizes="[10, 20, 50]"
            @current-change="handleCurrentChange"
            @size-change="handleSizeChange"
          />
        </el-tab-pane>

        <!-- 配置项 -->
        <el-tab-pane label="配置项" name="configs">
          <div class="tab-toolbar tab-toolbar--between">
            <span class="card-hint">配置项作为发布治理台账记录，供 Jenkins 流水线参数化引用</span>
            <el-button v-if="canConfig" type="primary" size="small" @click="openConfigDialog()">
              <el-icon><Plus /></el-icon>新增配置
            </el-button>
          </div>
          <div class="table-wrapper">
            <el-table :data="configs" v-loading="configsLoading">
              <el-table-column label="Key" min-width="160">
                <template #default="{ row }"><code class="mono config-key">{{ row.key }}</code></template>
              </el-table-column>
              <el-table-column label="Value" min-width="140">
                <template #default="{ row }"><span class="mono muted">{{ row.value || '—' }}</span></template>
              </el-table-column>
              <el-table-column label="环境" width="100">
                <template #default="{ row }"><span class="type-tag">{{ row.env_name || '全局' }}</span></template>
              </el-table-column>
              <el-table-column label="加密" width="70">
                <template #default="{ row }">
                  <el-icon v-if="row.is_encrypted" class="muted" title="已加密"><Lock /></el-icon>
                  <span v-else class="muted">—</span>
                </template>
              </el-table-column>
              <el-table-column label="说明" min-width="140">
                <template #default="{ row }"><span class="muted">{{ row.description || '—' }}</span></template>
              </el-table-column>
              <el-table-column v-if="canConfig" label="操作" width="130" fixed="right">
                <template #default="{ row }">
                  <el-button text type="primary" size="small" @click="openConfigDialog(row)">编辑</el-button>
                  <el-button text type="danger" size="small" @click="handleDeleteConfig(row)">删除</el-button>
                </template>
              </el-table-column>
              <template #empty><el-empty description="暂无配置项" :image-size="70" /></template>
            </el-table>
          </div>
        </el-tab-pane>

        <!-- 基本信息 -->
        <el-tab-pane label="基本信息" name="basic">
          <table class="basic-table">
            <tbody>
              <tr><td class="muted">应用名称</td><td class="basic-strong">{{ app.name }}</td></tr>
              <tr><td class="muted">显示名称</td><td>{{ app.display_name || '—' }}</td></tr>
              <tr><td class="muted">描述</td><td>{{ app.description || '—' }}</td></tr>
              <tr><td class="muted">应用类型</td><td>{{ typeLabel(app.app_type) }}</td></tr>
              <tr><td class="muted">Git 仓库</td><td class="mono basic-mono">{{ app.git_url || '—' }}<template v-if="app.git_url">（分支 {{ app.git_branch }}）</template></td></tr>
              <tr><td class="muted">Jenkins Job</td><td class="mono basic-mono">{{ app.jenkins_job_name || '—' }}</td></tr>
              <tr><td class="muted">创建人</td><td>{{ app.creator_name || '—' }} · {{ formatFullDateTime(app.created_at) }} 创建 · 最近更新 {{ formatRelativeTime(app.updated_at) }}</td></tr>
            </tbody>
          </table>
        </el-tab-pane>
      </el-tabs>
      <!-- 部署确认弹窗 -->
      <el-dialog v-model="deployDialogVisible" title="确认部署" width="520px" :close-on-click-modal="false">
        <div v-if="deployTarget" class="dlg-body">
          <div class="sum-box">
            <div class="sum-row"><span class="sum-k">应用</span><span class="sum-v">{{ app.name }}</span></div>
            <div class="sum-row">
              <span class="sum-k">目标环境</span>
              <span class="sum-v">{{ deployTarget.env_name }}<span v-if="deployTarget.approval_required" class="approval-tag">需审批</span></span>
            </div>
            <div class="sum-row"><span class="sum-k">Jenkins Job</span><span class="sum-v mono">{{ app.jenkins_job_name || '未配置' }}</span></div>
            <div class="sum-row"><span class="sum-k">当前版本</span><span class="sum-v mono">{{ deployTarget.latest_record?.version || '—' }}</span></div>
          </div>

          <div v-if="deployTarget.approval_required" class="warn-note" role="note">
            <el-icon><Warning /></el-icon>
            该环境需要审批：提交后进入「待审批」状态，审批通过后自动触发 Jenkins 执行。
          </div>

          <div class="field">
            <label for="deployVersionInput">版本号</label>
            <el-input id="deployVersionInput" v-model="deployVersion" placeholder="v3.1.9 / commit hash / tag" />
            <div class="hint">留空将自动使用「分支名 + 时间戳」兜底（如 main-20260824140211），保证 Jenkins 侧可追溯</div>
          </div>

          <div class="field field--last">
            <label>将下发给 Jenkins 的参数契约</label>
            <div class="sum-box sum-box--flat">
              <div class="sum-row"><span class="sum-k mono">APP_NAME</span><span class="sum-v mono">{{ app.name }}</span></div>
              <div class="sum-row"><span class="sum-k mono">ENV</span><span class="sum-v mono">{{ deployTarget.env_name }}</span></div>
              <div class="sum-row"><span class="sum-k mono">RELEASE_MODE</span><span class="sum-v mono">deploy</span></div>
              <div class="sum-row"><span class="sum-k mono">RECORD_ID…</span><span class="sum-v mono muted">提交后由平台生成并随参数下发</span></div>
            </div>
          </div>
        </div>
        <template #footer>
          <el-button @click="deployDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="deploying" @click="confirmDeploy">
            <el-icon><Promotion /></el-icon>确认部署
          </el-button>
        </template>
      </el-dialog>

      <!-- 配置项编辑弹窗 -->
      <el-dialog v-model="configDialogVisible" :title="configForm.id ? '编辑配置' : '新增配置'" width="480px" :close-on-click-modal="false">
        <el-form label-width="80px">
          <el-form-item label="Key" required>
            <el-input v-model="configForm.key" placeholder="如 DB_POOL_SIZE" />
          </el-form-item>
          <el-form-item label="Value">
            <el-input v-model="configForm.value" :type="configForm.is_encrypted ? 'password' : 'text'" placeholder="配置值" />
          </el-form-item>
          <el-form-item label="环境">
            <el-select v-model="configForm.env_id" placeholder="全局（所有环境）" clearable style="width: 100%">
              <el-option v-for="e in sortedEnvs" :key="e.env_id" :label="e.env_display_name || e.env_name" :value="e.env_id" />
            </el-select>
          </el-form-item>
          <el-form-item label="加密">
            <el-switch v-model="configForm.is_encrypted" />
            <span class="hint hint--inline">加密后列表中仅显示 ******</span>
          </el-form-item>
          <el-form-item label="说明">
            <el-input v-model="configForm.description" placeholder="用途说明（可选）" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="configDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="configSaving" @click="saveConfig">保存</el-button>
        </template>
      </el-dialog>
    </template>
  </div>
</template>
<script setup lang="ts">
import { ref, computed, watch, onActivated, onDeactivated } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowRight, CopyDocument, Lock, Plus, Promotion, Warning } from '@element-plus/icons-vue'
import {
  getDeployApp, updateDeployApp, getAppEnvs, executeDeploy, cancelDeploy,
  getDeployRecords, getAppConfigs, createAppConfig, updateAppConfig, deleteAppConfig,
} from '@/api/deploy'
import { usePagination } from '@/hooks/usePagination'
import { useAuthStore } from '@/stores/modules/auth'
import { formatRelativeTime, formatFullDateTime } from '@/utils/time'
import {
  deployStatusLabel, deployStatusType, isActiveStatus, triggerTypeLabel,
  formatDeployDuration, envColor,
} from '@/utils/deployStatus'

interface LatestRecord {
  id: number
  version: string
  status: string
  trigger_type: string
  trigger_user_name: string | null
  duration: number | null
  jenkins_build_url: string
  jenkins_build_number: number | null
  created_at: string | null
}

interface AppEnv {
  id: number
  env_id: number
  env_name: string
  env_display_name: string | null
  env_sort_order: number
  approval_required: boolean
  enabled: boolean
  latest_record: LatestRecord | null
}

interface AppInfo {
  id: number
  name: string
  display_name: string
  description: string
  app_type: string
  status: string
  git_url: string
  git_branch: string
  jenkins_job_name: string
  creator_name: string | null
  created_at: string
  updated_at: string
}

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const app = ref<AppInfo | null>(null)
const appEnvs = ref<AppEnv[]>([])
const pageLoading = ref(false)
const activeTab = ref('history')

const records = ref<any[]>([])
const historyLoading = ref(false)
const historyEnvId = ref<number | null>(null)

const configs = ref<any[]>([])
const configsLoading = ref(false)

const canExecute = computed(() => authStore.hasPermission('deploy.execute'))
const canUpdate = computed(() => authStore.hasPermission('deploy.update'))
const canConfig = computed(() => authStore.hasPermission('deploy.config'))

const appTypes = [
  { label: 'Web 应用', value: 'web' },
  { label: 'API 服务', value: 'api' },
  { label: '后台任务', value: 'worker' },
  { label: '前端项目', value: 'frontend' },
  { label: '其他', value: 'other' },
]
const typeLabel = (v: string) => appTypes.find(t => t.value === v)?.label || v

const sortedEnvs = computed(() =>
  [...appEnvs.value].sort((a, b) => (a.env_sort_order - b.env_sort_order) || (a.id - b.id)),
)

const isActive = (r: LatestRecord | null | undefined) => !!r && isActiveStatus(r.status)

// ── 数据加载 ──
const appName = () => String(route.params.name || '')

async function fetchApp() {
  const res: any = await getDeployApp(appName())
  app.value = res.data
}

async function fetchEnvs() {
  const res: any = await getAppEnvs(appName())
  appEnvs.value = res.data || []
}

async function fetchHistory(extra?: any) {
  historyLoading.value = true
  try {
    const res: any = await getDeployRecords({
      app_name: appName(),
      env_id: historyEnvId.value || undefined,
      page: extra?.page || currentPage.value,
      page_size: extra?.page_size || pageSize.value,
    })
    records.value = res.data.items
    total.value = res.data.total
  } finally {
    historyLoading.value = false
  }
}

const { currentPage, pageSize, total, paginationLayout, handleCurrentChange, handleSizeChange } = usePagination(fetchHistory)

async function fetchConfigs() {
  configsLoading.value = true
  try {
    const res: any = await getAppConfigs(appName())
    configs.value = res.data || []
  } finally {
    configsLoading.value = false
  }
}

async function fetchAll() {
  if (!appName()) return
  pageLoading.value = true
  try {
    await Promise.all([fetchApp(), fetchEnvs(), fetchConfigs()])
    await fetchHistory()
  } finally {
    pageLoading.value = false
  }
}

// ── 自动刷新：有进行中的部署时轮询环境卡片与历史 ──
let pollTimer: ReturnType<typeof setInterval> | null = null

function hasActive() {
  return appEnvs.value.some(e => isActive(e.latest_record))
}

function syncPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
  if (hasActive()) {
    pollTimer = setInterval(async () => {
      await fetchEnvs()
      await fetchHistory()
      if (!hasActive()) syncPolling()
    }, 10000)
  }
}

onActivated(fetchAll)
onDeactivated(() => { if (pollTimer) { clearInterval(pollTimer); pollTimer = null } })
watch(() => route.params.name, (n, o) => { if (n && n !== o) fetchAll() })
watch(appEnvs, syncPolling)

// ── 部署操作 ──
const deployDialogVisible = ref(false)
const deployTarget = ref<AppEnv | null>(null)
const deployVersion = ref('')
const deploying = ref(false)

function openDeploy(env: AppEnv) {
  deployTarget.value = env
  deployVersion.value = ''
  deployDialogVisible.value = true
}

async function confirmDeploy() {
  if (!deployTarget.value || !app.value) return
  deploying.value = true
  try {
    const res: any = await executeDeploy({
      app_name: app.value.name,
      env_id: deployTarget.value.env_id,
      version: deployVersion.value.trim() || undefined,
    })
    ElMessage.success(res.msg || '已提交')
    deployDialogVisible.value = false
    if (res.data?.id) router.push(`/deploy/records/${res.data.id}`)
  } finally {
    deploying.value = false
  }
}

async function handleCancel(record: LatestRecord) {
  await ElMessageBox.confirm(`确定取消部署单 #${record.id}（${record.version}）吗？`, '取消部署', {
    type: 'warning',
    confirmButtonText: '确定取消',
    cancelButtonText: '再想想',
  })
  await cancelDeploy(record.id)
  ElMessage.success('已取消')
  await fetchEnvs()
  await fetchHistory()
}

// ── 页头操作 ──
function goEdit() {
  router.push(`/deploy/apps/${app.value!.name}/edit`)
}

async function toggleArchive() {
  if (!app.value) return
  const archiving = app.value.status === 'active'
  await ElMessageBox.confirm(
    archiving
      ? `归档后应用将从发布总览矩阵中隐藏，且无法触发新部署。确定归档「${app.value.name}」吗？`
      : `确定恢复应用「${app.value.name}」吗？`,
    archiving ? '归档应用' : '恢复应用',
    { type: 'warning', confirmButtonText: '确定', cancelButtonText: '取消' },
  )
  const a = app.value
  await updateDeployApp(a.name, {
    name: a.name,
    display_name: a.display_name,
    description: a.description,
    app_type: a.app_type,
    status: archiving ? 'archived' : 'active',
    git_url: a.git_url,
    git_branch: a.git_branch,
    jenkins_job_name: a.jenkins_job_name,
  })
  ElMessage.success(archiving ? '已归档' : '已恢复')
  await fetchApp()
}

async function copyText(text: string) {
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制')
  } catch {
    ElMessage.warning('复制失败，请手动选择复制')
  }
}

function goRecord(id: number) {
  router.push(`/deploy/records/${id}`)
}

function goHistory(env: AppEnv) {
  router.push({ path: '/deploy/records', query: { app_name: app.value!.name, env_id: String(env.env_id) } })
}

// ── 配置项 ──
const configDialogVisible = ref(false)
const configSaving = ref(false)
const configForm = ref<{ id: number | null; key: string; value: string; env_id: number | null; is_encrypted: boolean; description: string }>({
  id: null, key: '', value: '', env_id: null, is_encrypted: false, description: '',
})

function openConfigDialog(row?: any) {
  configForm.value = row
    ? { id: row.id, key: row.key, value: row.is_encrypted ? '' : row.value, env_id: row.env_id, is_encrypted: row.is_encrypted, description: row.description }
    : { id: null, key: '', value: '', env_id: null, is_encrypted: false, description: '' }
  configDialogVisible.value = true
}

async function saveConfig() {
  const f = configForm.value
  if (!f.key.trim()) {
    ElMessage.warning('请填写 Key')
    return
  }
  configSaving.value = true
  try {
    const body = { key: f.key.trim(), value: f.value, env_id: f.env_id, is_encrypted: f.is_encrypted, description: f.description }
    if (f.id) {
      await updateAppConfig(f.id, body)
    } else {
      await createAppConfig(appName(), body)
    }
    ElMessage.success('已保存')
    configDialogVisible.value = false
    await fetchConfigs()
  } finally {
    configSaving.value = false
  }
}

async function handleDeleteConfig(row: any) {
  await ElMessageBox.confirm(`确定删除配置「${row.key}」吗？`, '删除配置', {
    type: 'warning',
    confirmButtonText: '删除',
    cancelButtonText: '取消',
  })
  await deleteAppConfig(row.id)
  ElMessage.success('已删除')
  await fetchConfigs()
}
</script>
<style scoped lang="scss">
.crumb {
  font-size: 13px;
  color: var(--text-muted);
  margin-bottom: 10px;

  a { color: var(--text-secondary); transition: color .15s; }
  a:hover { color: var(--primary-color); }
  .sep { margin: 0 6px; }
}

.detail-head {
  flex-wrap: wrap;
  gap: 10px;
}

.head-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.head-actions {
  display: flex;
  gap: 8px;
}

/* ── 状态 pill ── */
.pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;

  .dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: currentColor;
    flex: none;
  }

  .dot--pulse { animation: pulse 1.6s ease-in-out infinite; }

  &--success { color: #15803d; background: color-mix(in srgb, var(--success-color) 12%, transparent); }
  &--danger { color: #b42318; background: color-mix(in srgb, var(--danger-color) 10%, transparent); }
  &--warning { color: #b45309; background: color-mix(in srgb, var(--warning-color) 14%, transparent); }
  &--primary { color: var(--primary-color); background: var(--primary-bg); }
  &--info { color: var(--text-secondary); background: color-mix(in srgb, var(--text-muted) 14%, transparent); }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: .35; }
}

.type-tag {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 6px;
  font-size: 11.5px;
  font-weight: 600;
  color: var(--text-secondary);
  background: color-mix(in srgb, var(--text-muted) 12%, transparent);
}

.approval-tag {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 700;
  color: #b45309;
  background: color-mix(in srgb, var(--warning-color) 16%, transparent);
  margin-left: 6px;
}

.mono { font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace; }
.muted { color: var(--text-muted); }
.sp { flex: 1; }

/* ── 信息条 ── */
.info-strip {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1px;
  background: var(--border-color);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  overflow: hidden;
  margin-bottom: 18px;
}

.info-cell {
  background: var(--surface-color);
  padding: 13px 18px;
  min-width: 0;
}

.info-k {
  font-size: 11.5px;
  color: var(--text-muted);
  font-weight: 600;
  margin-bottom: 5px;
  letter-spacing: .3px;
}

.info-v {
  font-size: 13.5px;
  font-weight: 650;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 7px;
  word-break: break-all;

  &--sm { font-size: 12.5px; }

  .type-tag { margin-left: 4px; }
}

.copy-btn {
  border: 0;
  background: transparent;
  cursor: pointer;
  color: var(--text-muted);
  padding: 2px;
  border-radius: 4px;
  display: inline-grid;
  place-items: center;
  transition: color .15s;

  &:hover { color: var(--primary-color); }
}

/* ── 环境管道 ── */
.pipe {
  display: flex;
  align-items: stretch;
  margin-bottom: 18px;
}

.pipe-arrow {
  width: 36px;
  flex: none;
  display: grid;
  place-items: center;
  color: var(--text-muted);
  font-size: 18px;
}

.env-card {
  flex: 1;
  min-width: 0;
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-top: 3px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: 16px 18px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  transition: box-shadow .2s ease-out;

  &--running {
    box-shadow: 0 0 0 3px var(--primary-bg);
  }

  &--disabled {
    opacity: .62;
  }
}

.env-head {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.env-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex: none;
}

.env-name { font-size: 14px; font-weight: 750; }
.env-key { font-size: 11.5px; }

.env-ver {
  font-size: 19px;
  font-weight: 800;
  letter-spacing: -.2px;
  word-break: break-all;

  &--none { font-size: 13px; color: var(--text-muted); font-weight: 500; }
}

.env-meta {
  font-size: 12px;
  color: var(--text-muted);
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-height: 34px;
}

.meta-link {
  color: var(--primary-color);
  font-size: 12px;

  &:hover { text-decoration: underline; }
}

.env-foot {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-top: auto;

  .el-button + .el-button { margin-left: 0; }
}

/* ── Tabs ── */
.detail-tabs {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: 4px 16px 16px;

  :deep(.el-tabs__header) { margin-bottom: 8px; }
  :deep(.el-tabs__item) { font-weight: 600; }
}

.tab-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 0 12px;

  &--between { justify-content: space-between; }
}

.history-env-filter { width: 160px; }

.card-hint {
  font-size: 12.5px;
  color: var(--text-muted);
}

.version-code { font-weight: 700; font-size: 12.5px; }
.config-key { color: var(--primary-color); font-weight: 700; font-size: 12.5px; }

.pager {
  margin-top: 14px;
  justify-content: flex-end;
}

/* ── 基本信息表 ── */
.basic-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13.5px;

  td {
    padding: 11px 12px;
    border-bottom: 1px solid var(--border-color);
    vertical-align: top;
  }

  tr:last-child td { border-bottom: 0; }

  td:first-child {
    width: 140px;
    font-weight: 500;
  }
}

.basic-strong { font-weight: 650; }
.basic-mono { font-size: 12.5px; }

/* ── 部署弹窗 ── */
.dlg-body { display: flex; flex-direction: column; gap: 14px; }

.sum-box {
  background: color-mix(in srgb, var(--text-muted) 7%, transparent);
  border-radius: var(--border-radius);
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;

  &--flat { padding: 10px 16px; }
}

.sum-row {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 13px;
}

.sum-k {
  width: 88px;
  flex: none;
  color: var(--text-muted);
  font-size: 12px;
}

.sum-v {
  font-weight: 600;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 6px;
  word-break: break-all;
}

.warn-note {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  font-size: 12.5px;
  line-height: 1.6;
  color: #b45309;
  background: color-mix(in srgb, var(--warning-color) 12%, transparent);
  border: 1px solid color-mix(in srgb, var(--warning-color) 30%, transparent);
  border-radius: var(--border-radius);
  padding: 10px 12px;

  .el-icon { margin-top: 2px; flex: none; }
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;

  label {
    font-size: 13px;
    font-weight: 600;
    color: var(--text-secondary);
  }

  &--last { margin-bottom: 0; }
}

.hint {
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1.5;

  &--inline { margin-left: 10px; }
}

/* ── 响应式 ── */
@media (max-width: 900px) {
  .info-strip { grid-template-columns: repeat(2, 1fr); }

  .pipe { flex-direction: column; gap: 4px; }

  .pipe-arrow {
    width: auto;
    height: 28px;
    transform: rotate(90deg);
  }
}

@media (max-width: 768px) {
  .info-strip { grid-template-columns: 1fr; }
  .detail-head { flex-direction: column; align-items: flex-start; }
}
</style>
