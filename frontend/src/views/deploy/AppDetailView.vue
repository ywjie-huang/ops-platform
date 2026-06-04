<template>
  <div>
    <!-- 页面头部 -->
    <div class="page-header">
      <div style="display: flex; align-items: center; gap: 12px;">
        <el-button text @click="$router.push('/deploy/apps')"><el-icon><ArrowLeft /></el-icon> 返回</el-button>
        <h2 class="page-title">{{ app.display_name || app.name || '应用详情' }}</h2>
        <el-tag v-if="app.deploy_method" size="small" type="info">{{ app.deploy_method }}</el-tag>
        <el-tag v-if="app.status" :type="app.status === 'active' ? 'success' : 'info'" size="small">{{ app.status === 'active' ? '活跃' : '已归档' }}</el-tag>
      </div>
      <div style="display: flex; gap: 8px;">
        <el-button type="primary" @click="showDeployDialog()"><el-icon><Upload /></el-icon> 发布</el-button>
        <el-button @click="fetchData" :loading="refreshing"><el-icon><Refresh /></el-icon> 刷新</el-button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="16" class="stat-row">
      <el-col :span="6"><div class="stat-card"><div class="stat-value">{{ app.app_type === 'backend' ? '后端' : app.app_type === 'frontend' ? '前端' : app.app_type }}</div><div class="stat-label">应用类型</div></div></el-col>
      <el-col :span="6"><div class="stat-card"><div class="stat-value">{{ envConfigs.length }}</div><div class="stat-label">环境配置数</div></div></el-col>
      <el-col :span="6"><div class="stat-card"><div class="stat-value">{{ app.repo_branch || '-' }}</div><div class="stat-label">默认分支</div></div></el-col>
      <el-col :span="6"><div class="stat-card"><div class="stat-value">{{ records.length }}</div><div class="stat-label">发布次数</div></div></el-col>
    </el-row>

    <!-- Tab 内容 -->
    <div class="data-card">
      <el-tabs v-model="activeTab">
        <!-- 基本信息 -->
        <el-tab-pane label="基本信息" name="info">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="应用标识">{{ app.name }}</el-descriptions-item>
            <el-descriptions-item label="显示名称">{{ app.display_name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="应用类型">{{ app.app_type }}</el-descriptions-item>
            <el-descriptions-item label="部署方式">{{ app.deploy_method }}</el-descriptions-item>
            <el-descriptions-item label="仓库地址" :span="2">{{ app.repo_url || '-' }}</el-descriptions-item>
            <el-descriptions-item label="默认分支">{{ app.repo_branch || '-' }}</el-descriptions-item>
            <el-descriptions-item label="创建人">{{ app.creator_name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="描述" :span="2">{{ app.description || '-' }}</el-descriptions-item>
            <el-descriptions-item label="创建时间">{{ formatTime(app.created_at) }}</el-descriptions-item>
            <el-descriptions-item label="更新时间">{{ formatTime(app.updated_at) }}</el-descriptions-item>
          </el-descriptions>
        </el-tab-pane>

        <!-- 环境配置 -->
        <el-tab-pane label="环境配置" name="envs">
          <div style="margin-bottom: 12px;">
            <el-button type="primary" size="small" @click="showEnvDialog()">+ 添加环境配置</el-button>
          </div>
          <el-table :data="envConfigs" stripe>
            <el-table-column prop="environment_display_name" label="环境" width="120">
              <template #default="{row}"><el-tag size="small">{{ row.environment_display_name || row.environment_name }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="jenkins_job_name" label="Jenkins Job" min-width="180" show-overflow-tooltip />
            <el-table-column prop="docker_image" label="Docker 镜像" min-width="200" show-overflow-tooltip />
            <el-table-column prop="k8s_namespace" label="K8s 命名空间" width="120" />
            <el-table-column prop="k8s_deployment_name" label="K8s Deployment" min-width="150" />
            <el-table-column label="操作" width="140" fixed="right">
              <template #default="{row}">
                <el-button size="small" text type="primary" @click="showEnvDialog(row)">编辑</el-button>
                <el-popconfirm title="确认移除该环境配置？" @confirm="handleDeleteEnv(row.environment_id)">
                  <template #reference><el-button size="small" text type="danger">移除</el-button></template>
                </el-popconfirm>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <!-- 发布历史 -->
        <el-tab-pane label="发布历史" name="records">
          <el-table :data="records" stripe>
            <el-table-column prop="id" label="ID" width="60" />
            <el-table-column prop="environment_display_name" label="环境" width="100">
              <template #default="{row}"><el-tag size="small">{{ row.environment_display_name || row.environment_name }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="version" label="版本" min-width="120" show-overflow-tooltip />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{row}"><el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="creator_name" label="发起人" width="80" />
            <el-table-column prop="duration_seconds" label="耗时" width="80">
              <template #default="{row}">{{ row.duration_seconds ? row.duration_seconds + 's' : '-' }}</template>
            </el-table-column>
            <el-table-column prop="created_at" label="时间" width="160">
              <template #default="{row}">{{ formatTime(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="180" fixed="right">
              <template #default="{row}">
                <el-button size="small" text type="primary" @click="$router.push(`/deploy/records/${row.id}`)">详情</el-button>
                <el-button v-if="row.status === 'failed' || row.status === 'rejected'" size="small" text type="warning" @click="handleRetry(row.id)">重试</el-button>
                <el-button v-if="row.status === 'success' || row.status === 'failed'" size="small" text type="warning" @click="handleRollback(row.id)">回滚</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- 环境配置对话框 -->
    <el-dialog v-model="envDialogVisible" :title="editingEnvId ? '编辑环境配置' : '添加环境配置'" width="580px" destroy-on-close>
      <el-form :model="envForm" label-width="100px">
        <el-form-item label="环境">
          <el-select v-model="envForm.environment_id" style="width:100%" :disabled="!!editingEnvId">
            <el-option v-for="e in allEnvs" :key="e.id" :label="e.display_name || e.name" :value="e.id" />
          </el-select>
        </el-form-item>
        <el-divider content-position="left">Jenkins 配置</el-divider>
        <el-form-item label="Jenkins Job"><el-input v-model="envForm.jenkins_job_name" placeholder="Job 名称" /></el-form-item>
        <el-form-item label="构建参数"><el-input v-model="envForm.jenkins_params_json" type="textarea" :rows="2" placeholder='{"KEY":"value"}' /></el-form-item>
        <el-divider content-position="left">SSH 部署配置</el-divider>
        <el-form-item label="目标主机">
          <el-select v-model="envForm.ssh_asset_id" placeholder="选择主机" style="width:100%" clearable filterable>
            <el-option v-for="a in assets" :key="a.id" :label="`${a.name} (${a.ip_address})`" :value="a.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="部署路径"><el-input v-model="envForm.ssh_deploy_path" placeholder="/opt/apps/user-service/" /></el-form-item>
        <el-form-item label="部署脚本"><el-input v-model="envForm.ssh_deploy_script" type="textarea" :rows="2" placeholder="bash deploy.sh 或 systemctl restart user-service" /></el-form-item>
        <el-divider content-position="left">Docker / K8s 配置</el-divider>
        <el-form-item label="Docker 镜像"><el-input v-model="envForm.docker_image" placeholder="registry/repo:tag" /></el-form-item>
        <el-form-item label="K8s 命名空间"><el-input v-model="envForm.k8s_namespace" placeholder="default" /></el-form-item>
        <el-form-item label="K8s Deployment"><el-input v-model="envForm.k8s_deployment_name" placeholder="deployment 名称" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="envDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveEnv">保存</el-button>
      </template>
    </el-dialog>

    <!-- 发布对话框（支持普通发布和文件上传） -->
    <el-dialog v-model="deployDialogVisible" title="发布" width="500px" destroy-on-close>
      <el-form :model="deployForm" label-width="80px">
        <el-form-item label="环境">
          <el-select v-model="deployForm.environment_id" style="width:100%">
            <el-option v-for="ae in envConfigs" :key="ae.environment_id" :label="ae.environment_display_name || ae.environment_name" :value="ae.environment_id" />
          </el-select>
        </el-form-item>
        <el-form-item label="版本号"><el-input v-model="deployForm.version" placeholder="v1.0.0 / commit SHA" /></el-form-item>
        <el-form-item v-if="isSSHDeploy" label="上传文件">
          <el-upload
            ref="uploadRef"
            :auto-upload="false"
            :limit="1"
            :on-change="handleFileChange"
            :on-exceed="() => ElMessage.warning('只能上传一个文件')"
            drag
          >
            <el-icon style="font-size: 40px; color: var(--text-muted);"><Upload /></el-icon>
            <div style="color: var(--text-muted);">将文件拖到此处，或<em>点击上传</em></div>
            <template #tip>
              <div style="color: var(--text-muted); font-size: 12px;">支持 jar、zip、tar.gz 等部署包，最大 500MB</div>
            </template>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="deployDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleDeploy" :loading="deploying">
          {{ isSSHDeploy ? '上传并部署' : '确认发布' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onActivated } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getDeployApp, getAppEnvConfigs, saveAppEnvConfig, deleteAppEnvConfig, getDeployRecords, createDeployment, retryDeployment, rollbackDeployment, getDeployEnvs, uploadAndDeploy } from '@/api/deploy'
import { getAssets } from '@/api/assets'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()
const refreshing = ref(false)
const activeTab = ref('info')
const app = ref<any>({})
const envConfigs = ref<any[]>([])
const records = ref<any[]>([])
const allEnvs = ref<any[]>([])
const assets = ref<any[]>([])

const envDialogVisible = ref(false)
const editingEnvId = ref<number | null>(null)
const envForm = reactive({
  environment_id: null as number | null,
  jenkins_job_name: '', jenkins_params_json: '{}',
  docker_image: '', docker_host_id: null,
  k8s_cluster_id: null, k8s_namespace: 'default', k8s_deployment_name: '',
  ssh_asset_id: null as number | null, ssh_deploy_path: '', ssh_deploy_script: '',
})

const deployDialogVisible = ref(false)
const deployForm = reactive({ environment_id: null as number | null, version: '' })
const uploadFile = ref<File | null>(null)
const deploying = ref(false)

const isSSHDeploy = computed(() => {
  if (!deployForm.environment_id) return false
  const cfg = envConfigs.value.find(c => c.environment_id === deployForm.environment_id)
  return app.value.deploy_method === 'ssh' || (cfg && cfg.ssh_asset_id)
})

const statusType = (s: string) => ({ success: 'success', failed: 'danger', building: 'warning', deploying: 'warning', pending: 'info', approved: 'primary', rejected: 'danger', rolled_back: 'info' }[s] || 'info') as any
const statusLabel = (s: string) => ({ success: '成功', failed: '失败', building: '构建中', deploying: '部署中', pending: '待审批', approved: '已通过', rejected: '已驳回', rolled_back: '已回滚' }[s] || s)
const formatTime = (t: string) => t ? new Date(t).toLocaleString('zh-CN') : '-'

async function fetchData() {
  const id = Number(route.params.id)
  if (!id) return
  refreshing.value = true
  try {
    const [appRes, envsRes, recordsRes, allEnvsRes, assetsRes] = await Promise.all([
      getDeployApp(id),
      getAppEnvConfigs(id),
      getDeployRecords({ application_id: id }),
      getDeployEnvs(),
      getAssets(),
    ])
    app.value = (appRes as any).data
    envConfigs.value = (envsRes as any).data || []
    records.value = (recordsRes as any).data?.items || []
    allEnvs.value = (allEnvsRes as any).data || []
    assets.value = (assetsRes as any).data?.items || (assetsRes as any).data || []
  } finally { refreshing.value = false }
}

function showEnvDialog(row?: any) {
  editingEnvId.value = row?.environment_id || null
  Object.assign(envForm, row || {
    environment_id: null, jenkins_job_name: '', jenkins_params_json: '{}',
    docker_image: '', docker_host_id: null,
    k8s_cluster_id: null, k8s_namespace: 'default', k8s_deployment_name: '',
    ssh_asset_id: null, ssh_deploy_path: '', ssh_deploy_script: '',
  })
  envDialogVisible.value = true
}

async function handleSaveEnv() {
  if (!envForm.environment_id) { ElMessage.warning('请选择环境'); return }
  await saveAppEnvConfig(Number(route.params.id), envForm)
  ElMessage.success('保存成功')
  envDialogVisible.value = false
  fetchData()
}

async function handleDeleteEnv(envId: number) {
  await deleteAppEnvConfig(Number(route.params.id), envId)
  ElMessage.success('已移除')
  fetchData()
}

function showDeployDialog() {
  deployForm.environment_id = null
  deployForm.version = ''
  uploadFile.value = null
  deployDialogVisible.value = true
}

function handleFileChange(file: any) {
  uploadFile.value = file.raw || null
}

async function handleRetry(recordId: number) {
  await retryDeployment(recordId)
  ElMessage.success('重试已触发')
  fetchData()
}

async function handleRollback(recordId: number) {
  await rollbackDeployment(recordId)
  ElMessage.success('回滚记录已创建')
  fetchData()
}

async function handleDeploy() {
  if (!deployForm.environment_id) { ElMessage.warning('请选择环境'); return }

  deploying.value = true
  try {
    if (isSSHDeploy.value) {
      // SSH 部署：上传文件
      if (!uploadFile.value) { ElMessage.warning('请上传部署文件'); return }
      const formData = new FormData()
      formData.append('application_id', String(Number(route.params.id)))
      formData.append('environment_id', String(deployForm.environment_id))
      formData.append('version', deployForm.version)
      formData.append('file', uploadFile.value)
      await uploadAndDeploy(formData)
      ElMessage.success('部署完成')
    } else {
      await createDeployment({ application_id: Number(route.params.id), environment_id: deployForm.environment_id, version: deployForm.version })
      ElMessage.success('发布已触发')
    }
    deployDialogVisible.value = false
    fetchData()
  } finally { deploying.value = false }
}

// keep-alive 下 onMounted 只触发一次，用 onActivated 每次进入都刷新
onActivated(fetchData)
</script>

<style scoped>
.stat-row { margin-bottom: 16px; }
.stat-card { background: var(--surface-color); border: 1px solid var(--border-color); border-radius: 8px; padding: 16px; text-align: center; }
.stat-value { font-size: 24px; font-weight: 700; color: var(--text-primary); }
.stat-label { font-size: 13px; color: var(--text-muted); margin-top: 4px; }
.data-card { background: var(--surface-color); border: 1px solid var(--border-color); border-radius: 8px; padding: 16px; }
</style>
