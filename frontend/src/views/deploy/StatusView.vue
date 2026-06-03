<template>
  <div>
    <div class="page-header">
      <h2 class="page-title">发布看板</h2>
      <div style="display: flex; gap: 8px;">
        <el-button type="primary" @click="showQuickDeploy()">
          <el-icon><Upload /></el-icon> 快捷发布
        </el-button>
        <el-button @click="fetchData" :loading="loading">
          <el-icon><Refresh /></el-icon> 刷新
        </el-button>
      </div>
    </div>

    <!-- 概览卡片 -->
    <el-row :gutter="16" class="stat-row">
      <el-col :span="6"><div class="stat-card"><div class="stat-value">{{ overview.total_apps || 0 }}</div><div class="stat-label">应用总数</div></div></el-col>
      <el-col :span="6"><div class="stat-card"><div class="stat-value">{{ overview.building_count || 0 }}</div><div class="stat-label">构建中</div></div></el-col>
      <el-col :span="6"><div class="stat-card"><div class="stat-value">{{ overview.success_rate || 0 }}%</div><div class="stat-label">成功率</div></div></el-col>
      <el-col :span="6"><div class="stat-card"><div class="stat-value">{{ overview.pending_count || 0 }}</div><div class="stat-label">待审批</div></div></el-col>
    </el-row>

    <!-- 空状态引导 -->
    <div v-if="!loading && matrix.length === 0" class="empty-guide">
      <div class="empty-icon">📦</div>
      <h3>还没有注册应用</h3>
      <p>先注册一个应用，配置部署环境，就可以在这里一键发布啦</p>
      <el-button type="primary" @click="$router.push('/deploy/apps')">去注册应用</el-button>
    </div>

    <!-- 发布状态矩阵 -->
    <div v-else class="data-card">
      <div class="filter-bar">
        <span style="font-weight: 600; font-size: 15px;">应用 × 环境状态</span>
      </div>
      <el-table :data="matrix" stripe v-loading="loading" @row-click="handleRowClick">
        <el-table-column prop="app_name" label="应用" min-width="160">
          <template #default="{row}">
            <div>
              <strong>{{ row.display_name || row.app_name }}</strong>
              <div style="font-size: 12px; color: var(--text-muted);">{{ row.app_name }}</div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="app_type" label="类型" width="80">
          <template #default="{row}"><el-tag size="small" :type="appTypeType(row.app_type)">{{ appTypeLabel(row.app_type) }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="deploy_method" label="部署方式" width="100">
          <template #default="{row}"><el-tag size="small" type="info">{{ row.deploy_method }}</el-tag></template>
        </el-table-column>
        <el-table-column v-for="env in envColumns" :key="env.name" :label="env.display_name" min-width="150">
          <template #default="{row}">
            <div v-if="row.envs[env.name]" class="env-cell">
              <el-tag :type="statusType(row.envs[env.name].status)" size="small" class="env-status-tag">
                {{ statusLabel(row.envs[env.name].status) }}
              </el-tag>
              <span class="env-version" :title="row.envs[env.name].version">{{ row.envs[env.name].version }}</span>
              <el-button
                v-if="row.envs[env.name].record_id"
                size="small" text type="primary"
                @click.stop="$router.push(`/deploy/records/${row.envs[env.name].record_id}`)"
                class="env-detail-btn"
              >详情</el-button>
            </div>
            <span v-else style="color: var(--text-muted);">-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{row}">
            <el-button size="small" type="primary" @click.stop="showQuickDeploy(row)">发布</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 快捷发布对话框 -->
    <el-dialog v-model="deployDialogVisible" title="快捷发布" width="480px" destroy-on-close>
      <el-form :model="deployForm" label-width="80px">
        <el-form-item label="应用">
          <el-select v-model="deployForm.application_id" placeholder="选择应用" style="width:100%" filterable>
            <el-option v-for="app in allApps" :key="app.app_id" :label="app.display_name || app.app_name" :value="app.app_id">
              <span>{{ app.display_name || app.app_name }}</span>
              <span style="color: var(--text-muted); font-size: 12px; margin-left: 8px;">{{ app.deploy_method }}</span>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="环境">
          <el-select v-model="deployForm.environment_id" placeholder="选择环境" style="width:100%">
            <el-option v-for="env in availableEnvs" :key="env.id" :label="env.display_name || env.name" :value="env.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="版本号">
          <el-input v-model="deployForm.version" placeholder="如 v1.2.3、main、commit SHA" />
        </el-form-item>
        <el-form-item v-if="selectedApp?.deploy_method === 'docker'" label="镜像地址">
          <el-input v-model="deployForm.image" placeholder="registry/repo:tag" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="deployDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleQuickDeploy" :loading="deploying">确认发布</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getDeployStatus, getDeployOverview, getDeployEnvs, createDeployment, getDeployApps } from '@/api/deploy'
import { ElMessage } from 'element-plus'

const router = useRouter()
const loading = ref(false)
const matrix = ref<any[]>([])
const overview = ref<any>({})
const envs = ref<any[]>([])
const allApps = ref<any[]>([])

const deployDialogVisible = ref(false)
const deploying = ref(false)
const deployForm = ref({ application_id: null as number | null, environment_id: null as number | null, version: '', image: '' })

const envColumns = computed(() => envs.value.map(e => ({ name: e.name, display_name: e.display_name })))

const selectedApp = computed(() => allApps.value.find(a => a.app_id === deployForm.value.application_id))
const availableEnvs = computed(() => envs.value)

const appTypeType = (t: string) => ({ backend: '', frontend: 'success', service: 'warning', other: 'info' }[t] || '') as any
const appTypeLabel = (t: string) => ({ backend: '后端', frontend: '前端', service: '服务', other: '其他' }[t] || t)
const statusType = (s: string) => ({ success: 'success', failed: 'danger', building: 'warning', deploying: 'warning', pending: 'info', approved: 'primary', rejected: 'danger', rolled_back: 'info', none: 'info' }[s] || 'info') as any
const statusLabel = (s: string) => ({ success: '成功', failed: '失败', building: '构建中', deploying: '部署中', pending: '待审批', approved: '已通过', rejected: '已驳回', rolled_back: '已回滚', none: '未部署' }[s] || s)

function handleRowClick(row: any) {
  router.push(`/deploy/apps/${row.app_id}`)
}

function showQuickDeploy(row?: any) {
  deployForm.value = {
    application_id: row?.app_id || null,
    environment_id: null,
    version: '',
    image: '',
  }
  deployDialogVisible.value = true
}

async function handleQuickDeploy() {
  if (!deployForm.value.application_id) { ElMessage.warning('请选择应用'); return }
  if (!deployForm.value.environment_id) { ElMessage.warning('请选择环境'); return }
  deploying.value = true
  try {
    await createDeployment(deployForm.value as any)
    ElMessage.success('发布已触发')
    deployDialogVisible.value = false
    fetchData()
  } finally { deploying.value = false }
}

async function fetchData() {
  loading.value = true
  try {
    const [statusRes, overviewRes, envsRes, appsRes] = await Promise.all([
      getDeployStatus(),
      getDeployOverview(),
      getDeployEnvs(),
      getDeployApps({ page_size: 100 }),
    ])
    matrix.value = (statusRes as any).data || []
    overview.value = (overviewRes as any).data || {}
    envs.value = (envsRes as any).data || []
    allApps.value = (appsRes as any).data?.items || []
  } finally { loading.value = false }
}

onMounted(fetchData)
</script>

<style scoped>
.stat-row { margin-bottom: 16px; }
.stat-card { background: var(--surface-color); border: 1px solid var(--border-color); border-radius: 8px; padding: 16px; text-align: center; }
.stat-value { font-size: 28px; font-weight: 700; color: var(--text-primary); }
.stat-label { font-size: 13px; color: var(--text-muted); margin-top: 4px; }
.data-card { background: var(--surface-color); border: 1px solid var(--border-color); border-radius: 8px; padding: 16px; }
.filter-bar { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.env-cell { display: flex; align-items: center; gap: 6px; }
.env-status-tag { flex-shrink: 0; }
.env-version { font-size: 12px; color: var(--text-secondary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 80px; }
.env-detail-btn { flex-shrink: 0; }
.empty-guide { text-align: center; padding: 60px 20px; background: var(--surface-color); border: 1px solid var(--border-color); border-radius: 8px; }
.empty-icon { font-size: 48px; margin-bottom: 16px; }
.empty-guide h3 { color: var(--text-primary); margin-bottom: 8px; }
.empty-guide p { color: var(--text-muted); margin-bottom: 20px; }
</style>
