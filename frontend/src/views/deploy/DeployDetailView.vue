<template>
  <div>
    <!-- 页面头部 -->
    <div class="page-header">
      <div style="display: flex; align-items: center; gap: 12px;">
        <el-button text @click="$router.push('/deploy/records')"><el-icon><ArrowLeft /></el-icon> 返回</el-button>
        <h2 class="page-title">发布详情 #{{ record.id }}</h2>
        <el-tag :type="statusType(record.status)" size="small">{{ statusLabel(record.status) }}</el-tag>
      </div>
      <div style="display: flex; gap: 8px;">
        <el-button v-if="['failed', 'rejected', 'pending'].includes(record.status)" type="warning" size="small" @click="handleRetry">重试</el-button>
        <el-button v-if="record.status === 'success' || record.status === 'failed'" type="warning" size="small" @click="handleRollback">回滚</el-button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="16" class="stat-row">
      <el-col :span="6"><div class="stat-card"><div class="stat-value">{{ record.application_name || '-' }}</div><div class="stat-label">应用</div></div></el-col>
      <el-col :span="6"><div class="stat-card"><div class="stat-value">{{ record.environment_display_name || record.environment_name || '-' }}</div><div class="stat-label">环境</div></div></el-col>
      <el-col :span="6"><div class="stat-card"><div class="stat-value">{{ record.version || record.image || '-' }}</div><div class="stat-label">版本</div></div></el-col>
      <el-col :span="6"><div class="stat-card"><div class="stat-value">{{ record.duration_seconds ? record.duration_seconds + 's' : '-' }}</div><div class="stat-label">耗时</div></div></el-col>
    </el-row>

    <!-- Tab 内容 -->
    <div class="data-card">
      <el-tabs v-model="activeTab">
        <!-- 概览 -->
        <el-tab-pane label="概览" name="info">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="发布方式">{{ record.deploy_method }}</el-descriptions-item>
            <el-descriptions-item label="触发方式">{{ record.trigger_type }}</el-descriptions-item>
            <el-descriptions-item label="发起人">{{ record.creator_name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="Jenkins 构建号">
              <a v-if="record.jenkins_build_url" :href="record.jenkins_build_url" target="_blank">#{{ record.jenkins_build_number }}</a>
              <span v-else>{{ record.jenkins_build_number || '-' }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="创建时间">{{ formatTime(record.created_at) }}</el-descriptions-item>
            <el-descriptions-item label="开始时间">{{ formatTime(record.started_at) }}</el-descriptions-item>
            <el-descriptions-item label="完成时间">{{ formatTime(record.finished_at) }}</el-descriptions-item>
            <el-descriptions-item label="回滚来源">
              <el-button v-if="record.rollback_from" text type="primary" @click="$router.push(`/deploy/records/${record.rollback_from}`)">#{{ record.rollback_from }}</el-button>
              <span v-else>-</span>
            </el-descriptions-item>
          </el-descriptions>
        </el-tab-pane>

        <!-- 日志 -->
        <el-tab-pane label="日志" name="logs">
          <div class="log-toolbar" v-if="record.status === 'building'">
            <el-button size="small" @click="fetchLogs" :loading="logLoading">刷新日志</el-button>
            <span style="font-size: 12px; color: var(--text-muted);">构建中，可手动刷新查看最新日志</span>
          </div>
          <pre class="log-content"><code>{{ logText || '暂无日志' }}</code></pre>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onActivated } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getDeployRecord, getDeployLogs, retryDeployment, rollbackDeployment } from '@/api/deploy'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()
const activeTab = ref('info')
const record = ref<any>({})
const logText = ref('')
const logLoading = ref(false)

const statusType = (s: string) => ({ success: 'success', failed: 'danger', building: 'warning', deploying: 'warning', pending: 'info', rejected: 'danger', rolled_back: 'info' }[s] || 'info') as any
const statusLabel = (s: string) => ({ success: '成功', failed: '失败', building: '构建中', deploying: '部署中', pending: '待执行', rejected: '已驳回', rolled_back: '已回滚' }[s] || s)
const formatTime = (t: string) => t ? new Date(t).toLocaleString('zh-CN') : '-'

async function fetchData() {
  const id = Number(route.params.id)
  if (!id) return
  const res: any = await getDeployRecord(id)
  record.value = res.data
  await fetchLogs()
}

async function fetchLogs() {
  const id = Number(route.params.id)
  logLoading.value = true
  try {
    const res: any = await getDeployLogs(id)
    logText.value = res.data?.text || ''
  } finally { logLoading.value = false }
}

async function handleRetry() {
  await retryDeployment(Number(route.params.id))
  ElMessage.success('重试已触发')
  fetchData()
}

async function handleRollback() {
  await rollbackDeployment(Number(route.params.id))
  ElMessage.success('回滚记录已创建')
  fetchData()
}

// keep-alive 下 onMounted 只触发一次，用 onActivated 每次进入都刷新
onActivated(fetchData)
</script>

<style scoped>
.stat-row { margin-bottom: 16px; }
.stat-card { background: var(--surface-color); border: 1px solid var(--border-color); border-radius: 8px; padding: 16px; text-align: center; }
.stat-value { font-size: 20px; font-weight: 700; color: var(--text-primary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.stat-label { font-size: 13px; color: var(--text-muted); margin-top: 4px; }
.data-card { background: var(--surface-color); border: 1px solid var(--border-color); border-radius: 8px; padding: 16px; }
.log-toolbar { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.log-content { background: #1e1e1e; color: #d4d4d4; padding: 16px; border-radius: 6px; overflow: auto; max-height: 500px; font-size: 13px; line-height: 1.5; white-space: pre-wrap; word-break: break-all; }
</style>
