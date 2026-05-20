<template>
  <div v-if="visible" class="login-overlay">
    <el-card shadow="hover" class="login-card">
      <template #header>
        <div class="login-header">
          <span>🖥️ SSH 登录</span>
          <el-tag :type="connected ? 'success' : 'info'" size="small">
            {{ connected ? '已连接' : '未连接' }}
          </el-tag>
        </div>
      </template>
      <el-form :model="loginForm" label-width="80px" @submit.prevent="handleConnect">
        <el-form-item label="主机">
          <el-input :model-value="`${hostIp}:${loginForm.port}`" disabled />
        </el-form-item>
        <el-form-item label="认证方式">
          <el-select v-model="loginForm.authMode" style="width:100%" @change="onAuthModeChange">
            <el-option label="使用资产自带凭据" value="asset" />
            <el-option v-for="key in sshKeys" :key="key.id"
              :label="`${key.auth_type === 'key' ? '🔑' : '🔒'} ${key.name} (${key.username})`"
              :value="`key-${key.id}`" />
          </el-select>
        </el-form-item>
        <el-form-item label="用户名">
          <el-input v-model="loginForm.username" placeholder="root" :disabled="loginForm.authMode !== 'asset'" />
        </el-form-item>
        <el-form-item v-if="loginForm.authMode === 'asset'" label="密码">
          <el-input v-model="loginForm.password" type="password" show-password placeholder="请输入 SSH 密码" @keyup.enter="handleConnect" />
        </el-form-item>
        <el-form-item v-else label="凭据">
          <span class="credential-hint">{{ selectedKeyHint }}</span>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleConnect" :loading="connecting" style="width:100%">
            {{ connecting ? '连接中…' : '连接' }}
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

const props = defineProps<{
  visible: boolean
  hostIp: string
  sshKeys: any[]
  connecting: boolean
  connected: boolean
}>()

const emit = defineEmits<{
  'update:visible': [val: boolean]
  connect: [formData: { username: string; password: string; port: number; authMode: string }]
}>()

const loginForm = ref({
  username: 'root',
  password: '',
  port: 22,
  authMode: 'asset',
})

const selectedKeyHint = computed(() => {
  if (loginForm.value.authMode === 'asset') return ''
  const keyId = Number(loginForm.value.authMode.replace('key-', ''))
  const key = props.sshKeys.find(k => k.id === keyId)
  if (!key) return '未知密钥'
  return key.auth_type === 'key'
    ? `私钥认证 · ${key.username} · 端口 ${key.port}`
    : `密码认证 · ${key.username} · 端口 ${key.port}`
})

function onAuthModeChange(val: string) {
  if (val === 'asset') return
  const keyId = Number(val.replace('key-', ''))
  const key = props.sshKeys.find(k => k.id === keyId)
  if (key) {
    loginForm.value.username = key.username
    loginForm.value.port = key.port
  }
}

function handleConnect() {
  emit('connect', { ...loginForm.value })
}

function setDefaults(username: string, port: number) {
  loginForm.value.username = username
  loginForm.value.port = port
}

function setAuthMode(mode: string) {
  loginForm.value.authMode = mode
}

function clearPassword() {
  loginForm.value.password = ''
}

defineExpose({ setDefaults, setAuthMode, clearPassword, loginForm })
</script>

<style lang="scss" scoped>
.login-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(26, 27, 38, 0.92);
  z-index: 10;
}
.login-card {
  width: 420px;
  background: #24283b;
  border: 1px solid #33467c;
  :deep(.el-card__header) { border-bottom: 1px solid #33467c; }
  :deep(.el-card__body) { padding: 20px 24px; }
}
.login-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: #c0caf5;
}
.credential-hint {
  font-size: 13px;
  color: #565f89;
}
</style>
