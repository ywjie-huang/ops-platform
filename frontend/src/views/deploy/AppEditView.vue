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
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch, onActivated } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { getDeployApp, updateDeployApp } from '@/api/deploy'

const route = useRoute()
const router = useRouter()
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

onActivated(fetchApp)
// keep-alive 下切换不同应用时重新加载
watch(() => route.params.name, (n, o) => {
  if (n && n !== o) {
    appName.value = String(n)
    fetchApp()
  }
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
