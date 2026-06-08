<template>
  <div>
    <div class="page-header">
      <h2 class="page-title">{{ app.name || '应用详情' }}</h2>
      <div class="header-actions">
        <el-button @click="$router.push(`/deploy/apps/${appName}/edit`)">编辑</el-button>
        <el-button type="danger" @click="handleDelete">删除</el-button>
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
            <el-descriptions-item label="构建模式">{{ app.build_mode === 'jenkins' ? 'Jenkins' : '文件上传' }}</el-descriptions-item>
            <el-descriptions-item label="构建命令/Job">{{ app.build_mode === 'jenkins' ? app.jenkins_job_name : (app.build_command || '—') }}</el-descriptions-item>
            <el-descriptions-item label="健康检查">
              <template v-if="app.health_check_url">{{ app.health_check_url }}</template>
              <span v-else>按环境配置</span>
            </el-descriptions-item>
            <el-descriptions-item label="创建人">{{ app.creator_name || '—' }}</el-descriptions-item>
            <el-descriptions-item label="创建时间">{{ formatTime(app.created_at) }}</el-descriptions-item>
          </el-descriptions>
        </div>
      </el-tab-pane>

      <!-- Tab 2: 环境管理 -->
      <el-tab-pane label="环境管理" name="envs">
        <div v-loading="envLoading">
          <div style="display: flex; justify-content: flex-end; margin-bottom: 16px">
            <el-button type="primary" size="small" @click="openAddEnvDialog">+ 添加环境</el-button>
          </div>
          <el-empty v-if="!envLoading && appEnvs.length === 0" description="暂无环境配置，点击上方按钮添加" />

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
                <div class="env-field"><span class="env-field-label">健康检查端口：</span>{{ ae.health_check_port || '不检测' }}</div>
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

              <!-- 构建产物（每个环境独立） -->
              <template v-if="app.build_mode !== 'jenkins'">
                <div class="env-artifact-divider"></div>
                <div class="env-artifact">
                  <div class="env-artifact-title">构建产物</div>
                  <div v-if="ae.artifact_filename" class="env-artifact-file">
                    <div class="env-artifact-info">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16" class="env-artifact-icon">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                        <polyline points="14 2 14 8 20 8" />
                      </svg>
                      <span class="env-artifact-name">{{ ae.artifact_filename }}</span>
                      <span class="env-artifact-meta">{{ formatSize(ae.artifact_size) }} · {{ formatTime(ae.artifact_uploaded_at) }}</span>
                    </div>
                    <div class="env-artifact-actions">
                      <el-button size="small" type="primary" text @click="handleDownloadArtifact(ae)">
                        <el-icon><Download /></el-icon>下载
                      </el-button>
                      <el-upload
                        :show-file-list="false"
                        :before-upload="(file: File) => handleUploadArtifact(ae.env_id, file)"
                        accept=".jar,.war,.zip,.tar,.tar.gz,.tgz,.gz,.rpm,.deb,.whl,.pyz"
                        :disabled="uploadingEnvId === ae.env_id"
                      >
                        <el-button size="small" text type="primary" :loading="uploadingEnvId === ae.env_id">重新上传</el-button>
                      </el-upload>
                      <el-popconfirm title="确认删除此环境的构建产物？" @confirm="handleDeleteArtifact(ae.env_id)">
                        <template #reference><el-button size="small" text type="danger">删除</el-button></template>
                      </el-popconfirm>
                    </div>
                  </div>
                  <div v-else class="env-artifact-empty">
                    <el-upload
                      :show-file-list="false"
                      :before-upload="(file: File) => handleUploadArtifact(ae.env_id, file)"
                      accept=".jar,.war,.zip,.tar,.tar.gz,.tgz,.gz,.rpm,.deb,.whl,.pyz"
                      :disabled="uploadingEnvId === ae.env_id"
                    >
                      <el-button size="small" type="primary" :loading="uploadingEnvId === ae.env_id">
                        <el-icon><UploadFilled /></el-icon>上传构建产物
                      </el-button>
                    </el-upload>
                    <span class="env-artifact-hint">部署前需先上传此环境的构建产物</span>
                  </div>
                </div>
              </template>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <!-- Tab 3: 部署历史 -->
      <el-tab-pane label="部署历史" name="history">
        <div class="data-card">
          <el-table :data="records" stripe v-loading="recordsLoading" @row-click="(row: any) => $router.push(`/deploy/records/${row.id}`)" row-class-name="clickable-row">
            <el-table-column prop="id" label="ID" width="70" />
            <el-table-column prop="env_name" label="环境" width="100">
              <template #default="{ row }"><el-tag size="small" effect="plain">{{ row.env_name || '—' }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="version" label="版本" width="130">
              <template #default="{ row }"><code class="version-text">{{ row.version || '—' }}</code></template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }"><el-tag :type="statusTypeMap[row.status]" size="small">{{ statusLabelMap[row.status] || row.status }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="trigger_user_name" label="触发人" width="90" />
            <el-table-column prop="duration" label="耗时" width="90">
              <template #default="{ row }">{{ row.duration != null ? formatDuration(row.duration) : '—' }}</template>
            </el-table-column>
            <el-table-column prop="created_at" label="时间" min-width="170">
              <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
            </el-table-column>
          </el-table>
          <el-empty v-if="!recordsLoading && records.length === 0" description="暂无部署记录" />
        </div>
      </el-tab-pane>

      <!-- Tab 4: 配置管理 -->
      <el-tab-pane label="配置管理" name="configs">
        <div class="data-card">
          <div style="display: flex; justify-content: space-between; margin-bottom: 16px">
            <span />
            <el-button type="primary" size="small" @click="openConfigDialog()">+ 新增配置</el-button>
          </div>
          <el-table :data="configs" stripe v-loading="configsLoading">
            <el-table-column prop="key" label="Key" min-width="160">
              <template #default="{ row }"><code class="config-key">{{ row.key }}</code></template>
            </el-table-column>
            <el-table-column prop="value" label="Value" min-width="200">
              <template #default="{ row }">
                <span v-if="row.is_encrypted" class="config-encrypted">******</span>
                <span v-else class="config-value">{{ row.value || '—' }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="env_name" label="环境" width="100">
              <template #default="{ row }"><el-tag size="small" effect="plain">{{ row.env_name || '全局' }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="is_encrypted" label="加密" width="70">
              <template #default="{ row }"><el-icon v-if="row.is_encrypted" style="color: var(--warning-color)"><Warning /></el-icon></template>
            </el-table-column>
            <el-table-column prop="description" label="说明" min-width="140" />
            <el-table-column label="操作" width="140">
              <template #default="{ row }">
                <el-button size="small" text type="primary" @click="openConfigDialog(row)">编辑</el-button>
                <el-popconfirm title="确认删除此配置项？" @confirm="handleDeleteConfig(row.id)">
                  <template #reference><el-button size="small" text type="danger">删除</el-button></template>
                </el-popconfirm>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="!configsLoading && configs.length === 0" description="暂无配置项" />
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 添加环境弹窗 -->
    <el-dialog v-model="addEnvDialogVisible" title="添加环境" width="420px">
      <el-form label-width="80px">
        <el-form-item label="选择环境">
          <el-select v-model="addEnvId" placeholder="请选择环境" style="width: 100%">
            <el-option
              v-for="e in availableEnvs"
              :key="e.id"
              :label="e.display_name || e.name"
              :value="e.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addEnvDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleAddEnv" :loading="addEnvLoading">确定</el-button>
      </template>
    </el-dialog>

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
          <el-form-item label="健康检查端口">
            <el-input-number v-model="envForm.health_check_port" :min="0" :max="65535" placeholder="如：8080" style="width: 200px" />
            <span class="form-hint">部署后检测目标端口是否可达，0 表示不检测</span>
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

    <!-- 配置新增/编辑弹窗 -->
    <el-dialog v-model="configDialogVisible" :title="editingConfigId ? '编辑配置' : '新增配置'" width="520px">
      <el-form :model="configForm" label-width="80px">
        <el-form-item label="Key">
          <el-input v-model="configForm.key" placeholder="DATABASE_URL" :disabled="!!editingConfigId" />
        </el-form-item>
        <el-form-item label="Value">
          <el-input v-model="configForm.value" :type="configForm.is_encrypted ? 'password' : 'text'" :placeholder="configForm.is_encrypted ? '敏感值将加密存储' : '配置值'" />
        </el-form-item>
        <el-form-item label="环境">
          <el-select v-model="configForm.env_id" placeholder="全局（所有环境）" clearable style="width: 100%">
            <el-option v-for="e in envList" :key="e.id" :label="e.name" :value="e.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="加密">
          <el-switch v-model="configForm.is_encrypted" />
          <span class="config-hint">加密字段存储后不回显明文</span>
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="configForm.description" placeholder="配置项说明" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="configDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveConfig" :loading="configSaving">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onActivated } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Warning, Download, UploadFilled } from '@element-plus/icons-vue'
import { getDeployApp, deleteDeployApp, getAppEnvs, updateAppEnv, deleteAppEnv, executeDeploy, getDeployRecords, getDeployEnvs, getAppConfigs, createAppConfig, updateAppConfig, deleteAppConfig, uploadArtifact, deleteArtifact } from '@/api/deploy'
import { getAssets } from '@/api/assets'
import { getDockerHosts, getClusters } from '@/api/containers'

const route = useRoute()
const router = useRouter()
const appName = ref(String(route.params.name))
const activeTab = ref('overview')

// ── 应用数据 ──
const app = ref<any>({})
async function fetchApp() {
  const res: any = await getDeployApp(appName.value)
  app.value = res.data
}

// ── 环境配置 ──
const envLoading = ref(false)
const appEnvs = ref<any[]>([])
async function fetchEnvs() {
  envLoading.value = true
  try {
    const res: any = await getAppEnvs(appName.value)
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

// ── 部署历史 ──
const recordsLoading = ref(false)
const records = ref<any[]>([])
const statusLabelMap: Record<string, string> = { pending: '待执行', building: '构建中', deploying: '部署中', success: '成功', failed: '失败', cancelled: '已取消' }
const statusTypeMap: Record<string, string> = { pending: 'info', building: 'warning', deploying: 'warning', success: 'success', failed: 'danger', cancelled: 'info' }

async function fetchRecords() {
  recordsLoading.value = true
  try {
    const res: any = await getDeployRecords({ app_name: appName.value, page_size: 50 })
    records.value = res.data.items
  } finally {
    recordsLoading.value = false
  }
}

// ── 配置管理 ──
const configsLoading = ref(false)
const configs = ref<any[]>([])
const envList = ref<any[]>([])
const configDialogVisible = ref(false)
const editingConfigId = ref<number | null>(null)
const configSaving = ref(false)
const configForm = reactive({
  key: '',
  value: '',
  env_id: null as number | null,
  is_encrypted: false,
  description: '',
})

async function fetchConfigs() {
  configsLoading.value = true
  try {
    const res: any = await getAppConfigs(appName.value)
    configs.value = res.data
  } finally {
    configsLoading.value = false
  }
}

async function fetchEnvList() {
  const res: any = await getDeployEnvs().catch(() => ({ data: [] }))
  envList.value = res.data || []
}

function openConfigDialog(row?: any) {
  editingConfigId.value = row?.id || null
  Object.assign(configForm, row ? {
    key: row.key,
    value: row.is_encrypted ? '' : row.value,
    env_id: row.env_id,
    is_encrypted: row.is_encrypted,
    description: row.description,
  } : { key: '', value: '', env_id: null, is_encrypted: false, description: '' })
  configDialogVisible.value = true
}

async function handleSaveConfig() {
  if (!configForm.key.trim()) {
    ElMessage.warning('请输入 Key')
    return
  }
  configSaving.value = true
  try {
    if (editingConfigId.value) {
      await updateAppConfig(editingConfigId.value, { ...configForm })
    } else {
      await createAppConfig(appName.value, { ...configForm })
    }
    ElMessage.success('保存成功')
    configDialogVisible.value = false
    fetchConfigs()
  } finally {
    configSaving.value = false
  }
}

async function handleDeleteConfig(id: number) {
  await deleteAppConfig(id)
  ElMessage.success('已删除')
  fetchConfigs()
}

// ── 添加环境弹窗 ──
const addEnvDialogVisible = ref(false)
const addEnvId = ref<number | null>(null)
const addEnvLoading = ref(false)

const availableEnvs = computed(() => {
  const existingIds = new Set(appEnvs.value.map((ae: any) => ae.env_id))
  return envList.value.filter((e: any) => !existingIds.has(e.id))
})

function openAddEnvDialog() {
  addEnvId.value = null
  addEnvDialogVisible.value = true
}

async function handleAddEnv() {
  if (!addEnvId.value) {
    ElMessage.warning('请选择环境')
    return
  }
  addEnvLoading.value = true
  try {
    await updateAppEnv(appName.value, addEnvId.value, { enabled: true })
    ElMessage.success('添加成功')
    addEnvDialogVisible.value = false
    fetchEnvs()
  } finally {
    addEnvLoading.value = false
  }
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
  health_check_port: 0,
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
    health_check_port: ae.health_check_port || 0,
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
    await updateAppEnv(appName.value, editingEnv.value.env_id, { ...envForm })
    ElMessage.success('保存成功')
    envDialogVisible.value = false
    fetchEnvs()
  } finally {
    envSaving.value = false
  }
}

async function handleDelete() {
  try {
    await ElMessageBox.confirm('确认删除此应用？删除后不可恢复。', '确认删除', { type: 'warning' })
  } catch {
    return
  }
  try {
    await deleteDeployApp(appName.value)
    ElMessage.success('删除成功')
    router.push('/deploy/apps')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '删除失败')
  }
}

async function handleRemoveEnv(envId: number) {
  await deleteAppEnv(appName.value, envId)
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
      app_name: appName.value,
      env_id: deployingEnv.value.env_id,
      version: deployVersion.value,
    })
    console.log('[deploy] API 返回:', res.data)
    ElMessage.success('部署已触发')
    deployDialogVisible.value = false
    // 跳转到部署详情页
    router.push(`/deploy/records/${res.data.id}`)
  } finally {
    deploying.value = false
  }
}

// ── 构建产物（环境级别） ──
const uploadingEnvId = ref<number | null>(null)

async function handleUploadArtifact(envId: number, file: File) {
  uploadingEnvId.value = envId
  try {
    await uploadArtifact(appName.value, envId, file)
    ElMessage.success('上传成功')
    fetchEnvs()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '上传失败')
  } finally {
    uploadingEnvId.value = null
  }
  return false // 阻止 el-upload 默认上传
}

async function handleDeleteArtifact(envId: number) {
  await deleteArtifact(appName.value, envId)
  ElMessage.success('已删除')
  fetchEnvs()
}

function handleDownloadArtifact(ae: any) {
  const token = localStorage.getItem('token')
  const url = `/api/v1/deploy/apps/${appName.value}/envs/${ae.env_id}/artifact/download`
  fetch(url, { headers: { Authorization: `Bearer ${token}` } })
    .then(res => res.blob())
    .then(blob => {
      const blobUrl = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = blobUrl
      a.download = ae.artifact_filename || 'artifact'
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(blobUrl)
    })
    .catch(() => ElMessage.error('下载失败'))
}

// ── 辅助 ──
const typeLabel = (v: string) => ({ web: 'Web 应用', api: 'API 服务', worker: '后台任务', frontend: '前端项目', other: '其他' }[v] || v)
const strategyLabel = (v: string) => ({ ssh: 'SSH', docker: 'Docker', k8s: 'Kubernetes' }[v] || v)
const strategyType = (v: string) => ({ ssh: '', docker: 'warning', k8s: 'danger' }[v] || '') as any

function formatTime(iso: string) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('zh-CN')
}

function formatSize(bytes: number) {
  if (!bytes) return '0 B'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`
}

function formatDuration(sec: number) {
  if (sec < 60) return `${Math.round(sec)}s`
  const m = Math.floor(sec / 60)
  const s = Math.round(sec % 60)
  return `${m}m ${s}s`
}

// ── 初始化（keep-alive: onActivated 每次进入都刷新） ──
onActivated(() => {
  appName.value = String(route.params.name)
  fetchApp()
  fetchEnvs()
  fetchDropdowns()
  fetchRecords()
  fetchConfigs()
  fetchEnvList()
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

.form-hint {
  margin-left: 8px;
  color: var(--text-muted);
  font-size: 12px;
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

.version-text {
  background: var(--bg-color);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
  color: var(--text-primary);
}

:deep(.clickable-row) {
  cursor: pointer;
}

.config-key {
  background: var(--bg-color);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
  font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
  color: var(--primary-color);
}

.config-value {
  font-size: 13px;
  color: var(--text-secondary);
  word-break: break-all;
}

.config-encrypted {
  font-size: 13px;
  color: var(--text-muted);
  letter-spacing: 2px;
}

.config-hint {
  margin-left: 10px;
  font-size: 12px;
  color: var(--text-muted);
}

/* 环境卡片内构建产物 */
.env-artifact-divider {
  margin: 12px 0;
  border-top: 1px dashed var(--border-color);
}

.env-artifact-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 10px;
}

.env-artifact-file {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.env-artifact-info {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.env-artifact-icon {
  color: var(--primary-color);
  flex-shrink: 0;
}

.env-artifact-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  word-break: break-all;
}

.env-artifact-meta {
  font-size: 12px;
  color: var(--text-muted);
  white-space: nowrap;
}

.env-artifact-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.env-artifact-empty {
  display: flex;
  align-items: center;
  gap: 12px;
}

.env-artifact-hint {
  font-size: 12px;
  color: var(--text-muted);
}
</style>
