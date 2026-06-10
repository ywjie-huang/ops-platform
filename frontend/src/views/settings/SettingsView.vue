<template>
  <div>
    <div class="page-header"><h2 class="page-title">配置中心</h2></div>

    <div class="data-card" style="max-width:640px">
      <el-form label-width="120px" v-loading="loading">
        <el-divider content-position="left">监控服务</el-divider>

        <el-form-item label="Prometheus">
          <el-input v-model="configs['prometheus.url']" placeholder="http://172.16.24.31:30001" />
          <div class="form-tip">Prometheus 服务地址，用于主机监控和告警规则拉取</div>
        </el-form-item>
        <el-form-item>
          <el-button :loading="testing === 'prometheus'" @click="handleTest('prometheus')">测试连接</el-button>
          <el-tag v-if="testResults['prometheus'] !== undefined" :type="testResults['prometheus'] ? 'success' : 'danger'" style="margin-left:8px">
            {{ testResults['prometheus'] ? '连接成功' : '连接失败' }}
          </el-tag>
        </el-form-item>

        <el-form-item label="Alertmanager">
          <el-input v-model="configs['alertmanager.url']" placeholder="http://172.16.24.31:30093" />
          <div class="form-tip">Alertmanager 服务地址，用于告警事件拉取</div>
        </el-form-item>
        <el-form-item>
          <el-button :loading="testing === 'alertmanager'" @click="handleTest('alertmanager')">测试连接</el-button>
          <el-tag v-if="testResults['alertmanager'] !== undefined" :type="testResults['alertmanager'] ? 'success' : 'danger'" style="margin-left:8px">
            {{ testResults['alertmanager'] ? '连接成功' : '连接失败' }}
          </el-tag>
        </el-form-item>

        <el-divider content-position="left">Jenkins</el-divider>

        <el-form-item label="Jenkins URL">
          <el-input v-model="jenkinsConfig.url" placeholder="http://jenkins.example.com" />
          <div class="form-tip">Jenkins 服务器地址，用于触发构建（如 Job 配置了 Authentication Token）</div>
        </el-form-item>
        <el-form-item label="用户名">
          <el-input v-model="jenkinsConfig.username" placeholder="admin" />
          <div class="form-tip">Jenkins API 用户名</div>
        </el-form-item>
        <el-form-item label="API Token">
          <el-input v-model="jenkinsConfig.token" type="password" show-password placeholder="Jenkins API Token" />
          <div class="form-tip">在 Jenkins → 用户设置 → API Token 中生成</div>
        </el-form-item>
        <el-form-item>
          <el-button :loading="testing === 'jenkins'" @click="handleTestJenkins">测试连接</el-button>
          <el-tag v-if="testResults['jenkins'] !== undefined" :type="testResults['jenkins'] ? 'success' : 'danger'" style="margin-left:8px">
            {{ testResults['jenkins'] ? '连接成功' : '连接失败' }}
          </el-tag>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="saving" @click="handleSave">保存配置</el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getSettings, updateSetting, testConnection } from '@/api/settings'

const loading = ref(false)
const saving = ref(false)
const testing = ref('')
const configs = reactive<Record<string, string>>({})
const testResults = reactive<Record<string, boolean | undefined>>({})
const jenkinsConfig = reactive({ url: '', username: '', token: '' })

async function fetchConfigs() {
  loading.value = true
  try {
    const res: any = await getSettings()
    for (const item of res.data.items) {
      configs[item.key] = item.value
    }
    // 解析 jenkins_config JSON
    try {
      const jc = JSON.parse(configs['jenkins_config'] || '{}')
      jenkinsConfig.url = jc.url || ''
      jenkinsConfig.username = jc.username || ''
      jenkinsConfig.token = jc.token || ''
    } catch { /* ignore */ }
  } finally { loading.value = false }
}

async function handleSave() {
  saving.value = true
  try {
    for (const [key, value] of Object.entries(configs)) {
      if (key === 'jenkins_config') continue // 单独处理
      await updateSetting(key, value)
    }
    // 保存 Jenkins 配置
    await updateSetting('jenkins_config', JSON.stringify({
      url: jenkinsConfig.url.trim(),
      username: jenkinsConfig.username.trim(),
      token: jenkinsConfig.token.trim(),
    }))
    configs['jenkins_config'] = JSON.stringify({ url: jenkinsConfig.url, username: jenkinsConfig.username, token: jenkinsConfig.token })
    ElMessage.success('配置保存成功')
  } finally { saving.value = false }
}

async function handleTest(service: string) {
  testing.value = service
  testResults[service] = undefined
  const urlKey = `${service}.url`
  const url = configs[urlKey]?.trim()
  if (!url) {
    ElMessage.warning('请先输入 URL')
    testing.value = ''
    return
  }
  try {
    const res: any = await testConnection(service, url)
    testResults[service] = res.data?.ok ?? false
    if (testResults[service]) {
      ElMessage.success(res.msg)
    } else {
      ElMessage.warning(res.msg)
    }
  } catch {
    testResults[service] = false
  } finally { testing.value = '' }
}

async function handleTestJenkins() {
  testing.value = 'jenkins'
  testResults['jenkins'] = undefined
  if (!jenkinsConfig.url.trim()) {
    ElMessage.warning('请先输入 Jenkins URL')
    testing.value = ''
    return
  }
  try {
    const res: any = await testConnection('jenkins', jenkinsConfig.url.trim(), {
      username: jenkinsConfig.username.trim(),
      token: jenkinsConfig.token.trim(),
    })
    testResults['jenkins'] = res.data?.ok ?? false
    if (testResults['jenkins']) {
      ElMessage.success(res.msg)
    } else {
      ElMessage.warning(res.msg)
    }
  } catch {
    testResults['jenkins'] = false
  } finally { testing.value = '' }
}

onMounted(fetchConfigs)
</script>

<style scoped>
.form-tip { font-size: 12px; color: #909399; line-height: 1.4; margin-top: 4px; }
</style>
