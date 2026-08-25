<template>
  <div>
    <div class="page-header">
      <h2 class="page-title">编辑应用</h2>
      <el-button @click="$router.back()">返回</el-button>
    </div>

    <div v-loading="loading" class="data-card">
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="120px"
        style="max-width: 720px"
      >
        <div class="form-section-title">基本信息</div>
        <el-form-item label="应用名称" prop="name">
          <el-input v-model="form.name" maxlength="100" show-word-limit />
        </el-form-item>
        <el-form-item label="应用类型" prop="app_type">
          <el-select v-model="form.app_type" style="width: 100%">
            <el-option label="Web 应用" value="web" />
            <el-option label="API 服务" value="api" />
            <el-option label="后台任务" value="worker" />
            <el-option label="前端项目" value="frontend" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
        <el-form-item label="Jenkins Job" prop="jenkins_job_name">
          <el-input v-model="form.jenkins_job_name" placeholder="Jenkins Job 名称（执行构建与部署）" />
          <el-text type="info" size="small" class="release-mode-tip">
            Job 需声明参数：APP_NAME / ENV / VERSION / OPERATOR / RECORD_ID / RELEASE_MODE / ROLLBACK_FROM / CALLBACK_TOKEN。
          </el-text>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="form.status" style="width: 100%">
            <el-option label="活跃" value="active" />
            <el-option label="已归档" value="archived" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" />
        </el-form-item>

        <div class="form-section-title">Git 配置</div>
        <el-form-item label="Git 仓库地址">
          <el-input v-model="form.git_url" />
        </el-form-item>
        <el-form-item label="默认分支">
          <el-input v-model="form.git_branch" />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="handleSubmit" :loading="submitting">保存</el-button>
          <el-button @click="$router.back()">取消</el-button>
        </el-form-item>
      </el-form>

      <!-- 环境配置：独立于应用表单，操作即保存 -->
      <div class="form-section-title">环境配置</div>
      <p class="env-hint">将全局环境绑定到本应用后，即可在应用详情页对该环境发起部署；「停用」保留绑定但不可部署，「移除」解除绑定。</p>
      <div v-loading="envsLoading" class="env-list">
        <div v-for="env in allEnvs" :key="env.id" class="env-row">
          <div class="env-info">
            <span class="env-title">{{ env.display_name || env.name }}</span>
            <span class="env-key mono muted">{{ env.name }}</span>
            <span v-if="env.approval_required" class="approval-tag">需审批</span>
          </div>
          <span class="env-desc muted">{{ env.description || '' }}</span>
          <span class="sp"></span>
          <template v-if="boundOf(env)">
            <el-switch
              :model-value="boundOf(env)!.enabled"
              :disabled="!canUpdate"
              inline-prompt
              active-text="启用"
              inactive-text="停用"
              @change="(val: string | number | boolean) => toggleEnvEnabled(env, val === true)"
            />
            <el-button v-if="canUpdate" text type="danger" size="small" @click="removeEnv(env)">
              <el-icon><Delete /></el-icon><span>移除</span>
            </el-button>
          </template>
          <el-button v-else-if="canUpdate" size="small" @click="addEnv(env)">
            <el-icon><Plus /></el-icon><span>添加</span>
          </el-button>
          <span v-else class="muted">未绑定</span>
        </div>
        <el-empty v-if="!envsLoading && !allEnvs.length" description="暂无可用环境，请联系管理员在初始化数据中配置" :image-size="60" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, onActivated } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Plus, Delete } from '@element-plus/icons-vue'
import { getDeployApp, updateDeployApp, getDeployEnvs, getAppEnvs, updateAppEnv, deleteAppEnv } from '@/api/deploy'
import { useAuthStore } from '@/stores/modules/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const canUpdate = computed(() => authStore.hasPermission('deploy.update'))
const appName = ref(String(route.params.name))
const formRef = ref<FormInstance>()
const loading = ref(false)
const submitting = ref(false)

const form = reactive({
  name: '',
  description: '',
  app_type: 'web',
  status: 'active',
  git_url: '',
  git_branch: 'main',
  jenkins_job_name: '',
})

const rules: FormRules = {
  name: [
    { required: true, message: '请输入应用名称', trigger: 'blur' },
    { min: 2, max: 100, message: '长度 2-100 个字符', trigger: 'blur' },
  ],
  app_type: [{ required: true, message: '请选择应用类型', trigger: 'change' }],
}

async function fetchApp() {
  loading.value = true
  try {
    const res: any = await getDeployApp(appName.value)
    Object.assign(form, {
      name: res.data.name,
      description: res.data.description,
      app_type: res.data.app_type,
      status: res.data.status,
      git_url: res.data.git_url,
      git_branch: res.data.git_branch,
      jenkins_job_name: res.data.jenkins_job_name,
    })
  } finally {
    loading.value = false
  }
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    await updateDeployApp(appName.value, form)
    ElMessage.success('保存成功')
    router.push(`/deploy/apps/${appName.value}`)
  } finally {
    submitting.value = false
  }
}

onActivated(() => {
  fetchApp()
  fetchEnvs()
})
// keep-alive 下切换不同应用时重新加载
watch(() => route.params.name, (n, o) => {
  if (n && n !== o) {
    appName.value = String(n)
    fetchApp()
    fetchEnvs()
  }
})

// ── 环境配置 ──
const allEnvs = ref<any[]>([])
const appEnvs = ref<any[]>([])
const envsLoading = ref(false)

const boundOf = (env: any) => appEnvs.value.find((ae: any) => ae.env_id === env.id)

async function fetchEnvs() {
  envsLoading.value = true
  try {
    const [allRes, boundRes]: any[] = await Promise.all([getDeployEnvs(), getAppEnvs(appName.value)])
    allEnvs.value = (allRes.data || []).slice().sort((a: any, b: any) => (a.sort_order - b.sort_order) || (a.id - b.id))
    appEnvs.value = boundRes.data || []
  } finally {
    envsLoading.value = false
  }
}

async function addEnv(env: any) {
  await updateAppEnv(appName.value, env.id, { enabled: true })
  ElMessage.success(`已添加环境「${env.display_name || env.name}」`)
  await fetchEnvs()
}

async function toggleEnvEnabled(env: any, val: boolean) {
  const ae = boundOf(env)
  // 透传已有配置，避免 upsert 时用默认值覆盖 SSH / Docker / K8s 等字段
  await updateAppEnv(appName.value, env.id, { ...ae, enabled: val })
  ElMessage.success(val ? '已启用' : '已停用')
  await fetchEnvs()
}

async function removeEnv(env: any) {
  await ElMessageBox.confirm(
    `确定将环境「${env.display_name || env.name}」从本应用移除吗？历史部署记录不受影响。`,
    '移除环境',
    { type: 'warning', confirmButtonText: '移除', cancelButtonText: '取消' },
  )
  await deleteAppEnv(appName.value, env.id)
  ElMessage.success('已移除')
  await fetchEnvs()
}
</script>

<style scoped lang="scss">
.form-section-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 24px 0 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border-color);
}

.form-section-title:first-child {
  margin-top: 0;
}

.form-hint {
  margin-left: 12px;
  font-size: 12px;
  color: var(--text-muted);
}

/* ── 环境配置 ── */
.env-hint {
  font-size: 12.5px;
  color: var(--text-muted);
  margin: -6px 0 10px;
}

.env-list {
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: 4px 16px;
}

.env-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid var(--border-color);

  &:last-child { border-bottom: 0; }
}

.env-info {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  min-width: 0;
}

.env-title { font-weight: 650; }
.env-key { font-size: 11.5px; }

.env-desc {
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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
}

.mono { font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace; }
.muted { color: var(--text-muted); }
.sp { flex: 1; }
</style>
