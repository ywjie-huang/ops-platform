<template>
  <div v-loading="loading">
    <!-- 面包屑 -->
    <nav class="crumb" aria-label="面包屑">
      <router-link to="/deploy/apps">应用管理</router-link>
      <span class="sep">/</span>
      <router-link :to="`/deploy/apps/${appName}`">{{ appName }}</router-link>
      <span class="sep">/</span>
      <span>编辑</span>
    </nav>

    <!-- 页头 -->
    <div class="page-header edit-head">
      <div class="head-left">
        <h2 class="page-title">编辑应用</h2>
        <span class="pill" :class="form.status === 'active' ? 'pill--success' : 'pill--info'">
          <i class="dot"></i>{{ form.status === 'active' ? '活跃' : '已归档' }}
        </span>
        <span class="type-tag">{{ appTypeLabel(form.app_type) }}</span>
      </div>
    </div>

    <AppBaseFormCards ref="baseFormRef" :form="form">
      <!-- 状态卡片（辅列顶部） -->
      <template #side-top>
        <section class="form-card">
          <header class="card-head">
            <span class="card-icon"><el-icon><SwitchButton /></el-icon></span>
            <div class="card-head-t">
              <h3 class="card-title">状态</h3>
              <p class="card-desc">控制应用是否可发起新的部署</p>
            </div>
          </header>
          <el-radio-group v-model="form.status" class="status-radios">
            <el-radio-button value="active">活跃</el-radio-button>
            <el-radio-button value="archived">已归档</el-radio-button>
          </el-radio-group>
          <p class="card-note">归档后应用从发布总览矩阵隐藏，且无法触发新部署；历史记录保留。</p>
        </section>
      </template>

      <!-- 环境配置卡片（主列，即时保存） -->
      <template #main-extra>
        <section class="form-card">
          <header class="card-head">
            <span class="card-icon"><el-icon><Grid /></el-icon></span>
            <div class="card-head-t">
              <h3 class="card-title">环境配置</h3>
              <p class="card-desc">绑定全局环境后即可在详情页对其发起部署；此区块操作即时保存</p>
            </div>
          </header>
          <div v-loading="envsLoading" class="env-list">
            <div v-for="env in allEnvs" :key="env.id" class="env-row">
              <span class="env-dot" :style="{ background: envColor(env.name) }"></span>
              <div class="env-info" :class="{ 'env-info--off': boundOf(env) && !boundOf(env)!.enabled }">
                <div class="env-line">
                  <span class="env-title">{{ env.display_name || env.name }}</span>
                  <span class="env-key mono muted">{{ env.name }}</span>
                  <span v-if="env.approval_required" class="approval-tag">需审批</span>
                </div>
                <div class="env-desc muted">{{ env.description || '—' }}</div>
              </div>
              <span class="pill" :class="envPillClass(env)"><i class="dot"></i>{{ envPillText(env) }}</span>
              <template v-if="boundOf(env)">
                <el-switch
                  :model-value="boundOf(env)!.enabled"
                  :disabled="!canUpdate"
                  inline-prompt
                  active-text="启用"
                  inactive-text="停用"
                  aria-label="启用或停用该环境"
                  @change="(val: string | number | boolean) => toggleEnvEnabled(env, val === true)"
                />
                <el-button v-if="canUpdate" text type="danger" size="small" @click="removeEnv(env)">
                  <el-icon><Delete /></el-icon><span>移除</span>
                </el-button>
              </template>
              <el-button v-else-if="canUpdate" size="small" @click="addEnv(env)">
                <el-icon><Plus /></el-icon><span>添加</span>
              </el-button>
            </div>
            <el-empty v-if="!envsLoading && !allEnvs.length" description="暂无可用环境，请联系管理员在初始化数据中配置" :image-size="60" />
          </div>
        </section>
      </template>

      <template #footer-hint>环境配置即时生效；此处按钮仅保存基本信息、构建配置与状态</template>
      <template #footer>
        <el-button @click="$router.back()">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          <el-icon><Check /></el-icon>保存
        </el-button>
      </template>
    </AppBaseFormCards>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, onActivated } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete, Check, SwitchButton, Grid } from '@element-plus/icons-vue'
import { getDeployApp, updateDeployApp, getDeployEnvs, getAppEnvs, updateAppEnv, deleteAppEnv } from '@/api/deploy'
import { useAuthStore } from '@/stores/modules/auth'
import { appTypeLabel } from '@/utils/appTypes'
import { envColor } from '@/utils/deployStatus'
import AppBaseFormCards from './components/AppBaseFormCards.vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const canUpdate = computed(() => authStore.hasPermission('deploy.update'))
const appName = ref(String(route.params.name))
const baseFormRef = ref<InstanceType<typeof AppBaseFormCards>>()
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
  const valid = await baseFormRef.value?.validate()?.catch(() => false)
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

function envPillClass(env: any) {
  const ae = boundOf(env)
  if (!ae) return 'pill--info'
  return ae.enabled ? 'pill--success' : 'pill--warning'
}

function envPillText(env: any) {
  const ae = boundOf(env)
  if (!ae) return '未绑定'
  return ae.enabled ? '已启用' : '已停用'
}

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
.crumb {
  font-size: 13px;
  color: var(--text-muted);
  margin-bottom: 10px;

  a { color: var(--text-secondary); transition: color .15s; }
  a:hover { color: var(--primary-color); }
  .sep { margin: 0 6px; }
}

.edit-head { margin-bottom: 14px; }

.head-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

/* ── 状态 pill ── */
.pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;

  .dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; flex: none; }

  &--success { color: #15803d; background: color-mix(in srgb, var(--success-color) 12%, transparent); }
  &--warning { color: #b45309; background: color-mix(in srgb, var(--warning-color) 14%, transparent); }
  &--info { color: var(--text-secondary); background: color-mix(in srgb, var(--text-muted) 14%, transparent); }
}

.type-tag {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 6px;
  font-size: 11.5px;
  font-weight: 600;
  color: var(--text-secondary);
  background: color-mix(in srgb, var(--text-muted) 12%, transparent);
}

.status-radios { width: 100%; }

/* ── 环境配置 ── */
.env-list { min-height: 48px; }

.env-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  padding: 12px 0;
  border-bottom: 1px solid var(--border-color);

  &:first-child { padding-top: 2px; }
  &:last-child { border-bottom: 0; padding-bottom: 2px; }
}

.env-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex: none;
}

.env-info {
  flex: 1 1 240px;
  min-width: 0;

  &--off { opacity: .6; }
}

.env-line {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.env-title { font-weight: 650; }
.env-key { font-size: 11.5px; }
.env-desc { font-size: 12px; margin-top: 2px; }

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
</style>
