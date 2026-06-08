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
            <el-radio-button value="jenkins">Jenkins</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <!-- 文件上传模式 -->
        <template v-if="form.build_mode === 'upload'">
          <el-form-item label=" ">
            <el-text type="info" size="small">创建后可在应用详情页上传构建产物（jar / war / zip 等），部署时自动分发到目标服务器。</el-text>
          </el-form-item>
        </template>

        <!-- Jenkins 构建 -->
        <template v-if="form.build_mode === 'jenkins'">
          <el-form-item label="Job 名称">
            <el-input v-model="form.jenkins_job_name" placeholder="Jenkins Job 名称" />
          </el-form-item>
          <el-form-item label="Token">
            <el-input v-model="form.jenkins_token" placeholder="Jenkins 触发 Token" />
          </el-form-item>
        </template>

        <!-- 健康检查 -->
        <div class="form-section-title">健康检查</div>
        <el-form-item label="检测端口">
          <el-input-number v-model="form.health_check_port" :min="0" :max="65535" placeholder="如：8080" style="width: 200px" />
          <span class="form-hint">部署后检测目标端口是否可达，0 表示不检测</span>
        </el-form-item>
        <el-form-item label="超时时间（秒）">
          <el-input-number v-model="form.health_check_timeout" :min="5" :max="300" :step="5" />
        </el-form-item>

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
  git_url: '',
  git_branch: 'main',
  build_mode: 'upload',
  build_command: '',
  artifact_path: '',
  jenkins_job_name: '',
  jenkins_token: '',
  health_check_url: '',
  health_check_port: 0,
  health_check_timeout: 30,
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
</style>
