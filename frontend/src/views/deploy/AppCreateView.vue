<template>
  <div>
    <div class="page-header">
      <h2 class="page-title">创建应用</h2>
      <el-button @click="$router.back()">返回</el-button>
    </div>

    <div class="data-card">
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="120px"
        style="max-width: 720px"
      >
        <!-- 基本信息 -->
        <div class="form-section-title">基本信息</div>
        <el-form-item label="应用名称" prop="name">
          <el-input v-model="form.name" placeholder="如：user-service" maxlength="100" show-word-limit />
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
        <el-form-item label="部署策略" prop="deploy_strategy">
          <el-radio-group v-model="form.deploy_strategy">
            <el-radio-button value="ssh">SSH</el-radio-button>
            <el-radio-button value="docker">Docker</el-radio-button>
            <el-radio-button value="k8s">Kubernetes</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="执行模式">
          <el-radio-group v-model="form.release_mode">
            <el-radio-button value="platform">平台执行</el-radio-button>
            <el-radio-button value="jenkins">Jenkins 执行</el-radio-button>
          </el-radio-group>
          <el-text v-if="form.release_mode === 'jenkins'" type="info" size="small" class="release-mode-tip">
            模式 B：平台负责权限/审批/记录，Jenkins Job 负责构建与部署，完成后回调平台更新状态。
          </el-text>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="应用用途说明" />
        </el-form-item>

        <!-- Git 配置 -->
        <div class="form-section-title">Git 配置</div>
        <el-form-item label="Git 仓库地址">
          <el-input v-model="form.git_url" placeholder="https://github.com/org/repo.git" />
        </el-form-item>
        <el-form-item label="默认分支">
          <el-input v-model="form.git_branch" placeholder="main" />
        </el-form-item>

        <!-- 构建配置 -->
        <div class="form-section-title">构建配置</div>
        <el-form-item label="构建模式" prop="build_mode">
          <el-radio-group v-model="form.build_mode">
            <el-radio-button value="upload">文件上传</el-radio-button>
            <el-radio-button value="webhook">Webhook</el-radio-button>
            <el-radio-button value="jenkins">Jenkins</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <!-- 文件上传模式 -->
        <template v-if="form.build_mode === 'upload'">
          <el-form-item label=" ">
            <el-text type="info" size="small">创建后可在应用详情页上传构建产物（jar / war / zip 等），部署时自动分发到目标服务器。</el-text>
          </el-form-item>
        </template>

        <!-- Webhook 模式 -->
        <template v-if="form.build_mode === 'webhook'">
          <el-form-item label=" ">
            <el-text type="info" size="small">
              通过 Webhook 接收 CI/CD 系统（Jenkins、GitHub Actions、GitLab CI 等）推送的构建产物。
              创建后可在应用详情页获取 Webhook URL 和密钥。
            </el-text>
          </el-form-item>
        </template>

        <!-- Jenkins 构建 -->
        <template v-if="form.build_mode === 'jenkins'">
          <el-form-item label="Job 名称">
            <el-input v-model="form.jenkins_job_name" placeholder="Jenkins Job 名称" />
          </el-form-item>
          <el-form-item v-if="form.release_mode !== 'jenkins'" label="Token">
            <el-input v-model="form.jenkins_token" placeholder="Jenkins 远程触发 Token（可选，未配则用全局账号凭据）" />
          </el-form-item>
        </template>

        <!-- Jenkins 执行模式（模式 B）：需要 Job 名 + 参数契约 -->
        <template v-if="form.release_mode === 'jenkins' && form.build_mode !== 'jenkins'">
          <el-form-item label="Job 名称">
            <el-input v-model="form.jenkins_job_name" placeholder="Jenkins Job 名称（执行构建与部署）" />
          </el-form-item>
          <el-form-item label=" ">
            <el-text type="warning" size="small">
              Job 需声明参数：APP_NAME / ENV / VERSION / OPERATOR / RECORD_ID / RELEASE_MODE / ROLLBACK_FROM / CALLBACK_TOKEN，
              构建结束回调平台（详见 docs/design/modeb-demo/Jenkinsfile 模板）。
            </el-text>
          </el-form-item>
        </template>

        <!-- 提交 -->
        <el-form-item>
          <el-button type="primary" @click="handleSubmit" :loading="submitting">创建应用</el-button>
          <el-button @click="$router.back()">取消</el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onActivated } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { createDeployApp } from '@/api/deploy'

const router = useRouter()
const formRef = ref<FormInstance>()
const submitting = ref(false)

const form = reactive({
  name: '',
  description: '',
  app_type: 'web',
  deploy_strategy: 'ssh',
  release_mode: 'platform',
  git_url: '',
  git_branch: 'main',
  build_mode: 'upload',
  build_command: '',
  artifact_path: '',
  jenkins_job_name: '',
  jenkins_token: '',
})

const rules: FormRules = {
  name: [
    { required: true, message: '请输入应用名称', trigger: 'blur' },
    { min: 2, max: 100, message: '长度 2-100 个字符', trigger: 'blur' },
  ],
  app_type: [{ required: true, message: '请选择应用类型', trigger: 'change' }],
  deploy_strategy: [{ required: true, message: '请选择部署策略', trigger: 'change' }],
  build_mode: [{ required: true, message: '请选择构建模式', trigger: 'change' }],
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    await createDeployApp(form)
    ElMessage.success('创建成功')
    router.push('/deploy/apps')
  } finally {
    submitting.value = false
  }
}

// keep-alive: 每次进入页面重置表单
onActivated(() => {
  Object.assign(form, {
    name: '',
    description: '',
    app_type: 'web',
    deploy_strategy: 'ssh',
    git_url: '',
    git_branch: 'main',
    build_mode: 'upload',
    build_command: '',
    artifact_path: '',
    jenkins_job_name: '',
    jenkins_token: '',
    health_check_url: '',
    health_check_timeout: 30,
  })
  formRef.value?.clearValidate()
})
</script>

<style scoped>
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

.release-mode-tip {
  display: block;
  margin-top: 4px;
}
</style>
