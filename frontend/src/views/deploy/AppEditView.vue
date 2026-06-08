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
        <el-form-item label="部署策略" prop="deploy_strategy">
          <el-radio-group v-model="form.deploy_strategy">
            <el-radio-button value="ssh">SSH</el-radio-button>
            <el-radio-button value="docker">Docker</el-radio-button>
            <el-radio-button value="k8s">Kubernetes</el-radio-button>
          </el-radio-group>
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

        <div class="form-section-title">构建配置</div>
        <el-form-item label="构建模式" prop="build_mode">
          <el-radio-group v-model="form.build_mode">
            <el-radio-button value="upload">文件上传</el-radio-button>
            <el-radio-button value="jenkins">Jenkins</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <template v-if="form.build_mode === 'upload'">
          <el-form-item label=" ">
            <el-text type="info" size="small">在应用详情页上传构建产物（jar / war / zip 等），部署时自动分发到目标服务器。</el-text>
          </el-form-item>
        </template>
        <template v-if="form.build_mode === 'jenkins'">
          <el-form-item label="Job 名称">
            <el-input v-model="form.jenkins_job_name" />
          </el-form-item>
          <el-form-item label="Token">
            <el-input v-model="form.jenkins_token" />
          </el-form-item>
        </template>

        <div class="form-section-title">健康检查</div>
        <el-form-item label="健康检查 URL">
          <el-input v-model="form.health_check_url" />
        </el-form-item>
        <el-form-item label="超时时间（秒）">
          <el-input-number v-model="form.health_check_timeout" :min="5" :max="300" :step="5" />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="handleSubmit" :loading="submitting">保存</el-button>
          <el-button @click="$router.back()">取消</el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { getDeployApp, updateDeployApp } from '@/api/deploy'

const route = useRoute()
const router = useRouter()
const appId = ref(Number(route.params.id))
const formRef = ref<FormInstance>()
const loading = ref(false)
const submitting = ref(false)

const form = reactive({
  name: '',
  description: '',
  app_type: 'web',
  deploy_strategy: 'ssh',
  status: 'active',
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

const rules: FormRules = {
  name: [
    { required: true, message: '请输入应用名称', trigger: 'blur' },
    { min: 2, max: 100, message: '长度 2-100 个字符', trigger: 'blur' },
  ],
  app_type: [{ required: true, message: '请选择应用类型', trigger: 'change' }],
  deploy_strategy: [{ required: true, message: '请选择部署策略', trigger: 'change' }],
  build_mode: [{ required: true, message: '请选择构建模式', trigger: 'change' }],
}

async function fetchApp() {
  loading.value = true
  try {
    const res: any = await getDeployApp(appId.value)
    Object.assign(form, {
      name: res.data.name,
      description: res.data.description,
      app_type: res.data.app_type,
      deploy_strategy: res.data.deploy_strategy,
      status: res.data.status,
      git_url: res.data.git_url,
      git_branch: res.data.git_branch,
      build_mode: res.data.build_mode,
      build_command: res.data.build_command,
      artifact_path: res.data.artifact_path,
      jenkins_job_name: res.data.jenkins_job_name,
      jenkins_token: res.data.jenkins_token,
      health_check_url: res.data.health_check_url,
      health_check_timeout: res.data.health_check_timeout,
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
    await updateDeployApp(appId.value, form)
    ElMessage.success('保存成功')
    router.push(`/deploy/apps/${appId.value}`)
  } finally {
    submitting.value = false
  }
}

onMounted(fetchApp)
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
</style>
