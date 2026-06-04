<template>
  <div>
    <div class="page-header">
      <h2 class="page-title">{{ app.name || '应用详情' }}</h2>
      <div class="header-actions">
        <el-button @click="$router.push(`/deploy/apps/${appId}/edit`)">编辑</el-button>
        <el-button @click="$router.push('/deploy/apps')">返回列表</el-button>
      </div>
    </div>

    <el-tabs v-model="activeTab" class="detail-tabs">
      <!-- Tab 1: 概览 -->
      <el-tab-pane label="概览" name="overview">
        <div class="data-card">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="应用名称">{{ app.name }}</el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="app.status === 'active' ? 'success' : 'info'" size="small">
                {{ app.status === 'active' ? '活跃' : '已归档' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="应用类型">{{ typeLabel(app.app_type) }}</el-descriptions-item>
            <el-descriptions-item label="部署策略">
              <el-tag :type="strategyType(app.deploy_strategy)" size="small">{{ strategyLabel(app.deploy_strategy) }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="描述" :span="2">{{ app.description || '—' }}</el-descriptions-item>
            <el-descriptions-item label="Git 仓库">{{ app.git_url || '—' }}</el-descriptions-item>
            <el-descriptions-item label="默认分支">{{ app.git_branch || '—' }}</el-descriptions-item>
            <el-descriptions-item label="构建模式">{{ app.build_mode === 'jenkins' ? 'Jenkins' : '本地构建' }}</el-descriptions-item>
            <el-descriptions-item label="构建命令/Job">{{ app.build_mode === 'jenkins' ? app.jenkins_job_name : (app.build_command || '—') }}</el-descriptions-item>
            <el-descriptions-item label="产物路径">{{ app.artifact_path || '—' }}</el-descriptions-item>
            <el-descriptions-item label="健康检查">{{ app.health_check_url || '—' }}</el-descriptions-item>
            <el-descriptions-item label="创建人">{{ app.creator_name || '—' }}</el-descriptions-item>
            <el-descriptions-item label="创建时间">{{ formatTime(app.created_at) }}</el-descriptions-item>
          </el-descriptions>
        </div>
      </el-tab-pane>

      <!-- Tab 2: 环境管理 -->
      <el-tab-pane label="环境管理" name="envs">
        <div v-loading="envLoading">
          <el-empty v-if="!envLoading && appEnvs.length === 0" description="暂无环境配置" />

          <div v-for="ae in appEnvs" :key="ae.id" class="env-card">
            <div class="env-card-header">
              <div class="env-card-title">
                <span class="env-name">{{ ae.env_name }}</span>
                <el-tag v-if="ae.approval_required" type="warning" size="small">需审批</el-tag>
                <el-tag :type="ae.enabled ? 'success' : 'info'" size="small">
                  {{ ae.enabled ? '已启用' : '已禁用' }}
                </el-tag>
              </div>
              <div class="env-card-actions">
                <el-button size="small" type="primary" @click="openDeployDialog(ae)" :disabled="!ae.enabled">
                  <el-icon><Promotion /></el-icon>部署
                </el-button>
                <el-button size="small" text type="primary" @click="openEnvDialog(ae)">配置</el-button>
                <el-popconfirm title="确认移除此环境配置？" @confirm="handleRemoveEnv(ae.env_id)">
                  <template #reference><el-button size="small" text type="danger">移除</el-button></template>
                </el-popconfirm>
              </div>
            </div>

            <div class="env-card-body">
              <!-- SSH 策略 -->
              <template v-if="app.deploy_strategy === 'ssh'">
                <div class="env-field"><span class="env-field-label">目标主机：</span>{{ ae.ssh_asset_name ? `${ae.ssh_asset_name} (${ae.ssh_asset_ip})` : '未配置' }}</div>
                <div class="env-field"><span class="env-field-label">部署路径：</span>{{ ae.deploy_path || '未配置' }}</div>
                <div class="env-field"><span class="env-field-label">部署脚本：</span><code>{{ ae.deploy_script || '无' }}</code></div>
              </template>

              <!-- Docker 策略 -->
              <template v-if="app.deploy_strategy === 'docker'">
                <div class="env-field"><span class="env-field-label">Docker 主机：</span>{{ ae.docker_host_name || '未配置' }}</div>
                <div class="env-field"><span class="env-field-label">镜像：</span>{{ ae.docker_image || '未配置' }}</div>
                <div class="env-field"><span class="env-field-label">容器名：</span>{{ ae.docker_container_name || '—' }}</div>
                <div class="env-field"><span class="env-field-label">端口映射：</span>{{ ae.docker_ports || '—' }}</div>
                <div class="env-field"><span class="env-field-label">网络：</span>{{ ae.docker_network || '—' }}</div>
              </template>

              <!-- K8s 策略 -->
              <template v-if="app.deploy_strategy === 'k8s'">
                <div class="env-field"><span class="env-field-label">K8s 集群：</span>{{ ae.k8s_cluster_name || '未配置' }}</div>
                <div class="env-field"><span class="env-field-label">命名空间：</span>{{ ae.k8s_namespace }}</div>
                <div class="env-field"><span class="env-field-label">Deployment：</span>{{ ae.k8s_deployment || '未配置' }}</div>
                <div class="env-field"><span class="env-field-label">容器名：</span>{{ ae.k8s_container_name || '—' }}</div>
              </template>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <!-- Tab 3: 部署历史（占位） -->
      <el-tab-pane label="部署历史" name="history">
        <div class="data-card">
          <el-empty description="部署历史功能开发中（Step 6）" />
        </div>
      </el-tab-pane>

      <!-- Tab 4: 配置管理（占位） -->
      <el-tab-pane label="配置管理" name="configs">
        <div class="data-card">
          <el-empty description="配置管理功能开发中（Step 10）" />
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 环境配置弹窗 -->
    <el-dialog v-model="envDialogVisible" :title="`配置 — ${editingEnv?.env_name || ''}`" width="680px" top="5vh">
      <el-form v-if="editingEnv" :model="envForm" label-width="110px">
        <el-form-item label="启用">
          <el-switch v-model="envForm.enabled" />
        </el-form-item>

        <!-- SSH 配置 -->
        <template v-if="app.deploy_strategy === 'ssh'">
          <el-form-item label="目标主机">
            <el-select v-model="envForm.ssh_asset_id" placeholder="选择主机" style="width: 100%" filterable clearable>
              <el-option v-for="a in assets" :key="a.id" :label="`${a.name} (${a.ip_address})`" :value="a.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="部署路径">
            <el-input v-model="envForm.deploy_path" placeholder="/opt/apps/myapp/" />
          </el-form-item>
          <el-form-item label="部署脚本">
            <el-input v-model="envForm.deploy_script" type="textarea" :rows="5" placeholder="# 部署后执行的脚本&#10;cd /opt/apps/myapp&#10;./restart.sh" />
          </el-form-item>
        </template>

        <!-- Docker 配置 -->
        <template v-if="app.deploy_strategy === 'docker'">
          <el-form-item label="Docker 主机">
            <el-select v-model="envForm.docker_host_id" placeholder="选择 Docker 主机" style="width: 100%" filterable clearable>
              <el-option v-for="h in dockerHosts" :key="h.id" :label="h.name" :value="h.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="镜像">
            <el-input v-model="envForm.docker_image" placeholder="registry.example.com/app:latest" />
          </el-form-item>
          <el-form-item label="容器名">
            <el-input v-model="envForm.docker_container_name" placeholder="my-app" />
          </el-form-item>
          <el-form-item label="端口映射">
            <el-input v-model="envForm.docker_ports" placeholder="8080:80,443:443" />
          </el-form-item>
          <el-form-item label="环境变量">
            <el-input v-model="envForm.docker_env_vars" type="textarea" :rows="3" placeholder='{"KEY":"value","DB_HOST":"10.0.0.1"}' />
          </el-form-item>
          <el-form-item label="网络">
            <el-input v-model="envForm.docker_network" placeholder="bridge / host / 自定义网络名" />
          </el-form-item>
          <el-form-item label="额外参数">
            <el-input v-model="envForm.docker_extra_args" type="textarea" :rows="2" placeholder="--restart=always -v /data:/data" />
          </el-form-item>
        </template>

        <!-- K8s 配置 -->
        <template v-if="app.deploy_strategy === 'k8s'">
          <el-form-item label="K8s 集群">
            <el-select v-model="envForm.k8s_cluster_id" placeholder="选择集群" style="width: 100%" filterable clearable>
              <el-option v-for="c in k8sClusters" :key="c.id" :label="c.name" :value="c.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="命名空间">
            <el-input v-model="envForm.k8s_namespace" placeholder="default" />
          </el-form-item>
          <el-form-item label="Deployment">
            <el-input v-model="envForm.k8s_deployment" placeholder="my-deployment" />
          </el-form-item>
          <el-form-item label="容器名">
            <el-input v-model="envForm.k8s_container_name" placeholder="my-container" />
          </el-form-item>
        </template>
      </el-form>

      <template #footer>
        <el-button @click="envDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveEnv" :loading="envSaving">保存</el-button>
      </template>
    </el-dialog>

    <!-- 部署确认弹窗 -->
    <el-dialog v-model="deployDialogVisible" title="确认部署" width="460px">
      <div v-if="deployingEnv" class="deploy-confirm">
        <p>应用：<strong>{{ app.name }}</strong></p>
        <p>环境：<strong>{{ deployingEnv.env_name }}</strong></p>
        <p v-if="deployingEnv.approval_required" class="deploy-warn">
          <el-icon><Warning /></el-icon>该环境需要审批，部署将进入待审批状态
        </p>
        <el-form label-width="80px" style="margin-top: 16px">
          <el-form-item label="版本号">
            <el-input v-model="deployVersion" placeholder="可选：commit hash / tag / 版本号" />
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="deployDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleDeploy" :loading="deploying">确认部署</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Warning } from '@element-plus/icons-vue'
import { getDeployApp, getAppEnvs, updateAppEnv, deleteAppEnv, executeDeploy } from '@/api/deploy'
import { getAssets } from '@/api/assets'
import { getDockerHosts, getClusters } from '@/api/containers'

const route = useRoute()
const router = useRouter()
const appId = ref(Number(route.params.id))
const activeTab = ref('overview')

// ── 应用数据 ──
const app = ref<any>({})
async function fetchApp() {
  const res: any = await getDeployApp(appId.value)
  app.value = res.data
}

// ── 环境配置 ──
const envLoading = ref(false)
const appEnvs = ref<any[]>([])
async function fetchEnvs() {
  envLoading.value = true
  try {
    const res: any = await getAppEnvs(appId.value)
    appEnvs.value = res.data
  } finally {
    envLoading.value = false
  }
}

// ── 下拉数据 ──
const assets = ref<any[]>([])
const dockerHosts = ref<any[]>([])
const k8sClusters = ref<any[]>([])

async function fetchDropdowns() {
  const [a, d, k] = await Promise.all([
    getAssets({ page_size: 200 }).catch(() => ({ data: { items: [] } })),
    getDockerHosts().catch(() => ({ data: [] })),
    getClusters().catch(() => ({ data: [] })),
  ])
  assets.value = (a as any).data?.items || []
  dockerHosts.value = (d as any).data || []
  k8sClusters.value = (k as any).data || []
}

// ── 环境配置弹窗 ──
const envDialogVisible = ref(false)
const editingEnv = ref<any>(null)
const envSaving = ref(false)
const envForm = reactive<any>({
  enabled: true,
  ssh_asset_id: null,
  deploy_path: '',
  deploy_script: '',
  docker_host_id: null,
  docker_image: '',
  docker_container_name: '',
  docker_ports: '',
  docker_env_vars: '',
  docker_network: '',
  docker_extra_args: '',
  k8s_cluster_id: null,
  k8s_namespace: 'default',
  k8s_deployment: '',
  k8s_container_name: '',
})

function openEnvDialog(ae: any) {
  editingEnv.value = ae
  Object.assign(envForm, {
    enabled: ae.enabled,
    ssh_asset_id: ae.ssh_asset_id,
    deploy_path: ae.deploy_path,
    deploy_script: ae.deploy_script,
    docker_host_id: ae.docker_host_id,
    docker_image: ae.docker_image,
    docker_container_name: ae.docker_container_name,
    docker_ports: ae.docker_ports,
    docker_env_vars: ae.docker_env_vars,
    docker_network: ae.docker_network,
    docker_extra_args: ae.docker_extra_args,
    k8s_cluster_id: ae.k8s_cluster_id,
    k8s_namespace: ae.k8s_namespace,
    k8s_deployment: ae.k8s_deployment,
    k8s_container_name: ae.k8s_container_name,
  })
  envDialogVisible.value = true
}

async function handleSaveEnv() {
  envSaving.value = true
  try {
    await updateAppEnv(appId.value, editingEnv.value.env_id, { ...envForm })
    ElMessage.success('保存成功')
    envDialogVisible.value = false
    fetchEnvs()
  } finally {
    envSaving.value = false
  }
}

async function handleRemoveEnv(envId: number) {
  await deleteAppEnv(appId.value, envId)
  ElMessage.success('已移除')
  fetchEnvs()
}

// ── 部署弹窗 ──
const deployDialogVisible = ref(false)
const deployingEnv = ref<any>(null)
const deployVersion = ref('')
const deploying = ref(false)

function openDeployDialog(ae: any) {
  deployingEnv.value = ae
  deployVersion.value = ''
  deployDialogVisible.value = true
}

async function handleDeploy() {
  deploying.value = true
  try {
    const res: any = await executeDeploy({
      app_id: appId.value,
      env_id: deployingEnv.value.env_id,
      version: deployVersion.value,
    })
    ElMessage.success('部署已触发')
    deployDialogVisible.value = false
    // 跳转到部署详情页（Step 6 实现后改为跳转详情）
    router.push('/deploy/apps')
  } finally {
    deploying.value = false
  }
}

// ── 辅助 ──
const typeLabel = (v: string) => ({ web: 'Web 应用', api: 'API 服务', worker: '后台任务', frontend: '前端项目', other: '其他' }[v] || v)
const strategyLabel = (v: string) => ({ ssh: 'SSH', docker: 'Docker', k8s: 'Kubernetes' }[v] || v)
const strategyType = (v: string) => ({ ssh: '', docker: 'warning', k8s: 'danger' }[v] || '') as any

function formatTime(iso: string) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('zh-CN')
}

// ── 初始化 ──
onMounted(() => {
  appId.value = Number(route.params.id)
  fetchApp()
  fetchEnvs()
  fetchDropdowns()
})

watch(() => route.params.id, (newId) => {
  if (newId) {
    appId.value = Number(newId)
    fetchApp()
    fetchEnvs()
  }
})
</script>

<style scoped>
.header-actions {
  display: flex;
  gap: 8px;
}

.detail-tabs {
  margin-top: 4px;
}

.env-card {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  margin-bottom: 16px;
  overflow: hidden;
}

.env-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  background: color-mix(in srgb, var(--primary-color) 4%, transparent);
  border-bottom: 1px solid var(--border-color);
}

.env-card-title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.env-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.env-card-body {
  padding: 16px 20px;
}

.env-field {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 8px;
  line-height: 1.6;
}

.env-field:last-child {
  margin-bottom: 0;
}

.env-field-label {
  color: var(--text-muted);
  margin-right: 4px;
}

.env-field code {
  background: var(--bg-color);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
  color: var(--text-primary);
  word-break: break-all;
}

.deploy-confirm p {
  margin-bottom: 8px;
  font-size: 14px;
  color: var(--text-secondary);
}

.deploy-warn {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--warning-color);
  font-size: 13px;
}
</style>
