<template>
  <div>
    <!-- 面包屑 -->
    <nav class="crumb" aria-label="面包屑">
      <router-link to="/deploy/apps">应用管理</router-link>
      <span class="sep">/</span>
      <span>创建应用</span>
    </nav>

    <!-- 页头 -->
    <div class="page-header create-head">
      <div class="head-left">
        <h2 class="page-title">创建应用</h2>
        <span class="head-sub">应用 = 一个可发布单元，绑定一个 Jenkins Job 执行构建与部署</span>
      </div>
    </div>

    <AppBaseFormCards ref="baseFormRef" :form="form">
      <template #footer-hint>
        <span v-if="isDirty" class="dirty-note"><i class="dirty-dot"></i>有未保存的修改</span>
        <span v-else>创建后可进入「编辑应用」绑定部署环境</span>
      </template>
      <template #footer>
        <el-button @click="$router.back()">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          <el-icon><Plus /></el-icon>创建应用
        </el-button>
      </template>
    </AppBaseFormCards>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onActivated } from 'vue'
import { useRouter, onBeforeRouteLeave } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { createDeployApp } from '@/api/deploy'
import AppBaseFormCards from './components/AppBaseFormCards.vue'

const router = useRouter()
const baseFormRef = ref<InstanceType<typeof AppBaseFormCards>>()
const submitting = ref(false)

const DEFAULT_FORM = {
  name: '',
  description: '',
  app_type: 'web',
  git_url: '',
  git_branch: 'main',
  jenkins_job_name: '',
}

const form = reactive({ ...DEFAULT_FORM })

// ── 脏状态检测：与默认表单对比 ──
const DEFAULT_SNAPSHOT = JSON.stringify(DEFAULT_FORM)
const isDirty = computed(() => JSON.stringify(form) !== DEFAULT_SNAPSHOT)
let skipGuard = false

onBeforeRouteLeave(async () => {
  if (skipGuard || !isDirty.value) return true
  try {
    await ElMessageBox.confirm('当前页面有未填写完成的内容，离开后内容将丢失。确定离开吗？', '未保存的内容', {
      type: 'warning',
      confirmButtonText: '离开',
      cancelButtonText: '继续填写',
    })
    return true
  } catch {
    return false
  }
})

async function handleSubmit() {
  const valid = await baseFormRef.value?.validate()?.catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    await createDeployApp(form)
    skipGuard = true
    ElMessage.success('创建成功')
    router.push('/deploy/apps')
  } finally {
    submitting.value = false
  }
}

// keep-alive: 每次进入页面重置表单
onActivated(() => {
  Object.assign(form, DEFAULT_FORM)
  baseFormRef.value?.clearValidate()
})
</script>

<style scoped lang="scss">
.crumb {
  font-size: 13px;
  color: var(--text-muted);
  margin-bottom: 10px;

  a { color: var(--text-secondary); transition: color .15s; }
  a:hover { color: var(--primary-color); }
  .sep { margin: 0 6px; }
}

.create-head { margin-bottom: 14px; }

.head-left {
  display: flex;
  align-items: baseline;
  gap: 12px;
  flex-wrap: wrap;
}

.head-sub {
  font-size: 13px;
  color: var(--text-muted);
}
</style>
