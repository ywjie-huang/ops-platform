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
        <el-form-item label="Jenkins Job" prop="jenkins_job_name">
          <el-input v-model="form.jenkins_job_name" placeholder="Jenkins Job 名称（执行构建与部署）" />
          <el-text type="info" size="small" class="release-mode-tip">
            Job 需声明参数：APP_NAME / ENV / VERSION / OPERATOR / RECORD_ID / RELEASE_MODE / ROLLBACK_FROM / CALLBACK_TOKEN，构建结束回调平台更新状态。
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
    git_url: '',
    git_branch: 'main',
    jenkins_job_name: '',
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
