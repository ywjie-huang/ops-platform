<template>
  <div v-if="visible" class="login-overlay">
    <el-card shadow="hover" class="login-card">
      <template #header>
        <div class="login-header">
          <div>
            <strong>打开 SSH 会话</strong>
            <div class="login-subtitle">{{ hostIp }}</div>
          </div>
          <el-tag :type="connected ? 'success' : 'info'" size="small">
            {{ connected ? '已连接' : '未连接' }}
          </el-tag>
        </div>
      </template>

      <el-form :model="loginForm" label-width="84px" @submit.prevent="handleConnect">
        <el-form-item label="主机">
          <el-input :model-value="`${hostIp}:${loginForm.port}`" disabled />
        </el-form-item>
        <el-form-item label="认证方式">
          <el-select v-model="loginForm.authMode" class="auth-select" @change="onAuthModeChange">
            <el-option label="使用资产凭据" value="asset" />
            <el-option
              v-for="key in sshKeys"
              :key="key.id"
              :label="`${key.auth_type === 'key' ? '私钥' : '密码'} · ${key.name} (${key.username})`"
              :value="`key-${key.id}`"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="用户名">
          <el-input v-model="loginForm.username" placeholder="root" :disabled="loginForm.authMode !== 'asset'" />
        </el-form-item>
        <el-form-item v-if="loginForm.authMode === 'asset'" label="密码">
          <el-input
            v-model="loginForm.password"
            type="password"
            show-password
            placeholder="请输入 SSH 密码"
            @keyup.enter="handleConnect"
          />
        </el-form-item>
        <el-form-item v-else label="凭据">
          <span class="credential-hint">{{ selectedKeyHint }}</span>
        </el-form-item>
        <el-form-item>
          <el-button class="connect-button" type="primary" :loading="connecting" @click="handleConnect">
            {{ connecting ? '连接中' : '连接' }}
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

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
  const key = props.sshKeys.find((item) => item.id === keyId)
  if (!key) return '未知密钥'
  return key.auth_type === 'key'
    ? `私钥认证 · ${key.username} · 端口 ${key.port}`
    : `密码认证 · ${key.username} · 端口 ${key.port}`
})

function onAuthModeChange(val: string) {
  if (val === 'asset') return
  const keyId = Number(val.replace('key-', ''))
  const key = props.sshKeys.find((item) => item.id === keyId)
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
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background: rgba(8, 11, 15, 0.72);
  backdrop-filter: blur(2px);
}

.login-card {
  width: min(400px, calc(100% - 32px));
  background: var(--ssh-panel, #0f141b);
  border: 1px solid var(--ssh-border-strong, #2a3544);
  border-radius: 0;
  box-shadow: none;

  :deep(.el-card__header) {
    border-bottom: 1px solid var(--ssh-border, #1c2430);
    padding: 16px 20px 12px;
  }

  :deep(.el-card__body) {
    padding: 16px 20px 18px;
  }

  :deep(.el-form-item__label) {
    color: var(--ssh-muted, #6b7785);
  }

  :deep(.el-input__wrapper),
  :deep(.el-select__wrapper) {
    background: var(--ssh-bg, #0b0f14);
    border: 1px solid var(--ssh-border-strong, #2a3544);
    border-radius: 0;
    box-shadow: none;
  }

  :deep(.el-input__inner),
  :deep(.el-select__placeholder),
  :deep(.el-select__selected-item) {
    color: var(--ssh-text, #d8dee9);
  }
}

.login-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: var(--ssh-text, #d8dee9);
}

.login-subtitle {
  margin-top: 2px;
  color: var(--ssh-muted, #6b7785);
  font-family: var(--ssh-font-mono, ui-monospace, monospace);
  font-size: 12px;
}

.auth-select,
.connect-button {
  width: 100%;
}

.credential-hint {
  color: var(--ssh-muted, #6b7785);
  font-size: 13px;
}
</style>
