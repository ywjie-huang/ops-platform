<template>
  <div>
    <div class="page-header"><h2 class="page-title">模型配置</h2></div>

    <div class="data-card" style="max-width: 640px">
      <el-form label-width="100px" v-loading="loading">
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
          <el-button type="primary" :loading="saving" @click="handleSave">保存配置</el-button>
          <el-button :loading="testing" @click="handleTest">测试连接</el-button>
          <el-tag v-if="testOk !== null" :type="testOk ? 'success' : 'danger'" style="margin-left: 8px">
            {{ testOk ? '连接成功' : '连接失败' }}
          </el-tag>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getSettings, updateSetting, testLLMConnection } from '@/api/settings'

const loading = ref(false)
const saving = ref(false)
const testing = ref(false)
const testOk = ref<boolean | null>(null)
const configs = reactive<Record<string, string>>({
  'llm.base_url': '',
  'llm.api_key': '',
  'llm.model': '',
})

async function fetchConfigs() {
  loading.value = true
  try {
    const res: any = await getSettings()
    for (const item of res.data.items) {
      if (item.key.startsWith('llm.')) {
        configs[item.key] = item.value
      }
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

async function handleTest() {
  const base_url = configs['llm.base_url']?.trim()
  const api_key = configs['llm.api_key']?.trim()
  const model = configs['llm.model']?.trim()
  if (!base_url || !api_key || !model) {
    ElMessage.warning('请填写完整的模型配置')
    return
  }
  testing.value = true
  testOk.value = null
  try {
    const res: any = await testLLMConnection({ base_url, api_key, model })
    testOk.value = res.data?.ok ?? false
    testOk.value ? ElMessage.success(res.msg) : ElMessage.warning(res.msg)
  } catch {
    testOk.value = false
  } finally { testing.value = false }
}

onMounted(fetchConfigs)
</script>

<style scoped>
.form-tip { font-size: 12px; color: #909399; line-height: 1.4; margin-top: 4px; }
</style>
