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

        <el-divider content-position="left">AI 模型</el-divider>

        <el-form-item label="API 地址">
          <el-input v-model="configs['llm.base_url']" placeholder="https://api.openai.com/v1" />
          <div class="form-tip">OpenAI 兼容 API 地址，支持 OpenAI / DeepSeek / Qwen / Ollama 等</div>
        </el-form-item>

        <el-form-item label="API Key">
          <el-input v-model="configs['llm.api_key']" placeholder="sk-xxx" show-password />
          <div class="form-tip">API 密钥</div>
        </el-form-item>

        <el-form-item label="模型名称">
          <el-input v-model="configs['llm.model']" placeholder="gpt-4o" />
          <div class="form-tip">模型标识，如 gpt-4o、deepseek-chat、qwen-plus</div>
        </el-form-item>

        <el-form-item>
          <el-button :loading="testing === 'llm'" @click="handleTestLLM">测试连接</el-button>
          <el-tag v-if="testResults['llm'] !== undefined" :type="testResults['llm'] ? 'success' : 'danger'" style="margin-left:8px">
            {{ testResults['llm'] ? '连接成功' : '连接失败' }}
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
import { getSettings, updateSetting, testConnection, testLLMConnection } from '@/api/settings'

const loading = ref(false)
const saving = ref(false)
const testing = ref('')
const configs = reactive<Record<string, string>>({})
const testResults = reactive<Record<string, boolean>>({})

async function fetchConfigs() {
  loading.value = true
  try {
    const res: any = await getSettings()
    for (const item of res.data.items) {
      configs[item.key] = item.value
    }
  } finally { loading.value = false }
}

async function handleSave() {
  saving.value = true
  try {
    for (const [key, value] of Object.entries(configs)) {
      await updateSetting(key, value)
    }
    ElMessage.success('配置保存成功')
  } finally { saving.value = false }
}

async function handleTestLLM() {
  testing.value = 'llm'
  testResults['llm'] = undefined
  const base_url = configs['llm.base_url']?.trim()
  const api_key = configs['llm.api_key']?.trim()
  const model = configs['llm.model']?.trim()
  if (!base_url || !api_key || !model) {
    ElMessage.warning('请填写完整的 LLM 配置')
    testing.value = ''
    return
  }
  try {
    const res: any = await testLLMConnection({ base_url, api_key, model })
    testResults['llm'] = res.data?.ok ?? false
    if (testResults['llm']) {
      ElMessage.success(res.msg)
    } else {
      ElMessage.warning(res.msg)
    }
  } catch {
    testResults['llm'] = false
  } finally { testing.value = '' }
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

onMounted(fetchConfigs)
</script>

<style scoped>
.form-tip { font-size: 12px; color: #909399; line-height: 1.4; margin-top: 4px; }
</style>
